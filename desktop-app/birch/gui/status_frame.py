"""
Status frame for Ohm (Destiny)

Main frame for test execution
"""
import os
import wx
import time
import json
import zipfile

from pubsub import pub

from birch.gui.slot_summary import SlotSummaryPanel
from birch.gui.fixture_info_frame import FixtureInfoFrame
from birch.gui.log_viewer import LogViewerFrame
from birch.gui.job_info_frame import JobInfoFrame
from birch.gui.about_frame import AboutFrame


def add_panel_static_text(panel, text):
    """
    Create a StaticTextCtrl on panel, with visibility set to hidden
    """
    pass


class StatusFrame(wx.Frame):
    def __init__(self, gui_handle=None, product=None, slot_count=0, config=None, *args, **kwargs):

        self.config = config
        self.job_data = None
        self.provision_checkbox_state = False
        self.slot_count = slot_count
        wx.Frame.__init__(self, *args, **kwargs)
        self.gui_handle = gui_handle
        self.warning_enable = False
        
        self.create_menubar()

        # the subclass will fill this with a list of slots
        self.slotpanel = [None] * self.slot_count

        # main layout
        self.panel = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_DOUBLE | wx.WANTS_CHARS)
        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.heading()

        # this is to catch the module_sn scanner inputs
        self.module_sn_buffer = ""
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_event)

        # timer to flush invalid reads
        self.char_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_char_timer_elapsed, self.char_timer)

        self.setup_headerbox()

        self.setup_slots()

        self.pass_threshold = 0
        self.msg_topic = "status"
        pub.subscribe(self.pub_listener, self.msg_topic)

        self.panel.SetSizer(self.vbox)
        self.Layout()
        self.Centre()

    def heading(self):
        font = wx.Font(14, wx.SWISS, wx.NORMAL, wx.NORMAL)
        font2 = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL)

        self.next_eui = wx.StaticText(self.panel, label="Next EUI: ")
        self.next_eui.SetFont(font)
        self.next_eui_value = wx.StaticText(self.panel, label="")
        self.next_eui_value.SetFont(font)

        self.units_passed = wx.StaticText(self.panel, label="Units passed: ")
        self.units_passed.SetFont(font)
        self.units_passed_value = wx.StaticText(self.panel, label="0")
        self.units_passed_value.SetFont(font)

        self.units_tested = wx.StaticText(self.panel, label="Units tested: ")
        self.units_tested.SetFont(font)
        self.units_tested_value = wx.StaticText(self.panel, label="")
        self.units_tested_value.SetFont(font)
        self.eui_remaining = wx.StaticText(self.panel, label="Tokens remaining: ")
        self.eui_remaining.SetFont(font)
        self.eui_remaining_value = wx.StaticText(self.panel, label="")
        self.eui_remaining_value.SetFont(font)

        self.job_id = wx.StaticText(self.panel, label="Job: ")
        self.job_id.SetFont(font)
        self.job_id_value = wx.StaticText(self.panel, label="")
        self.job_id_value.SetFont(font)

        self.testsuite = wx.StaticText(self.panel, label="Test suite: ")
        self.testsuite.SetFont(font)
        self.testsuite_value = wx.StaticText(self.panel, label="")
        self.testsuite_value.SetFont(font)

    def pub_listener(self, message, arg2=None):
        """
        pusbsub listener - maps received messages to local UI update calls using wx callafter
        """
        fn_map = {
            "job": self.set_job_id,
            "testsuite": self.set_testsuite,
            "job_data": self.set_job_data,
            "units_passed": self.set_units_passed,
            "units_tested": self.set_units_tested,
            "pass_threshold": self.set_pass_threshold,
            "tokens_remaining": self.set_eui_remaining,
            "next_eui": self.set_next_eui,
            "firmware": self.set_firmware
            # "barcode": self.set_barcode,
        }

        # print("message", message)
        for f in fn_map.keys():
            if f in message:
                wx.CallAfter(fn_map[f], message[f])
        # print(f"status_frame:pub_listener {message} {arg2}")

    def create_menubar(self):
        """
        Create menu items and set icon
        """
        self.icon = wx.Icon(str(self.config.image_dir / "icon.png"))
        self.SetIcon(self.icon)

        # Menu Bar
        self.menubar = wx.MenuBar()
        self.menu = wx.Menu()

        self.menubar.Append(self.menu, ("Menu"))
        # logoff_item = self.menu.Append(-1, item="Operator log off", helpString="", kind=wx.ITEM_NORMAL)
        # self.Bind(wx.EVT_MENU, self.on_signout, logoff_item)

        # self.menu.AppendSeparator()
        info_item = self.menu.Append(-1, item="Result log", helpString="View result log", kind=wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_result_log, info_item)

        info_item = self.menu.Append(-1, item="Job information", helpString="Display job information",
                                     kind=wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_job_info, info_item)

        info_item = self.menu.Append(-1, item="Fixture information", helpString="Display fixture information",
                                     kind=wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_fixture_info, info_item)

        # info_item = self.menu.Append(-1, item="Hardware configuration", helpString="Configure hardware", kind=wx.ITEM_NORMAL)
        # self.Bind(wx.EVT_MENU, self.on_hardware_config, info_item)

        # info_item = self.menu.Append(-1, item="Export logs", helpString="Export log data", kind=wx.ITEM_NORMAL)
        # self.Bind(wx.EVT_MENU, self.on_log_export, info_item)

        info_item = self.menu.Append(-1, item="About", helpString="", kind=wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_about_info, info_item)

        self.menu.AppendSeparator()
        tmp_item = self.menu.Append(wx.ID_CLOSE, item="Exit", helpString="Close application", kind=wx.ITEM_NORMAL)
        self.Bind(wx.EVT_MENU, self.on_close, tmp_item)
        self.SetMenuBar(self.menubar)

    def on_button(self, event):
        return

    def on_close(self, i=0):
        for i in range(len(self.slotpanel)):
            self.reset_display(i)
        self.Close()

    def on_signout(self, i):
        pub.sendMessage("system", message={
            "operator_signout": True
        })

    def on_config(self, i):
        d = wx.Dialog(self, id=wx.ID_ANY, title="Configuration")
        d.ShowModal()

    def on_reset_display(self, event):
        for i in range(len(self.slotpanel)):
            self.reset_display(i)

    def on_job_info(self, i):
        f = JobInfoFrame(parent=self, config=self.job_data, title="Job information")
        f.ShowModal()

    def on_fixture_info(self, i):
        f = FixtureInfoFrame(parent=self, config=self.config.to_dict(), title="Fixture information")
        f.ShowModal()

    def on_log_export(self, i):
        dlg = wx.DirDialog(None, "Choose export location", "", wx.DD_DEFAULT_STYLE)

        if dlg.ShowModal() == wx.ID_CANCEL:
            return

            # save the current contents in the file
        pathname = dlg.GetPath()
        filename = "%s_%s.zip" % (self.config.product, time.strftime("%Y%m%d_%H%M%S", time.localtime()))
        fullname = pathname + os.sep + filename

        if self.gui_handle.db_export(fullname):
            wx.MessageBox("Logs exported to \n%s" % fullname)
        else:
            wx.MessageBox("Log exported failed!")

    def on_about_info(self, i):
        f = AboutFrame(parent=self, config=self.config, title="About")
        f.ShowModal()

    def on_hardware_config(self, i):
        f = HardwareConfigurationFrame(self, title="Hardware configuration")
        f.ShowModal()

    def on_result_log(self, i):
        f = LogViewerFrame(parent=self, config=self.config)
        f.Show()

    def update_slot_status(self, index, status):
        """
        Update the slot status from hardware
        """
        if index < len(self.slotpanel):
            self.slotpanel[index].update_slot_status(status)

    def set_test_tree(self, index, name, tree):
        """
        Set the tree view of the test suite.
        """
        if index < len(self.slotpanel):
            self.slotpanel[index].set_test_tree(name, tree)

    def set_eui(self, index, eui):
        """
        Set the EUI displayed next to slot.
        """
        if index < len(self.slotpanel):
            self.slotpanel[index].set_eui(eui)

    def set_eui_remaining(self, n):
        """
        Set the number of remaining tokens for this job
        """
        self.eui_remaining_value.SetLabel("%d" % n)

    def set_job_id(self, job_id):
        """
        Set the job ID field
        """
        self.job_id_value.SetLabel("%s" % job_id)
        self.panel.Layout()

    def set_testsuite(self, name):
        """
        Set the testsuite name
        """
        self.testsuite_value.SetLabel("%s" % name)
        self.panel.Layout()

    def set_job_data(self, job_data):
        """
        Store the job data for display if requested
        """
        self.job_data = job_data

    def set_next_eui(self, eui):
        """
        Set the display of the next EUI
        """
        if eui == "" or eui is None:
            self.next_eui_value.SetLabel("")
        else:
            self.next_eui_value.SetLabel("%s" % eui)
        self.panel.Layout()

    def set_pass_threshold(self, threshold):
        self.pass_threshold = threshold

    def set_units_passed(self, passed):
        if self.pass_threshold == 0:
            self.units_passed_value.SetLabel("%d" % passed)
        else:
            self.units_passed_value.SetLabel("%d/%d" % (passed, self.pass_threshold))
        self.panel.Layout()

    def set_test_result(self, index, result):
        if index < len(self.slotpanel):
            self.slotpanel[index].set_test_result(result)

    def set_status_message(self, index, msg):
        if index < len(self.slotpanel):
            self.slotpanel[index].set_status_message(msg)

    def step_progress(self, index, test_index, step_index, value):
        if index < len(self.slotpanel):
            self.slotpanel[index].step_progress(test_index, step_index, value)

    def test_result(self, index, test_index, value):
        if index < len(self.slotpanel):
            self.slotpanel[index].test_result(test_index, value)

    def reset_display(self, index):
        if index < len(self.slotpanel):
            self.slotpanel[index].reset_display()
            # self.slotpanel[index].set_eui("")

    def test_suite_start(self, index):
        if index < len(self.slotpanel):
            self.slotpanel[index].test_suite_start()

    def test_suite_complete(self, index):
        if index < len(self.slotpanel):
            self.slotpanel[index].test_suite_complete()

    def ShowFullScreen(self, *args):
        wx.Frame.ShowFullScreen(self, *args)
        for p in self.slotpanel:
            p.reset_display()
            p.update_layout()

    def set_error_codes(self, index, codes):
        if index < len(self.slotpanel):
            self.slotpanel[index].set_error_codes(codes)

    def set_previous_result(self, index, result):
        if index < len(self.slotpanel):
            self.slotpanel[index].set_previous_result(result)

    def set_units_tested(self, n):
        self.units_tested_value.SetLabel("%d" % n)

    def set_slot_neutral(self, index):
        if index < len(self.slotpanel):
            self.slotpanel[index].set_slot_neutral()

    def setup_headerbox(self):
        """
        Creates and configures self.headerbox, adds it to self.vbox

        The header box contains job and system status
        (e.g. tokens remaining, job title)

        Default display as for Ohm - horizontal layout of Job, units passed, units tested, eui_remaining.
        """
        self.headerbox = wx.BoxSizer(wx.HORIZONTAL)
        self.vbox.Add(self.headerbox, 1, wx.EXPAND | wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 5)

    def setup_slots(self):
        """
        Init slot for info display
        """
        self.slotgrid = wx.GridSizer(rows=1, cols=1, hgap=2, vgap=2)
        self.vbox.Add(self.slotgrid, 11, wx.ALL | wx.EXPAND, 5)

    def set_module_sn(self, s):
        self.module_sn_value.SetLabel(s)
        self.panel.Layout()
        pass

    def set_slot_module_sn(self, i, s):
        if i in range(self.slot_count):
            self.slotpanel[i].set_module_sn(s)
        pass

    def set_firmware(self, fw):
        """
        Deprecated
        """
        pass

    def enable_print_button(self, state):
        pass

    def inject_barcode(self, code):
        """
        Testing/automation: inject a scanned string.
        """
        if code is None:
            return False

        for c in code:
            if not self.process_char(c):
                return False
        return True

    def process_char(self, key_code):
        """
        Append input char to scan buffer.  

        If a new line is detected, emit buffer to manager.

        To deal with scans that do not include a new line, we also start a count down timer.
        If no data has been received for 400ms, and len(input buffer) > 4, the manager will 
        also be notified.

        """
        if key_code != '\r' and key_code != '\n':
            # reset char timer, append to buffer
            self.char_timer.Start(250)
            self.module_sn_buffer += key_code
        else:
            # if nothing in the buffer
            if len(self.module_sn_buffer.strip()) == 0:
                # note we are returning True on empty string.
                return True
            # stop char timer to prevent spurious firing
            self.char_timer.Stop()

            pub.sendMessage("system", message={
                "barcode_scan": self.module_sn_buffer.strip()
            })

            # clear buffer
            self.module_sn_buffer = ""
            # if result != True:
            #    wx.MessageBox("Invalid serial number!")
            #    return False
        return True

    def on_char_event(self, event):
        """
        Wait for a newline, then emit that buffer to the manager.

        Used to respond to module_sns.
        """
        if not self.IsShown():
            return
        if event.GetKeyCode() > 256:
            return
        key_code = chr(event.GetKeyCode())
        self.process_char(key_code)

    def on_char_timer_elapsed(self, event):
        self.char_timer.Stop()
        if len(self.module_sn_buffer.strip()) > 4:
            self.process_char('\n')
        self.module_sn_buffer = ""


if __name__ == "__main__":
    app = wx.App()
    f = StatusFrame(None, -1, "StatusFrame", size=(800, 600))
    f.Show()

    g = ConfigurationFrame(None, -1, "Test configuration")
    g.Show()
    app.MainLoop()
