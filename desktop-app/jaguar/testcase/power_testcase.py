import time
from statistics import mean

from .jaguar_testcase import JaguarTestCase


class PowerTestCase(JaguarTestCase):
    """
    Super class of power supply tests
    """

    def __init__(self, v_min=3.2, v_max=3.4, i_min=0.002, i_max=0.200, samples=10, delay=1, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.v_min = v_min
        self.v_max = v_max
        self.i_min = i_min
        self.i_max = i_max
        self.samples = samples
        self.delay = delay

    def setup(self):
        self.interface.power_off()
        self.interface.analog_enable(True)
        time.sleep(0.2)

    def teardown(self):
        self.interface.analog_enable(False)
        time.sleep(0.2)

    def capture(self):
        """
        Capture data
        """
        v_dc = []
        v_bat = []
        v_sys = []
        i_bat = []
        i_dc = []
        for i in range(10):
            time.sleep(0.1)
            v_dc.append(self.interface.dc_voltage())
            v_bat.append(self.interface.battery_voltage())
            v_sys.append(self.interface.sys_voltage())
            i_dc.append(self.interface.dc_current())
            i_bat.append(self.interface.battery_current())

        return v_dc, v_bat, v_sys, i_dc, i_bat


class DCPowerTestCase(PowerTestCase):
    """
    Apply DC power, measure Vsys and supply current

    Test ID: DC_POWER
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.append_step("Supply DC power", self.power_test)

    def power_test(self):
        """
        Apply battery power
        - Measure Vsys, expected to be around 3.3V
        - Measure supply current
        - Measure DC supply voltage, expect < 0.5V (We observe a 180mV offset from the DC current sense IC.
        Turn off battery power
        - Wait for Vsys to drop to <1V.

        Log Vsys, i_bat, v_dc

        TODO:
        i dc seems too small/noisy.
        """
        result = True
        self.interface.dc_power_en(True)
        time.sleep(self.delay)

        v_dc, v_bat, v_sys, i_dc, i_bat = self.capture()
        print(i_dc)
        print(i_bat)

        if min(v_sys) < self.v_min:
            self.log_error(self.ErrorCode.vsys_dc_min)
            self.event_logger.info("vsys_dc=%f < v_min=%f" % (min(v_sys), self.v_min))
            result = False
        if max(v_sys) > self.v_max:
            self.log_error(self.ErrorCode.vsys_dc_max)
            self.event_logger.info("vsys_dc=%f > v_min=%f" % (max(v_sys), self.v_max))
            result = False

        if min(i_dc) < self.i_min:
            self.log_error(self.ErrorCode.dc_current_min)
            self.event_logger.info("i_dc=%f < i_min=%f" % (min(i_dc), self.i_min))
            result = False
        if max(i_dc) > self.i_max:
            self.log_error(self.ErrorCode.dc_current_max)
            self.event_logger.info("i_dc=%f > i_min=%f" % (max(i_dc), self.i_max))
            result = False

        return {"result": result, "v_dc": mean(v_dc), "v_min": min(v_sys), "v_max": max(v_sys), "i_min": min(i_dc),
                "i_max": max(i_dc)}


class BatPowerTestCase(PowerTestCase):
    """
    Apply battery power, measure Vsys and supply current

    Test ID: BAT_POWER
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.append_step("Supply battery power", self.power_test)

    def power_test(self):
        """
        Apply battery power
        - Measure Vsys, expected to be around 3.3V
        - Measure supply current
        - Measure DC supply voltage, expect < 0.5V (We observe a 180mV offset from the DC current sense IC.
        Turn off battery power
        - Wait for Vsys to drop to <1V.

        Log Vsys, i_bat, v_dc

        TODO:
        apply power to VBAT2
        i bat seems noisy.
        """
        result = True
        self.interface.battery_power_en(True)
        time.sleep(self.delay)

        v_dc, v_bat, v_sys, i_dc, i_bat = self.capture()

        if min(v_sys) < self.v_min:
            self.log_error(self.ErrorCode.vsys_bat_min)
            self.event_logger.info("vsys_bat=%f < v_min=%f" % (min(v_sys), self.v_min))
            result = False
        if max(v_sys) > self.v_max:
            self.log_error(self.ErrorCode.vsys_bat_max)
            self.event_logger.info("vsys_bat=%f > v_max=%f" % (max(v_sys), self.v_max))
            result = False

        if min(i_bat) < self.i_min:
            self.log_error(self.ErrorCode.bat_current_min)
            self.event_logger.info("i_bat=%f < i_min=%f" % (min(i_bat), self.i_min))
            result = False
        if max(i_bat) > self.i_max:
            self.log_error(self.ErrorCode.bat_current_max)
            self.event_logger.info("i_bat=%f > i_max=%f" % (max(i_bat), self.i_max))
            result = False

        return {"result": result, "v_bat": mean(v_bat), "v_min": min(v_sys), "v_max": max(v_sys), "i_min": min(i_bat),
                "i_max": max(i_bat)}
