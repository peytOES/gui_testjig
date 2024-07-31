import wx
from collections import OrderedDict
from ..test_status import TestStatus

import time

TIMER_UPDATE_INTERVAL_MS = 143


class SlotPanel(wx.Panel):
    def __init__(self, index, show_serial=False, *args, **kwds):
        kwds["style"] = wx.TAB_TRAVERSAL | wx.BORDER_DOUBLE
        wx.Panel.__init__(self, *args, **kwds)

        self.heavy_font = wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL)
        self.heavy2_font = wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.emph_font = wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD)
        self.result_font = wx.Font(24, wx.SWISS, wx.NORMAL, wx.BOLD)

        self.index = index
        self.eui = " "
        self.bgcolor = TestStatus.color(
            TestStatus.INACTIVE)  # tuple([a-b for a,b in zip(self.GetBackgroundColour(), (25,25,25))])
        self.SetBackgroundColour(self.bgcolor)
        # slot name
        self.slot_name = wx.StaticText(self, label="%d" % (index + 1))
        self.slot_name.SetFont(self.emph_font)
        self.textcolor = self.slot_name.GetForegroundColour()

        self.msg_topic = "slot%02d" % index

        self.run_timer = wx.Timer(self)
        self.show_serial = show_serial
        self.Bind(wx.EVT_TIMER, self.update_timer, self.run_timer)

        self.Bind(wx.EVT_CHAR, self.on_char)
        self.start_time = None


    def on_char(self, event):
        """
        Propogate event to parent
        """
        wx.PostEvent(self.GetParent(), event)

    def update_layout(self):
        """
        Update layout in response to changing fields
        """
        self.result_text.SetLabel("   ")
        self.status_text.SetLabel("   ")
        self.Show()

    def on_close(self):
        self.reset_display()
        self.SetBackgroundColour(self.bgcolor)

    def reset_display(self):
        """
        Reset display to initial state.
        """
        # self.eui_label.SetLabel("   ")
        self.result_text.SetLabel("   ")
        self.status_text.SetLabel("   ")
        # self.SetBackgroundColour(self.bgcolor)

        for test in self.tree_items:
            self.tree.SetItemTextColour(test[0], self.textcolor)
            for step in test[1]:
                self.tree.SetItemTextColour(step, self.textcolor)

        # self.GetParent().SendSizeEvent()

    def set_test_tree(self, name, tree):
        """
        Set a test tree to display

        tree is structured as:
        [ 
            ("Test 1", ["step1", "step2", "step3"]),
            ("Test 2", ["step1", "step2", "step3"]),
            ("Test 3", ["step1", "step2", "step3"]),
        ]
        """
        self.tree.DeleteAllItems()
        self.tree_items = []
        root = self.tree.AddRoot(name)
        for test_name, steps in tree:
            test_item = self.tree.AppendItem(root, test_name)
            a = []
            for s in steps:
                a.append(self.tree.AppendItem(test_item, s))
            self.tree_items.append([test_item, a])

        self.tree.Expand(root)

    def update_slot_status(self, status):
        self.status = status
        pass

    def set_status_message(self, msg):
        self.status_text.SetLabel(msg)
        pass

    def update_test_status(self, test):
        pass

    def update_test_step_status(self, test, step):
        pass

    def update_timer(self, event):
        """ 
        Attached to the self.run_timer object
        """
        pass

    def set_test_result(self, result):
        """
        Display test result.

        result is one of TestStatus.*
        """
        self.SetBackgroundColour(TestStatus.color(result))
        if result == TestStatus.UNTESTED:
            # keep previous label
            pass
        elif result == TestStatus.INCOMPLETE or result == TestStatus.INACTIVE:
            self.result_text.SetLabel("   ")
        else:
            self.result_text.SetLabel(TestStatus.str(result))

        self.Layout()
        self.Refresh()

    def set_slot_neutral(self, *args, **kwargs):
        self.SetBackgroundColour(self.bgcolor)

    def set_eui(self, eui):
        """
        Set EUI display
        """
        self.eui = eui

    def step_progress(self, test_index, step_index, value):
        """
        Update step colour based on value.  
        """
        current_step = self.tree_items[test_index][1][step_index]
        self.tree.SetItemTextColour(current_step, TestStatus.color(value))

    def test_result(self, test_index, value):
        """
        Update test result colour
        """
        current_test = self.tree_items[test_index][0]
        self.tree.SetItemTextColour(current_test, TestStatus.color(value))

    def test_suite_start(self, *args, **kwargs):
        self.start_time = time.time()
        # update time elapsed every 85 ms
        self.run_timer.Start(TIMER_UPDATE_INTERVAL_MS)

    def test_suite_complete(self, *args, **kwargs):
        if self.run_timer.IsRunning():
            self.run_timer.Stop()

    def set_error_codes(self, codes):
        pass
