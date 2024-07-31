"""
Generic interface hardware.
"""
from .device import Device


class Interface(Device):
    def open(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass

    def detect(self, *args, **kwargs):
        """
        Test if interface is present and accessible.
        """
        return True

    def dut_present(self, *args, **kwargs):
        """
        Return True is DUT is present
        """
        return True

    def set_led(self, *args, **kwargs):
        pass

    def power_off(self):
        pass
