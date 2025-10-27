"""LL
Jaguar interface board: high-level interface that wraps the low-level fixture driver (JaguarInterface)
and provides safe, logged operations for production tests.

Key features:
- Safe fallbacks for v3_power_en and pwrkey_pulse (won't crash if LL lacks features)
- Guarded calls that ensure the LL is opened
- Light logging on rail/LED/GPIO operations
- Rail guard helpers to ensure mutually exclusive DC/BAT rails with VSYS verification
"""

import time
from typing import Optional, List

from birch.peripheral.interface import Interface
from birch.peripheral.util import find_port
from birch.test_status import TestStatus

# Low-level fixture driver + constants
from .jaguar_interface.jaguar_interface_ll import JaguarInterfaceLL
from .jaguar_interface.JaguarFixture import JaguarFixtureLED


class JaguarInterface(Interface):
    VID = "0483"
    PID = "5740"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interface: Optional[JaguarInterfaceLL] = None

        # Centralized V3 TP -> GND mapping for measurements/switching
        self.V3_GND_MAP = {
            "V_BATT1": "TP72",  # V_BATT1- (new GND)
            "V_BATT2": "TP73",  # V_BATT2- (new GND)
            "V_SYS": "TP11",
            "V_MDM": "TP33",
            "V_INT": "TP21",
        }

    # ---------- internal helpers ----------

    def _log(self, level: str, msg: str):
        """Small helper to avoid hasattr checks everywhere."""
        logger = getattr(self, "event_logger", None)
        if logger is None:
            return
        if level == "debug":
            logger.debug(msg)
        elif level == "info":
            logger.info(msg)
        elif level == "warning":
            logger.warning(msg)
        elif level == "error":
            logger.error(msg)
        elif level == "exception":
            logger.exception(msg)
        else:
            logger.info(msg)

    def _ensure_ll(self):
        if self.interface is None:
            raise RuntimeError("JaguarInterfaceLL not opened yet. Call open() first.")

    # ---------- open/close ----------

    def open(self) -> bool:
        port = find_port(vid=self.VID, pid=self.PID)
        if port is None:
            self._log("error", f"JaguarInterface.open: no port for VID={self.VID} PID={self.PID}")
            return False
        self._log("info", f"JaguarInterface.open: connecting on {port}")
        try:
            self.interface = JaguarInterfaceLL(port)
            # Some LLs need an explicit open(); uncomment if yours does.
            # self.interface.open()
            return True
        except Exception as e:
            self._log("exception", f"JaguarInterface.open failed: {e}")
            self.interface = None
            return False

    def close(self):
        self._log("info", "JaguarInterface.close")
        try:
            if self.interface:
                # Some LLs have explicit close(); if not, this is a no-op.
                self.interface.close()
        finally:
            self.interface = None

    # ---------- status LEDs ----------

    def set_led(self, status, value: int):
        """
        Set status LEDs according to overall test status.
        """
        self._ensure_ll()
        self._log("debug", f"JaguarInterface.set_led: status={status} value={value}")
        if status == TestStatus.PASS:
            self.interface.set_led(JaguarFixtureLED.LED_PASS, value)
            self.interface.set_led(JaguarFixtureLED.LED_FAIL, 0)
            self.interface.set_led(JaguarFixtureLED.LED_BUSY, 0)
        elif status in (TestStatus.FAIL, TestStatus.ERROR):
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

    # ---------- ADC measurements (pass-through) ----------

    def battery_current(self) -> float:
        """Current on VBAT power line (A)"""
        self._ensure_ll()
        return float(self.interface.battery_current())

    def dc_current(self) -> float:
        """Current on DC power input (A)"""
        self._ensure_ll()
        return float(self.interface.dc_current())

    def battery_voltage(self) -> float:
        """Voltage on VBAT input (V)"""
        self._ensure_ll()
        return float(self.interface.battery_voltage())

    def dc_voltage(self) -> float:
        """Voltage on DC input (V)"""
        self._ensure_ll()
        return float(self.interface.dc_voltage())

    def modem_voltage(self) -> float:
        """Voltage on DUT at Vmdm (V)"""
        self._ensure_ll()
        return float(self.interface.modem_voltage())

    def sys_voltage(self) -> float:
        """DUT Vsys voltage (V)"""
        self._ensure_ll()
        return float(self.interface.sys_voltage())

    # ---------- V3 power & helpers ----------

    def v3_power_en(self, value: bool) -> bool:
        """
        Enable/disable the new V3 rail (successor to V1/V2).

        Behavior:
          * If LL implements v3_power_en -> use it.
          * Else gracefully fall back to dc_power_en (no exception), and log a warning.
            This allows ProgramFirmwareTestCase.setup() to proceed on older rigs.
        """
        self._ensure_ll()
        on = bool(value)
        self._log("info", f"JaguarInterface.v3_power_en({on})")

        if hasattr(self.interface, "v3_power_en"):
            return bool(self.interface.v3_power_en(on))

        if hasattr(self.interface, "dc_power_en"):
            self._log("warning", "LL lacks v3_power_en; falling back to dc_power_en")
            return bool(self.interface.dc_power_en(on))

        self._log("error", "No v3_power_en or dc_power_en available in LL")
        raise NotImplementedError("Neither v3_power_en nor dc_power_en are available")

    def pwrkey_pulse(self, ms: int = 300) -> bool:
        """
        Assert PWRKEY for 'ms' milliseconds then release.
        Preferred: LL implements pwrkey_pulse. Fallback: LL exposes pwrkey(True/False).
        If neither is available, log a warning and return False (don't crash the test).
        """
        self._ensure_ll()
        self._log("info", f"JaguarInterface.pwrkey_pulse(ms={ms})")

        # Preferred implementation
        if hasattr(self.interface, "pwrkey_pulse"):
            try:
                return bool(self.interface.pwrkey_pulse(int(ms)))
            except NotImplementedError:
                pass
            except Exception as e:
                self._log("warning", f"LL pwrkey_pulse raised {e}; trying manual toggle")

        # Fallback: toggle boolean pwrkey()
        if hasattr(self.interface, "pwrkey"):
            try:
                self.interface.pwrkey(True)
                time.sleep(ms / 1000.0)
                self.interface.pwrkey(False)
                return True
            except Exception as e:
                self._log("error", f"pwrkey toggle failed: {e}")
                return False

        # Last resort: do not raise
        self._log("warning", "pwrkey_pulse not implemented on this fixture; skipping")
        return False

    def antenna_present(self) -> bool:
        """
        Optional guard: real implementation if LL exposes a sensor, else assume present.
        """
        self._ensure_ll()
        present = True
        if hasattr(self.interface, "antenna_present"):
            try:
                present = bool(self.interface.antenna_present())
            except Exception as e:
                self._log("warning", f"antenna_present read failed: {e}; assuming present")
                present = True
        self._log("debug", f"JaguarInterface.antenna_present -> {present}")
        return present

    def enable_vbatt2_safe(self, enable: bool) -> bool:
        """
        Guard enabling cellular rail (V_BATT2) behind antenna presence to protect the PA.
        """
        self._ensure_ll()
        if enable and not self.antenna_present():
            self._log("error", "Refusing to enable V_BATT2: antenna not detected")
            raise RuntimeError("Antenna not detected; refusing to enable V_BATT2 to protect the modem.")

        self._log("info", f"JaguarInterface.enable_vbatt2_safe({bool(enable)})")
        if hasattr(self.interface, "vbatt2_en"):
            return bool(self.interface.vbatt2_en(bool(enable)))
        if hasattr(self.interface, "battery_power_en"):
            return bool(self.interface.battery_power_en(bool(enable)))
        raise NotImplementedError("LL has no vbatt2_en or battery_power_en")

    def _route_v3_gnd(self, net_name: str):
        """
        Route the correct GND reference for V3 measurements (if LL supports it).
        """
        self._ensure_ll()
        tp = self.V3_GND_MAP.get(net_name)
        self._log("debug", f"JaguarInterface._route_v3_gnd: net={net_name} -> gnd={tp}")
        if tp and hasattr(self.interface, "set_measure_gnd"):
            try:
                self.interface.set_measure_gnd(tp)
            except Exception as e:
                self._log("warning", f"set_measure_gnd failed: {e}")

    def measure_v3_voltage(self, net_name: str) -> float:
        """
        High-level voltage read that auto-routes the V3 ground reference.
        net_name: one of 'V_SYS', 'V_MDM', 'V_BATT1', 'V_BATT2', 'V_INT'
        """
        self._ensure_ll()
        self._route_v3_gnd(net_name)
        if net_name == "V_SYS":
            val = float(self.sys_voltage())
        elif net_name == "V_MDM":
            val = float(self.modem_voltage())
        elif net_name in ("V_BATT1", "V_BATT2"):
            val = float(self.battery_voltage())
        elif net_name == "V_INT" and hasattr(self.interface, "int_voltage"):
            val = float(self.interface.int_voltage())
        else:
            raise ValueError(f"Unknown V3 net '{net_name}'")
        self._log("info", f"JaguarInterface.measure_v3_voltage({net_name}) -> {val:.6f} V")
        return val

    # ---------- rail controls (with light logging) ----------

    def dc_power_en(self, value) -> bool:
        self._ensure_ll()
        self._log("info", f"JaguarInterface.dc_power_en({bool(value)})")
        if hasattr(self.interface, "dc_power_en"):
            return bool(self.interface.dc_power_en(value))
        raise NotImplementedError("LL has no dc_power_en")

    def battery_power_en(self, value) -> bool:
        self._ensure_ll()
        self._log("info", f"JaguarInterface.battery_power_en({bool(value)})")
        if hasattr(self.interface, "battery_power_en"):
            return bool(self.interface.battery_power_en(value))
        raise NotImplementedError("LL has no battery_power_en")

    # ---------- fixture plumbing ----------

    def set_electromagnet(self, index: int, value: bool) -> bool:
        self._ensure_ll()
        self._log("debug", f"JaguarInterface.set_electromagnet(index={index}, value={value})")
        return bool(self.interface.set_mag(index, value))

    def set_dac(self, index: int, value: float):
        self._ensure_ll()
        self._log("debug", f"JaguarInterface.set_dac(index={index}, value={value})")
        return self.interface.set_dac(index, value)

    def dut_present(self, *args, **kwargs) -> bool:
        self._ensure_ll()
        present = bool(self.interface.dut_present())
        self._log("debug", f"JaguarInterface.dut_present -> {present}")
        return present

    def gpio_enable(self, enable: bool):
        self._ensure_ll()
        self._log("debug", f"JaguarInterface.gpio_enable({enable})")
        if hasattr(self.interface, "gpio_enable"):
            return self.interface.gpio_enable(enable)
        raise NotImplementedError("LL has no gpio_enable")

    def dig_out_power_enable(self, enable: bool):
        self._ensure_ll()
        self._log("debug", f"JaguarInterface.dig_out_power_enable({enable})")
        if hasattr(self.interface, "dig_out_power_enable"):
            return self.interface.dig_out_power_enable(enable)
        raise NotImplementedError("LL has no dig_out_power_enable")

    def read_dig_out(self) -> List[int]:
        self._ensure_ll()
        raw = self.interface.read_dig_out()[::-1]
        self._log("debug", f"JaguarInterface.read_dig_out -> {raw}")
        return raw

    def set_dig_in(self, index: int, value: bool):
        self._ensure_ll()
        self._log("debug", f"JaguarInterface.set_dig_in(index={index}, value={value})")
        if hasattr(self.interface, "set_dig_in"):
            return self.interface.set_dig_in(index, value)
        raise NotImplementedError("LL has no set_dig_in")

    def fixture_detect(self, level: bool):
        self._ensure_ll()
        self._log("debug", f"JaguarInterface.fixture_detect(level={level})")
        if hasattr(self.interface, "fixture_detect"):
            return self.interface.fixture_detect(level)
        raise NotImplementedError("LL has no fixture_detect")

    # ---------- power-off sequencing ----------

    def power_off(self):
        """
        Turn off all power, wait for Vsys to drop to 0.1 V (with timeout).
        """
        self._ensure_ll()
        self._log("info", "JaguarInterface.power_off: shutting down rails")

        # Best-effort shutdown order with guards
        try:
            if hasattr(self.interface, "rs232_enable"):
                self.interface.rs232_enable(False)
            if hasattr(self.interface, "jtag_enable"):
                self.interface.jtag_enable(False)
            if hasattr(self.interface, "battery_power_en"):
                self.interface.battery_power_en(False)
            if hasattr(self.interface, "dc_power_en"):
                self.interface.dc_power_en(False)
            if hasattr(self.interface, "set_cal_switch"):
                self.interface.set_cal_switch([True] * 5)
            if hasattr(self.interface, "analog_enable"):
                self.interface.analog_enable(True)
        finally:
            # Wait for discharge with a timeout
            count = 0
            max_checks = 40  # 40 * 0.25s = 10s
            try:
                v = self.sys_voltage()
            except Exception:
                v = 999.0
            while v > 0.1 and count < max_checks:
                self._log("debug", f"JaguarInterface.power_off: Vsys={v:.6f} V (waiting)")
                time.sleep(0.25)
                count += 1
                try:
                    v = self.sys_voltage()
                except Exception:
                    v = 999.0

            if count >= max_checks:
                self._log("warning", "JaguarInterface.power_off: timeout waiting for Vsys <= 0.1 V")

            if hasattr(self.interface, "set_cal_switch"):
                self.interface.set_cal_switch([False] * 5)
            if hasattr(self.interface, "analog_enable"):
                self.interface.analog_enable(False)

    # ---------- misc passthrough ----------

    def jtag_enable(self, value: bool):
        self._ensure_ll()
        self._log("debug", f"JaguarInterface.jtag_enable({value})")
        if hasattr(self.interface, "jtag_enable"):
            return self.interface.jtag_enable(value)
        raise NotImplementedError("LL has no jtag_enable")

    def analog_enable(self, value: bool):
        self._ensure_ll()
        self._log("debug", f"JaguarInterface.analog_enable({value})")
        if hasattr(self.interface, "analog_enable"):
            return self.interface.analog_enable(value)
        raise NotImplementedError("LL has no analog_enable")

    def rs232_enable(self, value: bool):
        self._ensure_ll()
        self._log("debug", f"JaguarInterface.rs232_enable({value})")
        if hasattr(self.interface, "rs232_enable"):
            return self.interface.rs232_enable(value)
        raise NotImplementedError("LL has no rs232_enable")

    def pulse(self, channel: int, value: bool):
        """
        Set LFP input high or low.
        """
        self._ensure_ll()
        self._log("debug", f"JaguarInterface.pulse(ch={channel}, value={value})")
        if hasattr(self.interface, "pulse"):
            return self.interface.pulse(channel, value)
        raise NotImplementedError("LL has no pulse")

    # =====================================================================
    #                Rail guard helpers (NEW in this version)
    # =====================================================================

    def _poll_voltage(self, fn, tries=20, delay=0.1):
        """Call a voltage getter repeatedly, return last value (or None)."""
        val = None
        for _ in range(int(tries)):
            try:
                val = float(fn())
            except Exception:
                val = None
            time.sleep(delay)
        return val

    def wait_vsys_above(self, thresh=0.5, timeout_s=3.0):
        end = time.time() + timeout_s
        last = None
        while time.time() < end:
            try:
                last = float(self.sys_voltage())
                if last >= thresh:
                    self._log("info", f"wait_vsys_above: VSYS={last:.3f} ≥ {thresh}")
                    return True
            except Exception:
                pass
            time.sleep(0.1)
        self._log("warning", f"wait_vsys_above timeout (last={last})")
        return False

    def wait_vsys_below(self, thresh=0.2, timeout_s=5.0):
        end = time.time() + timeout_s
        last = None
        while time.time() < end:
            try:
                last = float(self.sys_voltage())
                if last <= thresh:
                    self._log("info", f"wait_vsys_below: VSYS={last:.3f} ≤ {thresh}")
                    return True
            except Exception:
                pass
            time.sleep(0.12)
        self._log("warning", f"wait_vsys_below timeout (last={last})")
        return False

    def rails_set_dc_only(self, settle_s=0.25) -> bool:
        """
        Ensure BAT=OFF, DC=ON and VSYS rises (retry once if needed).
        Returns True if VSYS rose above ~0.5 V.
        """
        self._ensure_ll()
        self._log("info", "rails_set_dc_only: BAT=OFF, DC=ON")
        self.battery_power_en(False)
        self.dc_power_en(True)
        time.sleep(settle_s)

        if self.wait_vsys_above(thresh=0.5, timeout_s=2.0):
            return True

        # Retry once: toggle DC
        self._log("warning", "VSYS did not rise; retrying DC rail")
        self.dc_power_en(False)
        time.sleep(0.2)
        self.dc_power_en(True)
        time.sleep(settle_s)
        return self.wait_vsys_above(thresh=0.5, timeout_s=2.0)

    def rails_set_bat_only(self, settle_s=0.25) -> bool:
        """
        Ensure DC=OFF, BAT=ON and VSYS rises (retry once if needed).
        Returns True if VSYS rose above ~2.5 V (battery domain).
        """
        self._ensure_ll()
        self._log("info", "rails_set_bat_only: DC=OFF, BAT=ON")
        self.dc_power_en(False)
        self.battery_power_en(True)
        time.sleep(settle_s)

        if self.wait_vsys_above(thresh=2.5, timeout_s=2.0):
            return True

        # Retry once: toggle BAT
        self._log("warning", "VSYS did not rise on BAT; retrying battery rail")
        self.battery_power_en(False)
        time.sleep(0.2)
        self.battery_power_en(True)
        time.sleep(settle_s)
        return self.wait_vsys_above(thresh=2.5, timeout_s=2.0)

    def force_all_off_and_wait(self):
        """
        Turn off everything and wait until VSYS ~ 0 V (best-effort).
        """
        self._ensure_ll()
        self._log("info", "force_all_off_and_wait")
        try:
            if hasattr(self.interface, "battery_power_en"):
                self.interface.battery_power_en(False)
            if hasattr(self.interface, "dc_power_en"):
                self.interface.dc_power_en(False)
            if hasattr(self.interface, "set_cal_switch"):
                self.interface.set_cal_switch([True] * 5)
            if hasattr(self.interface, "analog_enable"):
                self.interface.analog_enable(True)
        except Exception as e:
            self._log("warning", f"force_all_off: {e}")
        finally:
            self.wait_vsys_below(thresh=0.2, timeout_s=6.0)
            try:
                if hasattr(self.interface, "set_cal_switch"):
                    self.interface.set_cal_switch([False] * 5)
                if hasattr(self.interface, "analog_enable"):
                    self.interface.analog_enable(False)
            except Exception:
                pass

    # Optional: quick snapshot for debugging rails
    def _rail_snapshot(self, tag=""):
        try:
            vdc = self.dc_voltage()
            vbat = self.battery_voltage()
            vsys = self.sys_voltage()
            self._log("info", f"[rails {tag}] VDC={vdc:.3f}  VBAT={vbat:.3f}  VSYS={vsys:.3f}")
        except Exception:
            pass
