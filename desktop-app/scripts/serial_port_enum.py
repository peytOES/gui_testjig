from __future__ import print_function
import logging
import serial

print(serial.__path__)
import time
import serial.tools.list_ports as list_ports


def traverse_ports():
    for comport in list_ports.comports():
        print("\n", time.time(), comport.device, comport.manufacturer, comport.description, comport.vid, comport.pid,
              comport.product, comport.name, comport.location, comport.interface, comport.hwid)
        if comport.vid is not None:
            print("%04X" % comport.vid, "%04X" % comport.pid)
        print(time.time(), "open")
        try:
            ser = serial.Serial(comport.device, 115200, write_timeout=0.01, timeout=0.1)
            print(time.time(), "closing")
            ser.close()
            print(time.time(), "closed")
        except serial.SerialException as e:
            print(e)

    pass


if __name__ == "__main__":
    traverse_ports()
