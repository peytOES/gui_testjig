import wx
from collections import OrderedDict
from ..testcase import TestStatus

from . import SlotPanel


class SlotDetailPanel(SlotPanel):
    def __init__(self, *args, **kwds):
        kwds["style"] = wx.TAB_TRAVERSAL | wx.BORDER_DOUBLE
        SlotPanel.__init__(self, *args, **kwds)

        vbox = wx.BoxSizer(wx.VERTICAL)
        title_box = wx.BoxSizer(wx.HORIZONTAL)
        # slot name
        self.eui_label = wx.StaticText(self, label="EUI: %s" % self.eui)
        self.eui_label.SetFont(self.emph_font)

        title_box.Add(self.slot_name, 1, wx.ALIGN_LEFT, 5)
        title_box.Add((1, 1), 1)
        title_box.Add(self.eui_label, 1, wx.ALIGN_RIGHT, 5)

        vbox.Add(title_box, 2, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # test tree
        self.tree = wx.TreeCtrl(self, wx.ID_ANY, wx.DefaultPosition,
                                style=wx.TR_HAS_BUTTONS | wx.VSCROLL  # \wx.TR_FULL_ROW_HIGHLIGHT|wx.TR_HIDE_ROOT
                                )

        vbox.Add((1, 1), 1)
        vbox.Add(self.tree, 8, wx.LEFT | wx.RIGHT | wx.EXPAND | wx.ALIGN_TOP, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        # status text
        self.status_text = wx.StaticText(self, label="  ")
        hbox.Add(self.status_text, 4, wx.TOP | wx.BOTTOM | wx.EXPAND | wx.ALIGN_LEFT, 5)
        vbox.Add(hbox, 2, wx.ALIGN_LEFT | wx.ALIGN_TOP, 5)

        # result text
        self.result_text = wx.StaticText(self, label="    ")
        self.result_text.SetFont(self.result_font)
        vbox.Add(self.result_text, 2, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL, 5)

        self.SetSizer(vbox)
        self.tree_items = []
        self.reset_display()
        self.Layout()
        self.Fit()

    def update_layout(self):
        """
        Update layout in response to changing fields
        """
        self.result_text.SetLabel("   ")
        self.status_text.SetLabel("   ")
        self.Show()

    def reset_display(self):
        """
        Reset display to initial state.
        """
        # self.eui_label.SetLabel("   ")
        self.result_text.SetLabel("   ")
        self.status_text.SetLabel("   ")
        self.SetBackgroundColour(self.bgcolor)

        for test in self.tree_items:
            self.tree.SetItemTextColour(test[0], self.textcolor)
            for step in test[1]:
                self.tree.SetItemTextColour(step, self.textcolor)

        # self.GetParent().SendSizeEvent()

    def set_led(self, index, enable):
        pass
        # self.led_box.set_led(index, enable)

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
        # self.status_text.SetLabel(str(status["version"]))
        pass

    def set_status_message(self, msg):
        # self.status = msg
        self.status_text.SetLabel(msg)
        pass

    def update_test_status(self, test):
        pass

    def update_test_step_status(self, test, step):
        pass

    # def set_test_result(self, result):
    #    """
    #    Display test result.

    #    result is one of TestStatus.*

    #    Handled in 
    #    """
    #    self.SetBackgroundColour(TestStatus.color(result))
    #    if result == TestStatus.INCOMPLETE:
    #        self.result_text.SetLabel("   ")
    #    else:
    #        self.result_text.SetLabel(TestStatus.str(result))

    #    self.Layout()
    #        

    def set_eui(self, eui):
        """
        Set EUI display
        """
        self.eui = eui
        self.eui_label.SetLabel("EUI: %s" % self.eui)
        self.Layout()

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
