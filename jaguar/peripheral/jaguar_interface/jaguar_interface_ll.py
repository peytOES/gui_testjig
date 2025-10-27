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
        # lightweight tracer; shows every GPIO write and snapshots
        self._trace = logging.getLogger("ll_pins").info
        self.open()

    def open(self):
        self.fixture_session = JaguarFixtureSession(self.port)
        self.event_logger.info("JaguarInterfaceLL: Setup complete, waiting for input...")
        self.session = self.fixture_session.jaguarFixture

    def close(self):
        self.fixture_session.close()
        self.session = None

    # ---------------- GPIO wrapper & helpers ----------------

    def _gpio(self, out_enum, val: bool):
        """Trace and write a fixture GPIO output in one place."""
        try:
            name = getattr(out_enum, "name", str(out_enum))
        except Exception:
            name = str(out_enum)
        self._trace(f"GPIO {name} <- {int(bool(val))}")
        return self.session.set_gpio(out_enum, bool(val))

    def _read_voltages_snapshot(self):
        """Take a one-line voltage snapshot and trace it: VDC/VBAT/VSYS."""
        try: vdc = float(self.dc_voltage())
        except Exception: vdc = float("nan")
        try: vbat = float(self.battery_voltage())
        except Exception: vbat = float("nan")
        try: vsys = float(self.sys_voltage())
        except Exception: vsys = float("nan")
        self._trace(f"SNAP VDC={vdc:.3f} VBAT={vbat:.3f} VSYS={vsys:.3f}")
        return vdc, vbat, vsys

    def sweep_outputs_effects(self, settle=0.25, skip_names=()):
        """
        Toggle each GPIO output ON then OFF while measuring VDC/VBAT/VSYS.
        Use with BAT OFF + DC ON to discover which output lifts VSYS (VSYS gate).
        Returns: dict[name] = {'off': (vdc,vbat,vsys), 'on': (vdc,vbat,vsys)}
        """
        results = {}
        time.sleep(0.1)
        for out in JaguarFixtureGPIOOutput:
            name = getattr(out, "name", str(out))
            if name in skip_names or name in ("GPIO_OUTPUT_NONE",):
                continue
            # Skip LEDs; they’re noisy and irrelevant for power path
            if "LFP" in name or "MAG_" in name or "LED" in name:
                pass  # ok to include, but harmless to toggle
            try:
                # OFF
                self._gpio(out, False)
                time.sleep(settle)
                off_snap = self._read_voltages_snapshot()
                # ON
                self._gpio(out, True)
                time.sleep(settle)
                on_snap = self._read_voltages_snapshot()
                # back OFF to leave fixture in a safe state
                self._gpio(out, False)
                time.sleep(0.05)
                results[name] = {"off": off_snap, "on": on_snap}
            except Exception as e:
                self._trace(f"SWEEP {name} error: {e}")
        return results

    def find_vsys_gate_candidate(self, settle=0.25):
        """
        With BAT OFF and DC ON, search for the output that increases VSYS the most.
        Returns: (best_name, delta_vsys_volts, results_dict)
        """
        # Preconditions (best-effort)
        try:
            self.dc_power_en(True)
            self.battery_power_en(False)
        except Exception:
            pass
        time.sleep(settle)
        _ = self._read_voltages_snapshot()

        # Avoid toggling the main enables inside the sweep (we set them already)
        skip = ("GPIO_OUTPUT_DC_EN", "GPIO_OUTPUT_EN_3V8")
        effects = self.sweep_outputs_effects(settle=settle, skip_names=skip)

        best, best_dv = None, 0.0
        for name, snaps in effects.items():
            dv = snaps["on"][2] - snaps["off"][2]  # VSYS delta
            if dv > best_dv:
                best, best_dv = name, dv

        self._trace(f"VSYS gate candidate: {best} (ΔVSYS={best_dv:.3f} V)")
        return best, best_dv, effects

    # ---------------- Existing LL API (now routed via _gpio) ----------------

    def analog_enable(self, enable):
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_ANALOG_EN, enable)

    def gpio_enable(self, enable):
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_GPIO_EN, enable)

    def jtag_enable(self, enable):
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_JTAG_EN, enable)

    def usb_enable(self, enable):
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_USB_EN, enable)

    def dig_out_power_enable(self, enable):
        # Active low on this rig
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_DIG_OUT_PWR, enable == False)

    def rs232_enable(self, enable):
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_RS232_EN, enable)

    def set_fixture_detect(self, enable):
        # Comment says 'active low' on board; keep current polarity unless you confirm inversion
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_FIXTURE_DETECT, enable)

    def set_led(self, led, value):
        # Fixture LED API is inverted (value==0 means ON); leave as-is
        self.session.set_led(led, value == 0)

    def set_dac(self, dac, value):
        if value > 255:
            self.event_logger.warning("JaguarInterfaceLL: Valid DAC range is 8 bits...")
            value = 255
        self.session.set_dac(dac, int(value))

    # -------- Rails / ADCs --------

    def battery_power_en(self, val):
        """Battery switch is active-low."""
        return self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_EN_3V8, val == False)

    def dc_power_en(self, val):
        return self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_DC_EN, val)

    # OPTIONAL (wire this after discovery): VSYS/load-switch gate
    def v3_power_en(self, val):
        """
        Bind this to the discovered enum that actually gates VSYS.
        Example (after discovery): GPIO_OUTPUT_DUT_RST or GPIO_OUTPUT_4_20_PWR, etc.
        """
        # TODO: replace GPIO_OUTPUT_VSYS_GATE with the real enum name you find
        return self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_GPIO_EN, bool(val))
        # ↑ TEMP: using GPIO_EN as a harmless default; update after find_vsys_gate_candidate()

    def battery_voltage(self):
        # Scaled in fixture: 10:1 divider (10 + 1)/1
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
        """Active low (board)."""
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_FIXTURE_DETECT, level)

    def battery_current(self):
        # (unchanged) — left as-is
        if self.session.gpio_input_switch_3:
            return (self.battery_voltage() / 100) / 0.0797 * self.session.adc_batt_current
        elif self.session.gpio_input_switch_2:
            return (self.battery_voltage() / 100) / 0.69 * self.session.adc_batt_current
        elif self.session.gpio_input_switch_1:
            return (self.battery_voltage() / 1000) / 0.68 * self.session.adc_batt_current
        elif self.session.gpio_input_switch_0:
            return (self.battery_voltage() / 10000) / 0.6864 * self.session.adc_batt_current
        else:
            ret = (self.battery_voltage() / 100000) / 0.687 * self.session.adc_batt_current - 620e-9
            if ret < 0:
                ret = 0
            return ret

    def set_dig_in(self, index, value):
        if index == 0:
            return self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_DIG_IN_0, value)
        elif index == 1:
            return self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_DIG_IN_1, value)

    def set_mag(self, index, value):
        if index == 0:
            return self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_MAG_0, value == False)
        elif index == 1:
            return self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_MAG_1, value == False)

    def dc_current(self):
        return (self.session.adc_dc_current - 0.002) / 0.15 / 20

    def sys_voltage(self):
        # Scale 31/10 (20k//1k with 10k to GND)
        return (self.session.adc_sys_voltage * (31 / 10.))

    def modem_voltage(self):
        return (self.session.adc_vmdm * (31 / 10.))

    def set_cal_switch(self, val):
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_CAL_LOAD_0, val[0])
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_CAL_LOAD_1, val[1])
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_CAL_LOAD_2, val[2])
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_CAL_LOAD_3, val[3])
        self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_CAL_LOAD_4, val[4])

    def pulse(self, channel, val):
        if channel == 1:
            self._gpio(JaguarFixtureGPIOOutput.GPIO_OUTPUT_LFP_0, val)

    def dut_present(self):
        return self.session.gpio_input_lid_detect == 0

    def read_dig_out(self):
        return (
            self.session.gpio_input_dig_out_rtn_3,
            self.session.gpio_input_dig_out_rtn_2,
            self.session.gpio_input_dig_out_rtn_1,
            self.session.gpio_input_dig_out_rtn_0,
        )
