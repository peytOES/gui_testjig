import logging
import tempfile
from pathlib import Path

from .programmer import Programmer


BASE_ADDRESS = "0x1FF800D0"
OFFSET = "0x14"


class STLinkProgrammer(Programmer):
    """
    Drive ST-LINK via the `st-flash`/`st-info` tools (tested on V2).

    Helpful CLI:
      st-flash --help
      st-info  --help

    Notes:
      • For STM32L1, modifying RDP via st-flash requires writing the entire option
        word and is target-specific/risky. We deliberately do NOT implement set_rdp()
        here. Use STM32CubeProgrammer for RDP changes.
    """

    def __init__(self, debug=False, serial=None, freq=None, connect_under_reset=None, *args, **kwargs):
        """
        serial - ST-LINK serial number in hex (optional if only one is connected).
        freq   - SWD frequency in KHz (string), e.g. "1800"
        """
        self.serial = serial
        self.debug = debug
        self.freq = freq
        self.connect_under_reset = connect_under_reset

        # Tool paths/names are expected to be on PATH (adjust if needed)
        self.executable = "st-flash"
        self.info_exec = "st-info"

        # ensure base stores last result
        self.result = None

    # ---------- helpers ----------

    def device_options(self):
        """
        Build CLI option list for st-flash/st-info based on ctor args.
        """
        opt = []
        if self.debug:
            opt += ["--debug"]
        if self.freq is not None:
            opt += ["--freq", self.freq]
        if self.serial is not None:
            opt += ["--serial", self.serial]
        if self.connect_under_reset:
            opt += ["--connect-under-reset"]
        return opt

    def detect_errors(self):
        """
        st-flash returns nonzero on failure; still scan stdout for 'ERROR' just in case.
        """
        if not self.result or self.result.stdout is None:
            return True
        out = self.result.stdout
        return (b"ERROR" in out) or (b"Error" in out)

    # ---------- basic ops ----------

    def erase(self):
        """
        st-flash [opts] erase
        """
        cmd = [self.executable] + self.device_options() + ["erase"]
        return self.execute(cmd)

    def write(self, filename, address=0x8000000):
        """
        st-flash [opts] write <file> <addr>
        """
        if isinstance(address, int):
            address = hex(address)
        cmd = [self.executable] + self.device_options() + ["write", filename, address]
        return self.execute(cmd)

    def read(self, filename, address=0x8000000, size=1024):
        """
        st-flash [opts] read <file> <addr> <size>
        """
        if isinstance(address, int):
            address = hex(address)
        if isinstance(size, int):
            size = hex(size)
        cmd = [self.executable] + self.device_options() + ["read", filename, address, size]
        return self.execute(cmd)

    # ---------- RDP (read only; writing is intentionally not implemented here) ----------

    def set_rdp(self, level=0):
        """
        Intentionally not implemented for st-flash on STM32L1, because it requires writing
        target-specific option words and can permanently lock/erase devices if done wrong.
        Use STM32CubeProgrammer's CLI (-ob rdp=...) path instead.
        """
        raise NotImplementedError(
            "Setting RDP via st-flash is not supported here. Use STM32CubeProgrammer (STM32_Programmer_CLI -ob rdp=...)."
        )

    def read_rdp(self) -> int:
        """
        Read RDP by dumping the option area to a temp file and inspecting the first byte.

        Returns the logical level:
          0 for Level 0 (RDP byte 0xAA)
          1 for Level 1 (RDP byte 0x55 or other)
          2 for Level 2 (RDP byte 0xCC)

        Implementation detail:
          st-flash --area=option read <temp.bin> <size>
        We read 16 bytes which covers OB headers across L1 families.
        """
        with tempfile.TemporaryDirectory() as tmpd:
            out_path = Path(tmpd) / "option.bin"
            cmd = [self.executable] + self.device_options() + ["--area=option", "read", str(out_path), "16"]
            ok = self.execute(cmd)
            if not ok:
                # Base execute() already logged stdout/stderr; return Level 1 (safe default) or raise
                self.event_logger.warning("st-flash option read failed; assuming RDP Level 1")
                return 1

            try:
                data = out_path.read_bytes()
                if not data:
                    self.event_logger.warning("Empty option area dump; assuming RDP Level 1")
                    return 1
                rdp = data[0]  # RDP byte is first in the option frame on STM32 L-series
            except Exception as e:
                self.event_logger.error(f"Failed to read option.bin: {e}")
                return 1

        if rdp == 0xAA:
            return 0
        if rdp == 0xCC:
            return 2
        # Most other values (incl. 0x55) indicate Level 1
        return 1

    # ---------- probe ----------

    def probe(self):
        """
        Probe for ST-LINK and target info.
        st-info [opts] --probe
        """
        cmd = [self.info_exec] + self.device_options() + ["--probe"]
        return self.execute(cmd)


# Keep your existing quick test flow
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    s = STLinkProgrammer()
    s.erase()
    s.write("test_file", 0x12)
    s.write("test_file", "0x12")
    s.read("test_file", "0x12", 0x12)
    s.read("test_file", "0x12", "0x12")