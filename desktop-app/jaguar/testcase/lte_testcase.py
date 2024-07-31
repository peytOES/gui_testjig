import time
import re
from statistics import mean

from .jaguar_testcase import JaguarTestCase
from birch.peripheral.lte_module import UBloxSara


class LTETestCase(JaguarTestCase):
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

        # module info
        self.application_version = application_version
        self.fw_version = fw_version
        self.manufacturer_identification = manufacturer_identification
        self.model = model
        self.type_code = type_code
        self.files = files

        # network status
        self.cops = cops
        self.creg = creg
        self.csq_power = csq_power
        self.csq_quality = csq_quality

        self.sara = None
        self.append_step("Acquire SARA", self.acquire)
        self.append_step("Read module information", self.read_info)
        self.append_step("Read network information", self.read_network_info)
        self.append_step("Measure power", self.lte_power)

    def setup(self):
        self.interface.dc_power_en(False)
        self.interface.battery_power_en(False)
        time.sleep(1)
        self.interface.battery_power_en(True)
        self.interface.rs232_enable(True)
        time.sleep(0.5)
        self.interface.analog_enable(True)

    def teardown(self):
        self.target.enable_ble_passthrough(False)
        self.interface.dc_power_en(False)
        self.interface.battery_power_en(False)
        self.interface.analog_enable(False)


    def acquire(self):
        result = self.target.enable_lte_passthrough(True)
        if not result:
            self.log_error(self.ErrorCode.lte_passthrough_enable_fail)
            return {"result": False}
        # now we should have a connection to the sara
        self.sara = UBloxSara(self.target.connection)

        t0 = time.time()

        while time.time() - t0 < self.detect_time:
            time.sleep(1)
            if self.sara.ping():
                return {"result": True}

        self.log_error(self.ErrorCode.lte_communication_failed)
        return {"result": False}

    def read_info(self):
        """
        E.g.
                        {
                    "application_version": "L0.0.00.00.05.12,A.02.19",
                    "card_id": "89302720399930687685",
                    "files": "+ULSTFILE: cs-certificate.pem.crt,cs-private.pem.key,legacy_ca.pem",
                    "fw_version": "L0.0.00.00.05.12 [Oct 08 2020 15:00:01]",
                    "imei": "356726100870880",
                    "manufacturer_identification": "u-blox",
                    "model": "SARA-R410M-02B",
                    "sc_lock": "+CLCK: 0",
                    "sc_pin_status": "+CPIN: READY",
                    "type_code": "SARA-R410M-02B-03"
                },
                {
        """
        if self.sara is None or self.ErrorCode.lte_communication_failed in self.error_code:
            return {"result": False}
        result = True
        info = self.sara.read_module_info()
        for k in info:
            if info[k] is None:
                result = False
                self.event_logger.info("%s: %s" % (k, info[k]))
                self.log_error(self.ErrorCode.lte_read_module_info_failed)
            # if '\r' in info[k]:
            #     info[k] = info[k].split('\r') 

        self.target.imei = info["imei"]
        self.target.sim = info["card_id"]

        if self.application_version is not None:
            if re.fullmatch(self.application_version, info["application_version"]) is None:
                self.log_error(self.ErrorCode.lte_application_version_mismatch)
                result = False

        if self.fw_version is not None:
            if re.fullmatch(self.fw_version, info["fw_version"]) is None:
                self.log_error(self.ErrorCode.lte_fw_version_mismatch)
                result = False

        if self.manufacturer_identification is not None:
            if re.fullmatch(self.manufacturer_identification, info["manufacturer_identification"]) is None:
                self.log_error(self.ErrorCode.lte_manufacturer_identification_mismatch)
                result = False

        if self.model is not None:
            if re.fullmatch(self.model, info["model"]) is None:
                self.log_error(self.ErrorCode.lte_model_mismatch)
                result = False

        if self.type_code is not None and self.type_code != '':
            if re.fullmatch(self.type_code, info["type_code"]) is None:
                self.log_error(self.ErrorCode.lte_type_code_mismatch)
                result = False

        if self.files is not None:
            if re.fullmatch(self.files, info["files"]) is None:
                self.log_error(self.ErrorCode.lte_files_mismatch)
                result = False

        return {"result": result, **info}

    def read_network_info(self):
        """
    {
        "network_registration_status": "+CREG: 0,2",
        "operator_selection": "+COPS: 0",
        "signal_quality": "+CSQ: 99,99",
        "step_name": "Read network information"
    },
        """
        if self.sara is None or self.ErrorCode.lte_communication_failed in self.error_code:
            return {"result": False}
        
        
        result = True
        info = self.sara.read_network_info()
        for k in info:
            if info[k] is None:
                result = False
                self.log_error(self.ErrorCode.lte_read_network_info_failed) ############

        if self.cops is not None:
            if re.fullmatch(self.cops, info["operator_selection"]) is None:
                self.log_error(self.ErrorCode.lte_cops_mismatch)
                result = False

        if self.creg is not None:
            if re.fullmatch(self.creg, info["network_registration_status"]) is None:
                self.log_error(self.ErrorCode.lte_creg_mismatch)
                result = False

        csq_power = None
        csq_qual = None
        try:
            a = info["signal_quality"]
            a = a.replace("+CSQ:", "").strip().split(",")

            csq_power = int(a[0])
            csq_qual = int(a[1])
        except Exception as e:
            self.event_logger.info("LTE read_network_info csq parse failed: %s" % info["signal_quality"])

        if self.csq_power is not None:
            if csq_power is None:
                self.log_error(self.ErrorCode.lte_csq_power_parse)
                result = False
            else:
                if csq_power < int(self.csq_power):
                    self.log_error(self.ErrorCode.lte_csq_power_min)
                    result = False
        if self.csq_quality is not None:
            if csq_qual is None:
                self.log_error(self.ErrorCode.lte_csq_quality_parse)
                result = False
            else:
                if csq_power < int(self.csq_power):
                    self.log_error(self.ErrorCode.lte_csq_quality_min)
                    result = False

        return {"result": result, **info}

    def lte_power(self):
        if self.sara is None:
            return {"result": False}
        result = True
        v_mdm = []
        i_lte = []
        for i in range(self.samples):
            v_mdm.append(self.interface.modem_voltage())
            i_lte.append(self.interface.battery_current())
            time.sleep(0.1)

        self.event_logger.info("I_lte %s" % str(i_lte))
        self.event_logger.info("V_mdm %s" % str(v_mdm))

        if mean(i_lte) < self.i_min:
            self.log_error(self.ErrorCode.lte_current_min)
            result = False
        if mean(i_lte) > self.i_max:
            self.log_error(self.ErrorCode.lte_current_max)
            result = False

        if mean(v_mdm) < self.v_min:
            self.log_error(self.ErrorCode.lte_voltage_min)
            result = False
        if mean(v_mdm) > self.v_max:
            self.log_error(self.ErrorCode.lte_voltage_max)
            result = False
        return {"result": result, "i": mean(i_lte), "v_mdm": mean(v_mdm)}
