from birch.manager import ManagerUI

from .peripheral.target_dut import JaguarTargetDUT
from .gui.operator_gui import JaguarOperatorGUI
from .slot import JaguarSlot


class JaguarManagerUI(ManagerUI):
    def __init__(self, title='Jaguar Production Fixture', *args, **kwargs):
        super().__init__(title, *args, **kwargs)
