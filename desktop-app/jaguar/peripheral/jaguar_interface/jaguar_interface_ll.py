import time
import logging

from .JaguarFixtureSession import JaguarFixtureSession
from .JaguarFixture import *


class JaguarInterfaceLL():
    event_logger = logging.getLogger("event_logger")

    def __init__(self, port):
        self.port = port
        self.fixture_session = None
        self.session = None
        self.open()

    def open(self):
        self.fixture_session = JaguarFixtureSession(self.port)
        self.event_logger.info("JaguarInterfaceLL: Setup complete, waiting for input...")
        self.session = self.fixture_session.jaguarFixture

    def close(self):
        self.fixture_session.close()
        self.session = None

    def analog_enable(self, enable):
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_ANALOG_EN, enable)

    def gpio_enable(self, enable):
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_GPIO_EN, enable)

    def jtag_enable(self, enable):
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_JTAG_EN, enable)

    def usb_enable(self, enable):
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_USB_EN, enable)

    def dig_out_power_enable(self, enable):
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_DIG_OUT_PWR, enable == False)

    def rs232_enable(self, enable):
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_RS232_EN, enable)

    def set_fixture_detect(self, enable):
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_FIXTURE_DETECT, enable)

    def set_led(self, led, value):
        self.session.set_led(led, value == 0)

    def set_dac(self, dac, value):
        if value > 255:
            self.event_logger.warning("JaguarInterfaceLL: Valid DAC range is 8 bits...")
            value = 255
        self.session.set_dac(dac, int(value))

    def battery_current(self):
        return self.session.adc_batt_current

    def battery_voltage(self):
        return self.session.adc_batt_voltage

    def battery_power_en(self, val):
        """
        Active low
        """
        return self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_EN_3V8, val == False)

    def dc_power_en(self, val):
        return self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_DC_EN, val)

    def battery_voltage(self):
        return self.session.adc_batt_voltage * (10 + 1) / 1

    def dc_voltage(self):
        return self.session.adc_dc_voltage * (10 + 1) / 1

    def input_switch(self):
        return "%d%d%d%d" % (
            self.session.gpio_input_switch_0,
            self.session.gpio_input_switch_1,
            self.session.gpio_input_switch_2,
            self.session.gpio_input_switch_3)

    def fixture_detect(self, level):
        """ active low"""
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_FIXTURE_DETECT, level)

    def battery_current(self):
        # print(self.session.gpio_input_switch_3,self.session.gpio_input_switch_2,self.session.gpio_input_switch_1,self.session.gpio_input_switch_0)
        if self.session.gpio_input_switch_3:
            """
            Calibration: Vbat/100 = 38mA
            """
            return (self.battery_voltage() / 100) / 0.0797 * self.session.adc_batt_current
        elif self.session.gpio_input_switch_2:
            # TODO: Not calibrated
            return (self.battery_voltage() / 100) / 0.69 * self.session.adc_batt_current
        elif self.session.gpio_input_switch_1:
            """
            Calibration: Vbat/1000 = 3.8mA
            """
            return (self.battery_voltage() / 1000) / 0.68 * self.session.adc_batt_current
        elif self.session.gpio_input_switch_0:
            """
            Calibration: Vbat/10k
            """
            return (self.battery_voltage() / 10000) / 0.6864 * self.session.adc_batt_current
        else:
            # 1M cal, 
            # Gives 33 instead of 38uA on CAL3
            # ret = (self.battery_voltage()/1000000) / 0.078149 * self.session.adc_batt_current - 620e-9
            # 100k cal, gives 3.7uA on CAL4
            ret = (self.battery_voltage() / 100000) / 0.687 * self.session.adc_batt_current - 620e-9

            if ret < 0:
                ret = 0
            return ret
        # print("Not calibrated")
        self.event_logger.warning("JaguarInterfaceLL: battery_current %s %s %s %s %f" % (
        self.session.gpio_input_switch_3, self.session.gpio_input_switch_2, self.session.gpio_input_switch_1,
        self.session.gpio_input_switch_0, self.session.adc_batt_current))
        return self.session.adc_batt_current

    def set_dig_in(self, index, value):
        if index == 0:
            return self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_DIG_IN_0, value)
        elif index == 1:
            return self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_DIG_IN_1, value)

    def set_mag(self, index, value):
        if index == 0:
            return self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_MAG_0, value == False)
        elif index == 1:
            return self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_MAG_1, value == False)

    def dc_current(self):
        return (self.session.adc_dc_current - 0.002) / 0.15 / 20

    def sys_voltage(self):
        """
        Scale by 
         
       ----|-- 20k -- 1k --  DUT
          10k 
           v
        """
        return (self.session.adc_sys_voltage * (31 / 10.))

    def modem_voltage(self):
        """
        Scale by 
         
       ----|-- 20k -- 1k --  DUT
          10k 
           v
        """
        return (self.session.adc_vmdm * (31 / 10.))

    def set_cal_switch(self, val):
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_CAL_LOAD_0, val[0])
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_CAL_LOAD_1, val[1])
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_CAL_LOAD_2, val[2])
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_CAL_LOAD_3, val[3])
        self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_CAL_LOAD_4, val[4])

    def pulse(self, channel, val):
        if channel == 1:
            self.session.set_gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_LFP_0, val)

    def dut_present(self):
        return self.session.gpio_input_lid_detect == 0

    def read_dig_out(self):
        return self.session.gpio_input_dig_out_rtn_3, self.session.gpio_input_dig_out_rtn_2, self.session.gpio_input_dig_out_rtn_1, self.session.gpio_input_dig_out_rtn_0


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s', level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

    j = JaguarInterfaceLL("/dev/ttyACM0")
    # j.fixture_detect(False)
    # j.power_off()
    time.sleep(0.1)
    j.session.set_led(1, 0)
    j.session.get_fw_version()
    time.sleep(0.5)

    j.analog_enable(True)
    j.battery_power_en(True)
    j.dc_power_en(False)
    j.jtag_enable(True)
    j.rs232_enable(False)
    for i in range(1000):
        # if i == 2:
        #    j.set_cal_switch([False, False, False, False, True])
        # if i == 7:
        #    j.battery_power_en(False)
        # if i == 8:
        #    j.dc_power_en(False)
        time.sleep(0.1)
        print("%d %0.6fmA %0.3f %0.3fV %0.3fV %0.3fV %0.3fV %0.3f %0.3f %s" % (
            j.session.counter,
            j.battery_current() * 1000,
            j.session.adc_dc_current,
            j.battery_voltage(),
            j.dc_voltage(),
            j.modem_voltage(),
            j.sys_voltage(),
            j.session.adc_4_20_ch0,
            j.session.adc_4_20_ch1,
            j.input_switch()))

    # j.power_off()
    j.close()
