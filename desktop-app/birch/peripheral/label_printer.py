"""
Label printer driver.
"""
import sys
import socket
import glob
import threading
import logging
import os
import time
import telnetlib
from pathlib import Path
from .device import Device

event_logger = logging.getLogger("event_logger")


class ZebraPrinter(object):
    """
    Handles telnet interface to label printer
    """

    @staticmethod
    def print_label(ip_address: str, port: int = 9100, zpl="", timeout=10):
        """
        Print a zpl file, return True is successful
        """
        with threading.Lock():
            result = ""
            try:
                socket.setdefaulttimeout(timeout)
                tn = telnetlib.Telnet(ip_address, port)
                result = tn.write(bytearray(zpl, 'utf-8'))
                tn.close()
                return True
            except ConnectionRefusedError:
                event_logger.info(msg="LabelPrinter::ConnectionRefusedError")
                return False
            except OSError:
                event_logger.info(msg="LabelPrinter::OSError")
                return False
            except Exception as e:
                event_logger.exception("LabelPrinter::Unexpected error: %s" % e)
                return False
        return False


class LabelPrinter(Device):
    def __init__(self, config, ip=None, port=None):
        self.config = config
        self.ip = ip
        self.port = port

    def print_result(self, result):
        if result["result"] not in ["PASS", "FAIL"]:
            return

        fname = result["result"].lower() + ".zpl"
        # print("Using label ", self.config.config_dir, fname)
        # print("printer", self.ip, self.port)

        with open(Path(self.config.config_dir) / "labels" / fname, "r") as f:
            raw = f.read()
            # perform field substitution if needed
            formatted = raw
            return ZebraPrinter.print_label(
                ip_address=self.ip,
                port=self.port,
                zpl=formatted)
