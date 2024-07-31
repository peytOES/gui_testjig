import wx
import json
import os
# from ..manager import Config

from pygments import highlight, lexers, formatters


class LogViewerFrame(wx.Frame):
    def __init__(self, config, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        self.line_index = -1
        self.config = config

        self.text = wx.TextCtrl(self, -1, "", size=(800, 600), style=wx.TE_MULTILINE | wx.TE_READONLY)
        #
        sizer = wx.BoxSizer(wx.VERTICAL)
        #
        btnsizer = wx.BoxSizer()

        btn = wx.Button(self, wx.ID_BACKWARD)
        btn.Bind(wx.EVT_BUTTON, self.on_backward)

        btnsizer.Add(btn, 0, wx.ALL, 5)
        btnsizer.Add((5, -1), 0, wx.ALL, 5)

        btn = wx.Button(self, wx.ID_OK)
        btnsizer.Add(btn, 0, wx.ALL, 5)
        btnsizer.Add((5, -1), 0, wx.ALL, 5)
        btn.Bind(wx.EVT_BUTTON, self.on_close)

        btn = wx.Button(self, wx.ID_FORWARD)
        btnsizer.Add(btn, 0, wx.ALL, 5)
        btn.Bind(wx.EVT_BUTTON, self.on_forward)

        sizer.Add(self.text, 10, wx.EXPAND | wx.ALL, 5)
        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.SetSizerAndFit(sizer)
        self.view()

    def on_close(self, evt):
        self.Close()

    def view(self):
        fname = self.config.log_dir / "result.log"
        try:
            f = open(fname, 'r')
            log_data = f.readlines()
        except FileNotFoundError:
            log_data = ""

        m = ""
        i = 0
        if self.line_index < 0:
            self.line_index = len(log_data) - 1
        if self.line_index > len(log_data):
            self.line_index = len(log_data) - 1
        if self.line_index < len(log_data) and self.line_index >= 0:
            line = log_data[self.line_index]
            data = json.loads(line)
            formatted_json = json.dumps(data, indent=4, sort_keys=True)
            self.text.SetValue(formatted_json)
            self.SetTitle("%s : %d/%d" % (fname, self.line_index, len(log_data) - 1))
        return

    def on_forward(self, event):
        self.line_index += 1
        self.view()

    def on_backward(self, event):
        self.line_index -= 1
        self.view()
