import sys, os

sys.path.append(os.getcwd())

import time
from pubsub import pub
import wx

from .operator_select_frame import OperatorSelectFrame
from .job_selection_frame import JobSelectFrame
from .status_frame import StatusFrame


class OperatorGUI(object):
    """
    Super class of test operator GUI.

    Takes a handle to the manager callback dictionary.

    Creates an operator and job selection frame.

    Checks for single instance.

    TODO: replace mgr_cb with pubsub
    """

    def __init__(self, mgr_cb={}, slot_count=1, product=None, product_string="Production fixture", config=None, *args,
                 **kwargs):
        self.state = 0
        self.app = wx.App()

        self.mgr_cb = mgr_cb
        self.product = product
        self.slot_count = slot_count
        self.config = config

        # self.name = ".SingleApp-%s-%s" % (product, wx.GetUserId())
        # self.instance = wx.SingleInstanceChecker(self.name)

        # if self.instance.IsAnotherRunning():
        #    wx.MessageBox("Another instance is running", "ERROR")
        #    sys.exit(0)

        self.product_string = product_string

        self.init_frames()

        # operator sign-in
        self._operator_list = None
        self._testsuite_list = None

        self.msg_topic = "system"
        pub.subscribe(self.pub_listener, self.msg_topic)

        self.operator_frame.Hide()
        self.testsuite_frame.Hide()
        self.status_frame.Hide()
        self.status_frame.SetMinClientSize((400, 400))
        self.operator_frame.Raise()

    def init_frames(self):
        """
        Create frames used in UI.

        Override in subclasses
        """
        # primary frame - override as required.
        print("creating status frame")
        self.status_frame = StatusFrame(gui_handle=self, slot_count=self.slot_count, parent=None,
                                        title=self.product_string, config=config)
        # suite selection
        self.testsuite_frame = JobSelectFrame(self.config, self.status_frame, -1, self.product_string, size=(1024, 600))
        self.operator_frame = OperatorSelectFrame(self.config, self.status_frame, -1, self.product_string)

    def pub_listener(self, message, arg2=None):
        """
        pusbsub listener - maps received messages to local UI update calls using wx callafter
        """
        fn_map = {
            "message": wx.MessageBox,
        }

        for f in fn_map.keys():
            if f in message:
                wx.CallAfter(fn_map[f], message[f])
        print(f"status_frame:pub_listener {message} {arg2}")

    def run(self):
        """
        Start gui app.  

        When complete, this takes all the windows with it.
        """
        print("wx,app.main")
        self.app.MainLoop()

    @property
    def operator_list(self):
        return self._perator_list

    @operator_list.setter
    def operator_list(self, operator_list):
        self._operator_list = operator_list
        self.operator_frame.set_operator_list(self._operator_list)
        self.safe_wx_call(self.status_frame.Hide)
        self.safe_wx_call(self.operator_frame.Show)
        self.safe_wx_call(self.status_frame.Hide)

    @property
    def testsuite_list(self):
        return self._testsuite_list

    @testsuite_list.setter
    def testsuite_list(self, testsuite_list):
        self._testsuite_list = testsuite_list
        self.testsuite_frame.set_suite_list(testsuite_list)
        self.safe_wx_call(self.operator_frame.Hide)
        self.safe_wx_call(self.status_frame.Hide)
        self.safe_wx_call(self.testsuite_frame.Show)

    def job_active(self):
        self.safe_wx_call(self.operator_frame.Hide)
        self.safe_wx_call(self.testsuite_frame.Hide)
        self.safe_wx_call(self.status_frame.Show)
        self.safe_wx_call(self.status_frame.Maximize)

    #######################################################3
    # UI events
    def signout(self):
        if "operator_signout" in self.mgr_cb:
            self.mgr_cb["operator_signout"]()

    def suite_select_cb(self, i):
        print("suite select cb")
        result = self.mgr_cb["testsuite_select"](i)
        if result:
            pass
        else:
            return False

        self.operator_frame.Hide()
        self.testsuite_frame.Hide()
        self.status_frame.Show()
        for i in range(self.slot_count):
            self.reset_display(i)
        self.state = 2

        self.status_frame.Maximize()
        return True

    def load_suite_cb(self, i):
        # notify manager
        self.mgr_cb["testsuite_load"](i)

    # def barcode_scan_cb(self, s):
    #    """
    #    Propogate scanned barcode from GUI to BarcodeScanner object
    #    """
    #    print("barcode_scan_cb")
    #    if "barcode_scan_cb" in self.mgr_cb:
    #        return self.mgr_cb["barcode_scan_cb"](s)
    #    # if nothing defined return true
    #    return True

    def db_export(self, filename):
        """
        Trigger db export to filename
        """
        if "db_export" in self.mgr_cb:
            return self.mgr_cb["db_export"](filename)
        return False

    def print_label_button_cb(self):
        if "print_label_button_cb" in self.mgr_cb:
            return self.mgr_cb["print_label_button_cb"]()
        return False

    ######################################################33
    # Calls from test engine
    def safe_wx_call(self, *args):
        try:
            # print("safe_wx_call", args)
            wx.CallAfter(*args)
        except AssertionError:
            print("GUI AssertionError caught")

    def message_box(self, text):
        """
        Display test in a message box
        """
        self.safe_wx_call(wx.MessageBox, text)

    # slot related values
    def update_slot_status(self, slot, status):
        """
        Receive data from test manager, publish in GUI
        """
        self.safe_wx_call(self.status_frame.update_slot_status, slot, status)

    def set_eui(self, slot, eui):
        """
        Set the displayed EUI for slot in position index 
        """
        if eui is not None:
            self.safe_wx_call(self.status_frame.set_eui, slot, eui)
        else:
            self.safe_wx_call(self.status_frame.set_eui, slot, "")

    def show_error_box(self, msg):
        """
        Show a modal error box
        """
        print("Error box", msg)
        # self.safe_wx_call(self.status_frame.set_status_message, slot, msg)

    def test_result(self, slot, test_index, value):
        self.safe_wx_call(self.status_frame.test_result, slot, test_index, value)

    def reset_display(self, slot):
        self.safe_wx_call(self.status_frame.reset_display, slot)

    def test_suite_start(self, slot):
        self.safe_wx_call(self.status_frame.test_suite_start, slot)

    def test_suite_complete(self, slot):
        self.safe_wx_call(self.status_frame.test_suite_complete, slot)

    def set_error_codes(self, slot, codes):
        self.safe_wx_call(self.status_frame.set_error_codes, slot, codes)

    def set_previous_result(self, slot, result):
        self.safe_wx_call(self.status_frame.set_previous_result, slot, result)

    def set_units_passed(self, passed, threshold):
        if passed is None:
            passed = 0
        if threshold is None:
            threshold = 0
        self.safe_wx_call(self.status_frame.set_units_passed, passed, threshold)

    def set_barcode(self, s):
        self.safe_wx_call(self.status_frame.set_module_sn, s)

    def set_slot_barcode(self, i, s):
        self.safe_wx_call(self.status_frame.set_slot_module_sn, i, s)

    def set_firmware(self, i, s):
        self.safe_wx_call(self.status_frame.set_firmware, i, s)

    def enable_print_button(self, state):
        self.safe_wx_call(self.status_frame.enable_print_button, state)

    @staticmethod
    def factory(*args, **kwargs):
        """
        Find a subclass with the name 
         (str(product) + OperatorGUI).lower()
        
        """

        product = kwargs["config"].product
        for cls in OperatorGUI.__subclasses__():
            print(cls.__name__, product)
            if cls.__name__.lower() == (product + "OperatorGUI").lower():
                return cls(*args, **kwargs)
        raise Exception("OperatorUI %s not found" % product)
