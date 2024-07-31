import time

from .jaguar_testcase import JaguarTestCase


class MemoryProtectTestcase(JaguarTestCase):
    def __init__(self, rdp_level=1, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.rdp_level = rdp_level
        self.append_step("Set RDP", self.set_rdp)
        self.append_step("Validate RDP", self.read_rdp)

    def setup(self):
        self.interface.dc_power_en(True)
        self.interface.battery_power_en(False)
        self.interface.analog_enable(True)
        self.interface.jtag_enable(True)
        time.sleep(1)

    def teardown(self):
        self.interface.dc_power_en(False)
        self.interface.battery_power_en(False)
        self.interface.analog_enable(False)
        self.interface.rs232_enable(False)
        self.interface.jtag_enable(False)
        time.sleep(1)

    def set_rdp(self):
        """
        Set readout protection
        """
        if self.rdp_level not in [0, 1, 2]:
            raise Exception("Invalid RDP level")

        result = self.programmer.set_rdp(self.rdp_level)
        if not result:
            self.log_error(self.ErrorCode.rdp_set_failed)
        return {"result": result, "level": self.rdp_level}

    def read_rdp(self):
        """
        Restart device, read RDP
        """
        result = True
        rdp = self.programmer.read_rdp()

        if rdp == "AA":
            level = 0
        elif rdp == "CC":
            level = 2
        else:
            level = 1

        # if the RDP is set to level 1 then you cannot read the option bytes either, you will fail to read it.
        # (options are: 0 for no protection, 1 for temporary read protection, 2 for permanent read protection)
        # if level != self.rdp_level or rdp is None:
        if level != self.rdp_level:
            self.log_error(self.ErrorCode.rdp_validate_failed)
            result = False

        return {"result": result, "rdp_value": rdp, "rdp_level": level}
