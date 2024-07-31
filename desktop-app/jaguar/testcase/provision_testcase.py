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

from scripts import ascii_message
from statistics import mean
from rogers_api import jasper


from .jaguar_testcase import JaguarTestCase
from birch.peripheral.lte_module import UBloxSara




class ProvisionTestCase(JaguarTestCase):
    """
    Super class of test cases the use STlink and microUSB to assign certificates to device and activate sim

    Tested
    """
            


    STANDARD_SUBJECT = "/C=CA/ST=ONT/L=Mississauga/O=ROMET LIMITED/CN=rometlimited.com"
    DEFAULT_CA_CERT_VALIDITY = 1278
    
    def __init__(self, 
                 detect_time=30,
                 rootCA = "rootCA",
                 days=127,
                 erase=False,
                 flash=False,
                 firmware_list=[],
                 provision_enable=True,
                 *args, 
                 **kwargs):
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
        self.ROMET_STD_IOT_POLICY_FILE = self.PATH_TO_CERTS / ("romet_standard_iot_policy.json")

        if(self.provision_enable):
            self.append_step("Check for Internet Connection",self.internet)
            if(self.eraseBool):
                self.append_step("Erase Existing Flash",self.erase)
            if(self.flashBool):
                self.append_step("Flash Fresh Firmware",self.flash)
            self.append_step("Upload Certificates",self.upload_certificates)

    # SETUP + TEARDOWN are necessary functions at start and end of test to open and close the io
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

    # Function to enable LTE module and set it as a self.sara 
    def acquire(self):
        result = self.target.enable_lte_passthrough(True)
        if not result:
            self.log_error(self.ErrorCode.dut_unlock_failed)
            return {"result": False}
        # now we should have a connection to the sara
        self.sara = UBloxSara(self.target.connection)

        t0 = time.time()

        while time.time() - t0 < self.detect_time:
            time.sleep(1)
            if self.sara.ping():
                return {"result": True,"provision_status":True}

        self.log_error(self.ErrorCode.lte_communication_failed)
        return {"result": False}

    # Function to create an RSA encryption key file
    def create_key_pair(self, cert_name):
        cmd = f"openssl genrsa -out {cert_name}.key 2048"
        result = subprocess.check_output(cmd, shell=True).decode().rstrip()
        if result != "":
            print(result)

    # Function to create csr file
    def create_csr(self, csr_name, registration_code=0):
        if registration_code == 0:
            cmd = f'openssl req -new -key {csr_name}.key -out {csr_name}.csr -subj "{self.STANDARD_SUBJECT}"'
        else:
            cmd = f'openssl req -new -key {csr_name}.key -out {csr_name}.csr -subj "/CN={registration_code}"'
        result = 0
        result = subprocess.check_output(cmd, shell=True).decode().rstrip()
        if result != "":
            print(result)

    # Function to create x509 certificate for the device
    def generate_device_certificate(sefl, ca_name, device_name, days):
        cmd = f"openssl x509 -req -in {device_name}.csr -CA {ca_name}.pem -CAkey {ca_name}.key -CAcreateserial -out {device_name}.pem -days {days} -sha256"
        result = subprocess.check_output(cmd, shell=True).decode().rstrip()
        if result != "":
            print(result)

    # Function to register device certificates with aws 
    def register_device_certificate(self, ca_name, device_name):
        cmd = f"aws iot register-certificate --certificate-pem file://{device_name}.pem --ca-certificate-pem file://{ca_name}.pem"
        result = subprocess.check_output(cmd, shell=True).decode().rstrip()
        print(result)
        j = json.loads(result)
        try:
            cert_id = j["certificateId"]
            cert_arn = j["certificateArn"]
            print(f"Device Certificate Id: {cert_id}")
            cmd = (
                f"aws iot update-certificate --certificate-id {cert_id} --new-status ACTIVE"
            )
            result = subprocess.check_output(cmd, shell=True).decode().rstrip()
            if result != "":
                print(result)
        except KeyError:
            print("Error: certificateId not found in response. ")
            exit()

        return cert_arn

    # Function to create thing in aws with device iot as its name
    def create_thing(self, thing_name):
        cmd = f"aws iot create-thing --thing-name {thing_name}"
        result = subprocess.check_output(cmd, shell=True).decode().rstrip()
        j = json.loads(result)
        print(f'Thing Created\nname: {j["thingName"]}\nthingARN:{j["thingArn"]}')

    # Function to attach certificate to the thing using aws cli
    def attach_certificate_to_thing(self, thing_name, certificate_arn):
        cmd = f" aws iot attach-thing-principal --thing-name {thing_name} --principal {certificate_arn}"
        result = subprocess.check_output(cmd, shell=True).decode().rstrip()
        print("Certificate attached to thing")

    # Function to create the device certificates and register them to the device in aws
    def create_device(self, cafile, cakey, days):
        if cafile != None and cakey != None and int(days) > 0:
            try:
                print("Creating Device Cert")
                self.create_key_pair(self.DEVICE_NAME)
                print("Creating CSR")
                self.create_csr(self.DEVICE_NAME)
                self.generate_device_certificate(self.DEVICE_CA_NAME, self.DEVICE_NAME, days)
                print("Registering Device Cert")
                cert_arn = self.register_device_certificate(self.DEVICE_CA_NAME, self.DEVICE_NAME)
                # get the iot number from the device
                iot_id = self.programmer.extract_iot()
                # create the thing from iot num
                self.create_thing(iot_id)
                # attach certificate to thing
                self.attach_certificate_to_thing(iot_id, cert_arn)
                return [cert_arn, iot_id]
            except:
                self.log_error(self.ErrorCode.aws_device_register_failure)

        else:
            print("CA file. CA key or days is missing")

    # Function to download the device Certificate authority 
    def download_ca(self):
        # download all files in ca root but exclude any folders
        cmd = f'aws s3 cp s3://ccb-ca . --recursive --exclude "*/*"'
        result = subprocess.check_output(cmd, shell=True).decode().rstrip()
        if "Completed" not in result:
            print(
                "ERROR: Non crtical. Failed to upload device CA. Contact Product Development"
            )
            return False
        print("Device CA downloaded successful")

    # Function to create a device policy if it does not exist  
    def create_policy_from_json(self, policy_name, policy_file_path):

        # check if policy exists
        cmd = f"aws iot get-policy --policy-name {policy_name}"
        try:
            result = subprocess.check_output(cmd, shell=True).decode().rstrip()
            print(f"Policy {policy_name} already exists.")
            self.event_logger.info(f"{policy_name} retrieved successfully")

        except subprocess.CalledProcessError:
            try:
                cmd = f"aws iot create-policy --policy-name {policy_name} --policy-document file://{policy_file_path}"
                result = subprocess.check_output(cmd, shell=True).decode().rstrip()
                self.event_logger.info(f"{policy_name} retrieved from {policy_file_path} successfully")
            except subprocess.CalledProcessError:
                self.log_error(self.ErrorCode.aws_policy_attachment_failed)
                print("ERROR: Policy name most likely exists")
                exit()
            print(f"Policy {policy_name} created")
            return

    # Function to attach the device policy to the device certificate
    def attach_policy_to_device_cert(self, device_cert_arn, policy_name):
        cmd = (
            f"aws iot attach-policy --target {device_cert_arn} --policy-name {policy_name}"
        )
        result = subprocess.check_output(cmd, shell=True).decode().rstrip()
        print(result)
        if(result == ''):
            self.log_error(self.ErrorCode.aws_policy_attachment_failed)

    def read_cert(self, filename):
        f = open(filename, "r")
        size = len(f.read())
        f.seek(0)
        return [f, size]

    def clean_up(self,include_rootca=False):
        print("Cleaning up...")
        self.delete_file(f"{self.VERIFICATION_NAME}.csr")
        self.delete_file(f"{self.VERIFICATION_NAME}.key")
        self.delete_file(f"{self.VERIFICATION_NAME}.pem")
        self.delete_file(f"{self.DEVICE_CA_NAME}.srl")
        self.delete_file(f"{self.DEVICE_NAME}.csr")
        self.delete_file(f"{self.DEVICE_NAME}.key")
        self.delete_file(f"{self.DEVICE_NAME}.pem")

    def delete_file(self,f):
        try:
            os.remove(f)
        except FileNotFoundError:
            pass

    def upload_certificates(self):
        if(self.internet_connection):
            cafile = self.PATH_TO_CERTS / f"{self.rootCA}.pem"
            cakey = self.PATH_TO_CERTS /f"{self.rootCA}.key"
            days = self.days

            if cafile != None:
                # check if the cafile exists
                if os.path.exists(cafile) == False:
                    # download the latest ca
                    if self.download_ca() == False:
                        self.log_error(self.ErrorCode.aws_ca_cert_download_failed)
                        print("ERROR: failed to get device ca")
                        exit()
                else:
                    pass
            
            if cafile != None and cakey != None and days != None:

                # reset the chip so it starts the USB port for SARA
                # reset=HWrst needs to be set as well. 
                self.programmer.set_rdp(0)
                self.programmer.chip_reset()
                
                # create device
                cert_arn, iot_id = self.create_device(cafile=cafile,cakey=cakey,days=days)
                # create policy
                self.create_policy_from_json("std_romet_iot_policy", self.ROMET_STD_IOT_POLICY_FILE)
                # attach policy to device
                self.attach_policy_to_device_cert(cert_arn, self.ROMET_STD_IOT_POLICY)

                # load certs to memory
                aws_ca, aws_ca_size = self.read_cert(self.AWS_AUTH_CA_NAME)
                device_cert, device_cert_size = self.read_cert(f"{self.DEVICE_NAME}.pem")
                device_key, device_key_size = self.read_cert(f"{self.DEVICE_NAME}.key")

                # test if LTE chip com port is ready
                if(self.acquire()['result']):
                    print("OK, We acquired the SARA")
                else:           
                    print("Somethign went wrong. Failed to respond to AT command")
                    aws_ca.close()
                    device_cert.close()
                    device_key.close()
                    self.clean_up()
                    return {"result": False,"provision_status":False}


                # transfer certs and if it fails, close, clean, exit
                if self.sara.send_cert(aws_ca, "aws_ca", aws_ca_size) == False:
                    print("ERROR: Certificate aws_ca failed")
                    aws_ca.close()
                    device_cert.close()
                    device_key.close()
                    self.clean_up()
                    self.log_error(self.ErrorCode.lte_aws_ca_cert_transfer_unsuccessful)
                    return {"result": False,"provision_status":False}
                if (self.sara.send_cert(device_cert, "device_cert", device_cert_size) == False):
                    print("ERROR: Certificate device_cert failed")
                    aws_ca.close()
                    device_cert.close()
                    device_key.close()
                    self.clean_up()
                    self.log_error(self.ErrorCode.lte_device_cert_transfer_unsuccessful)
                    return {"result": False,"provision_status":False}
                if self.sara.send_cert(device_key, "device_key", device_key_size) == False:
                    print("ERROR: Certificate device_key failed")
                    aws_ca.close()
                    device_cert.close()
                    device_key.close()
                    self.clean_up()
                    self.log_error(self.ErrorCode.lte_device_key_transfer_unsuccessful)
                    return {"result": False,"provision_status":False}

                # close files
                aws_ca.close()
                device_cert.close()
                device_key.close()

                # activate the sim and pairing to iot 
                print("Pairing iccid and iot ID...")
                iccid = self.sara.get_sim_iccid()
                if iccid == None:
                    self.log_error(self.ErrorCode.lte_sim_iccid_invalid)
                    print("Error: could not get iccid")
                    self.clean_up()
                    return {"result": False}

                # get rogers api credentials object 
                creds = json.load(open(self.PATH_TO_CONFIG / "credentials/credentials.json"))
                API_KEY = creds["api_key"]
                username = creds["username"]

                rogers = jasper.Jasper(username, API_KEY)
                print(rogers.set_device_id(self.sara.iccid, iot_id))
                
                # delete certs from computer
                self.clean_up()
                print(ascii_message.PASS_STRING)
                print(iot_id)
                result = True

            else:
                self.log_error(self.ErrorCode.aws_failed_ca_requirements)
                print("CA required. See confluence documentation for solutions.")
            
            return {"result": result,"provision_status": result, "iot":iot_id}
        else:
            return {"result": False,"provision_status": False}

    def erase(self):
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

        for f in self.firmware_list:
            if "address" in f:
                address = f["address"]
            else:
                address = None
            self.event_logger.info("Flashing %s %s" % (firmware_path / f["file"], address))
            result &= self.programmer.write(str(firmware_path / f["file"]), address)
            if not result:
                self.log_error(self.ErrorCode.dut_program_failed)
                break
            time.sleep(1)

        return {"result": result, "firmware_list": self.firmware_list}

    #Check for internet connection
    def internet(self,host="8.8.8.8", port=53, timeout=3):
        """
        Host: 8.8.8.8 (google-public-dns-a.google.com)
        OpenPort: 53/tcp
        Service: domain (DNS/TCP)
        """
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            result = True
        except socket.error as ex:
            print(ex)
            result = False

        self.internet_connection = result
        if not result:
            self.log_error(self.ErrorCode.no_internet_connection)
        return {"result": result}
