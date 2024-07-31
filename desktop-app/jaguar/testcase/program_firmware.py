import time
from pathlib import Path

from .jaguar_testcase import JaguarTestCase


class ProgramFirmwareTestCase(JaguarTestCase):
    """
    Super class of test cases the use STlink to program firmware

    Tested
    """

    def __init__(self, firmware_list: list, erase=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.firmware_list = firmware_list
        if erase:
            self.append_step("Erase", self.erase)
        self.append_step("Flash", self.flash)

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
            self.event_logger.info("Flashing %s %s" % (firmware_path / f["file"], address))
            result &= self.programmer.write(str(firmware_path / f["file"]), address)
            if not result:
                self.log_error(self.ErrorCode.dut_program_failed)
                break
            time.sleep(1)

        return {"result": result, "firmware_list": self.firmware_list}
