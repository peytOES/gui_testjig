import logging
import re

from birch.peripheral.programmer import Programmer

BASE_ADDRESS = "0x1FF800D0"
OFFSET = "0x14"


def escape_ansi(line):
    ansi_escape = re.compile(b'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub(b'', line)


class STM32CubeProgrammer(Programmer):
    """
    Use STM32CubeProgrammer CLI to program device.

    Key points:
      • Reads RDP using '-ob displ' (no raw 0x1FF80000)
      • Proper RDP mapping: 0→0xAA, 1→0x55, 2→0xCC
      • execute_norst() avoids unnecessary '-rst -run' for read/display commands
      • Robust extract_iot(): reads 0x20 bytes, regex-parses words, LE→bytes
    """

    def __init__(
        self,
        executable=r"C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe",
        serial_number=None,
        *args,
        **kwargs
    ):
        self.serial_number = serial_number
        self.executable = executable
        self.result = None

    # --- Base call wrappers ---
    def execute(self, cmd, timeout=5):
        """Append '-rst -run' (use for write/erase/modify ops)."""
        self.event_logger.info("Programmer execute: %s" % " ".join(cmd))
        return super().execute(cmd + ["-rst", "-run"], timeout)

    def execute_norst(self, cmd, timeout=5):
        """Do not append '-rst -run' (use for read/inspect ops)."""
        self.event_logger.info("Programmer execute (no reset): %s" % " ".join(cmd))
        return super().execute(cmd, timeout)

    def detect_errors(self):
        """
        Treat presence of 'Error:' in stdout/stderr as failure.
        Do NOT fail just because self.result is None; execute() already handles that.
        """
        if not self.result:
            return False
        out = (self.result.stdout or b"") + b"\n" + (self.result.stderr or b"")
        out = out.lower()
        return b"error:" in out

    # --- Common CLI args ---
    def device_options(self):
        """
        -q               : quiet banner
        -c port=swd ...  : SWD, 1800 kHz
        --sn=...         : optional probe serial
        """
        opt = "-q -c port=swd freq=1800".split()
        if self.serial_number is not None:
            opt += [f"--sn={self.serial_number}"]
        return opt

    # --- Basic commands ---
    def erase(self):
        """
        Erase entire device.
        CLI: ... --erase all
        """
        cmd = [self.executable] + self.device_options() + "--erase all".split()
        return self.execute(cmd)

    def write(self, filename, address=0x8000000):
        """
        Program and verify at address.
        CLI: ... --write <file> <addr> --verify
        """
        if isinstance(address, int):
            address = hex(address)
        cmd = [self.executable] + self.device_options() + ["--write", filename, address, "--verify"]
        return self.execute(cmd, timeout=30)

    def read(self, filename, address=0x8000000, size=1024):
        """Binary memory reads are not used in this rig (use readRaw if needed)."""
        raise Exception("Not implemented")

    def readRaw(self, address=0x8000000, size=1024):
        """
        Convenience 32-bit raw read (no reset).
        CLI: ... -r32 <addr> <size>
        """
        if isinstance(address, int):
            address = hex(address)
        if isinstance(size, int):
            size = hex(size)
        cmd = [self.executable] + self.device_options() + ["-r32", address, size]
        self.event_logger.info("Programmer execute (no reset): %s" % " ".join(cmd))
        return super().execute(cmd, timeout=10)

    def chip_reset(self):
        """Hardware reset."""
        cmd = [self.executable] + self.device_options() + ["reset=HWrst"]
        self.execute(cmd)

    # --- Helpers ---
    def _parse_u32_words(self, text: str) -> list[int]:
        """
        Extract 32-bit hex words from STM32_Programmer_CLI output.
        Accepts lines like:
          '0x1FF800D0 : 12473530 37333732'
        Returns a list of integers.
        """
        words = re.findall(r"\b([0-9A-Fa-f]{8})\b", text)
        return [int(w, 16) for w in words]

    # --- Project helpers ---
    def extract_iot(self):
        """
        Robustly read OTP/IOT from 0x1FF800D0.
        - Read 0x20 bytes (32B) -> 8 x 32-bit words
        - Parse words from CLI output (regex)
        - Convert words to bytes (little-endian, MCU storage order)
        - Trim trailing 0x00 padding
        - Return 'iot' + UPPERCASE hex (no spaces)

        This replaces the fragile token-splitting that raised "list index out of range".
        """
        # Read 0x20 bytes (32B) from BASE_ADDRESS using -r32
        cmd = [self.executable] + self.device_options() + ["-r32", BASE_ADDRESS, "0x20"]
        if not self.execute_norst(cmd, timeout=10):
            # one more attempt with execute() to capture full logs
            self.execute(cmd, timeout=10)
            raise RuntimeError("extract_iot: CLI read failed")

        # Decode/clean output
        out = self.result.stdout
        text = out.decode("ascii", "ignore") if isinstance(out, (bytes, bytearray)) else str(out or "")

        # Parse all 32-bit words present
        words = self._parse_u32_words(text)
        if not words:
            raise RuntimeError(f"extract_iot: no 32-bit words found in:\n{text}")

        # Compose bytes (little-endian per STM32 word storage)
        raw = bytearray()
        for w in words:
            raw.extend(int(w).to_bytes(4, "little", signed=False))

        # Trim trailing padding zeros (OTP dumps often padded)
        while raw and raw[-1] == 0x00:
            raw.pop()

        # Canonical IOT string
        iot_id = "iot" + raw.hex().upper()
        self.event_logger.info(f"IOT OTP @{BASE_ADDRESS}: words={len(words)} bytes={len(raw)} IOT={iot_id}")
        return iot_id

    # --- RDP control ---
    def set_rdp(self, level=0):
        """
        Set RDP level:
          0 -> 0xAA (Level 0 / no protection)
          1 -> 0x55 (Level 1)
          2 -> 0xCC (Level 2 / permanent lock on many series)
        """
        if level == 0:
            value = 0xAA
        elif level == 1:
            value = 0x55
        elif level == 2:
            value = 0xCC
        else:
            self.event_logger.error(f"Invalid RDP level: {level}")
            return False

        cmd = [self.executable] + self.device_options() + ["-ob", f"rdp=0x{value:02X}"]
        self.execute(cmd)
        result = escape_ansi(self.result.stdout or b"").strip()
        self.event_logger.info("Set RDP result: %s" % result)

        if b"Option Bytes successfully programmed" in result:
            return True
        if b"Warning: Option Bytes are unchanged, Data won't be downloaded" in result:
            return True
        return False

    def read_rdp(self):
        """
        Read RDP safely using '-ob displ' (no reset).
        Returns: 'AA', '55', 'CC', or '??'
        """
        cmd = [self.executable] + self.device_options() + ["-ob", "displ"]
        self.execute_norst(cmd, timeout=10)

        out = self.result.stdout
        if isinstance(out, bytes):
            out = out.decode(errors="ignore")

        for line in out.splitlines():
            if "RDP" in line:
                m = re.search(r"RDP\s*[:=]\s*0x([0-9A-Fa-f]{2})", line)
                if m:
                    return m.group(1).upper()

        self.event_logger.warning("RDP value not found in -ob displ output.")
        return "??"

    def read_mcu_id(self) -> bytes:
        """
        Read 12 bytes at 0x1FF80050 (no reset) and return raw bytes.
        """
        cmd = [self.executable] + self.device_options() + ["-r8", "0x1FF80050", "12"]
        self.execute_norst(cmd)
        result = escape_ansi(self.result.stdout or b"").strip()
        self.event_logger.info("Read MCU ID%s" % result)
        # last 12 tokens are the byte values
        tokens = result.split()[-12:]
        return b"".join(tokens)

    def probe(self):
        """Just call CLI with connection options and return banner lines."""
        cmd = [self.executable] + self.device_options()
        if not self.execute_norst(cmd):
            return []
        return escape_ansi(self.result.stdout or b"").split(b"\n")


# Optional quick test harness (unchanged)
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    s = STM32CubeProgrammer(
        executable=r"C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
    )
    fname = "assets/active/VALIDATION/jaguar_test_fw.bin"

    assert s.set_rdp(0)
    assert s.erase()
    assert s.write(fname, 0x8000000)
    assert not s.write(fname[:-2], 0x8000000)

    mcu_id = s.read_mcu_id()
    print(mcu_id)
    print(s.read_rdp())
    print(s.set_rdp(1))
    print(s.read_rdp())
