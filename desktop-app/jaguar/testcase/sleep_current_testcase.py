import time
from statistics import mean

from .jaguar_testcase import JaguarTestCase


class SleepCurrentTestCase(JaguarTestCase):
    """
    Run from Vbat, enter sleep mode ("p"), measure i_bat

    """

    def __init__(self, i_min=0.00001, i_max=0.001, samples=10, delay=1, *args, **kwargs):
        """
        i_min minimum current threshold
        i_max maximum current threshold
        samples: number of samples to measure
        delay: time between enter sleep mode and data capture start
        """
        super().__init__(*args, **kwargs)
        self.i_min = i_min
        self.i_max = i_max
        self.samples = samples
        self.delay = delay

        self.append_step("Enter sleep mode", self.enter_sleep_mode)
        self.append_step("Measure", self.measure)

    def setup(self):
        self.interface.dc_power_en(False)
        self.interface.battery_power_en(False)
        self.interface.analog_enable(True)
        self.interface.jtag_enable(False)
        time.sleep(1)
        self.interface.dc_power_en(False)
        self.interface.battery_power_en(True)
        self.interface.analog_enable(True)
        self.interface.rs232_enable(True)

    def teardown(self):
        self.interface.dc_power_en(False)
        self.interface.battery_power_en(False)
        self.interface.analog_enable(False)
        self.interface.rs232_enable(False)

    def enter_sleep_mode(self):
        self.target.enter_sleep_mode()
        self.interface.rs232_enable(False)
        time.sleep(self.delay)
        return {"result": True}

    def measure(self):
        result = True
        samples = []
        for i in range(self.samples):
            time.sleep(0.1)
            samples.append(self.interface.battery_current())

        self.event_logger.info("Sleep current %s" % str(samples))
        if mean(samples) < self.i_min:
            result = False
            self.log_error(self.ErrorCode.sleep_current_min)
        if mean(samples) > self.i_max:
            result = False
            self.log_error(self.ErrorCode.sleep_current_max)

        avg = sum(samples) / len(samples)

        return {"result": result, "samples": self.samples, "i_min": min(samples), "i_max": max(samples), "i_mean": avg}
