import json
import time
import enum
from pathlib import Path
import logging

from pubsub import pub

from birch.core.state_machine import StateMachine, State
from birch.core.common import BirchObject, LogObject
from birch.peripheral.target_dut import TargetDUT
from birch.peripheral.label_printer import LabelPrinter

from birch.testsuite import TestSuite
from birch.test_status import TestStatus


class SlotState(enum.IntEnum):
    INIT = 0  # init state
    SLOT_SELECT = 1  # wait for slot selection scan
    SCAN_BARCODE = 2  # wait for barcode scan
    EMPTY = 3  # waiting for module to be inserted
    ACTIVE = 4  # test cases are running
    RESULT = 5  # display result
    COMPLETE = 6  # job complete
    ERROR = 7  # Some error occurred
    NO_TOKENS = 8  # No tokens available


class SlotView():
    """
    Abstraction object used by GUI
    """

    def __init__(self, slot):
        self.slot = slot

        self.index = 0
        self.serial_number = ""
        self.eui = ""
        self.firmware = ""
        self.elapsed_time = ""
        self.test_result = None
        self.previous_result = None
        self.previous_eui = None

        self.data = {
            "index": 0,
            "elapsed_time": 0.0,
            "color": None,
            "test_result": None,
            "previous_result": None
        }


