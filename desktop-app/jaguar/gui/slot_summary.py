import wx
from birch.gui import SlotSummaryPanel


class JaguarSlotSummaryPanel(SlotSummaryPanel):
    def init_labels(self):
        self.module_sn_title = wx.StaticText(self, label="Serial number:")
        self.module_sn_title.SetFont(self.heavy_font)
        self.module_sn_label = wx.StaticText(self, label="")
        self.module_sn_label.SetFont(self.heavy_font)

        bmp = wx.Image(str(self.config.image_dir / "background.png"), wx.BITMAP_TYPE_ANY).ConvertToBitmap()
        self.bitmap = wx.StaticBitmap(self, -1, bmp, pos=(0, 0), size=(bmp.GetWidth(), bmp.GetHeight()))

        self.module_sn_title.Show()
        self.module_sn_label.Show()

        self.prev_result_title = wx.StaticText(self, label="Previous result:")
        self.prev_result_title.SetFont(self.heavy_font)
        self.prev_result_label = wx.StaticText(self, label="")
        self.prev_result_label.SetFont(self.heavy_font)

        self.time_title = wx.StaticText(self, label="Elapsed time:")
        self.time_label = wx.StaticText(self, label="00:00")

        self.error_code_label = wx.StaticText(self, label="")
        self.error_code_label.SetFont(self.heavy_font)
        # status text
        self.status_text = wx.StaticText(self, label="  ")
        # result text
        self.result_text = wx.StaticText(self, label="    ")
        self.result_text.SetFont(self.result_font)

        self.dut_info_sizer.Add(self.module_sn_title, 2, wx.EXPAND | wx.ALL, 5)
        self.dut_info_sizer.Add(self.module_sn_label, 2, wx.EXPAND | wx.ALL, 5)
        self.dut_info_sizer.Add(self.time_title, 2, wx.EXPAND | wx.ALL, 5)
        self.dut_info_sizer.Add(self.time_label, 2, wx.EXPAND | wx.ALL, 5)
        self.prev_result_sizer.Add(self.prev_result_title, 2, wx.EXPAND | wx.ALL, 5)
        self.prev_result_sizer.Add(self.prev_result_label, 2, wx.EXPAND | wx.ALL, 5)

    def set_eui(self, eui):
        pass
