# jaguar/testcase/__init__.py

# Import the base first to avoid cycles
from .jaguar_testcase import JaguarTestCase

# Then import concrete testcases (including analog)
from .internet_testcase import InternetConnectionTestCase
from .power_testcase import DCPowerTestCase, BatPowerTestCase
from .program_firmware import ProgramFirmwareTestCase
from .analog_testcase import AnalogTestCase
from .digital_testcase import DigitalTestCase
from .ble_testcase import BLETestCase
from .lte_testcase import LTETestCase
from .sleep_current_testcase import SleepCurrentTestCase
from .provision_testcase import ProvisionTestCase
from .memory_protect import MemoryProtectTestcase

__all__ = [
    "JaguarTestCase",
    "InternetConnectionTestCase",
    "DCPowerTestCase",
    "BatPowerTestCase",
    "ProgramFirmwareTestCase",
    "AnalogTestCase",
    "DigitalTestCase",
    "BLETestCase",
    "LTETestCase",
    "SleepCurrentTestCase",
    "ProvisionTestCase",
    "MemoryProtectTestcase",
]
