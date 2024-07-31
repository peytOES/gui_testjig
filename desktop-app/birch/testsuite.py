import time
import sys
import threading
import logging
import logging.handlers
import json
import datetime
from datetime import timezone
import serial
import os

from birch.test_status import TestStatus
from birch.database.db_interface import DBInterface
from birch.testcase.testcase import TestCase


class TestSuite(object):
    """
    Test suite: sequence of testcases, dependencies etc for execution
    """

    event_logger = logging.getLogger("event_logger")
    lock = threading.RLock()

    def __init__(self,
                 slot,
                 filename,
                 config,
                 device_list=None):

        self.result_logger = logging.getLogger("result_logger")
        self.event_logger = logging.getLogger("event_logger")
        # keep track of where we are in test
        self.test_index = 0
        self.status = None
        self.config = config
        self.device_list = device_list

        # handle of our parent slot manager
        self.slot = slot

        self.job = slot.job
        # print("\n\n\n>>> self.job", self.job, self.job.path)
        # self.serial_mgr = SerialManager()
        self.log_info("Loading", {"testsuite_file": filename})

        # load test suite data
        with TestSuite.lock:
            with open(filename, 'r') as f:
                data = json.load(f)

        self.name = data["name"]
        if "retries" in data.keys():
            self.retries = data["retries"]
        else:
            # default retries
            self.retries = 3

        ##connect to a result database
        self.event_logger.warning("DB disabled")
        if "db_name" in data:
            self.db = DBInterface.create(**self.config.result_db, product=self.config.product)
            self.log_info("Connection to database", {"db_name": data["db_name"]})
            self.db.set_database(data["db_name"])
        else:
            self.db = DBInterface.create(None, product=self.config.product)
            self.log_info("No database defined", {})
            self.db.disable()

        self.status = TestStatus.UNTESTED

        self.preconditions = {}
        self.testcases = {}

        self.card_eui = None

        for c in data["test_cases"]:
            # print("Test case", c["target"], c)
            # test cases types have all been imported, create an instance

            # testcase_type = eval(c["target"])
            param = {}

            param["job"] = self.job
            param["slot"] = self.slot.index
            param["test_id"] = c["id"]
            param["step_callback"] = self.step_callback
            param["status_callback"] = self.slot.status_msg_cb
            param["device_list"] = self.device_list
            param["config"] = self.config
            param["timeout"] = c["timeout"]
            if "retries" in c.keys():
                param["retries"] = c["retries"]
            else:
                param["retries"] = self.retries

            # append fixture level parameters
            if c["id"] in self.config.test_parameters:
                param.update(self.config.test_parameters[c["id"]])

            # append test_suite level parameters - these may override the fixture level ones
            param.update(c["parameters"])

            # append job specific parameters from job.json - these may override the fixture and test_suite level parameters
            if self.job is not None:
                if c["id"] in self.job._parameters:
                    param.update(self.job._parameters[c["id"]])

            # bring in test specific parameters specified in job.json
            # if c["id"] in self.job.parameters:
            #    param.update(self.job.parameters[c["id"]])

            instance = TestCase.create(c["target"], **param)
            steps = instance.get_step_names()

            testname = "%s - %s" % (c["id"], c["name"])
            self.testcases[c["id"]] = instance
            self.preconditions[c["id"]] = c["preconditions"]

    def log_info(self, msg, extra={}):
        # print(msg, extra)
        extra["location"] = "TestSuite"
        extra["slot"] = str(self.slot.index)
        TestSuite.event_logger.info(
            msg=msg,
            extra=extra
        )

    def next_testcase(self):
        """
        Return the next test, None when done
        """
        start = time.time()
        for t in self.testcases.values():
            if t.status == TestStatus.UNTESTED:
                preconditions_satisfied = True
                for d in self.preconditions[t.test_id]:
                    if self.testcases[d].status != TestStatus.PASS:
                        preconditions_satisfied = False

                if preconditions_satisfied:
                    return t
        return None

    def log_debug(self, *args, **kwargs):
        print(*args, **kwargs)

    def run(self):
        self.event_logger.info("testsuite run()")
        self.test_index = 0
        self.status = TestStatus.PASS
        self.serial_number = None
        self.label_data = {}

        step_log = []
        start = datetime.datetime.now(timezone.utc).astimezone()

        t = self.next_testcase()
        self.set_led(TestStatus.INCOMPLETE)
        while t is not None:

            for i in range(t.retries):  # retry loop
                self.log_info("Running test %s (attempt %d/%d)" % (t.test_id, i + 1, t.retries))
                try:
                    result = t.execute(retry_count=i)
                except Exception:
                    # catching Exceptions here
                    exc_type, exc_value, exc_trace = sys.exc_info()
                    self.log_info(
                        msg="Test suite exception",
                        extra={
                            "exception_type": exc_type,
                            "exception_value": exc_value,
                            "exception_trace": exc_trace
                        }
                    )
                    t.status = TestStatus.ERROR

                step_log.append({
                    "test_id": t.test_id,
                    "result": TestStatus.str(t.status),
                    "log": t.log,
                    "error_code": t.error_code,
                    "timestamp": t.timestamp.isoformat(),
                    "duration": t.duration,
                    "retry_count": i,
                })

                if t.status == TestStatus.PASS or t.status == TestStatus.SKIP:
                    # if passed, do not retry
                    break

            self.slot.report_error_codes(t.error_code)
            self.test_index += 1

            if t.status == TestStatus.FAIL:
                # if we fail any test, test suite status = FAIL.
                # skipping has no impact
                self.status = TestStatus.FAIL
            elif t.status == TestStatus.ERROR:
                self.status = TestStatus.ERROR

            t = self.next_testcase()

        self.set_led(self.status)
        duration = (datetime.datetime.now(timezone.utc) - start).total_seconds()
        result_dict = {
            "result": TestStatus.str(self.status),
            "slot": self.slot.index + 1,
            "timestamp": start.isoformat(),
            "duration": duration,
            "steps": step_log,
            "job_id": str(self.job),
            "operator_id": self.slot.operator_id,
            "fixture": self.config.fixture_id,
            "product": self.config.product,
            "serial": self.slot.barcode
        }

        serial = ""

        # to file
        self.result_logger.warning(
            msg="log",
            extra=result_dict)
        # to db
        self.db.log_result(result_dict)
        self.db.log_device(self.device_list["target"])

        return result_dict

    def set_led(self, led):
        if "interface" in self.device_list:
            if self.device_list["interface"] is not None:
                self.device_list["interface"].set_led(led, True)

    def step_callback(self, step_index, value):
        """
        Callback from test case, relay to GUI
        """
        pass

    def label_data_callback(self, value):
        """
        Callback for storing the install code read from the card
        """
        self.label_data = value
