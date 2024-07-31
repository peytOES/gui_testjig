"""
Jaguar interface board
"""
import time

from birch.peripheral.interface import Interface
from birch.peripheral.util import find_port
from birch.test_status import TestStatus

# from .jaguar_interface_ll import JaguarInterfaceLowLevel
from .jaguar_interface.jaguar_interface_ll import JaguarInterfaceLL
from .jaguar_interface.JaguarFixture import JaguarFixtureLED


class JaguarInterface(Interface):
    VID = '0483'
    PID = '5740'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interface = None

    def open(self):
        port = find_port(vid=self.VID, pid=self.PID)
        if port is None:
            return False
        self.interface = JaguarInterfaceLL(port)
        return True

    # status indication
    def set_led(self, status, value):
        """
        Set status leds
        """
        if status == TestStatus.PASS:
            self.interface.set_led(JaguarFixtureLED.LED_PASS, value)
            self.interface.set_led(JaguarFixtureLED.LED_FAIL, 0)
            self.interface.set_led(JaguarFixtureLED.LED_BUSY, 0)
        elif status == TestStatus.FAIL or status == TestStatus.ERROR:
            self.interface.set_led(JaguarFixtureLED.LED_PASS, 0)
            self.interface.set_led(JaguarFixtureLED.LED_BUSY, 0)
            self.interface.set_led(JaguarFixtureLED.LED_FAIL, value)
        elif status == TestStatus.INCOMPLETE:
            self.interface.set_led(JaguarFixtureLED.LED_BUSY, value)
            self.interface.set_led(JaguarFixtureLED.LED_PASS, 0)
            self.interface.set_led(JaguarFixtureLED.LED_FAIL, 0)
        elif status == TestStatus.UNTESTED:
            self.interface.set_led(JaguarFixtureLED.LED_PASS, 0)
            self.interface.set_led(JaguarFixtureLED.LED_FAIL, 0)
            self.interface.set_led(JaguarFixtureLED.LED_BUSY, 0)

    # ADC measurements
    def battery_current(self):
        """
        Current on VBAT power line (A)
        """
        return self.interface.battery_current()

    def dc_current(self):
        """
        Current on DC power input
        """
        return self.interface.dc_current()

    def battery_voltage(self):
        """
        Voltage on VBAT input
        """
        return self.interface.battery_voltage()

    def dc_voltage(self):
        """
        Voltage on DC input
        """
        return self.interface.dc_voltage()

    def modem_voltage(self):
        """
        Voltage on DUT at Vmdm
        """
        return self.interface.modem_voltage()

    def sys_voltage(self):
        """
        DUT Vsys voltage
        """
        return self.interface.sys_voltage()

    def dc_power_en(self, value):
        return self.interface.dc_power_en(value)

    def battery_power_en(self, value):
        return self.interface.battery_power_en(value)

    def set_electromagnet(self, index, value):
        """
        Set electromagnet with index to value (True, False)
        """
        return self.interface.set_mag(index, value)

    def set_dac(self, index, value: float):
        """
        Set DAC (1/2)
        Valuge is float 0-1
        """
        self.interface.set_dac(index, value)

    def dut_present(self, *args, **kwargs):
        # print("Bypassing dut_present")
        # return True
        return self.interface.dut_present()

    def gpio_enable(self, enable):
        self.interface.gpio_enable(enable)

    def dig_out_power_enable(self, enable):
        self.interface.dig_out_power_enable(enable)

    def read_dig_out(self):
        a = self.interface.read_dig_out()[::-1]
        print("read_dig_out", a)
        return a

    def set_dig_in(self, index, value):
        return self.interface.set_dig_in(index, value)

    def fixture_detect(self, level):
        self.interface.fixture_detect(level)

    def power_off(self):
        """
        Turn off all power, wait for Vsys to drop to 1V
        """
        time.sleep(0.2)
        self.interface.rs232_enable(False)
        self.interface.jtag_enable(False)
        self.interface.battery_power_en(False)
        self.interface.dc_power_en(False)
        self.interface.set_cal_switch([True] * 5)
        self.interface.analog_enable(True)
        count = 0
        while self.sys_voltage() > 0.1 and count < 10:  # add timeout
            print("JaguarInterface.sys_voltage()", self.sys_voltage())
            time.sleep(0.25)
            count += 1
        self.interface.set_cal_switch([False] * 5)
        self.interface.analog_enable(False)

    def jtag_enable(self, value):
        self.interface.jtag_enable(value)

    def analog_enable(self, value):
        self.interface.analog_enable(value)

    def rs232_enable(self, value):
        self.interface.rs232_enable(value)

    def pulse(self, channel, value):
        """
        Set LFP input high or low.  
        """
        self.interface.pulse(channel, value)

    def close(self):
        self.interface.close()
