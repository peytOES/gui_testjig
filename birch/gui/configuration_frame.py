import wx

import time
import os
from . import ConfigFilePanel


class ConfigurationFrame(wx.Frame):
    """
    Configuration frame
    """

    def __init__(self, *args, **kwds):
        wx.Frame.__init__(self, *args, **kwds)

        self.panel = wx.Panel(self, wx.ID_ANY)
        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.test_config = ConfigFilePanel(self.panel, wx.ID_ANY)

        self.vbox.Add(self.test_config, 0, wx.ALL | wx.EXPAND, 0)

        self.panel.SetSizer(self.vbox)
