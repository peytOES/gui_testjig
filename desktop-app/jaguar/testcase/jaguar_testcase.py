from birch.testcase.testcase import TestCase


class JaguarTestCase(TestCase):
    """
    Parent class of all jaguar test cases
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.target = self.device_list["target"]
        self.interface = self.device_list["interface"]
        self.ble = self.device_list["ble"]
        self.programmer = self.device_list["programmer"]
