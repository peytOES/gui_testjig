import time
import re
import logging
import contextlib
from statistics import mean

from .jaguar_testcase import JaguarTestCase
from birch.peripheral.lte_module import UBloxSara


# -----------------------------------------------------------------------------
# Readable, consistent, context-rich logging utilities
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # switch to DEBUG for bring-up


class _ReadableLogMixin:
    LOG_TRUNC = 600

    def _fmt(self, msg: str, **fields) -> str:
        kv = " ".join(f"{k}={repr(v)}" for k, v in fields.items() if v is not None)
        cls = getattr(self, "__class__", type("X", (), {})).__name__
        return f"[{cls}] {msg}" + (f" | {kv}" if kv else "")

    def _emit(self, level: str, text: str):
        print(text)
        getattr(logger, level, logger.info)(text)
        try:
            if hasattr(self, "event_logger") and self.event_logger:
                getattr(self.event_logger, level, self.event_logger.info)(text)
        except Exception:
            pass

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


class LTETestCase(_ReadableLogMixin, JaguarTestCase):
    """
    Read information from LTE module, including network & signal strength
    """

    def __init__(self,
                 detect_time=10,
                 samples=10,
                 i_min=0.01,
                 i_max=0.2,
                 v_min=3.3,
                 v_max=4.2,
                 application_version=None,
                 fw_version=None,
                 manufacturer_identification=None,
                 model=None,
                 type_code=None,
                 files=None,
                 cops=None,
                 creg=None,
                 csq_power=None,
                 csq_quality=None,
                 *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.detect_time = detect_time
        self.i_min = i_min
        self.i_max = i_max
        self.samples = samples
        self.v_min = v_min
        self.v_max = v_max

        # module info expectations
        self.application_version = application_version
        self.fw_version = fw_version
        self.manufacturer_identification = manufacturer_identification
        self.model = model
        self.type_code = type_code
        self.files = files

        # network status expectations
        self.cops = cops
        self.creg = creg
        self.csq_power = csq_power
        self.csq_quality = csq_quality

        self.sara = None
        self.append_step("Acquire SARA", self.acquire)
        self.append_step("Read module information", self.read_info)
        self.append_step("Read network information", self.read_network_info)
        self.append_step("Measure power", self.lte_power)

    # -------------------------------------------------------------------------
    # Power rails & IO setup/teardown
    # -------------------------------------------------------------------------

    def setup(self):
        with self._step("LTE test setup"):
            self.interface.dc_power_en(False)
            self.interface.battery_power_en(False)
            time.sleep(1)
            self.interface.battery_power_en(True)
            self.interface.rs232_enable(True)
            time.sleep(0.5)
            self.interface.analog_enable(True)

    def teardown(self):
        with self._step("LTE test teardown"):
            self.target.enable_ble_passthrough(False)
            self.interface.dc_power_en(False)
            self.interface.battery_power_en(False)
            self.interface.analog_enable(False)

    # -------------------------------------------------------------------------
    # Acquire SARA (passthrough + ping loop)
    # -------------------------------------------------------------------------

    def acquire(self):
        with self._step("Enable LTE passthrough"):
            result = self.target.enable_lte_passthrough(True)
            if not result:
                self._error("Failed to enable LTE passthrough")
                self.log_error(self.ErrorCode.lte_passthrough_enable_fail)
                return {"result": False}

        # now we should have a connection to the SARA
        self.sara = UBloxSara(self.target.connection)

        with self._step("Detect SARA module", timeout_s=self.detect_time):
            t0 = time.time()
            tries = 0
            while time.time() - t0 < self.detect_time:
                time.sleep(1)
                tries += 1
                if self.sara.ping():
                    self._info("SARA responded to AT ping", tries=tries, elapsed_s=round(time.time() - t0, 3))
                    return {"result": True}
            self._error("No response from SARA within detect_time", tries=tries, elapsed_s=round(time.time() - t0, 3))
            self.log_error(self.ErrorCode.lte_communication_failed)
            return {"result": False}

    # -------------------------------------------------------------------------
    # Module information
    # -------------------------------------------------------------------------

    def read_info(self):
        """
        Expected info keys include:
          application_version, card_id, files, fw_version, imei,
          manufacturer_identification, model, sc_lock, sc_pin_status, type_code
        """
        if self.sara is None or self.ErrorCode.lte_communication_failed in self.error_code:
            self._warn("Skipping read_info: SARA not available or communication failure flagged")
            return {"result": False}

        with self._step("Read module information"):
            result = True
            info = self.sara.read_module_info() or {}

            # Log a concise snapshot
            snapshot = {
                "imei": info.get("imei"),
                "icc_id": info.get("card_id"),
                "model": info.get("model"),
                "fw": info.get("fw_version"),
                "app": info.get("application_version"),
                "type": info.get("type_code"),
                "files": (info.get("files") or "")[:120]  # avoid spam
            }
            self._info("Module info snapshot", **snapshot)

            # Null checks
            for k in ("application_version", "card_id", "files", "fw_version", "imei",
                      "manufacturer_identification", "model", "type_code"):
                if info.get(k) is None:
                    result = False
                    self._warn("Module info missing key", key=k, value=None)
                    self.log_error(self.ErrorCode.lte_read_module_info_failed)

            # Save identifiers to target
            if info.get("imei"):
                self.target.imei = info["imei"]
            if info.get("card_id"):
                self.target.sim = info["card_id"]

            # Expectations with regex
            def _check(exp, actual, err_code, name):
                nonlocal result
                if exp is None:
                    return
                ok = re.fullmatch(exp, actual or "")
                if ok is None:
                    result = False
                    self._error(f"{name} mismatch", expected=exp, actual=actual)
                    self.log_error(err_code)

            _check(self.application_version, info.get("application_version"),
                   self.ErrorCode.lte_application_version_mismatch, "application_version")
            _check(self.fw_version, info.get("fw_version"),
                   self.ErrorCode.lte_fw_version_mismatch, "fw_version")
            _check(self.manufacturer_identification, info.get("manufacturer_identification"),
                   self.ErrorCode.lte_manufacturer_identification_mismatch, "manufacturer_identification")
            _check(self.model, info.get("model"),
                   self.ErrorCode.lte_model_mismatch, "model")
            if (self.type_code or "") != "":
                _check(self.type_code, info.get("type_code"),
                       self.ErrorCode.lte_type_code_mismatch, "type_code")
            _check(self.files, info.get("files"),
                   self.ErrorCode.lte_files_mismatch, "files")

            return {"result": result, **info}

    # -------------------------------------------------------------------------
    # Network info (CREG/COPS/CSQ)
    # -------------------------------------------------------------------------

    def read_network_info(self):
        """
        Example:
        {
          "network_registration_status": "+CREG: 0,2",
          "operator_selection": "+COPS: 0",
          "signal_quality": "+CSQ: 99,99"
        }
        """
        if self.sara is None or self.ErrorCode.lte_communication_failed in self.error_code:
            self._warn("Skipping read_network_info: SARA not available or communication failure flagged")
            return {"result": False}

        with self._step("Read network information"):
            result = True
            info = self.sara.read_network_info() or {}
            self._info("Network info raw",
                       CREG=info.get("network_registration_status"),
                       COPS=info.get("operator_selection"),
                       CSQ=info.get("signal_quality"))

            # Basic null checks
            for k in ("network_registration_status", "operator_selection", "signal_quality"):
                if info.get(k) is None:
                    result = False
                    self._warn("Network info missing key", key=k, value=None)
                    self.log_error(self.ErrorCode.lte_read_network_info_failed)

            # Expectations (regex)
            def _check(exp, actual, err_code, name):
                nonlocal result
                if exp is None:
                    return
                ok = re.fullmatch(exp, actual or "")
                if ok is None:
                    result = False
                    self._error(f"{name} mismatch", expected=exp, actual=actual)
                    self.log_error(err_code)

            _check(self.cops, info.get("operator_selection"),
                   self.ErrorCode.lte_cops_mismatch, "COPS")
            _check(self.creg, info.get("network_registration_status"),
                   self.ErrorCode.lte_creg_mismatch, "CREG")

            # Parse CSQ
            csq_power = None
            csq_qual = None
            raw_csq = info.get("signal_quality") or ""
            try:
                a = raw_csq.replace("+CSQ:", "").strip().split(",")
                if len(a) >= 2:
                    csq_power = int(a[0])
                    csq_qual = int(a[1])
                self._info("CSQ parsed", csq_power=csq_power, csq_quality=csq_qual)
            except Exception:
                self._warn("CSQ parse failed", raw=raw_csq)
                self.event_logger.info("LTE read_network_info csq parse failed: %s" % raw_csq)

            # Threshold checks
            if self.csq_power is not None:
                if csq_power is None:
                    result = False
                    self._error("CSQ power parse error")
                    self.log_error(self.ErrorCode.lte_csq_power_parse)
                elif csq_power < int(self.csq_power):
                    result = False
                    self._error("CSQ power below minimum", actual=csq_power, min=int(self.csq_power))
                    self.log_error(self.ErrorCode.lte_csq_power_min)

            if self.csq_quality is not None:
                if csq_qual is None:
                    result = False
                    self._error("CSQ quality parse error")
                    self.log_error(self.ErrorCode.lte_csq_quality_parse)
                elif csq_qual < int(self.csq_quality):  # FIX: compare quality to quality
                    result = False
                    self._error("CSQ quality below minimum", actual=csq_qual, min=int(self.csq_quality))
                    self.log_error(self.ErrorCode.lte_csq_quality_min)

            # Include parsed numbers in return for convenience
            return {"result": result, "csq_power_val": csq_power, "csq_quality_val": csq_qual, **info}

    # -------------------------------------------------------------------------
    # Power measurement (current/voltage)
    # -------------------------------------------------------------------------

    def lte_power(self):
        if self.sara is None:
            self._warn("Skipping lte_power: SARA not available")
            return {"result": False}

        with self._step("Measure LTE power",
                        samples=self.samples, i_min=self.i_min, i_max=self.i_max,
                        v_min=self.v_min, v_max=self.v_max):
            result = True
            v_mdm = []
            i_lte = []

            for _ in range(self.samples):
                try:
                    v_mdm.append(self.interface.modem_voltage())
                    i_lte.append(self.interface.battery_current())
                except Exception as e:
                    self._warn("Sample read failed", err=str(e))
                time.sleep(0.1)

            # Snapshot arrays (truncated)
            def _short(arr, n=10):
                return arr[:n] + (["..."] if len(arr) > n else [])

            self._info("Samples snapshot",
                       i_len=len(i_lte), v_len=len(v_mdm),
                       i_first=_short(i_lte), v_first=_short(v_mdm))

            try:
                i_mean = mean(i_lte)
                v_mean = mean(v_mdm)
            except Exception as e:
                self._error("Mean calculation failed", err=str(e))
                return {"result": False}

            self._info("Averages", i_mean=i_mean, v_mean=v_mean)

            if i_mean < self.i_min:
                result = False
                self._error("LTE current below minimum", actual=i_mean, min=self.i_min)
                self.log_error(self.ErrorCode.lte_current_min)
            if i_mean > self.i_max:
                result = False
                self._error("LTE current above maximum", actual=i_mean, max=self.i_max)
                self.log_error(self.ErrorCode.lte_current_max)

            if v_mean < self.v_min:
                result = False
                self._error("Modem voltage below minimum", actual=v_mean, min=self.v_min)
                self.log_error(self.ErrorCode.lte_voltage_min)
            if v_mean > self.v_max:
                result = False
                self._error("Modem voltage above maximum", actual=v_mean, max=self.v_max)
                self.log_error(self.ErrorCode.lte_voltage_max)

            return {"result": result, "i": i_mean, "v_mdm": v_mean}
