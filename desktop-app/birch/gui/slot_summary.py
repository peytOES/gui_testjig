import time
import re
import wx
from pubsub import pub

from ..test_status import TestStatus
from .slot_panel import SlotPanel


class SlotSummaryPanel(SlotPanel):
    def __init__(self, config, *args, **kwds):
        self.config = config
        kwds["style"] = wx.TAB_TRAVERSAL | wx.BORDER_DOUBLE
        SlotPanel.__init__(self, *args, **kwds)

        self.error_codes = []

        self.dut_info_sizer = wx.FlexGridSizer(cols=2, hgap=2, vgap=5)
        self.prev_result_sizer = wx.FlexGridSizer(cols=2, hgap=2, vgap=5)
        img_grid_sizer = wx.FlexGridSizer(cols=2, hgap=2, vgap=5)

        self.init_labels()

        title_box = wx.BoxSizer(wx.HORIZONTAL)
        title_box.Add(self.slot_name, 1, wx.ALIGN_LEFT, 5)

        hbox = wx.BoxSizer(wx.HORIZONTAL)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(title_box, 1, wx.EXPAND | wx.ALL, 5)
        vbox.Add(self.dut_info_sizer, 2, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        vbox.Add(self.status_text, 2, wx.LEFT | wx.EXPAND | wx.ALIGN_LEFT, 5)
        vbox.Add(self.result_text, 2, wx.LEFT | wx.ALIGN_CENTER_HORIZONTAL, 0)
        vbox.Add(self.error_code_label, 2, wx.EXPAND | wx.ALL, 5)
        vbox.Add(self.prev_result_sizer, 2, wx.EXPAND | wx.ALL, 0)
        vbox.Add(img_grid_sizer, 2, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        hbox.Add(vbox, wx.EXPAND | wx.ALL)

        self.error_code_tooltip = wx.ToolTip("Tool tip")
        self.error_code_label.SetToolTip(None)

        pub.subscribe(self.pub_listener, self.msg_topic)

        hbox.Add(self.bitmap, 2, wx.EXPAND | wx.ALL, 20)

        self.SetSizer(hbox)
        self.tree_items = []
        self.reset_display()
        self.Layout()
        self.Fit()

    def init_labels(self):
        self.eui_title = wx.StaticText(self, label="EUI:")
        self.eui_title.SetFont(self.heavy_font)
        self.eui_label = wx.StaticText(self, label="")
        self.eui_label.SetFont(self.heavy_font)

        self.module_sn_title = wx.StaticText(self, label="Serial number:")
        self.module_sn_title.SetFont(self.heavy_font)
        self.module_sn_label = wx.StaticText(self, label="")
        self.module_sn_label.SetFont(self.heavy_font)

        bmp = wx.Image(str(self.config.image_dir / "background.png"), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.bitmap = wx.StaticBitmap(self, -1, bmp, pos=(0, 0), size=(bmp.GetWidth(), bmp.GetHeight()))

        self.module_sn_title.Show()
        self.module_sn_label.Show()

        self.prev_eui_title = wx.StaticText(self, label="Previous EUI:")
        self.prev_eui_title.SetFont(self.heavy_font)
        self.prev_eui_label = wx.StaticText(self, label="")
        self.prev_eui_label.SetFont(self.heavy_font)
        self.prev_result_title = wx.StaticText(self, label="Previous result:")
        self.prev_result_title.SetFont(self.heavy_font)
        self.prev_result_label = wx.StaticText(self, label="")
        self.prev_result_label.SetFont(self.heavy_font)

        self.time_title = wx.StaticText(self, label="Elapsed time:")
        # self.time_label.SetFont(self.emph_font)
        self.time_label = wx.StaticText(self, label="00:00")
        # self.time_title.SetFont(self.emph_font)

        self.error_code_label = wx.StaticText(self, label="")
        self.error_code_label.SetFont(self.heavy_font)
        # status text
        self.status_text = wx.StaticText(self, label="  ")
        # result text
        self.result_text = wx.StaticText(self, label="    ")
        self.result_text.SetFont(self.result_font)

        self.dut_info_sizer.Add(self.module_sn_title, 2, wx.EXPAND | wx.ALL, 5)
        self.dut_info_sizer.Add(self.module_sn_label, 2, wx.EXPAND | wx.ALL, 5)
        self.dut_info_sizer.Add(self.eui_title, 2, wx.EXPAND | wx.ALL, 5)
        self.dut_info_sizer.Add(self.eui_label, 2, wx.EXPAND | wx.ALL, 5)
        self.dut_info_sizer.Add(self.time_title, 2, wx.EXPAND | wx.ALL, 5)
        self.dut_info_sizer.Add(self.time_label, 2, wx.EXPAND | wx.ALL, 5)
        self.prev_result_sizer.Add(self.prev_eui_title, 2, wx.EXPAND | wx.ALL, 5)
        self.prev_result_sizer.Add(self.prev_eui_label, 2, wx.EXPAND | wx.ALL, 5)
        self.prev_result_sizer.Add(self.prev_result_title, 2, wx.EXPAND | wx.ALL, 5)
        self.prev_result_sizer.Add(self.prev_result_label, 2, wx.EXPAND | wx.ALL, 5)

    def pub_listener(self, message, arg2=None):
        """
        pusbsub listener - maps received messages to local UI update calls using wx callafter
        """
        fn_map = {
            "status_msg": self.set_status_message,
            "neutral": self.set_slot_neutral,
            "status": self.update_slot_status,
            "test_result": self.set_test_result,
            "previous_result": self.set_previous_result,
            "timer_start": self.test_suite_start,
            "timer_stop": self.test_suite_complete,
            "serial_number": self.set_module_sn,
            "error_codes": self.set_error_codes,
        }

        for f in fn_map.keys():
            if f in message:
                # print(fn_map[f], message[f])
                wx.CallAfter(fn_map[f], message[f])
        # print(f"slot:pub_listener: {message} {arg2}")

    def set_slot_neutral(self, *args, **kwargs):
        super().set_slot_neutral(*args, **kwargs)
        self.time_label.SetLabel("   ")

    def update_timer(self, event):
        """ 
        Attached to the self.run_timer object
        """
        t = time.time() - self.start_time
        self.time_label.SetLabel("%0.3f" % t)

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
        self.result_text.SetLabel("   ")
        self.status_text.SetLabel("   ")
        self.time_label.SetLabel("   ")
        self.error_code_label.SetLabel("   ")
        self.error_code_label.SetToolTip(None)
        self.SetBackgroundColour(self.bgcolor)

    def set_eui(self, eui):
        """
        Set EUI string. Ignore if eui == None
        """
        if self.eui is not None:
            self.prev_eui_label.SetLabel(self.eui)
        if eui == "" or eui is None:
            # if empty EUI - not used.
            self.eui = None
            self.eui_label.SetLabel("")
        elif eui:
            # 
            self.eui = eui
            self.eui_label.SetLabel(self.eui)
            self.Layout()

    def set_previous_result(self, result):
        if result != None:
            self.prev_result_label.SetLabel(TestStatus.str(result))
        else:
            self.prev_result_label.SetLabel("")
            self.Layout()

    def set_module_sn(self, module_sn):
        """
        Set module_sn value
        """
        # print("set_module_sn", module_sn)
        if module_sn == "" or module_sn is None:
            self.module_sn_label.SetLabel("")
        else:
            self.module_sn_label.SetLabel(module_sn)

    def step_progress(self, test_index, step_index, value):
        """
        Update step colour based on value.  
        """
        current_step = self.tree_items[test_index][1][step_index]
        # self.tree.SetItemTextColour(current_step, TestStatus.color(value))

    def test_result(self, test_index, value):
        """
        Update test result colour
        """
        current_test = self.tree_items[test_index][0]
        # self.tree.SetItemTextColour(current_test, TestStatus.color(value))

    def set_error_codes(self, codes):
        """
        Display error codes

        codes is a list of ErrorCode instances
        """
        self.error_codes = codes
        s = ", ".join(["%d" % c.value for c in codes])
        self.error_code_label.SetLabel(s)
        self.error_code_label.Wrap(self.GetSize()[0] - 10)

        s = ""
        if len(self.error_codes) > 0:
            for c in self.error_codes:
                s += "%d : %s\n" % (c.value, c.name)

            self.error_code_tooltip = wx.ToolTip(s)
            self.error_code_label.SetToolTip(self.error_code_tooltip)
        else:
            self.error_code_label.SetToolTip(None)

        self.Layout()
