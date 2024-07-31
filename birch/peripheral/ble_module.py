import serial
import time
import re
import logging

"""
As the testing is already done by u-blox, an OEM manufacturer does not need to repeat software tests
or measurement of the module’s RF performance or tests over analog and digital interfaces in their
production test.
However, an OEM manufacturer should focus on:
• Module assembly on the device; it should be verified that:
o Soldering and handling process did not damage the module components
o All module pins are well soldered on device board
o There are no short circuits between pins
• Component assembly on the device; it should be verified that:
o Communication with host controller can be established
o The interfaces between module and device are working
o Overall RF performance test of the device including antenna

"""
"""
BLE Bar code
???| MAC        | date?
F74|CCF9579763CF|0204

LTE: B38SARA-R410M-02B-00_356726100955202_0215
"""

import re

MAC_PATTERN = r"[0-9a-fA-F]{12}"


class BLEModule():
    event_logger = logging.getLogger("event_logger")

    def __init__(self, connection):
        self.connection = connection


class UBloxNina(BLEModule):

    def at_command(self, cmd: bytes):
        self.event_logger.info("Nina >> %s" % cmd)
        self.connection.write(cmd + b"\r\n")
        resp = self.connection.read(1024)
        self.event_logger.info("Nina << %s" % resp)
        result = b"OK" in resp
        resp = resp.replace(b"OK", b"")
        resp = resp.replace(b"\"", b"")
        resp = resp.strip()
        return result, resp

    def read_module_info(self):
        """
        Manufacturer identification AT+CGMI
        Model AT+CGMM
        Serial number AT+GSN
        type code ATI0
        MCUID +ATI10
        Application version ATI9
        MCUID +ATI10
        Software version AT+GMR


        MAC address:
        AT+UMLA=1
        +UMLA:CCF9579763CF

        """
        cmds = {
            "manufacturer_identification": b"AT+CGMI",
            "model": b"AT+CGMM",
            "serial_number": b"AT+GSN",
            "type_code": b"ATI0",
            "application_version": b"ATI9",
            "mcuid": b"ATI10",
            "fw_version": b"AT+GMR",
            "mac_address": b"AT+UMLA=1"
        }
        module_info = {}
        for c in cmds:
            # print(">> ", cmds[c])
            resp = self.at_command(cmds[c])
            # print("<< ", resp)

            if resp[0]:  # specific case to clean up mac address
                module_info[c] = str(resp[1], "utf-8")

                if c == "mac_address":
                    mac = re.findall(MAC_PATTERN, module_info[c])
                    if len(mac) > 0:
                        module_info[c] = mac[0]
                    else:
                        module_info[c] = None
                else:  # generally remove any lines starting with AT
                    result = ""
                    for segment in module_info[c].split():
                        if segment[:2] != "AT":
                            result += segment
                    module_info[c] = result
            else:
                module_info[c] = None

        return module_info

    def wait_for_connect(self, timeout=10):
        """
        Wait up to 10 seconds for a connection

        Return (True|False, remote address)
        """
        t0 = time.time()
        while time.time() - t0 < timeout:
            resp = self.connection.read(1024)
            if b"+UUBTACLC" in resp:
                try:
                    connection_handle, connection_type, address = re.findall(b"UUBTACLC:(\d),(\d),(\w+)", resp.strip())[
                        0]
                    address = address[:-1].decode("utf-8")
                    return True, address
                except Exception:
                    return False, ""
        return False, ""

    def wait_for_disconnect(self, timeout=10):
        """
        Wait up to 10 seconds for disconnect
        """
        t0 = time.time()
        while time.time() - t0 < timeout:
            resp = self.connection.read(1024)
            if b"+UUBTACLD" in resp:
                return True, resp

        return False, ""

    def connection_rssi(self, address: bytes):
        """
        Return RSSI of currently running connection.

        AT+UBTRSS=000780144029
        +UBTRSS:-54
        OK
        """
        resp = self.at_command(b"AT+UBTRSS=" + address)
        resp = resp.replace(b"OK", "")
        resp = resp.strip()
        return resp.split(":")[-1]

    def enter_ble_mode(self, timeout=1):
        """
        Move to jaguar control?
        """
        self.connection.write(b"b \r\n")
        t0 = time.time()
        while time.time() - t0 < timeout:
            resp = self.connection.read(1024)
            if b"BLE mode" in resp:
                time.sleep(0.1)
                return True, resp
            time.sleep(0.1)


"""
Connection detected:

+UUBTACLC:0,0,77F2EEA6FC3Cr

+UUBTLEPHYU:0,0,2,2


Disconnection:
+UUBTACLD:0
"""


class BLEAtMock(UBloxNina):
    # mock to test the ble response stripping
    def at_command(self, cmd: bytes):
        cmds = {
            "manufacturer_identification": b"AT+CGMI",
            "model": b"AT+CGMM",
            "serial_number": b"AT+GSN",
            "type_code": b"ATI0",
            "application_version": b"ATI9",
            "mcuid": b"ATI10",
            "fw_version": b"AT+GMR",
            "mac_address": b"AT+UMLA=1"
        }

        resp = cmd + b"\r\n\r\nTest\r\n"
        return True, resp


if __name__ == "__main__":
    b = BLEAtMock(None)
    print(b.read_module_info())
