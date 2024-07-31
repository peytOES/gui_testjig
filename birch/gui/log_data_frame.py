import wx
import json
from ..manager import Config


class LogDataFrame(wx.Dialog):
    def __init__(self, *args, **kwds):
        wx.Dialog.__init__(self, *args, **kwds)

        message = "text"  # json.dumps(Config, indent=4, sort_keys=True)
        text = wx.TextCtrl(self, -1, message, size=(640, 640), style=wx.TE_MULTILINE | wx.TE_READONLY)
        #
        sizer = wx.BoxSizer(wx.VERTICAL)
        #
        btnsizer = wx.BoxSizer()

        # destination file
        file_select_ctl

        btn = wx.Button(self, wx.ID_OK)
        btnsizer.Add(btn, 0, wx.ALL, 5)

        sizer.Add(text, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.SetSizerAndFit(sizer)
