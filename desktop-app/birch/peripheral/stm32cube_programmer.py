import logging
import re

from birch.peripheral.programmer import Programmer


def escape_ansi(line):
    ansi_escape = re.compile(b'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub(b'', line)


class STM32CubeProgrammer(Programmer):
    """
    Use STM32Cube programmer to program device
    """

    def __init__(self,
                 executable=r"C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe",
                 serial_number=None, *args, **kwargs):
        """
        serial - programmer serial number in hex, optional if only one is connected to the system.
        """
        self.serial_number = serial_number

        self.executable = executable

    def execute(self, cmd, timeout=5):
        self.event_logger.info("Programmer execute: %s" % " ".join(cmd))
        return super().execute(cmd + ["-rst", "-run"], timeout)

    def detect_errors(self):
        """"
        STM32_Programmer does not return a clean status code, instead look for an Error in the stdout
        """
        if b"Error:" in self.result.stdout:
            return True
        return False

    def device_options(self):
        """
        Convenience function to add the device serial number if defined.

        Set speed to 1800kHz
        """
        opt = "-q -c port=swd freq=1800".split()
        if self.serial_number is not None:
            opt += ["--sn=%s" % self.serial_number]
        return opt

    def erase(self):
        """
        Erase

        ./STM32_Programmer.sh -c port=swd --erase all


        """
        cmd = [self.executable] + self.device_options() + "--erase all".split()
        return self.execute(cmd)

    def write(self, filename, address=0x8000000):
        """
        Write firmware to device starting from <address>, verify 

         ./STM32_Programmer.sh -c port=swd --write /home/jvdh/work/projects/jaguar_fixture/reference/fw/fw_testing-ccb/projROMET_L151_TEST_20201030/Debug/jaguar_test_fw.bin 0x8000000 --verify

        """
        if type(address) is int:
            address = hex(address)
        cmd = [self.executable] + self.device_options() + ["--write"] + [filename] + [address] + ["--verify"]
        return self.execute(cmd, timeout=30)

    def read(self, filename, address=0x8000000, size=1024):
        raise Exception("Not implemented")
        # if type(address) is int:
        #    address = hex(address)
        # if type(size) is int:
        #    size = hex(size)
        # cmd = [self.executable] + self.device_options() + ["read"] + [filename] + [address] + [size]
        # self.execute(cmd)

    def set_rdp(self, level=0):
        """
        Set RDP protection bits

        ./STM32_Programmer.sh -c port=swd -ob rdp=0x0 --b displ
        """
        if level == 1:
            value = 0x00
        elif level == 2:
            value = 0xcc
        else:
            value = 0xaa

        cmd = [self.executable] + self.device_options() + ["-ob"] + ["rdp=0x%02x" % value]
        self.execute(cmd)
        result = escape_ansi(self.result.stdout).strip()
        self.event_logger.info("Read RDP %s" % result)

        if b"Option Bytes successfully programmed" in result:
            result = result.split()[-1]
            return True
        if b"Warning: Option Bytes are unchanged, Data won't be downloaded" in result:
            return True
        return False

    def read_rdp(self):
        """
        Read RDP byte, where 0xcc= 2, 0xaa=1, and everything else is 1

        ./STM32_Programmer_CLI -c port=swd -r8 0x1FF80000 1
        """

        cmd = [self.executable] + self.device_options() + ["-r8", "0x1FF80000", "1"]
        self.execute(cmd)
        result = escape_ansi(self.result.stdout).strip()
        val = re.findall(b"0x1FF80000 : (\w+)", result)
        if len(val) == 1:
            return val[0].decode("utf-8")
        self.event_logger.warning("option byte read failed: %s" % result)
        return None

    def read_mcu_id(self) -> str:
        """
        Read MCU ID from0x1FF80050, 0x1FF80054, and 0x1FF80064
        """
        cmd = [self.executable] + self.device_options() + ["-r8", "0x1FF80050", "12"]
        self.execute(cmd)
        result = escape_ansi(self.result.stdout).strip()
        self.event_logger.info("Read MCU ID%s" % result)
        result = result.split()[-12:]
        return b"".join(result)

    def probe(self):
        """
        probe for devices
        """
        cmd = [self.executable] + self.device_options()
        if not self.execute(cmd):
            result = False

        return escape_ansi(self.result.stdout).split(b"\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    s = STM32CubeProgrammer(
        executable="/home/jvdh/STMicroelectronics/STM32Cube/STM32CubeProgrammer/bin/STM32_Programmer.sh")
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
