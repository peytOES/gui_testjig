from . import TestCase


class Birch_UnitTestCase(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.append_step("Unit test step1 ", self.step1)

    def step1(self):
        print("step1")
        return {"result": True}
