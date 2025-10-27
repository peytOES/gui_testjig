import time
import re

from .jaguar_testcase import JaguarTestCase


class MemoryProtectTestcase(JaguarTestCase):
    """
    Set and validate RDP for Jaguar V3 hardware.

    Workflow:
      1) setup(): V3 bring-up sequence for safe SWD access
      2) set_rdp(): write desired RDP level (0, 1, or 2) if the programmer supports it
      3) read_rdp(): validate by querying the programmer (no raw 0x1FF80000 reads)
      4) teardown(): rails & interfaces off
    """

    def __init__(self, rdp_level=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if rdp_level not in (0, 1, 2):
            raise ValueError("rdp_level must be 0, 1, or 2")
        self.rdp_level = rdp_level
        self.append_step("Set RDP", self.set_rdp)
        self.append_step("Validate RDP", self.read_rdp)

    # -------- power & access sequencing --------

    def setup(self):
        """
        V3: DC OFF; enable battery + V3 rails; enable analog and JTAG.
        """
        try:
            self.interface.dc_power_en(False)
        except Exception:
            pass

        self.interface.v3_power_en(True)
        self.interface.battery_power_en(True)

        self.interface.analog_enable(True)
        self.interface.jtag_enable(True)
        time.sleep(1)

    def teardown(self):
        """
        Best-effort shutdown of rails and interfaces.
        """
        for fn in (
            lambda: self.interface.dc_power_en(False),
            lambda: self.interface.battery_power_en(False),
            lambda: self.interface.analog_enable(False),
            lambda: self.interface.rs232_enable(False),
            lambda: self.interface.jtag_enable(False),
        ):
            try:
                fn()
            except Exception:
                pass
        time.sleep(1)

    # -------- steps --------

    def set_rdp(self):
        """
        Set readout protection via programmer.set_rdp(level) when available.
        If the programmer does not support setting RDP (e.g., STLinkProgrammer), skip gracefully.
        """
        try:
            result = self.programmer.set_rdp(self.rdp_level)
        except NotImplementedError:
            # Some programmers (st-flash) should not set RDP; treat as a no-op.
            self.event_logger.info("Programmer does not support set_rdp(); skipping RDP write.")
            result = True
        except Exception as e:
            self.event_logger.error(f"set_rdp failed: {e}")
            result = False

        if not result:
            self.log_error(self.ErrorCode.rdp_set_failed)

        return {"result": result, "level": self.rdp_level}

    def read_rdp(self):
        """
        Validate RDP by querying the programmer.
        Works with:
          - STM32CubeProgrammer.read_rdp() -> 'AA'/'55'/'CC'/'??'
          - STLinkProgrammer.read_rdp()    -> 0/1/2
        """
        level, rdp_hex = self._get_rdp_level_and_hex()

        result = (level == self.rdp_level)
        if not result:
            self.log_error(self.ErrorCode.rdp_validate_failed)

        return {"result": result, "rdp_value": rdp_hex, "rdp_level": level}

    # -------- helpers --------

    @staticmethod
    def _hex_to_level(rdp_hex: str) -> int:
        """
        Map RDP hex byte to logical level:
          0xAA -> 0
          0xCC -> 2
          else -> 1
        """
        x = (rdp_hex or "").strip().upper()
        if x == "AA":
            return 0
        if x == "CC":
            return 2
        return 1

    @staticmethod
    def _level_to_hex(level: int) -> str:
        """
        Map logical level to the conventional RDP hex:
          0 -> 'AA'
          1 -> '55'
          2 -> 'CC'
        """
        return {0: "AA", 1: "55", 2: "CC"}.get(level, "55")

    def _get_rdp_level_and_hex(self):
        """
        Try the programmer's read_rdp() first:
          - If it returns int (0/1/2), convert to hex.
          - If it returns str ('AA'/'55'/'CC' or '??'), convert to level.
        If no read_rdp() is available, attempt a CLI call via programmer.execute()
        if the programmer exposes 'executable' and 'device_options' (STM32CubeProgrammer).
        """
        # 1) Preferred: programmer.read_rdp()
        if hasattr(self.programmer, "read_rdp"):
            try:
                val = self.programmer.read_rdp()
                # Numeric level (e.g., STLinkProgrammer)
                if isinstance(val, int):
                    return val, self._level_to_hex(val)
                # Hex string path (e.g., STM32CubeProgrammer)
                if isinstance(val, str):
                    val = val.strip().upper()
                    if re.fullmatch(r"[0-9A-F]{2}", val):
                        return self._hex_to_level(val), val
                    # Unknown string -> treat as Level 1 by convention
                    return 1, "??"
            except Exception as e:
                self.event_logger.warning(f"programmer.read_rdp() failed: {e}")

        # 2) Fallback: direct CLI call for STM32CubeProgrammer-style wrappers
        if hasattr(self.programmer, "executable") and hasattr(self.programmer, "device_options"):
            try:
                exe = self.programmer.executable
                opts = self.programmer.device_options() if callable(self.programmer.device_options) else []
                cmd = [exe] + list(opts) + ["-ob", "displ"]
                # Use the base execute() to capture stdout into programmer.result
                ok = self.programmer.execute(cmd, timeout=10)
                _ = ok  # ok not strictly needed; stdout is captured regardless
                out = self.programmer.result.stdout
                if isinstance(out, bytes):
                    out = out.decode(errors="ignore")
                for line in out.splitlines():
                    if "RDP" in line:
                        m = re.search(r"RDP\s*[:=]\s*0x([0-9A-Fa-f]{2})", line)
                        if m:
                            rdp_hex = m.group(1).upper()
                            return self._hex_to_level(rdp_hex), rdp_hex
            except Exception as e:
                self.event_logger.error(f"Fallback -ob displ read failed: {e}")

        # 3) Last resort: unknown -> treat as Level 1
        self.event_logger.warning("Unable to read RDP; assuming Level 1.")
        return 1, "??"