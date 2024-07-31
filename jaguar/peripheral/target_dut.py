import attr
import time
import datetime
import serial
import logging

from birch.peripheral.target_dut import TargetDUT
from birch.peripheral.util import find_port


@attr.s
class JaguarTargetDUT(TargetDUT):
    PID = "6001"
    VID = "0403"
    # fields that will be logged
    product = attr.ib(default="jaguar")
    iot = attr.ib(default="")
    ble_mac = attr.ib(default="")
    imei = attr.ib(default="")
    sim = attr.ib(default="")
    timestamp = datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat()

    connection = None
    comms_retry = 3

    def open(self):
        """
        Open serial connection to target dut 
        """
        port = find_port(vid=self.VID, pid=self.PID)
        if port is None:
            return False
        try:
            self.connection = serial.Serial(port, 115200, write_timeout=0.1, timeout=0.1)
            return True
        except:
            return False
        

    def close(self):
        """
        Close serial connection to target dut
        """
        self.connection.close()

    def uart_write(self, data, resp=False):
        self.connection.read(1024)
        for d in data:
            self.connection.write(bytes([d]))
        time.sleep(0.1)
        if resp == False:
            return None
        else:
            for j in range(10):
                time.sleep(0.1)
                s = self.connection.readline(1000)
                if len(s) > 0:
                    return s
        return None

    def reset(self):
        pass

    def enable_ble_passthrough(self, value):
        if value:
            cmd = "b \r\n"
            resp = self.uart_write(bytes(cmd, "utf-8"), resp=True)
            return resp
        else:
            pass  # raise Exception("Not implemented")

    def enable_lte_passthrough(self, value):
        if value:
            self._lte_passthrough = True
            self.connection.read(1024)
            cmd = "m \r\n"
            self.uart_write(bytes(cmd, "utf-8"), resp=False)
            for i in range(12):
                resp = self.connection.readline()
                if b"MODEM TO" in resp:
                    return True
                time.sleep(1)
            return False
        else:
            self._lte_passthrough = False
            return True

    def enter_sleep_mode(self):
        """
        Enter low-power sleep mode
        """
        cmd = "p \r\n"
        resp = self.uart_write(bytes(cmd, "utf-8"), resp=True)
        return resp

    def read_pin(self, port: str, pin: int):
        """
        Read GPIO level.

        Returns -1 for error, 0 for low, 1 for high
        """
        cmd = "6 %s %d     \r" % (port.upper(), pin)
        resp = self.uart_write(bytes(cmd, "utf-8"), resp=True)
        try:
            value = int(resp.strip().split(b":")[1])
        except Exception as e:
            self.event_logger.info("JaguarTargetDUT read invalid value %s" % str(resp))
            return -1
        return value

    def set_pin(self, port: str, pin: int, value: bool):
        cmd = "5 %s %d %d    \r" % (port.upper(), pin, value)
        resp = self.uart_write(bytes(cmd, "utf-8"), resp=False)

    def read_adc(self):
        """
        Returns 12bit ADC values
        """
        for i in range(self.comms_retry):
            resp = self.uart_write(b"4\r", resp=True)
            if resp is None:
                time.sleep(0.5)
                continue
            if b"ADC" in resp:
                resp = resp.replace(b":", b" ")
                resp = resp.replace(b",", b" ")
                _, a, _, b, _, c = (resp.split())
                print(int(a), int(b), int(c))
                return (int(a), int(b), int(c))
            time.sleep(1)
        return -1, -1, -1

    def set_dac(self, channel, value):
        """
        Send command to set DAC out on the DUT

        channel = [1,2]
        value = 0-255
        """
        if channel not in [1, 2]:
            self.event_logger.info("JaguarTargetDUT set_dac invalid channel")
            return False
        if value < 0 or value > 255:
            self.event_logger.info("JaguarTargetDUT set_dac invalid value")
            return False

        cmd = "2 %d %d\r" % (channel, value)
        resp = self.uart_write(bytes(cmd, "utf-8"), resp=False)
        return True

    def read_pulse_count(self):
        cmd = "3 1 \r"
        resp = self.uart_write(bytes(cmd, "utf-8"), resp=True)
        try:
            count = int(resp.strip().split(b":")[-1])
        except Exception as e:
            self.event_logger.info("JaguarTargetDUT read_pulse_count failed %s" % str(e))
            return -1
        return count

    def read_mag(self, index):
        if index == 0:
            return self.read_pin("A", 0)
        elif index == 1:
            return self.read_pin("C", 13)
        return 0
