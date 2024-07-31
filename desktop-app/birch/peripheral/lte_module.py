import serial
import time
import re
import logging

"""
UBlox SARA LTE modem module driver
https://www.u-blox.com/sites/default/files/SARA-R4_ATCommands_UBX-17003787.pdf
"""


class LTEModule():
    event_logger = logging.getLogger("event_logger")
    pass


class UBloxSara(LTEModule):
    def __init__(self, connection):
        self.connection = connection

    def at_command(self, cmd: bytes):
        self.event_logger.info("LTE >> %s" % cmd)

        self.connection.write(cmd + b"\r\n")
        time.sleep(0.1)
        resp = self.connection.read(1024)
        self.event_logger.info("LTE << %s" % resp)
        result = b"OK" in resp or b"ULSTFILE" in resp
        resp = resp.replace(cmd, b"")
        resp = resp.replace(b"OK", b"")
        resp = resp.replace(b"\"", b"")
        resp = resp.replace(b"+CCID: ", b"")
        resp = resp.replace(b"AT+CC: ", b"")
        resp = resp.strip()
        return result, resp

    def read_info(self, cmds):
        resp = self.connection.read(1024)
        info = {}
        for k in cmds:
            at_resp = self.at_command(cmds[k])
            if at_resp[0]:
                resp = at_resp[1].replace(b"\xff", b"x")
                # print(resp)
                info[k] = str(resp, "utf-8")
            else:
                info[k] = None

        return info

    def read_module_info(self):
        """
        Read module info, format as a dictionary.
        """

        cmds = {
            "manufacturer_identification": b"AT+CGMI",
            "model": b"AT+CGMM",
            "fw_version": b"AT+GMR",
            "imei": b"AT+GSN",
            "type_code": b"ATI0",
            "application_version": b"ATI9",
            "card_id": b"AT+CCID",
            "sc_lock": b'AT+CLCK="SC",2',
            "sc_pin_status": b'AT+CPIN?',
            "files": b'AT+ULSTFILE',
        }
        return self.read_info(cmds)

    def read_network_info(self):
        """
        Read connection info
        """
        cmds = {
            "operator_selection": b'AT+COPS?',
            "network_registration_status": b'AT+CREG?',
            "signal_quality": b"AT+CSQ",
            # "active_profile":b"AT&V",
        }
        return self.read_info(cmds)

    def ping(self):
        """
        Send AT, expect OK
        """
        result, resp = self.at_command(b"AT")
        return result
