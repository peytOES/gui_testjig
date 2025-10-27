import time
from statistics import mean
import re

from .jaguar_testcase import JaguarTestCase
from birch.peripheral.ble_module import UBloxNina


class BLETestCase(JaguarTestCase):
    """
    Scan for and connect to BLE module on Jaguar board.

    Board-type behavior:
      - V1/V2 (legacy): DC ON, Battery OFF, RS232 ON. Current measured via dc_current().
      - V3: DC OFF, Battery ON (and v3_power_en(True) if available), RS232 ON.
            Current prefers battery rail reader if available, else falls back to dc_current().
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
                 board_type="V2",   # NEW: "V1" / "V2" (legacy) or "V3" (battery power path)
                 *args, **kwargs):
        """
        scan_duration: Time in seconds to scan  (default 10s)
        min_rssi : Minimum RSSI value of scan result (default -50)

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

        self.board_type = board_type
        self._used_v3_power = False

        self.append_step("Acquire NINA", self.configure)
        self.append_step("Read BLE info", self.read_info)
        self.append_step("Scanning", self.scan)
        self.append_step("Connect", self.connect)
        self.append_step("Measure current", self.ble_current)
        self.append_step("Disconnect", self.disconnect)

    # ---------------------- Power sequencing ----------------------

    def _setup_power_v1_v2(self):
        """
        Legacy path (matches original V2 behavior):
          DC OFF -> Battery OFF -> small delay -> DC ON -> RS232 ON
        """
        try:
            self.interface.dc_power_en(False)
        except Exception:
            pass
        try:
            self.interface.battery_power_en(False)
        except Exception:
            pass
        time.sleep(0.1)
        try:
            self.interface.dc_power_en(True)
        except Exception:
            pass
        try:
            self.interface.rs232_enable(True)
        except Exception:
            pass

    def _setup_power_v3(self):
        """
        V3 path (battery power):
          DC OFF -> Battery OFF (brief) -> v3_power_en(True) if available -> Battery ON -> RS232 ON
        """
        try:
            self.interface.dc_power_en(False)
        except Exception:
            pass
        # ensure clean start on battery rail
        try:
            self.interface.battery_power_en(False)
        except Exception:
            pass
        time.sleep(0.1)

        # Optional dedicated V3 rail
        try:
            if hasattr(self.interface, "v3_power_en"):
                self.interface.v3_power_en(True)
                self._used_v3_power = True
        except Exception:
            self._used_v3_power = False

        try:
            self.interface.battery_power_en(True)
        except Exception:
            pass
        try:
            self.interface.rs232_enable(True)
        except Exception:
            pass

    def setup(self):
        """
        Power up according to board_type. Also clear any stale BLE connection.
        """
        # Try to disconnect any existing BLE session on the host/fixture
        try:
            self.ble.disconnect()
        except Exception:
            pass

        if self.board_type in ("V1", "V2"):
            self._setup_power_v1_v2()
        else:
            # Default non-legacy to V3 behavior
            self._setup_power_v3()

        # Give rails / module time to come up
        time.sleep(1)

    # ---------------------- Steps ----------------------

    def configure(self):
        self.target.enable_ble_passthrough(True)

        # now we should have a nina
        self.nina = UBloxNina(self.target.connection)
        # check if we have communication
        time.sleep(0.5)
        result = False
        for _ in range(3):
            try:
                result = self.nina.at_command(b"AT")[0]
            except Exception:
                result = False
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
        try:
            info = self.nina.read_module_info()
        except Exception:
            info = None

        if info is None:
            self.log_error(self.ErrorCode.ble_read_info_failed)
            result = False
            info = {}
        else:
            for k in list(info.keys()):
                if info[k] is None:
                    result = False
                    info[k] = ""
                    self.log_error(self.ErrorCode.ble_read_info_failed)

        if "mac_address" not in info:
            self.log_error(self.ErrorCode.ble_mac_address_not_read)
        else:
            self.target.ble_mac = info["mac_address"].lower()

        if self.application_version is not None:
            if re.fullmatch(self.application_version, info.get("application_version", "")) is None:
                self.log_error(self.ErrorCode.ble_application_version_mismatch)
                result = False

        if self.fw_version is not None:
            if re.fullmatch(self.fw_version, info.get("fw_version", "")) is None:
                self.log_error(self.ErrorCode.ble_fw_version_mismatch)
                result = False

        if self.manufacturer_identification is not None:
            if re.fullmatch(self.manufacturer_identification, info.get("manufacturer_identification", "")) is None:
                self.log_error(self.ErrorCode.ble_manufacturer_identification_mismatch)
                result = False

        if self.model is not None:
            if re.fullmatch(self.model, info.get("model", "")) is None:
                self.log_error(self.ErrorCode.ble_model_mismatch)
                result = False

        if self.type_code is not None:
            if re.fullmatch(self.type_code, info.get("type_code", "")) is None:
                self.log_error(self.ErrorCode.ble_type_code_mismatch)
                result = False

        return {"result": result, **info}

    def scan(self):
        if self.scan_duration == 0:
            # scanning disabled
            return {"result": True}
        if getattr(self.target, "ble_mac", "") == "":
            return {"result": False}

        try:
            devices = self.ble.scan(self.scan_duration)
        except Exception:
            devices = {}

        for d in devices:
            if d.lower() == self.target.ble_mac:
                rssi = devices[d]
                if rssi < self.min_rssi:
                    self.log_error(self.ErrorCode.ble_scan_rssi_below_threshold)
                    return {"result": False, "rssi": rssi}
                return {"result": True, "rssi": rssi}

        self.log_error(self.ErrorCode.ble_scan_dut_not_detected)
        return {"result": False}

    def connect(self):
        if getattr(self.target, "ble_mac", "") == "":
            return {"result": False}
        try:
            result = self.ble.connect(self.target.ble_mac)
        except Exception:
            result = False

        if not result:
            self.log_error(self.ErrorCode.ble_connect_from_host_failed)
            return {"result": result}

        result, host_mac = self.nina.wait_for_connect(2)
        if not result:
            self.log_error(self.ErrorCode.ble_connect_to_module_failed)
            return {"result": result}

        return {"result": result, "host_mac": host_mac}

    def _read_current_once(self):
        """
        Single-sample current read according to board_type.
        V3 prefers a battery rail reader if available, else dc_current.
        """
        if self.board_type == "V3":
            # Try common battery current reader names
            for name in ("bat_current", "battery_current", "current_batt", "vbatt_current"):
                if hasattr(self.interface, name):
                    try:
                        return float(getattr(self.interface, name)())
                    except Exception:
                        pass
        # Fallback / legacy
        try:
            return float(self.interface.dc_current())
        except Exception:
            return 0.0

    def ble_current(self):
        result = True
        samples = []
        for _ in range(self.samples):
            time.sleep(0.1)
            try:
                samples.append(self._read_current_once())
            except Exception:
                samples.append(0.0)

        avg_i = mean(samples) if samples else 0.0

        if avg_i < self.i_min:
            self.log_error(self.ErrorCode.ble_current_min)
            result = False
        if avg_i > self.i_max:
            self.log_error(self.ErrorCode.ble_current_max)
            result = False
        return {"result": result, "i": avg_i}

    def disconnect(self):
        try:
            self.ble.disconnect()
        except Exception:
            pass
        return {"result": True}

    def teardown(self):
        try:
            self.target.enable_ble_passthrough(False)
        except Exception:
            pass

        # Power down safely for both paths
        if self.board_type == "V3":
            try:
                self.interface.rs232_enable(False)
            except Exception:
                pass
            try:
                self.interface.battery_power_en(False)
            except Exception:
                pass
            if self._used_v3_power:
                try:
                    self.interface.v3_power_en(False)
                except Exception:
                    pass
            try:
                self.interface.dc_power_en(False)
            except Exception:
                pass
        else:
            try:
                self.interface.rs232_enable(False)
            except Exception:
                pass
            try:
                self.interface.dc_power_en(False)
            except Exception:
                pass
            try:
                self.interface.battery_power_en(False)
            except Exception:
                pass
