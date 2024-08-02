import time

from .jaguar_testcase import JaguarTestCase


class AnalogTestCase(JaguarTestCase):
    """
    Test case for analog inputs and outputs
    
    Analog in:
        Apply 0, 1.6V, 3.2V to AIN[01], read back through DUT serial port.
        The DUT has protection resistors on analog inputs, compare with expected voltages at DUT pins.

        Compare 
        0V in < vlow_max out
        vmid_min <1.6V in < vmid_max out
        3.2V in < vhigh_min out


        "vlow_min":0.00  Min voltage on ADC8/9 for input voltage of 0V
        "vlow_max":0.05  Max voltage on ADC8
        "vmid_min":0.5  Min voltage on ADC8/9 for input voltage of 1.6V
        "vmid_max":0.6  Min voltage on ADC8/9 for input voltage of 1.6V
        "vhigh_min":1.0 Min voltage on ADC8/9 for input voltage of 3.2V
        "vhigh_max":1.2 Min voltage on ADC8/9 for input voltage of 3.2V

        "vsys_min":1.65 Min value on ADC15 (vbat measurement terminal)
        "vsys_max":1.85 Max value on ADC15 (vbat measurement terminal)
    """

    def __init__(self,
                 vlow_min=0, vlow_max=0.05,
                 vmid_min=0.5, vmid_max=0.6,
                 vhigh_min=1.0, vhigh_max=1.2,
                 vsys_min=1.7, vsys_max=1.8,
                 board_type='V1',
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.board_type = board_type

        if('V1' in self.board_type):
            self.append_step("Analog inputs", self.analog_in)
        self.append_step("VSys level", self.analog_vsys_level)

        self.thresholds = [
            [vlow_min, vlow_max],
            [vmid_min, vmid_max],
            [vhigh_min, vhigh_max]
        ]
        self.vsys_min = vsys_min
        self.vsys_max = vsys_max

    def setup(self):
        self.interface.gpio_enable(True)
        self.interface.rs232_enable(True)
        self.interface.dc_power_en(True)
        self.interface.battery_power_en(False)
        self.interface.analog_enable(True)
        time.sleep(0.5)

    def analog_in(self):
        """
        Apply voltages to analog inputs, read back over serial port.
        """
        result = True
        values = [[-1, -1], [-1, -1], [-1, -1]]

        sys_voltage = self.interface.sys_voltage()

        def adc_to_v(a):
            return (a) / 4096 * sys_voltage

        for dac_index, dac in enumerate([1, 2]):
            for level, input_val in enumerate([0, 128, 255]):
                # print("level", level)
                self.interface.set_dac(dac, input_val)
                time.sleep(0.2)
                readback = self.target.read_adc()[dac_index]
                if readback == -1:
                    result = False
                    self.log_error(self.ErrorCode.adc_not_read)
                v_dut = adc_to_v(readback)

                values[level][dac_index] = v_dut
                # print("Compare vdut ",v_dut," to ", self.thresholds[level])
                th_min = self.thresholds[level][0]
                th_max = self.thresholds[level][1]

                if th_min > v_dut:
                    result = False
                    # print("th_min > v_dut")
                    self.log_error(self.ErrorCode.adc_vmin_exceeded)
                if th_max < v_dut:
                    result = False
                    # print("th_max < v_dut")
                    self.log_error(self.ErrorCode.adc_vmax_exceeded)
        return {"result": result, "vsys": sys_voltage, "values": values}

    def analog_vsys_level(self):
        """
        The DUT ADC is supposed to measure 0.5 * Vsys = 0.5 * 3.5 = 1.75.  
        However, we experimentally observe a higher value read by the ADC, 
        around 2.2V.  This may be due to the large discharge time on the ADC input cap 
        - it is pulled high until measurement and is discharging at the time of measuring.
        """
        result = True
        sys_voltage = self.interface.sys_voltage()

        def adc_to_v(a):
            return (a) / 4096 * sys_voltage

        readback = self.target.read_adc()[2]
        # print("raw", readback)
        if readback == -1:
            self.log_error(self.ErrorCode.adc_not_read)
        v_sys_dut = adc_to_v(readback)

        if self.vsys_min > v_sys_dut:
            self.log_error(self.ErrorCode.adc_vsys_min_exceeded)
            result = False
        if self.vsys_max < v_sys_dut:
            self.log_error(self.ErrorCode.adc_vsys_max_exceeded)
            result = False
        return {"result": result, "vsys": sys_voltage, "vsys_dut": v_sys_dut}

    def teardown(self):
        self.interface.set_dac(1, 0)
        self.interface.set_dac(2, 0)
        self.interface.gpio_enable(False)
        self.interface.rs232_enable(False)
        self.interface.dc_power_en(False)
        self.interface.analog_enable(False)
        self.interface.battery_power_en(False)
