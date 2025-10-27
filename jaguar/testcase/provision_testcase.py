# jaguar/testcase/provision_testcase.py

#   "lte_sim_iccid_invalid": 3120,
#   "lte_aws_ca_cert_transfer_unsuccessful": 3121,
#   "lte_device_cert_transfer_unsuccessful": 3122,
#   "lte_device_key_transfer_unsuccessful": 3123,
#   "aws_device_register_failure": 3124,
#   "aws_policy_retrieval_failed": 3125,
#   "aws_policy_attachment_failed": 3126,
#   "aws_ca_cert_download_failed": 3127,
#   "aws_failed_ca_requirements": 3128

import time
from pathlib import Path
import subprocess
import json
import os
import socket
import re
import traceback
import logging
import contextlib

from scripts import ascii_message
from statistics import mean  # kept if used elsewhere
from rogers_api import jasper

from .jaguar_testcase import JaguarTestCase
from birch.peripheral.lte_module import UBloxSara

# -----------------------------------------------------------------------------
# Readable, consistent, context-rich logging utilities
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # set to DEBUG during bring-up for more detail


class _ReadableLogMixin:
    """
    Mixin for consistent, readable, context-rich logs that print to console and
    (if present) forward to self.event_logger. Output is human-friendly with key=value context.
    """

    LOG_TRUNC = 600  # Max chars to show from stdout/stderr for shell commands

    def _fmt(self, msg: str, **fields) -> str:
        kv = " ".join(f"{k}={repr(v)}" for k, v in fields.items() if v is not None)
        cls = getattr(self, "__class__", type("X", (), {})).__name__
        return f"[{cls}] {msg}" + (f" | {kv}" if kv else "")

    def _emit(self, level: str, text: str):
        # Console
        print(text)
        # Python logger
        getattr(logger, level, logger.info)(text)
        # Event logger (if present)
        try:
            if hasattr(self, "event_logger") and self.event_logger:
                getattr(self.event_logger, level, self.event_logger.info)(text)
        except Exception:
            pass  # never let logging crash the test

    def _debug(self, msg: str, **fields): self._emit("debug", self._fmt(msg, **fields))
    def _info(self, msg: str, **fields):  self._emit("info",  self._fmt(msg, **fields))
    def _warn(self, msg: str, **fields):  self._emit("warning", self._fmt(msg, **fields))
    def _error(self, msg: str, **fields): self._emit("error", self._fmt(msg, **fields))

    @contextlib.contextmanager
    def _step(self, name: str, **ctx):
        start = time.time()
        self._info(f"▶ {name} – begin", **ctx)
        try:
            yield
        except Exception as e:
            dur = round(time.time() - start, 3)
            self._error(f"✖ {name} – failed", duration_s=dur, err_type=type(e).__name__, err=str(e))
            raise
        else:
            dur = round(time.time() - start, 3)
            self._info(f"✔ {name} – done", duration_s=dur)

    def _run_cmd(self, cmd: str, *, name: str | None = None, timeout: int | None = None) -> str:
        """
        Run a shell command with clear logs (command, duration, rc, truncated stdout/stderr).
        Raises on nonzero exit (like check_output). Returns stdout text.
        """
        step_name = name or "Run command"
        with self._step(step_name, cmd=cmd):
            t0 = time.time()
            try:
                res = subprocess.run(
                    cmd, shell=True, text=True,
                    capture_output=True, timeout=timeout, check=True
                )
                dur = round(time.time() - t0, 3)
                out = (res.stdout or "").strip()
                err = (res.stderr or "").strip()
                self._info("Command OK", rc=res.returncode, secs=dur,
                           stdout=out[:self.LOG_TRUNC] or None,
                           stderr=err[:self.LOG_TRUNC] or None)
                return out
            except subprocess.CalledProcessError as e:
                dur = round(time.time() - t0, 3)
                out = (e.stdout or "").strip()
                err = (e.stderr or "").strip()
                self._error("Command FAILED", rc=e.returncode, secs=dur,
                            stdout=out[:self.LOG_TRUNC] or None,
                            stderr=err[:self.LOG_TRUNC] or None)
                raise


# Valid AWS IoT Thing name pattern
THING_NAME_RE = re.compile(r'^[A-Za-z0-9:_-]+$')


