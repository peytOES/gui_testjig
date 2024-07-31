import time
from pathlib import Path

from .jaguar_testcase import JaguarTestCase


class ProgramFirmwareTestCase(JaguarTestCase):
    """
    Super class of test cases the use STlink to program firmware

    Tested
    """

    def __init__(self, firmware_list: list, erase=True, US_FW="", CAN_FW="" , get_iot=True, fw="US", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.firmware_list = firmware_list
        self.fw=fw 
        self.US_FW = US_FW
        self.CAN_FW = CAN_FW

        if erase:
            self.append_step("Erase", self.erase)
        self.append_step("Flash", self.flash)
        if(get_iot):
            self.append_step("Get IOT Number:", self.get_iot)

    def setup(self):
        self.interface.dc_power_en(True)
        self.interface.jtag_enable(True)
        time.sleep(1)

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
            # if production is  the name of the firmware file you want to use to flash, the we have to look at us/canada fw
            if('production' in f['file']):
                if('USA' in self.fw):
                    f['file'] = self.US_FW
                elif('CAN' in self.fw):
                    f['file'] = self.CAN_FW
                    
            self.event_logger.info("Flashing %s %s" % (firmware_path / f["file"], address))
            result &= self.programmer.write(str(firmware_path / f["file"]), address)
            if not result:
                self.log_error(self.ErrorCode.dut_program_failed)
                break
            time.sleep(1)

        return {"result": result, "firmware_list": self.firmware_list}

    # define a function to extract the IOT
    def get_iot(self):
        try:
            self.iot =  self.programmer.extract_iot()
        except:
            self.iot = "iotNotRead"
        if(len(self.iot) == len("iot0D473230383233350041002B")):
            result = True
        else:
            self.log_error(self.ErrorCode.iot_validate_failed)
            result = False
            self.iot = "iotNotRead"
        return {"result": result, "iot":self.iot}