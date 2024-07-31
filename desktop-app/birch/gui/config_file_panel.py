import wx


class ConfigFilePanel(wx.Panel):
    """
    Configuration file selector
    """

    def __init__(self, *args, **kwds):
        kwds["style"] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)
        self.SetBackgroundColour((255, 255, 255))

        self.config_file = "config_name"
        self.config_name = "config_file"
        # led images
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        st1 = wx.StaticText(self, label=self.config_name)

        self.config_file_name = wx.StaticText(self, label=self.config_file)

        button = wx.Button(self, id=wx.ID_ANY, label="Change file")
        button.Bind(wx.EVT_BUTTON, self.on_button)

        self.hbox.Add(st1, 0, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_HORIZONTAL, 10)
        self.hbox.Add(self.config_file_name, 1, wx.ALL | wx.ALIGN_LEFT, 10)
        self.hbox.Add((1, 1), 1)
        self.hbox.Add(button, 0, wx.ALL | wx.EXPAND | wx.ALIGN_RIGHT | wx.ALIGN_CENTER, 0)
        self.SetSizer(self.hbox)

    def on_button(self, event):
        self.config_file = wx.FileSelector("Choose a file", "/home/jvdh")
        self.config_file_name.SetLabel(self.config_file)
