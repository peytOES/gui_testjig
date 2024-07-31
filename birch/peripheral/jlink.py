import sys
import subprocess
import os
import time

if sys.platform == "win32":
    APPLICATION = "commander.exe"
    # STARTUP_INFO = subprocess.STARTUPINFO()
    # STARTUP_INFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
else:
    APPLICATION = "commander"

DEBUG = False


class JLink(object):
    def __init__(self, application=None, device=None, serial=None):
        self.serial = serial
        self.application = application
        self.device = device

    def log(self, *args, **kwargs):
        if DEBUG:
            print(args, kwargs)

    def run(self, args):
        """
        Args is a list of arguments"
        """
        cmd = []
        if self.application is None:
            self.log("No application specified")
            return
        else:
            cmd.append(self.application)
        if self.serial is not None:
            cmd += ["--serialno=%s" % self.serial]
        if self.device is not None:
            cmd += ["--device=%s" % self.device]

        if sys.platform == "win32":
            result = subprocess.run(cmd + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # result = subprocess.Popen(cmd + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=STARTUP_INFO)
        else:
            result = subprocess.run(cmd + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            self.log("JLINK failed:", cmd + args)
            print("JLINK failed:", cmd + args)
        return result


class SilabsJLink(JLink):
    jlink_response_map = {
        b'Part Number': "part_number",
        b'Die Revision': "die_revision",
        b'Production Ver': "production_version",
        b'Flash Size': "flash_size",
        b'SRAM Size': "sram_size",
        b'Unique ID': "unique_id",
        b'FW Version': "version",
        # locked : bool - read from stderr
    }

    def __init__(self, path="", *args, **kwargs):
        JLink.__init__(self, application=path + "commander/" + APPLICATION, *args, **kwargs)

    def parse_response(self, response):
        """
        JLink returns information in tables, e.g.

            Part Number    : EFR32MG1B232F256GM32
            Die Revision   : A3
            Production Ver : 156
            Flash Size     : 256 kB
            SRAM Size      : 32 kB
            Unique ID      : 90fd9ffffe1873af
        
        This function parses the result for the a:b formatted lines,
        if a is in jlink_response_map, add the value to the return dictionary.

        If device is locked, we expect:
            JLinkError: Silicon Labs AAP detected. Device locked 
            WARNING: Could not connect to target device
            ERROR: Could not connect debugger.
        """
        result_dict = {}
        self.log(response.returncode);
        self.log(response);
        if response.returncode == 0:
            fields = response.stdout
            fields = fields.split(b'\n')
            for f in fields:
                try:
                    a, b = [x.strip() for x in f.split(b':')]
                    if a in self.jlink_response_map:
                        result_dict[self.jlink_response_map[a]] = b.decode("utf-8")
                except ValueError:
                    # ignore lines that are not in a : b 
                    pass
            result_dict["locked"] = False
        else:  # error code, device might be locked?
            if b"JLinkError: Silicon Labs AAP detected. Device locked" in response.stderr:
                result_dict["locked"] = True
        return result_dict

    def reset_adapter(self):
        """
        Reset adaptor recover to known state

        This blocks for 3 seconds.
        """
        count = 10
        param = "adapter reset"
        while count > 0:
            count -= 1
            res = self.run(param.split())
            if res.returncode == 0:
                time.sleep(1)
                return res
            else:
                time.sleep(1)

        return res

    def reset(self):
        param = "device reset"
        return self.run(param.split()).returncode == 0

    def recover(self):
        param = "device recover"
        time.sleep(1)
        return self.run(param.split())

    def debug_mode(self, mode):
        """
        Valid modes:

        OFF, MCU, IN, OUT - OUT is default
        """
        if mode not in ["OFF", "MCU", "IN", "OUT"]:
            return False
        param = "adapter dbgmode %s" % mode
        result = self.run(param.split())
        time.sleep(0.2)
        return result

    def flash(self, filename):
        """
        Flash file to device
        """
        param = ["flash", "--masserase", filename]
        result = self.run(param)
        if result.returncode != 0:
            return (False, result.stdout.decode("utf-8"))
        else:
            return (True, "")

    # function for reading information
    def device_info(self):
        """
        Read device info, return as dict.

        If reading failed, return {}
        """
        param = ["device", "info"]
        response = self.run(param)
        result = self.parse_response(response)
        return result

    def probe(self):
        """
        Read JLink device information
        """
        param = "adapter probe"
        response = self.run(param.split())
        result = self.parse_response(response)
        return result


if __name__ == "__main__":
    j = SilabsJLink(device="EFR32")
