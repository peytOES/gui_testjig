import time
from statistics import mean
import re

from .jaguar_testcase import JaguarTestCase
from birch.peripheral.ble_module import UBloxNina


class BLETestCase(JaguarTestCase):
    """
    Scan for and connect to BLE module on Jaguar board
    """

    def __init__(self,
                 scan_duration=10,
                 min_rssi=-50,
                 i_min=0.002,
                 i_max=0.02,
                 samples=10,

                 application_version=None,
                 fw_version=None,
                 manufacturer_identification=None,
                 model=None,
                 type_code=None,
                 *args, **kwargs):
        """
        scan_duration: Time in seconds to scan  (default 10s)
        min_rssi : Minimum RSSI value of scan result (default -55)

        samples: number of current samples to take
        i_min : minimum expected current (mean over samples)
        i_max : maximum expected current (mean over samples)
        """
        super().__init__(*args, **kwargs)

        self.nina = None
        self.mac_addr = None
        self.min_rssi = min_rssi
        self.scan_duration = scan_duration
        self.i_min = i_min
        self.i_max = i_max
        self.samples = samples

        self.application_version = application_version
        self.fw_version = fw_version
        self.manufacturer_identification = manufacturer_identification
        self.model = model
        self.type_code = type_code

        self.append_step("Acquire NINA", self.configure)
        self.append_step("Read BLE info", self.read_info)
        self.append_step("Scanning", self.scan)
        self.append_step("Connect", self.connect)
        self.append_step("Measure current", self.ble_current)
        self.append_step("Disconnect", self.disconnect)

    def setup(self):
        self.interface.dc_power_en(False)
        self.interface.battery_power_en(False)
        time.sleep(0.1)
        self.interface.dc_power_en(True)
        self.interface.rs232_enable(True)
        try:
            self.ble.disconnect()
        except:
            pass
        time.sleep(1)
        pass

    def configure(self):

        self.target.enable_ble_passthrough(True)

        # now we should have a nina
        self.nina = UBloxNina(self.target.connection)
        # check if we have communication
        time.sleep(0.5)
        for i in range(3):
            result = self.nina.at_command(b"AT")[0]
            if result:
                break
            time.sleep(1)
        if not result:
            self.log_error(self.ErrorCode.ble_communication_failed)
        return {"result": result}

    def read_info(self):
        """
        
                {
                    "application_version": "5.0.0-011,NINA-B11X-5.0.0-011-0-g1aaa693",
                    "fw_version": "5.0.0-011",
                    "mac_address": "CCF957976C0A",
                    "manufacturer_identification": "u-blox",
                    "mcuid": "0E505C506E3F9539",
                    "model": "NINA-B1",
                    "serial_number": "0225371288464394",
                    "type_code": "NINA-B112-04B-00"
                },
        """
        result = True
        info = self.nina.read_module_info()
        if info is None:
            self.log_error(self.ErrorCode.ble_read_info_failed)
            result = False
            info = {}
        else:
            for k in info:
                if info[k] is None:
                    result = False
                    info[k] = ""
                    self.log_error(self.ErrorCode.ble_read_info_failed)

        if "mac_address" not in info:
            self.log_error(self.ErrorCode.ble_mac_address_not_read)
        else:
            self.target.ble_mac = info["mac_address"].lower()

        if self.application_version is not None:
            if re.fullmatch(self.application_version, info["application_version"]) is None:
                self.log_error(self.ErrorCode.ble_application_version_mismatch)
                result = False

        if self.fw_version is not None:
            if re.fullmatch(self.fw_version, info["fw_version"]) is None:
                self.log_error(self.ErrorCode.ble_fw_version_mismatch)
                result = False

        if self.manufacturer_identification is not None:
            if re.fullmatch(self.manufacturer_identification, info["manufacturer_identification"]) is None:
                self.log_error(self.ErrorCode.ble_manufacturer_identification_mismatch)
                result = False

        if self.model is not None:
            if re.fullmatch(self.model, info["model"]) is None:
                self.log_error(self.ErrorCode.ble_model_mismatch)
                result = False

        if self.type_code is not None:
            if re.fullmatch(self.type_code, info["type_code"]) is None:
                self.log_error(self.ErrorCode.ble_type_code_mismatch)
                result = False

        return {"result": result, **info}

    def scan(self):
        if self.scan_duration == 0:
            # scanning discabled
            return {"result": True}
        if self.target.ble_mac == "":
            return {"result": False}
        # tryCount =0 
        # for tryCount in range(2):
        #     try:
        devices = {}
        try:
            devices = self.ble.scan(self.scan_duration)
        except:
            devices = {}
            pass
            # except:
            #     devices = {}
            # if devices != {}:
            #     break
        
        for d in devices:
            # print("Scan >", repr(d), repr(self.target.ble_mac))
            if d.lower() == self.target.ble_mac:
                rssi = devices[d]
                # print("found", rssi, self.min_rssi, rssi<self.min_rssi)
                if rssi < self.min_rssi:
                    self.log_error(self.ErrorCode.ble_scan_rssi_below_threshold)
                    return {"result": False, "rssi": devices[d]}
                return {"result": True, "rssi": devices[d]}

        self.log_error(self.ErrorCode.ble_scan_dut_not_detected)
        return {"result": False}

    def connect(self):
        if self.target.ble_mac == "":
            return {"result": False}
        try:
            result = self.ble.connect(self.target.ble_mac)
        except:
            result = False
            
        if not result:
            self.log_error(self.ErrorCode.ble_connect_from_host_failed)
            return {"result": result}
        result, host_mac = self.nina.wait_for_connect(2)
        if not result:
            self.log_error(self.ErrorCode.ble_connect_to_module_failed)
            return {"result": result}

        return {"result": result, "host_mac": host_mac}

    def ble_current(self):
        result = True
        i_dc = []
        for i in range(self.samples):
            time.sleep(0.1)
            i_dc.append(self.interface.dc_current())

        if mean(i_dc) < self.i_min:
            self.log_error(self.ErrorCode.ble_current_min)
            result = False
        if mean(i_dc) > self.i_max:
            self.log_error(self.ErrorCode.ble_current_max)
            result = False
        return {"result": result, "i": mean(i_dc)}

    def disconnect(self):
        self.ble.disconnect()
        return {"result": True}

    def teardown(self):
        self.target.enable_ble_passthrough(False)
        self.interface.dc_power_en(False)
        self.interface.battery_power_en(False)
        self.interface.rs232_enable(False)
