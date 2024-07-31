import time

from .jaguar_testcase import JaguarTestCase


class DigitalTestCase(JaguarTestCase):
    """
    Test case for excercising digital GPIOs on jaguar board
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.append_step("Digital input", self.digital_in)
        self.append_step("Digital output", self.digital_out)
        self.append_step("Magnetic switch", self.magnetic_switch)
        self.append_step("Pulse", self.pulse_input)

    def setup(self):
        self.interface.dc_power_en(True)
        self.interface.gpio_enable(True)
        self.interface.rs232_enable(True)
        self.interface.battery_power_en(False)
        time.sleep(0.5)

    def teardown(self):
        self.interface.gpio_enable(False)
        self.interface.rs232_enable(False)
        self.interface.dc_power_en(False)

    def digital_in(self):
        """
        DIGIN1, DIGIN2 to jaguar, read back via serial
        """
        result = True

        delay = 0.2
        # DIGIN1 = B4
        self.interface.set_dig_in(0, False)
        time.sleep(delay)
        self.interface.set_dig_in(1, False)
        time.sleep(delay)
        resp = self.target.read_pin("B", 4)
        if resp != 0:
            self.log_error(self.ErrorCode.digin1_clear_failed)
            result = False

        self.interface.set_dig_in(0, True)
        time.sleep(delay)
        resp = self.target.read_pin("B", 4)
        if resp != 1:
            self.log_error(self.ErrorCode.digin1_set_failed)
            result = False

        resp = self.target.read_pin("B", 3)
        time.sleep(delay)
        if resp != 0:
            self.log_error(self.ErrorCode.digin2_clear_failed)
            result = False

        self.interface.set_dig_in(1, True)
        time.sleep(delay)
        resp = self.target.read_pin("B", 3)
        if resp != 1:
            self.log_error(self.ErrorCode.digin2_set_failed)
            result = False

        self.interface.set_dig_in(0, False)
        time.sleep(delay)
        self.interface.set_dig_in(1, False)
        time.sleep(delay)

        return {"result": result}

    def digital_out(self):
        """
        Test DIG_OUT[1..4] on Jaguar.
        Pins:
            DIG_OUT1 : A15
            DIG_OUT2 : C0
            DIG_OUT3 : C11
            DIG_OUT4 : C12

        0) GPIO enable
        1) enable Digital out power
        2) for each pin
            - set low
            - set high
            - compare
        """
        result = True
        d = 0.2
        self.interface.dig_out_power_enable(True)
        self.target.set_pin("A", 15, 0)
        time.sleep(d)
        self.target.set_pin("C", 0, 0)
        time.sleep(d)
        self.target.set_pin("C", 11, 0)
        time.sleep(d)
        self.target.set_pin("C", 12, 0)
        time.sleep(d)

        # all clear
        dig_out = self.interface.read_dig_out()
        if dig_out != (True, True, True, True):
            self.log_error(self.ErrorCode.digout_clear_failed)
            result = False

        # DIG_OUT1
        self.target.set_pin("A", 15, 1)
        time.sleep(d)
        dig_out = self.interface.read_dig_out()
        if dig_out[0] != False:
            self.log_error(self.ErrorCode.digout1_set_failed)
            result = False
        self.target.set_pin("A", 15, 0)

        # C0
        self.target.set_pin("C", 0, 1)
        time.sleep(d)
        dig_out = self.interface.read_dig_out()
        if dig_out[1] != False:
            self.log_error(self.ErrorCode.digout2_set_failed)
            result = False
        self.target.set_pin("C", 0, 0)

        # C11
        self.target.set_pin("C", 11, 1)
        time.sleep(d)
        dig_out = self.interface.read_dig_out()
        if dig_out[2] != False:
            self.log_error(self.ErrorCode.digout3_set_failed)
            result = False
        self.target.set_pin("C", 11, 0)

        # C12
        self.target.set_pin("C", 12, 1)
        time.sleep(d)
        dig_out = self.interface.read_dig_out()
        if dig_out[3] != False:
            self.log_error(self.ErrorCode.digout4_set_failed)
            result = False
        self.target.set_pin("C", 12, 0)

        self.interface.dig_out_power_enable(False)
        return {"result": result}

    def magnetic_switch(self):
        """
        Enable,disable electromagnet, read back pin.
        """
        result = True
        d = 1

        self.interface.set_electromagnet(0, False)
        time.sleep(d)
        readback = self.target.read_pin("A", 0)
        if readback != 1:
            result = False
            self.log_error(self.ErrorCode.mag_sense)
        self.interface.set_electromagnet(0, True)
        time.sleep(d)
        readback = self.target.read_pin("A", 0)
        if readback != 0:
            result = False
            self.log_error(self.ErrorCode.mag_sense)
        result = True

        self.interface.set_electromagnet(1, False)
        time.sleep(d)
        readback = self.target.read_pin("C", 13)
        if readback != 0:
            result = False
            self.log_error(self.ErrorCode.mag_wake)
        self.interface.set_electromagnet(1, True)
        time.sleep(d)
        readback = self.target.read_pin("C", 13)
        if readback != 1:
            result = False
            self.log_error(self.ErrorCode.mag_wake)
        return {"result": result}

    def pulse_input(self):
        """
        Read pulse counter, toggle pin, read pulse counter
        """
        result = True
        # clear counter
        count_log = {}
        self.target.read_pulse_count()
        # 0, 1, 5, and 10 pulses
        for i in [1, 5, 10]:
            d = 0.05
            for j in range(i):
                self.interface.pulse(1, 0)
                time.sleep(d)
                self.interface.pulse(1, 1)
                time.sleep(d)
            count = self.target.read_pulse_count()
            if count != i:
                result = False
                self.log_error(self.ErrorCode.pulse_count_mismatch)
            count_log[i] = count

        return {"result": result, **count_log}
