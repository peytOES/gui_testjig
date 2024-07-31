import enum
import time
import attr

from pubsub import pub

from birch.config import find_config_dir
from birch.core.state_machine import StateMachine, State
from birch import Config
from birch.slot import Slot
from birch.operator import OperatorList
from birch.job.job_manager import JobManager
from birch.job.job_bundle_installer import JobBundleInstaller
from birch.job.job_bundle import JobBundle

from birch.gui.operator_gui import OperatorGUI
from birch.logger import log_setup


class ManagerState(enum.Enum):
    INIT = 0
    SELECT_OPERATOR = 1
    SELECT_JOB = 2
    JOB_ACTIVE = 3
    JOB_COMPLETE = 4


class Manager(StateMachine):
    def __init__(self, config_dir="assets/conf/", slot_count=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_dir = config_dir

        self.config = Config.load(config_dir)

        log_setup(self.config.log_dir)
        self.operator_list = None

        self.job_bundle_class = JobBundle

        self.state = ManagerState.INIT
        self.state_table = {
            ManagerState.INIT: State(
                self.state_init_enter,
                self.state_init_run,
                self.state_init_exit),
            ManagerState.SELECT_OPERATOR: State(
                self.state_select_operator_init,
                self.state_select_operator_run,
                None),
            ManagerState.SELECT_JOB: State(
                self.state_select_job_init,
                self.state_select_job_run,
                None),
            ManagerState.JOB_ACTIVE: State(
                self.state_job_active_enter,
                self.state_job_active_run,
                None),
            ManagerState.JOB_COMPLETE: State(
                self.state_job_complete_entry,
                self.state_job_complete_run,
                None
            ),
        }

        # list of test interfaces/object available
        self.device_list = {}

        # Target slots
        self.slot_count = slot_count
        self.slots = []

        self.msg_topic = "system"
        pub.subscribe(self.pub_listener, self.msg_topic)

    def pub_listener(self, message, arg2=None):
        """
        pusbsub listener - maps received messages to local UI update calls using wx callafter
        """
        fn_map = {
            "operator": self.operator_list.select
        }

        for f in fn_map.keys():
            if f in message:
                try:
                    fn_map[f](message[f])
                except Exception as e:
                    self.event_logger("Message call failed: %s %s", f, str(message))

        print(f"manager:pub_listener {message} {arg2}")
    



    def create_slots(self):
        self.slots = [
            Slot.create(self.config.product, mgr=self, index=i, config=self.config,
                        complete_cb=self.job_complete_callback) for i in range(self.slot_count)
        ]

    def start(self):
        self.create_slots()
        super().start()

    def stop(self):
        super().stop()
        for s in self.slots:
            s.stop()

    def state_init_enter(self):
        self.operator_list = OperatorList.load(self.config_dir, self.select_operator_callback)
        # load list of installed jobs
        self.job_mgr = JobManager.load(
            active_dir=self.config.active_dir,
            select_callback=self.select_job_callback,
            debug=self.config.debug
        )
        pass

    def state_init_run(self):
        self.state_transition(ManagerState.SELECT_OPERATOR)

    def state_init_exit(self):
        pass

    def state_select_operator_init(self):
        pass

    def state_select_operator_run(self):
        self.log_debug("select operator")

    def state_select_job_init(self):
        JobBundleInstaller(bundle_class=self.job_bundle_class, input_dir=self.config.input_dir)
        self.job_mgr = JobManager.load(
            active_dir=self.config.active_dir,
            select_callback=self.select_job_callback,
            debug=self.config.debug
        )

    def state_select_job_run(self):
        self.log_debug("select job")

    def state_job_active_enter(self):
        for s in self.slots:
            s.set_job(self.job_mgr.get_selected())
            s.set_operator(self.operator_list.get_selected_name())
            s.start_thread()

    def state_job_active_run(self):
        self.log_debug("job active")

    def state_job_complete_entry(self):
        for s in self.slots:
            s.stop_thread()

    def state_job_complete_run(self):
        pass

    def select_operator_callback(self, *args, **kwargs):
        if self.state == ManagerState.SELECT_OPERATOR:
            self.state_transition(ManagerState.SELECT_JOB)

    def select_job_callback(self, *args, **kwargs):
        if self.state == ManagerState.SELECT_JOB:
            self.state_transition(ManagerState.JOB_ACTIVE)

    def job_complete_callback(self, *args, **kwargs):
        self.state_transition(ManagerState.JOB_COMPLETE)

    def barcode_scan_callback(self, *args, **kwargs):
        """
        Barcode scan call from UI
        """
        # TODO: move to barcode/serial number object to perform validation
        for s in self.slots:
            s.barcode_scan_cb(*args, **kwargs)

        # TODO return false for invalid barcode
        return True

    def operator_signout(self, *args, **kwargs):
        # TODO - stop job, close things
        for s in self.slots:
            s.operator_signout()
        self.state_transition(ManagerState.INIT)

    def status_msg_cb(self, index, msg, *args, **kwargs):
        pass

    def test_result_cb(self, index, result, *args, **kwargs):
        pass

    def set_slot_neutral(self, index):
        pass


class ManagerUI(Manager):
    """
    Manager with UI
    """

    def __init__(self, title='Test fixture', *args, **kwargs):
        super().__init__(*args, **kwargs)
        mgr_cb = {
            "operator_signout": self.operator_signout,
        }
        self.gui = OperatorGUI.factory(product_string=title, config=self.config, slot_count=self.slot_count)

    def start(self):
        super().start()

    def run(self):
        super().run()

    def start_gui(self):
        self.gui.run()

    def state_select_operator_init(self):
        self.gui.operator_list = self.operator_list
        super().state_select_operator_init()

    def state_select_job_init(self):
        super().state_select_job_init()
        self.gui.testsuite_list = self.job_mgr

    def state_job_active_enter(self):
        super().state_job_active_enter()
        self.gui.job_active()
