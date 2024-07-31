from __future__ import print_function
import time
import sys
import serial


# 1) run test_serial.py
# 2) Orange light stops flashing. Buffer overflow
# 3) After ~30sec re-open port -> orange light starts flashing again


def serial_test(port):
    p = serial.Serial(port, baudrate=115200, write_timeout=0.1, timeout=0.1)
    p.read()

    for i in range(100):
        p.write(b"1" * (i ** 2) + b"\r\n")
        print(i, p.read(i ** 2 + 30))


if __name__ == "__main__":
    try:
        serial_test(sys.argv[1])
    except serial.SerialTimeoutException as e:
        print(e)

    time.sleep(5)
    serial_test(sys.argv[1])
