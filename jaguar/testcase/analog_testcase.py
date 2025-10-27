import time

from .jaguar_testcase import JaguarTestCase


class AnalogTestCase(JaguarTestCase):
    """
    Analog checks with board-type aware power sequencing.

    - V1:
        * Legacy behavior: enable DC power, disable battery
        * Steps: "Analog inputs" (AIN[0/1]) + "VSys level" (ADC-based)
    - V2:
        * Legacy power path (same as V1) unless changed later
        * Steps: "VSys level" only (no Analog inputs)
    - V3:
        * Battery-powered path: DC OFF, Battery ON, optional v3_power_en(True)
        * Steps: "VSys level" using measure_v3_voltage("V_SYS") if available,
                 else safe fallback
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
        self.vsys_min = vsys_min
        self.vsys_max = vsys_max
        self._used_v3_power = False

        # Keep legacy behavior for V1 (has Analog inputs step) and include VSys for all
        if 'V1' in self.board_type:
            self.append_step("Analog inputs", self.analog_in)

        # Always include VSys level step; required for V3
        self.append_step("VSys level", self.analog_vsys_level)

        # Thresholds for the V1 analog_in verification
        self.thresholds = [
            [vlow_min, vlow_max],
            [vmid_min, vmid_max],
            [vhigh_min, vhigh_max]
        ]

        print(f"[AnalogTestCase] init board_type={board_type}  "
              f"vsys_min={vsys_min}  vsys_max={vsys_max}")

    # -------------------- Power Setup --------------------

    def _setup_power_v3(self):
        print("Setup[V3]: ensuring battery power path...")
        # DC OFF
        try:
            self.interface.dc_power_en(False)
            print("  DC power -> OFF")
        except Exception:
            pass

        # Optional dedicated V3 rail
        try:
            if hasattr(self.interface, "v3_power_en"):
                self.interface.v3_power_en(True)
                self._used_v3_power = True
                print("  V3 power -> ON")
        except Exception:
            self._used_v3_power = False

        # Battery ON + helpful rails
        for fn_name, desc in [
            ("battery_power_en", "Battery -> ON"),
            ("gpio_enable", "GPIO -> ON"),
            ("rs232_enable", "RS232 -> ON"),
        ]:
            try:
                getattr(self.interface, fn_name)(True)
                print(f"  {desc}")
            except Exception:
                pass

        # Analog measurement path ON
        self.interface.analog_enable(True)
        print("  Analog path -> ENABLED")
        time.sleep(0.5)

    def _setup_power_legacy(self):
        print("Setup[Legacy]: enabling DC power path...")
        try:
            self.interface.gpio_enable(True)
            print("  GPIO -> ON")
        except Exception:
            pass
        try:
            self.interface.rs232_enable(True)
            print("  RS232 -> ON")
        except Exception:
            pass
        try:
            self.interface.dc_power_en(True)
            print("  DC power -> ON")
        except Exception:
            pass
        try:
            self.interface.battery_power_en(False)
            print("  Battery -> OFF")
        except Exception:
            pass

        self.interface.analog_enable(True)
        print("  Analog path -> ENABLED")
        time.sleep(0.5)

    def setup(self):
        print("\n=== ANALOG_TEST ===")
        print(f"Setup: board_type={self.board_type}")

        if self.board_type == 'V3':
            self._setup_power_v3()
        else:
            # Keep existing behavior for V1/V2
            self._setup_power_legacy()

    # -------------------- Test Steps ---------------------

    def analog_in(self):
        """
        V1 only: Apply voltages to analog inputs, read back over serial port.
        Uses same math and error codes as legacy implementation.
        """
        result = True
        values = [[-1, -1], [-1, -1], [-1, -1]]

        sys_voltage = self.interface.sys_voltage()

        def adc_to_v(a):
            return a / 4096 * sys_voltage

        for dac_index, dac in enumerate([1, 2]):
            for level, input_val in enumerate([0, 128, 255]):
                try:
                    self.interface.set_dac(dac, input_val)
                except Exception:
                    pass
                time.sleep(0.2)
                readback = self.target.read_adc()[dac_index]
                if readback == -1:
                    result = False
                    self.log_error(self.ErrorCode.adc_not_read)
                v_dut = adc_to_v(readback)

                values[level][dac_index] = v_dut

                th_min, th_max = self.thresholds[level]
                if th_min > v_dut:
                    result = False
                    self.log_error(self.ErrorCode.adc_vmin_exceeded)
                if th_max < v_dut:
                    result = False
                    self.log_error(self.ErrorCode.adc_vmax_exceeded)
        return {"result": result, "values": values, "vsys": sys_voltage}

    def analog_vsys_level(self):
        """
        VSys check:
          - On V3: prefer measure_v3_voltage("V_SYS") if provided by the interface.
          - On V1/V2: use ADC-based approach with sys_voltage() scaling.
        Bounds (vsys_min/max) are optional; None disables that bound.
        """
        print("[ANALOG_TEST] measuring VSYS...")
        result = True
        skipped = []

        if self.board_type == 'V3':
            # V3 path: ask fixture for direct V_SYS if available
            try:
                if hasattr(self.interface, "measure_v3_voltage"):
                    vsys = float(self.interface.measure_v3_voltage("V_SYS"))
                    print(f"  VSYS (via V3 route): {vsys:.3f} V")
                else:
                    # Fall back to overall system voltage if specific probe not available
                    vsys = float(self.interface.sys_voltage())
                    print(f"  VSYS (fallback sys_voltage): {vsys:.3f} V")
            except Exception:
                # Final fallback to sys_voltage on any error
                vsys = float(self.interface.sys_voltage())
                print(f"  VSYS (fallback sys_voltage): {vsys:.3f} V")
        else:
            # Legacy ADC read of Vsys channel (index 2), scaled by sys_voltage
            sys_voltage = float(self.interface.sys_voltage())

            def adc_to_v(a):
                return a / 4096 * sys_voltage

            readback = self.target.read_adc()[2]
            if readback == -1:
                self.log_error(self.ErrorCode.adc_not_read)
            vsys = adc_to_v(readback)
            print(f"  VSYS (ADC-based): {vsys:.3f} V  [sys={sys_voltage:.3f} V]")

        # Bounds check if provided
        if self.vsys_min is not None:
            print(f"  Check min ≥ {self.vsys_min:.3f} V")
            if vsys < self.vsys_min:
                self.log_error(self.ErrorCode.adc_vsys_min_exceeded)
                print("   ❌ BELOW MIN")
                result = False
        else:
            skipped.append("min")

        if self.vsys_max is not None:
            print(f"  Check max ≤ {self.vsys_max:.3f} V")
            if vsys > self.vsys_max:
                self.log_error(self.ErrorCode.adc_vsys_max_exceeded)
                print("   ❌ ABOVE MAX")
                result = False
        else:
            skipped.append("max")

        if skipped and len(skipped) == 2:
            print("  → All bounds skipped → INFORMATIONAL PASS")
            result = True

        print(f"[ANALOG_TEST] result={'PASS' if result else 'FAIL'}\n")
        return {"result": result, "vsys": vsys, "skipped": skipped}

    # -------------------- Teardown -----------------------

    def teardown(self):
        print("[ANALOG_TEST] teardown...")

        # Shared clean-up
        try:
            self.interface.set_dac(1, 0)
        except Exception:
            pass
        try:
            self.interface.set_dac(2, 0)
        except Exception:
            pass

        # Disable helper rails if present
        for fn_name, desc in [
            ("gpio_enable", "GPIO -> OFF"),
            ("rs232_enable", "RS232 -> OFF"),
        ]:
            try:
                getattr(self.interface, fn_name)(False)
                print(f"  {desc}")
            except Exception:
                pass

        # Analog path off
        try:
            self.interface.analog_enable(False)
            print("  Analog path -> DISABLED")
        except Exception:
            pass

        # Power rails off (handle both legacy and V3 paths)
        if self.board_type == 'V3':
            try:
                self.interface.battery_power_en(False)
                print("  Battery -> OFF")
            except Exception:
                pass
            if self._used_v3_power:
                try:
                    self.interface.v3_power_en(False)
                    print("  V3 power -> OFF")
                except Exception:
                    pass
            try:
                self.interface.dc_power_en(False)
                print("  DC power -> OFF")
            except Exception:
                pass
        else:
            # Legacy leaves DC ON during test; turn it off on exit
            try:
                self.interface.dc_power_en(False)
                print("  DC power -> OFF")
            except Exception:
                pass
            try:
                self.interface.battery_power_en(False)
                print("  Battery -> OFF")
            except Exception:
                pass
