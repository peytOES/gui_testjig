from jaguar.peripheral.interface import JaguarInterface
import time

if __name__ == "__main__":
    j = JaguarInterface()
    j.open()

    j.analog_enable(True)
    j.battery_power_en(True)
    j.dc_power_en(False)
    while (1):
        print("%.3fmA %.3fmA %.3fV" % (j.battery_current() * 1000, j.dc_current() * 1000, j.sys_voltage()))
        time.sleep(0.1)
