import logging
import time
import datetime

from birch.test_status import TestStatus
from birch.provision_status import ProvisionStatus
from birch.error_codes import load_error_codes


class TestTimeoutException(Exception):
    pass


class TestStep():
    def __init__(self, name, fn):
        self.name = name
        self.fn = fn


class StepData():
    def __init__(self, result, data):
        self.result = result
        self.data = data


class TestCase(object):
    """
    Test case base class
    """

    def __init__(self,
                 test_id="ID",
                 status_callback=None,
                 step_callback=None,
                 retries=3,
                 timeout=10.,
                 slot=0,
                 config=None,
                 job=None,
                 device_list=None,
                 **kwargs):

        self.event_logger = logging.getLogger("event_logger")

        self.test_id = test_id
        self.timestamp = None
        self.timeout = timeout
        self.duration = 0
        self.retries = retries
        self.slot = slot
        self.device_list = device_list
        self.job = job
        self.config = config
        self.iot = None
        self.ErrorCode = load_error_codes(self.config.config_dir)

        self.steps = []
        # callback functions
        self.status_msg_cb = status_callback
        self.step_cb = step_callback
        # hardware interfaces
        self.enabled = True
        # reset
        self.log = []
        self.error_code = []
        self.status = TestStatus.UNTESTED
        self.provisionStatus = ProvisionStatus.INCOMPLETE
        self.reset()

    def status_call(self, *args, **kwargs):
        if self.status_msg_cb:
            self.status_msg_cb(*args, **kwargs)

    def step_call(self, *args, **kwargs):
        if self.step_call:
            self.step_cb(*args, **kwargs)

    def execute(self, retry_count, *args, **kwargs):
        """
        Run all the registered steps
        """

        self.timestamp = datetime.datetime.now(datetime.timezone.utc).astimezone()
        if not self.enabled:
            self.error_code = []
            self.status = TestStatus.SKIP
            return True

        self.reset()
        self.status = TestStatus.INCOMPLETE
        self.status_call("%s: Setup (%d/%d)" % (self.test_id, retry_count + 1, self.retries))
        self.setup()
        count = 0
        self.status = TestStatus.PASS
        for s in self.steps:
            # check if timeout exceeded
            dt = (datetime.datetime.now(datetime.timezone.utc).astimezone() - self.timestamp).total_seconds()
            if dt > self.timeout:
                self.event_logger.debug("timeout %.2f %.2f" % (self.timeout, dt))
                self.status = TestStatus.ERROR
                self.log_error(self.ErrorCode.timeout)
                break;
            # check if dut removed
            if self.device_list["interface"].dut_present() != True:
                self.log_error(self.ErrorCode.dut_removed)
                self.status = TestStatus.ERROR
                break;

            # update status message in GUI
            self.status_call("%s: %s (%d/%d)" % (self.test_id, s.name, retry_count + 1, self.retries))

            step_data = s.fn()
            step_data["step_name"] = s.name
            self.log.append(step_data)

            if step_data["result"] != True:
                self.status = TestStatus.FAIL
            
            try:
                if step_data["provision_status"]:
                    self.provisionStatus = ProvisionStatus.COMPLETE
                
                if "iot" in step_data:
                    self.iot = step_data["iot"]


            except:
                pass

            # update step progress in GUI
            self.step_cb(count, self.status)

            count += 1

        self.status_call("%s: Tear down (%d/%d)" % (self.test_id, retry_count + 1, self.retries))
        self.teardown()

        self.duration = (datetime.datetime.now(datetime.timezone.utc) - self.timestamp).total_seconds()
        if self.status == TestStatus.PASS:
            self.error_code = []
            self.event_logger.debug("Test passed")
            return True
        elif self.status == TestStatus.FAIL:
            self.event_logger.debug("Test failed")
            return False
        elif self.status == TestStatus.ERROR:
            self.event_logger.debug("Error")
            return False
        else:
            # No steps: treat as skipped
            self.status = TestStatus.SKIP
            return True

    def is_ready(self):
        """
        Attempt to acquire resources necessary for execution.

        return True is successful, else False
        """
        return True

    def reset(self):
        """
        Reset to untested state
        """
        self.log = []
        self.error_code = []
        self.status = TestStatus.UNTESTED

    def skip(self):
        """
        Skip this test.

        Test status is updated to SKIP
        """
        self.status = TestStep.SKIP

    def append_step(self, name, fn):
        """
        Add a function to the list steps to be followed for this test

        name : Step name (string)
        fn : Step function (void)
        """
        self.steps.append(TestStep(name, fn))

    def setup(self):
        """
        Setup to do before execution.

        Over-ride in children
        """
        pass

    def teardown(self):
        """
        Clean up after test.
        Over-ride in children
        """
        pass

    def get_status(self):
        """
        Return test status
        """
        return self.status

    def get_step_names(self):
        """
        Return list of step names (for display in GUI)
        """
        return [s.name for s in self.steps]

    def trace(self, *args, **kwargs):
        if self.ctl is None:
            return
        if self.ctl.trace:
            print(time.time(), *args, **kwargs)

    def raise_timeout(self):
        raise TestTimeoutException

    def log_error(self, error):
        self.error_code.append(error)

    @staticmethod
    def all_testcases(cls):
        return set(cls.__subclasses__()).union(
            [s for c in cls.__subclasses__() for s in TestCase.all_testcases(c)] + [TestCase])

    @staticmethod
    def create(testcase, *args, **kwargs):
        """
        Instantiate an instance of the named testcase by looking for a matching name in the
        subclasses of TestCase
        """
        # print("Known testcases:", TestCase.all_testcases(TestCase))
        for cls in TestCase.all_testcases(TestCase):
            if cls.__name__.lower() == testcase.lower():
                # print(args, kwargs)
                return cls(*args, **kwargs)
        raise Exception("Test case %s not found" % testcase)
