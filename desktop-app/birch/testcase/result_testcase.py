from .testcase import TestCase
import time


class ResultTestCase(TestCase):
    """
    Pass/fail/error depending on the scanned barcode.

    Uses Device()
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.target = self.device_list["target"]
        self.interface = self.device_list["interface"]

        self.append_step("Step 1", self.step1)
        self.append_step("Step 2", self.step2)

    def step1(self):
        """
        Dummy step
        """
        time.sleep(0.5)
        return {"result": True}

    def step2(self):
        """
        Check serial number to derive result.

        if F in barcode 
        """
        time.sleep(0.5)
        barcode = self.target.get_barcode()
        if "F" in barcode:
            self.log_error(self.ErrorCode.test_code)
            return {"result": False}

        if "E" in barcode:
            raise Exception("Step2 exception")

        return {"result": True}
