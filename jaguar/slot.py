from birch.slot import SlotSingle, SlotState

from birch.peripheral.stm32cube_programmer import STM32CubeProgrammer
from birch.peripheral.ble import BLE

from .peripheral.interface import JaguarInterface
from birch.peripheral.interface import Interface


class JaguarSlot(SlotSingle):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def state_init_enter(self):
        self.interface = JaguarInterface()
        self.device_list["interface"] = self.interface
        self.programmer = STM32CubeProgrammer()
        self.device_list["programmer"] = self.programmer
        self.ble = BLE()
        self.device_list["ble"] = self.ble

        self.open_detected = False
        super().state_init_enter()

    def state_empty_run(self):
        if self.job.is_complete():
            self.state_transition(SlotState.COMPLETE)
            return

        if self.state_elapsed_time() > 20:
            self.state_transition(SlotState.SCAN_BARCODE)

        # if not self.interface.dut_present():
        self.open_detected = True

        if self.open_detected and self.interface.dut_present():
            self.state_transition(SlotState.ACTIVE)
            self.open_detected = False
