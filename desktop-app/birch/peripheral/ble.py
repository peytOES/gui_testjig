import time
import binascii
import logging

from .bled112.scanner import BLED112
from birch.peripheral.util import find_port


class BLE():
    """
    High-level  BLE parent class - handles the BLE dongle
    """
    VID = "2458"
    PID = "0001"
    event_logger = logging.getLogger("event_logger")

    def __init__(self, *args, **kwargs):
        self.bled = None

    def open(self):
        if self.bled is not None:
            # already open
            return True
        port = find_port(vid=self.VID, pid=self.PID)
        if port is None:
            return False

        self.bled = BLED112(port, 115200)
        self.bled.open()
        return True

    def close(self):
        if self.bled:
            self.bled.close()
            self.bled = None

    def scan(self, duration=5):
        """
        Return list of addresses and RSSI values found.
        """
        self.open()
        devices = self.bled.scan(duration)
        if devices is None:
            self.close()
            return {}
        # format addresses
        ret = {}
        for device in devices:
            addr = binascii.b2a_hex(device[::-1]).decode("utf-8")
            ret[addr] = devices[device]
        self.close()
        return ret

    def connect(self, addr: str, duration=5):
        """
        Connect to specified addr
        """
        self.open()
        if self.bled is None:
            self.event_logger.warning("BLED112 open failed")
            return False
        # reverse byte order for BLED
        addr = binascii.a2b_hex(addr)[::-1]

        if len(addr) != 6:
            return False
        # self.bled.open()
        self.bled.scan(duration, target=addr)
        return self.bled.connected()

    def check_activity(self, *args, **kwargs):
        if self.bled:
            self.bled.check_activity(*args, **kwargs)

    def disconnect(self):
        if self.bled:
            self.bled.disconnect()
            self.close()

    def transmit(self):
        return True
