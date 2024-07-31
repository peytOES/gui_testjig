from .programmer import Programmer


class STLinkProgrammer(Programmer):
    """
    Using st-flash to drive STlink.  Tested on V2.

    $ st-flash -h
    invalid command line
    command line:   ./st-flash [--debug] [--reset] [--connect-under-reset] [--hot-plug] [--opt] [--serial <serial>] [--format <format>] [--flash=<fsize>] [--freq=<KHz>] [--area=<area>] {read|write} [path] [addr] [size]
    command line:   ./st-flash [--debug] [--connect-under-reset] [--hot-plug] [--freq=<KHz>] [--serial <serial>] erase
    command line:   ./st-flash [--debug] [--freq=<KHz>] [--serial <serial>] reset
       <addr>, <serial> and <size>: Use hex format.
       <fsize>: Use decimal, octal or hex (prefix 0xXXX) format, optionally followed by k=KB, or m=MB (eg. --flash=128k)
       <format>: Can be 'binary' (default) or 'ihex', although <addr> must be specified for binary format only.
       <area>: Can be 'main' (default), 'system', 'otp', 'optcr', 'optcr1', 'option' or 'option_boot_add'
    print tool version info:   ./st-flash [--version]
    example read option byte: ./st-flash --area=option read [path] [size]
    example write option byte: ./st-flash --area=option write 0xXXXXXXXX
    On selected targets:
    example read boot_add option byte:  ./st-flash --area=option_boot_add read
    example write boot_add option byte: ./st-flash --area=option_boot_add write 0xXXXXXXXX
    example read option control register byte:  ./st-flash --area=optcr read
    example write option control register1 byte:  ./st-flash --area=optcr write 0xXXXXXXXX
    example read option control register1 byte:  ./st-flash --area=optcr1 read
    example write option control register1 byte:  ./st-flash --area=optcr1 write 0xXXXXXXXX
    """

    def __init__(self, debug=False, serial=None, freq=None, connect_under_reset=None, *args, **kwargs):
        """
        serial - programmer serial number in hex, optional if only one is connected to the system.
        """
        self.serial = serial
        self.debug = debug
        self.freq = freq
        self.connect_under_reset = connect_under_reset

        # TODO: paths.
        self.executable = "st-flash"

    def device_options(self):
        """
        Convenience function to add the device serial number if defined
        """
        opt = []
        if self.debug:
            opt += ["--debug"]
        if self.freq is not None:
            opt += ["--freq", self.freq]
        if self.serial is not None:
            opt += ["--serial", self.serial]
        if self.connect_under_reset is not None:
            opt += ["--connect-under-reset"]
        return opt

    def erase(self):
        """
        ./st-flash [--debug] [--connect-under-reset] [--hot-plug] [--freq=<KHz>] [--serial <serial>] erase
        """
        cmd = [self.executable] + self.device_options() + ["erase"]
        self.execute(cmd)

    def write(self, filename, address=0x8000000):
        """
        Write firmware to device starting from address:
        st-flash write firmware.bin address
        """
        if type(address) is int:
            address = hex(address)
        cmd = [self.executable] + self.device_options() + ["write"] + [filename] + [address]
        self.execute(cmd)

    def read(self, filename, address=0x8000000, size=1024):
        if type(address) is int:
            address = hex(address)
        if type(size) is int:
            size = hex(size)
        cmd = [self.executable] + self.device_options() + ["read"] + [filename] + [address] + [size]
        self.execute(cmd)

    def set_rdp(self, level=0):
        """
        Set RDP protection bits

        For stm32l151 set 0x1FF80000 to appropriate value
        self.programmer.read("test.hex", 0x1FF80000, 1)

        """

        print("rdp not tested")
        if level == 1:
            value = 0x00
        elif level == 2:
            value = 0xcc
        else:
            value = 0xaa

        return True

    def read_rdp(self) -> int:
        """
        Read RDP byte, returns the logical RDP level.

        st-flash read test.hex 0x1FF80000 1
        """
        print("rdp not tested")
        rdp_byte = 0xaa

        if rdp_byte == 0xcc:
            return 2
        if rdp_byte == 0xaa:
            return 0
        return 1

    def probe(self):
        """
        probe for devices
        """
        cmd = ["st-info"] + self.device_options() + ["--probe"]
        if self.execute(cmd):
            print(self.result.stdout)

    # def execute(self, cmd, timeout=5):
    #    self.event_logger.info("Programmer execute: %s"%" ".join(cmd))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    s = STLinkProgrammer()
    s.erase()
    s.write("test_file", 0x12)
    s.write("test_file", "0x12")
    s.read("test_file", "0x12", 0x12)
    s.read("test_file", "0x12", "0x12")