class Slot(StateMachine):
    """
    Test slot. 

    One slot deals with one DUT at a time
    """

    def __init__(self, index, mgr=None, config=None, complete_cb=None, enabled=True, device_list={}, *args, **kwargs):
        super().__init__(prefix="slot%02d" % index, *args, **kwargs)
        self.mgr = mgr
        self.index = index
        self.msg_topic = "slot%02d" % index
        self.config = config
        self.device_list = device_list
        self.result_dict = {}
        self.fw = 'USA'

        self.complete_cb = complete_cb

        self.logger = logging.getLogger(__name__ + "%02d" % index)
        self.logger.setLevel(logging.DEBUG)

        self.state = SlotState.INIT
        self.state_table = {
            SlotState.INIT: State(
                self.state_init_enter,
                self.state_init_run,
                None),
            SlotState.SLOT_SELECT: State(
                self.state_slot_select_enter,
                self.state_slot_select_run,
                None),
            SlotState.SCAN_BARCODE: State(  # wait for a module scan
                self.state_scan_barcode_enter,
                self.state_scan_barcode_run,
                None),
            SlotState.EMPTY: State(  # waiting for card to be detected
                self.state_empty_enter,
                self.state_empty_run,
                None),
            SlotState.ACTIVE: State(  # test cases are running
                self.state_active_enter,
                self.state_active_run,
                None),
            SlotState.RESULT: State(  # test result is displayed
                self.state_result_enter,
                self.state_result_run,
                self.state_result_exit),
            SlotState.COMPLETE: State(  # job complete
                self.state_complete_enter,
                self.state_complete_run,
                None),
            SlotState.ERROR: State(  # error occurred
                self.state_error_enter,
                self.state_error_run,
                self.state_error_exit),
            SlotState.NO_TOKENS: State(  # out of tokens
                self.state_no_tokens_enter,
                self.state_no_tokens_run,
                None),
        }
        # self.device = None
        # self.peripheral= None
        self.job = None
        self.operator_id = None
        self.barcode = None
        self.test_suite = None
        self.token = None
        self.provision_enable = False #By default, provision enable is True and only set to false if the check
        self.log_upload_enable = True
        self.warning_enable = True
        # show label print warning only once
        self.label_print_warning = True

        pub.subscribe(self.pub_listener, "system")

    def pub_listener(self, message, arg2=None):
        """
        pusbsub listener - maps received messages to local function calls
        """
        fn_map = {
            "barcode_scan": self.barcode_scan,
        }

        for f in fn_map.keys():
            if f in message:
                try:
                    fn_map[f](message[f])
                except Exception as e:
                    self.event_logger.exception("Message call failed: %s %s", f, str(message))

        # print(f"manager:pub_listener {message} {arg2}")

    def stop(self):
        super().stop()
        self.log_info("Slot stop")
        # self.peripheral.stop()
        # self.device.stop()

    def run(self):
        self.log_info("Slot run")
        self.state = SlotState.INIT

        super().run()

    def state_init_enter(self):
        self.label_print_warning = True
        pub.sendMessage(self.msg_topic, message={
            "neutral": True,
            "test_result": TestStatus.INACTIVE,
            "serial_number": "",
            "previous_result": TestStatus.INACTIVE,
            "status_msg": "",
            "status": "",
            "eui": None,
            "serial_number": None,
            "error_codes": [],
        })

        self.device_list["printer"] = LabelPrinter(self.config, **self.config.printer)

        self.open_devices()

    def state_init_run(self):
        if self.job is not None:
            self.state_transition(SlotState.SLOT_SELECT)

    def state_scan_barcode_enter(self):
        pub.sendMessage(self.msg_topic, message={
            "status_msg": "Scan module...",
            "serial_number": None,
        })

        # create a device
        d = TargetDUT.factory(product=self.config.product)
        self.device_list["target"] = d
        d.open()

        self.test_auto_scan()

    def state_scan_barcode_run(self):
        if self.job is not None and self.job.is_complete():
            self.state_transition(SlotState.COMPLETE)

    def state_empty_enter(self):
        pub.sendMessage(self.msg_topic, message={
            "status_msg": "Insert DUT..."
        })
        pub.sendMessage(self.msg_topic, message={
            "test_result": TestStatus.INCOMPLETE,
        })
        if self.barcode is not None:
            pub.sendMessage(self.msg_topic, message={"serial_number": self.barcode})

    def state_empty_run(self):
        if self.job.is_complete():
            self.state_transition(SlotState.COMPLETE)
            return

        if self.state_elapsed_time() > 20:
            self.state_transition(SlotState.SCAN_BARCODE)

        self.state_transition(SlotState.ACTIVE)

    def state_active_enter(self):
        self.error_codes = []
        pub.sendMessage(self.msg_topic, message={
            "status_msg": "DUT detected"
        })
        self.result_dict = {}
        try:
            self.test_suite = TestSuite(
                self,
                Path(self.config.testsuite_dir) / self.job._test_suite["filename"],
                self.config,
                self.device_list
            )

            # Token reservation
            if self.job.token_total() > 0:
                self.token = self.job.reserve_token()
                if self.token == None:
                    self.state_transition(SlotState.NO_TOKENS)
                    return

                token_data = self.job.read_token_data(self.token)
                self.device_list["target"].assign_token(token_data)
                self.logger.info("Assign token %s" % (self.device_list["target"]))

            pub.sendMessage(self.msg_topic, message={
                "timer_start": True,
                "eui": self.token,
            })

            self.state_transition(SlotState.ACTIVE)

        except Exception as e:
            pub.sendMessage("system", message={
                "message": "Test suite initialisation failed: %s" % str(e)
            })
            self.event_logger.exception("Slot %i: state_active_enter exception %s" % (self.index, e))
            self.log_info("Slot %i: state_active_enter exception %s" % (self.index, e))
            self.state_transition(SlotState.INIT)

    def state_active_run(self):
        if self.job.is_complete():
            self.state_transition(SlotState.COMPLETE)
            return
        try:
            self.result_dict = self.test_suite.run()
        except Exception as e:
            pub.sendMessage("system", message={
                "message": "Test suite execution failed: %s" % str(e)
            })
            self.log_info("Slot %i: state_active_run exception %s" % (self.index, e))
            self.state_transition(SlotState.INIT)
            self.test_suite.status = TestStatus.ERROR

        self.state_transition(SlotState.RESULT)

    def state_result_enter(self):
        if self.test_suite.status == TestStatus.PASS:
            # log passed unit
            self.job.use_token(self.token)
            self.job.unit_passed()
        else:
            self.job.release_token(self.token)

        self.print_label()

        self.token = None
        self.job.unit_tested()

        # Show test result
        pub.sendMessage(self.msg_topic, message={
            "test_result": self.test_suite.status,
            "timer_stop": True,
        })

    def state_result_run(self):
        if self.job.is_complete():
            self.state_transition(SlotState.COMPLETE)

        else:
            self.test_auto_scan()

    def state_result_exit(self):
        self.error_codes = []
        if self.test_suite is None:
            prev_result = None
        else:
            prev_result = self.test_suite.status
        pub.sendMessage(self.msg_topic, message={
            "neutral": True,
            "previous_result": prev_result,
            "test_result": TestStatus.INACTIVE,
            "status_msg": "",
            "status": "",
            "eui": None,
            "serial_number": None,
            "error_codes": []
        })

    def state_complete_enter(self):
        # Job complete state
        pub.sendMessage(self.msg_topic, message={
            "status_msg": "",
            "test_result": TestStatus.JOB_COMPLETE
        })
        if self.complete_cb is not None:
            self.complete_cb()

        if self.job is not None:
            self.job.delete()

        self.log_info("state_complete_run")
        self.thread.stop()

    def state_complete_run(self):
        time.sleep(1)

    def state_no_tokens_enter(self):
        pub.sendMessage(self.msg_topic, message={
            "test_result": TestStatus.NO_TOKENS
        })

    def state_no_tokens_run(self):
        if self.job.token_total() > 0:
            self.token = self.job.reserve_token()
            if self.token is None:
                pub.sendMessage(self.msg_topic, message={
                    "test_result": TestStatus.NO_TOKENS
                })
                time.sleep(1)
            else:
                self.release_token(self.token)
                self.token = None
        pass

    def state_slot_select_enter(self):
        self.barcode = None
        pub.sendMessage(self.msg_topic, message={"status": "Scan slot"})

    def state_slot_select_run(self):
        """
        Slot selection, if only one slot is available, continue through to 
        barcode scan state.
        """
        if self.job is None:
            # No job, 
            self.state_transition(SlotState.INIT)
            return

        if self.job.is_complete():
            self.state_transition(SlotState.COMPLETE)
            return

        # single slot at this time
        if self.index == 0:
            self.state_transition(SlotState.SCAN_BARCODE)

    def state_error_enter(self):
        pass

    def state_error_run(self):
        pass

    def state_error_exit(self):
        pass

    # transitions.
    def set_job(self, job):
        print("set job")
        self.job = job

    def set_operator(self, name):
        self.operator_id = name

    # callbacks 
    def status_msg_cb(self, *args, **kwargs):
        """
        Status message from test case to UI
        """
        pub.sendMessage(self.msg_topic, message={"status_msg": args[0]})

    def test_result_cb(self, *args, **kwargs):
        """
        Test result from test case to UI
        """
        pass

    def report_error_codes(self, error_codes, *args, **kwargs):
        self.error_codes += error_codes
        self.error_codes = list(set(error_codes))
        pub.sendMessage(self.msg_topic, message={"error_codes": self.error_codes})

    def barcode_scan(self, barcode_string, *args, **kwargs):
        self.event_logger.info("barcode_scan %s %d %s" % (barcode_string, self.index, self.state))
        if self.job is None:
            return

        if self.state == SlotState.SCAN_BARCODE:
            self.log_info("barcode_scan %s", barcode_string)
            if "SLOT" in barcode_string and barcode_string != "SLOT%02d" % (self.index + 1):
                self.state_transition(SlotState.SLOT_SELECT)
            else:
                # validate barcode
                if self.job.validate_barcode(barcode_string):
                    # assign barcode to device
                    if self.device_list["target"].set_barcode(barcode_string):
                        self.state_transition(SlotState.EMPTY)
                        self.barcode = barcode_string
                    else:
                        self.log_info("set barcode failed")
                else:
                    self.log_info("barcode validation failed")
                    # TODO: multi slot will result in multiple pop-ups
                    pub.sendMessage("system", message={
                        "message": "Barcode validation failed: %s" % (barcode_string)
                    })

        elif self.state == SlotState.SLOT_SELECT:
            if barcode_string == "SLOT%02d" % (self.index + 1):
                self.state_transition(SlotState.SCAN_BARCODE)

        elif self.state == SlotState.RESULT:
            # validate barcode
            if self.job.validate_barcode(barcode_string):
                # Showing result, this is a new scan for the next run
                if self.index == 0:
                    if self.device_list["target"].set_barcode(barcode_string):
                        self.state_transition(SlotState.EMPTY)
                        self.barcode = barcode_string
                    else:
                        self.log_info("set barcode failed")
                else:
                    # multi slot scan
                    pass
            else:
                self.log_info("barcode validation failed")
                pub.sendMessage("system", message={
                    "message": "Barcode validation failed: %s" % (barcode_string)
                })

    def test_auto_scan(self):
        """
        Auto test mode: generate a scan event
        """
        if self.config.run_mode == "auto":
            time.sleep(1)
            self.barcode_scan("AUTO_+%f" % time.time())

    def operator_signout(self):
        # self.stop()
        # print("operator_signout")
        self.job = None
        self.state_transition(SlotState.INIT)

        pass

    def print_label(self):
        if self.result_dict == {}:
            # no result
            return
        if "printer" not in self.device_list:
            # printer not defined
            return
        
        if not self.device_list["printer"].print_result(self.result_dict):
            if self.label_print_warning:
                pub.sendMessage("system", message={
                    "message": "Label printing failed"
                })
                self.label_print_warning = False

    def open_devices(self):
        for d in self.device_list:
            if self.device_list[d] is not None:
                if not self.device_list[d].open():
                    pub.sendMessage("system", message={
                        "message": "Slot: Opening device %s:%s failed" % (d, self.device_list[d])
                    })

    @staticmethod
    def all_slots(cls):
        return set(cls.__subclasses__()).union(
            [s for c in cls.__subclasses__() for s in Slot.all_slots(c)] + [Slot])

    @staticmethod
    def create(slot, *args, **kwargs):
        """
        Instantiate an instance of the named slot by looking for a matching name in the
        subclasses of TestCase
        """
        for cls in Slot.all_slots(Slot):
            if cls.__name__.lower() == (slot + "Slot").lower():
                return cls(*args, **kwargs)
        raise Exception("Slot %s not found" % slot)


class SlotSingle(Slot):
    """
    TODO: Slightly different logic applies to single slot setups - slot select state always leads to barcode scan state
    """
    pass