class ProvisionTestCase(_ReadableLogMixin, JaguarTestCase):
    """
    Super class of test cases that use STLink and microUSB to assign certificates
    to device and activate SIM.
    """

    STANDARD_SUBJECT = "/C=CA/ST=ONT/L=Mississauga/O=ROMET LIMITED/CN=rometlimited.com"
    DEFAULT_CA_CERT_VALIDITY = 1278

    def __init__(
        self,
        detect_time=30,
        rootCA="rootCA",
        days=127,
        erase=False,
        flash=False,
        firmware_list=[],
        provision_enable=True,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.detect_time = detect_time
        self.rootCA = rootCA
        self.days = days
        self.eraseBool = erase
        self.flashBool = flash
        self.firmware_list = firmware_list
        self.provision_enable = provision_enable
        self.internet_connection = False
        self.sara = None

        self.PATH_TO_CONFIG = Path(self.config.active_dir) / Path(self.job._id)
        self.PATH_TO_CERTS = self.PATH_TO_CONFIG / "certificates"
        self.AWS_AUTH_CA_NAME = self.PATH_TO_CERTS / "legacy.pem"
        self.DEVICE_CA_NAME = self.PATH_TO_CERTS / self.rootCA
        self.VERIFICATION_NAME = self.PATH_TO_CERTS / "verificationCert"
        self.DEVICE_NAME = self.PATH_TO_CERTS / "deviceCert"
        self.ROMET_STD_IOT_POLICY = "std_romet_iot_policy"
        self.ROMET_STD_IOT_POLICY_FILE = self.PATH_TO_CERTS / "romet_standard_iot_policy.json"

        if self.provision_enable:
            self.append_step("Check for Internet Connection", self.internet)
            if self.eraseBool:
                self.append_step("Erase Existing Flash", self.erase)
            if self.flashBool:
                self.append_step("Flash Fresh Firmware", self.flash)
            self.append_step("Upload Certificates", self.upload_certificates)

    # -------------------------------------------------------------------------
    # SETUP / TEARDOWN
    # -------------------------------------------------------------------------

    def setup(self):
        self.interface.dc_power_en(False)
        self.interface.battery_power_en(False)
        time.sleep(1)
        self.interface.battery_power_en(True)
        self.interface.rs232_enable(True)
        time.sleep(0.5)
        self.interface.analog_enable(True)
        time.sleep(0.5)
        self.interface.jtag_enable(True)

    def teardown(self):
        self.target.enable_ble_passthrough(False)
        self.interface.dc_power_en(False)
        self.interface.battery_power_en(False)
        self.interface.analog_enable(False)

    # -------------------------------------------------------------------------
    # LTE acquire
    # -------------------------------------------------------------------------

    def acquire(self):
        with self._step("Enable LTE passthrough"):
            if not self.target.enable_lte_passthrough(True):
                self.log_error(self.ErrorCode.dut_unlock_failed)
                return {"result": False}

        self.sara = UBloxSara(self.target.connection)

        with self._step("Detect SARA module", timeout_s=self.detect_time):
            t0 = time.time()
            while time.time() - t0 < self.detect_time:
                time.sleep(1)
                if self.sara.ping():
                    self._info("SARA responded to ping")
                    return {"result": True, "provision_status": True}

        self._error("LTE communication failed (no ping response within detect_time)")
        self.log_error(self.ErrorCode.lte_communication_failed)
        return {"result": False}

    # -------------------------------------------------------------------------
    # Certificate + AWS device provisioning
    # -------------------------------------------------------------------------

    def create_device(self, cafile, cakey, days):
        # Validate inputs
        if cafile is None or cakey is None or int(days) <= 0:
            self._warn("Skipping provisioning due to missing inputs",
                       cafile=str(cafile), cakey=str(cakey), days=days)
            return None

        self._info("Starting provisioning flow",
                   cafile=str(cafile), cakey=str(cakey), days=days)

        try:
            # STEP 0 – IoT ID
            with self._step("STEP 0 – Extract IoT ID"):
                iot_id = (self.programmer.extract_iot() or "").strip()
                self._info("IoT ID read", iot_id=iot_id or "<empty>")

                bad = (
                    not iot_id
                    or "No debug probe detected" in iot_id
                    or not THING_NAME_RE.match(iot_id)
                )
                if bad:
                    self._error("Invalid IoT ID from programmer", iot_id=iot_id or "<empty>")
                    self.log_error(self.ErrorCode.aws_device_register_failure)
                    return None

            # STEP 1 – Create device key pair
            with self._step("STEP 1 – Create device key pair", device_name=str(self.DEVICE_NAME)):
                self._run_cmd(f"openssl genrsa -out {str(self.DEVICE_NAME)}.key 2048",
                              name="openssl genrsa")

            # STEP 2 – CSR
            with self._step("STEP 2 – Create CSR"):
                subj = self.STANDARD_SUBJECT
                self._run_cmd(
                    f'openssl req -new -key {str(self.DEVICE_NAME)}.key '
                    f'-out {str(self.DEVICE_NAME)}.csr -subj "{subj}"',
                    name="openssl req (CSR)"
                )

            # STEP 3 – Device certificate (signed by device CA)
            with self._step("STEP 3 – Generate device certificate", days=days):
                self._run_cmd(
                    f"openssl x509 -req -in {str(self.DEVICE_NAME)}.csr "
                    f"-CA {str(self.DEVICE_CA_NAME)}.pem -CAkey {str(self.DEVICE_CA_NAME)}.key "
                    f"-CAcreateserial -out {str(self.DEVICE_NAME)}.pem -days {int(days)} -sha256",
                    name="openssl x509"
                )

            # STEP 4 – Register device certificate with AWS IoT
            with self._step("STEP 4 – Register device certificate with AWS IoT"):
                out = self._run_cmd(
                    f"aws iot register-certificate "
                    f"--certificate-pem file://{str(self.DEVICE_NAME)}.pem "
                    f"--ca-certificate-pem file://{str(self.DEVICE_CA_NAME)}.pem",
                    name="aws iot register-certificate"
                )
                j = json.loads(out)
                cert_id = j.get("certificateId")
                cert_arn = j.get("certificateArn")
                if not cert_id or not cert_arn:
                    raise RuntimeError("Missing certificateId/certificateArn in AWS response")
                self._info("Device certificate registered",
                           certificateId=cert_id, certificateArn=cert_arn)

                self._run_cmd(
                    f"aws iot update-certificate --certificate-id {cert_id} --new-status ACTIVE",
                    name="aws iot update-certificate"
                )

            # STEP 5 – Create Thing
            with self._step("STEP 5 – Create IoT Thing", thing=iot_id):
                out = self._run_cmd(f"aws iot create-thing --thing-name {iot_id}",
                                    name="aws iot create-thing")
                j = json.loads(out)
                self._info("Thing created",
                           thingName=j.get("thingName"),
                           thingArn=j.get("thingArn"))

            # STEP 6 – Attach certificate to Thing
            with self._step("STEP 6 – Attach certificate to Thing"):
                self._run_cmd(
                    f"aws iot attach-thing-principal --thing-name {iot_id} --principal {cert_arn}",
                    name="aws iot attach-thing-principal"
                )

            self._info("Provisioning sequence completed", iot_id=iot_id, cert_arn=cert_arn)
            return [cert_arn, iot_id]

        except Exception as e:
            self._error("Exception during provisioning", err_type=type(e).__name__, err=str(e))
            self.log_error(self.ErrorCode.aws_device_register_failure)
            return None

    # -------------------------------------------------------------------------
    # S3 CA download
    # -------------------------------------------------------------------------

    def download_ca(self):
        with self._step("Download Device CA from S3", bucket="s3://ccb-ca"):
            out = self._run_cmd('aws s3 cp s3://ccb-ca . --recursive --exclude "*/*"',
                                name="aws s3 cp")
            if "Completed" not in out:
                self._warn("Device CA download returned without 'Completed'",
                           stdout=out[:300] or None)
                self._warn("Non-critical: Failed to download device CA. Contact Product Development")
                return False
            self._info("Device CA downloaded")
            return True

    # -------------------------------------------------------------------------
    # Policy ensure/attach
    # -------------------------------------------------------------------------

    def create_policy_from_json(self, policy_name, policy_file_path):
        with self._step("Ensure IoT policy exists",
                        policy=policy_name, file=str(policy_file_path)):
            try:
                self._run_cmd(f"aws iot get-policy --policy-name {policy_name}",
                              name="aws iot get-policy")
                self._info("Policy already exists", policy=policy_name)
            except subprocess.CalledProcessError:
                self._run_cmd(
                    f"aws iot create-policy --policy-name {policy_name} "
                    f"--policy-document file://{str(policy_file_path)}",
                    name="aws iot create-policy"
                )
                self._info("Policy created", policy=policy_name)

    def attach_policy_to_device_cert(self, device_cert_arn, policy_name):
        with self._step("Attach policy to device certificate",
                        policy=policy_name, cert_arn=device_cert_arn):
            try:
                self._run_cmd(
                    f"aws iot attach-policy --target {device_cert_arn} --policy-name {policy_name}",
                    name="aws iot attach-policy"
                )
            except subprocess.CalledProcessError:
                self.log_error(self.ErrorCode.aws_policy_attachment_failed)
                raise

    # -------------------------------------------------------------------------
    # Local file helpers
    # -------------------------------------------------------------------------

    def read_cert(self, filename):
        f = open(filename, "r")
        size = len(f.read())
        f.seek(0)
        return [f, size]

    def clean_up(self, include_rootca=False):
        self._info("Cleaning up temporary cert files...", include_rootca=include_rootca)
        self.delete_file(f"{self.VERIFICATION_NAME}.csr")
        self.delete_file(f"{self.VERIFICATION_NAME}.key")
        self.delete_file(f"{self.VERIFICATION_NAME}.pem")
        self.delete_file(f"{self.DEVICE_CA_NAME}.srl")
        self.delete_file(f"{self.DEVICE_NAME}.csr")
        self.delete_file(f"{self.DEVICE_NAME}.key")
        self.delete_file(f"{self.DEVICE_NAME}.pem")
        if include_rootca:
            self.delete_file(f"{self.DEVICE_CA_NAME}.pem")
            self.delete_file(f"{self.DEVICE_CA_NAME}.key")

    def delete_file(self, f):
        try:
            os.remove(f)
            self._debug("Deleted file", path=f)
        except FileNotFoundError:
            self._debug("File not found during cleanup", path=f)

    # -------------------------------------------------------------------------
    # Main provisioning step
    # -------------------------------------------------------------------------

    def upload_certificates(self):
        if not self.internet_connection:
            self._warn("No internet connection – skipping provisioning")
            return {"result": False, "provision_status": False}

        result = False
        iot_id = None

        cafile = self.PATH_TO_CERTS / f"{self.rootCA}.pem"
        cakey = self.PATH_TO_CERTS / f"{self.rootCA}.key"
        self._info("CA file check", cafile=str(cafile), cakey=str(cakey))
        days = self.days

        if cafile is not None:
            if not os.path.exists(cafile):
                self._warn("Device CA pem not found – attempting S3 download", cafile=str(cafile))
                if not self.download_ca():
                    self.log_error(self.ErrorCode.aws_ca_cert_download_failed)
                    self._error("Failed to get device CA")
                    return {"result": False, "provision_status": False}
            else:
                self._info("Device CA pem found", cafile=str(cafile))

        if cafile is not None and cakey is not None and days is not None:
            # Reset the chip so it starts the USB port for SARA
            with self._step("Reset DUT (RDP=0 + Chip Reset)"):
                self.programmer.set_rdp(0)
                self.programmer.chip_reset()

            # Create device (validates IoT ID first)
            res = self.create_device(cafile=cafile, cakey=cakey, days=days)
            if not res:
                self.clean_up()
                return {"result": False, "provision_status": False}
            cert_arn, iot_id = res

            # Ensure/attach policy
            self.create_policy_from_json(self.ROMET_STD_IOT_POLICY, self.ROMET_STD_IOT_POLICY_FILE)
            self.attach_policy_to_device_cert(cert_arn, self.ROMET_STD_IOT_POLICY)

            # Load certs to memory
            aws_ca, aws_ca_size = self.read_cert(str(self.AWS_AUTH_CA_NAME))
            device_cert, device_cert_size = self.read_cert(f"{str(self.DEVICE_NAME)}.pem")
            device_key, device_key_size = self.read_cert(f"{str(self.DEVICE_NAME)}.key")

            # Test if LTE chip com port is ready
            if self.acquire()["result"]:
                self._info("SARA acquired – ready for certificate transfer")
            else:
                self._error("SARA failed to respond to AT command – aborting")
                aws_ca.close(); device_cert.close(); device_key.close()
                self.clean_up()
                return {"result": False, "provision_status": False}

            # Transfer certs; on failure, close/cleanup/return
            with self._step("Transfer certificates to SARA"):
                if self.sara.send_cert(aws_ca, "aws_ca", aws_ca_size) is False:
                    self._error("Certificate transfer failed", which="aws_ca")
                    aws_ca.close(); device_cert.close(); device_key.close()
                    self.clean_up()
                    self.log_error(self.ErrorCode.lte_aws_ca_cert_transfer_unsuccessful)
                    return {"result": False, "provision_status": False}

                if self.sara.send_cert(device_cert, "device_cert", device_cert_size) is False:
                    self._error("Certificate transfer failed", which="device_cert")
                    aws_ca.close(); device_cert.close(); device_key.close()
                    self.clean_up()
                    self.log_error(self.ErrorCode.lte_device_cert_transfer_unsuccessful)
                    return {"result": False, "provision_status": False}

                if self.sara.send_cert(device_key, "device_key", device_key_size) is False:
                    self._error("Certificate transfer failed", which="device_key")
                    aws_ca.close(); device_cert.close(); device_key.close()
                    self.clean_up()
                    self.log_error(self.ErrorCode.lte_device_key_transfer_unsuccessful)
                    return {"result": False, "provision_status": False}

            # Close files
            aws_ca.close()
            device_cert.close()
            device_key.close()

            # Activate the SIM and pair to IoT
            with self._step("Pair ICCID and IoT ID"):
                iccid = self.sara.get_sim_iccid()
                if iccid is None:
                    self.log_error(self.ErrorCode.lte_sim_iccid_invalid)
                    self._error("Could not get ICCID from SARA")
                    self.clean_up()
                    return {"result": False, "provision_status": False}

                # Rogers API credentials
                creds_path = self.PATH_TO_CONFIG / "credentials/credentials.json"
                creds = json.load(open(creds_path))
                API_KEY = creds["api_key"]
                username = creds["username"]

                rogers = jasper.Jasper(username, API_KEY)
                self._info("Rogers set_device_id response",
                           response=rogers.set_device_id(self.sara.iccid, iot_id))

            # Delete certs from computer
            self.clean_up()
            print(ascii_message.PASS_STRING)  # preserve existing PASS banner
            print(iot_id)  # preserve existing IoT ID print
            result = True
            return {"result": result, "provision_status": result, "iot": iot_id}
        else:
            self.log_error(self.ErrorCode.aws_failed_ca_requirements)
            self._error("CA required. See confluence documentation for solutions.")
            return {"result": False, "provision_status": False}

    # -------------------------------------------------------------------------
    # DUT erase/flash
    # -------------------------------------------------------------------------

    def erase(self):
        with self._step("Erase DUT"):
            result = self.programmer.set_rdp(0)
            if not result:
                self.log_error(self.ErrorCode.dut_unlock_failed)

            result = self.programmer.erase()
            if not result:
                self.log_error(self.ErrorCode.dut_erase_failed)
            return {"result": result, "erase": True}

    def flash(self):
        result = True
        firmware_path = Path(self.config.active_dir) / Path(self.job._id)

        with self._step("Flash firmware", count=len(self.firmware_list)):
            for f in self.firmware_list:
                address = f.get("address")
                file_path = str(firmware_path / f["file"])
                self._info("Flashing segment", file=file_path, address=address)
                ok = self.programmer.write(file_path, address)
                result &= ok
                if not ok:
                    self.log_error(self.ErrorCode.dut_program_failed)
                    break
                time.sleep(1)

        return {"result": result, "firmware_list": self.firmware_list}

    # -------------------------------------------------------------------------
    # Internet check
    # -------------------------------------------------------------------------

    def internet(self, host="1.1.1.1", port=443, timeout=3):
        """
        Host: 1.1.1.1 (Cloudflare)
        OpenPort: 443/tcp
        """
        try:
            socket.setdefaulttimeout(timeout)
            with self._step("Internet check", host=host, port=port, timeout_s=timeout):
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((host, port))
                s.close()
                self.internet_connection = True
                return {"result": True}
        except socket.error as ex:
            self._warn("No internet connectivity", err=str(ex))
            self.internet_connection = False
            self.log_error(self.ErrorCode.no_internet_connection)
            return {"result": False}
