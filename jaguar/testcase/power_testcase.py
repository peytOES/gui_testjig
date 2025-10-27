import time
from statistics import mean

from .jaguar_testcase import JaguarTestCase
class PowerTestCase(JaguarTestCase):
    """
    Simple power test base for V3 hardware.

    - If a bound (min/max) is None, that check is skipped.
    - If *all* checks are skipped, we mark the test as informational PASS.
    """

    def __init__(
        self,
        v_min=None,            # Lower bound for Vsys (None = skip)
        v_max=None,            # Upper bound for Vsys (None = skip)
        i_min=None,            # Lower bound for current (None = skip)
        i_max=None,            # Upper bound for current (None = skip)
        samples=10,            # Number of samples to take
        delay=1.0,             # Settle time after enabling rails
        sample_interval=0.1,   # Delay between samples
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.v_min = v_min
        self.v_max = v_max
        self.i_min = i_min
        self.i_max = i_max
        self.samples = samples
        self.delay = delay
        self.sample_interval = sample_interval

        print(f"[PowerTestCase] init  v_min={v_min} v_max={v_max}  "
              f"i_min={i_min} i_max={i_max}  samples={samples} "
              f"delay={delay}s interval={sample_interval}s")

    # ---- lifecycle ----
    def setup(self):
        print("[PowerTestCase] setup: power_off, analog_enable(True)")
        self.interface.power_off()
        self.interface.analog_enable(True)
        time.sleep(0.2)

    def teardown(self):
        print("[PowerTestCase] teardown: power_off, analog_enable(False)")
        self.interface.power_off()
        self.interface.analog_enable(False)
        time.sleep(0.2)

    # ---- sampling ----
    def capture(self):
        """Capture a small window of measurements."""
        print(f"[capture] {self.samples} samples @ {self.sample_interval}s")
        v_dc, v_bat, v_sys, i_dc, i_bat = [], [], [], [], []
        for _ in range(self.samples):
            time.sleep(self.sample_interval)
            v_dc.append(self.interface.dc_voltage())
            v_bat.append(self.interface.battery_voltage())
            v_sys.append(self.interface.sys_voltage())
            i_dc.append(self.interface.dc_current())
            i_bat.append(self.interface.battery_current())

        def stats(name, arr):
            if not arr:
                print(f"  {name}: no data")
                return None, None, None
            m = mean(arr)
            mn, mx = min(arr), max(arr)
            print(f"  {name}: mean={m:.6f}  min={mn:.6f}  max={mx:.6f}  (n={len(arr)})")
            return m, mn, mx

        print("→ summary:")
        vdc_mean, vdc_min, vdc_max = stats("VDC", v_dc)
        vbat_mean, vbat_min, vbat_max = stats("VBAT", v_bat)
        vsys_mean, vsys_min, vsys_max = stats("VSYS", v_sys)
        idc_mean, idc_min, idc_max = stats("IDC", i_dc)
        ibat_mean, ibat_min, ibat_max = stats("IBAT", i_bat)

        return (
            (vdc_mean, vdc_min, vdc_max, v_dc),
            (vbat_mean, vbat_min, vbat_max, v_bat),
            (vsys_mean, vsys_min, vsys_max, v_sys),
            (idc_mean, idc_min, idc_max, i_dc),
            (ibat_mean, ibat_min, ibat_max, i_bat),
        )

    # ---- bound checking (simple prints) ----
    def _check_bounds(self, series_vals, lo, hi, err_lo, err_hi, label):
        """
        series_vals = (mean, min, max, raw_list)
        Returns (passed: bool, skipped: bool)
        """
        mean_v, mn, mx, series = series_vals
        if not series:
            print(f"[check {label}] no data → FAIL")
            self.log_error(err_lo)  # record something
            return False, False

        skip_lo = lo is None
        skip_hi = hi is None
        if skip_lo and skip_hi:
            print(f"[check {label}] bounds: min=SKIP max=SKIP → INFORMATIONAL")
            return True, True

        ok = True
        if not skip_lo:
            print(f"[check {label}] min≥{lo:.6f}? measured min={mn:.6f}")
            if mn < lo:
                ok = False
                self.log_error(err_lo)
        else:
            print(f"[check {label}] min=SKIP")

        if not skip_hi:
            print(f"[check {label}] max≤{hi:.6f}? measured max={mx:.6f}")
            if mx > hi:
                ok = False
                self.log_error(err_hi)
        else:
            print(f"[check {label}] max=SKIP")

        print(f"[check {label}] → {'PASS' if ok else 'FAIL'}")
        return ok, False

    def _finalize(self, checks):
        """
        checks: list of tuples (passed: bool, skipped_all_bounds: bool, label: str)
        If ALL checks had all bounds skipped → informational PASS (result=True, informational=True)
        Else → result = logical AND of passed flags.
        """
        all_skipped = all(skipped for _, skipped, _ in checks)
        if all_skipped:
            print("[finalize] all checks had no bounds → INFORMATIONAL PASS")
            return True, {"informational": True, "checks_skipped": [lbl for _, _, lbl in checks]}
        # normal case: at least one real check ran
        result = all(passed for passed, _, _ in checks)
        skipped = [lbl for _, skipped, lbl in checks if skipped]
        if skipped:
            print(f"[finalize] skipped (no bounds): {', '.join(skipped)}")
        print(f"[finalize] overall → {'PASS' if result else 'FAIL'}")
        return result, {"informational": False, "checks_skipped": skipped}


class DCPowerTestCase(PowerTestCase):
    """
    DC_POWER: Use DC input to power DUT and sample VSYS/IDC/VDC.
    This test is used mainly to set rails and log readings for Gen-V3.
    If no bounds are provided, it will PASS as informational.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.append_step("Supply DC power", self.power_test)

    def power_test(self):
        print("\n=== DC_POWER ===")
        print("Set rails: BAT=OFF, DC=ON")
        self.interface.battery_power_en(False)
        self.interface.dc_power_en(True)
        print(f"Settling {self.delay}s...")
        time.sleep(self.delay)

        vdc, vbat, vsys, idc, ibat = self.capture()

        print("Checking bounds:")
        pass_v, skip_v = self._check_bounds(vsys, self.v_min, self.v_max,
                                            self.ErrorCode.vsys_dc_min, self.ErrorCode.vsys_dc_max,
                                            "VSYS(DC)")
        pass_i, skip_i = self._check_bounds(idc, self.i_min, self.i_max,
                                            self.ErrorCode.dc_current_min, self.ErrorCode.dc_current_max,
                                            "IDC")

        result, meta = self._finalize([
            (pass_v, skip_v, "VSYS(DC)"),
            (pass_i, skip_i, "IDC"),
        ])

        payload = {
            "result": result,
            "v_dc": vdc[0],
            "v_sys_min": vsys[1],
            "v_sys_max": vsys[2],
            "i_dc_min": idc[1],
            "i_dc_max": idc[2],
            **meta,
        }
        print(f"[DC_POWER] payload: {payload}\n")
        return payload


class BatPowerTestCase(PowerTestCase):
    """
    BAT_POWER: Use battery rail to power DUT and sample VSYS/IBAT/VBAT.
    If no bounds are provided, it will PASS as informational.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.append_step("Supply battery power", self.power_test)

    def power_test(self):
        print("\n=== BAT_POWER ===")
        print("Set rails: DC=OFF, BAT=ON")
        self.interface.dc_power_en(False)
        self.interface.battery_power_en(True)
        print(f"Settling {self.delay}s...")
        time.sleep(self.delay)

        vdc, vbat, vsys, idc, ibat = self.capture()

        print("Checking bounds:")
        pass_v, skip_v = self._check_bounds(vsys, self.v_min, self.v_max,
                                            self.ErrorCode.vsys_bat_min, self.ErrorCode.vsys_bat_max,
                                            "VSYS(BAT)")
        pass_i, skip_i = self._check_bounds(ibat, self.i_min, self.i_max,
                                            self.ErrorCode.bat_current_min, self.ErrorCode.bat_current_max,
                                            "IBAT")

        result, meta = self._finalize([
            (pass_v, skip_v, "VSYS(BAT)"),
            (pass_i, skip_i, "IBAT"),
        ])

        payload = {
            "result": result,
            "v_bat": vbat[0],
            "v_sys_min": vsys[1],
            "v_sys_max": vsys[2],
            "i_bat_min": ibat[1],
            "i_bat_max": ibat[2],
            **meta,
        }
        print(f"[BAT_POWER] payload: {payload}\n")
        return payload
