import wx
import time
import json


class AboutFrame(wx.Dialog):
    def __init__(self, config, *args, **kwds):
        self.config = config
        wx.Dialog.__init__(self, *args, **kwds)

        self.bold_font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD)
        sizer = wx.BoxSizer(wx.VERTICAL)
        grid_sizer = wx.FlexGridSizer(cols=2, hgap=2, vgap=5)

        self.key_value(grid_sizer, config.description, bold=True)
        self.key_value(grid_sizer, "Fixture ID", config.fixture_id)
        self.key_value(grid_sizer, "Fixture number", config.fixture_number)
        self.key_value(grid_sizer, "Sofware version", config.version)

        for slot in sorted(config.slot_map.keys()):
            slot_info = config.slot_map[slot]
            if slot_info["enabled"] == False:
                continue
            fw = "not connected"
        #           try:
        #               fw = Config["firmware_version"][slot]
        #           except KeyError:
        #               # fw version not found
        #               pass

        # self.key_value(grid_sizer, "Slot %s"%slot, bold=True)

        # self.key_value(grid_sizer, "Serial number", "sn")
        # self.key_value(grid_sizer, "Firmware", "fw_version")

        btnsizer = wx.BoxSizer()
        btn = wx.Button(self, wx.ID_OK)
        btnsizer.Add(btn, 0, wx.ALL, 5)

        sizer.Add(grid_sizer, 2, wx.EXPAND | wx.ALL, 10)
        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.SetSizerAndFit(sizer)

    def key_value(self, sizer, key, value="", bold=False):
        k = wx.StaticText(self, label=str(key) + ":")
        if bold:
            k.SetFont(self.bold_font)

        v = wx.StaticText(self, label=str(value))
        sizer.Add(k, 2, wx.EXPAND | wx.ALL, 5)
        sizer.Add(v, 2, wx.EXPAND | wx.ALL, 5)
