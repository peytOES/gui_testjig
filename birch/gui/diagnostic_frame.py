import wx


class DiagnosticFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        # kwargs["style"] = wx.TAB_TRAVERSAL
        wx.Frame.__init__(self, *args, **kwargs)

        self._status = dict()

        self.init_ui()
        self.Centre()
        self.Show()

    def init_ui(self):
        panel = wx.Panel(self, wx.ID_ANY)

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        st1 = wx.StaticText(panel, label="/dev/ttyACM0")
        hbox1.Add(st1, flag=wx.RIGHT, border=8)
        st2 = wx.StaticText(panel, label="serial_number")
        hbox1.Add(st2, flag=wx.LEFT, border=8, proportion=1)
        vbox.Add(hbox1, 0, wx.ALL | wx.CENTER, 5)

        vbox.Add((-1, 20))

        self.lv1 = wx.ListView(panel, -1, size=(-1, 100),
                               style=wx.LC_REPORT
                                     | wx.BORDER_SUNKEN)
        self.lv1.InsertColumn(0, "Property", width=300)
        self.lv1.InsertColumn(1, "Value")
        vbox.Add(self.lv1, 0, wx.ALL | wx.EXPAND, 10)

        vbox.Add((-1, 20))
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        st3 = wx.StaticText(panel, label="LED: ")
        hbox2.Add(st3, flag=wx.RIGHT, border=8)

        btn1 = wx.ToggleButton(panel, label="Busy")
        hbox2.Add(btn1, 0, wx.ALL | wx.CENTER, 5)
        btn1.Bind(wx.EVT_BUTTON, self.toggle_led)
        btn2 = wx.ToggleButton(panel, label="Pass")
        hbox2.Add(btn2, 0, wx.ALL | wx.CENTER, 5)
        btn2.Bind(wx.EVT_BUTTON, self.toggle_led)
        btn3 = wx.ToggleButton(panel, label="Fail")
        hbox2.Add(btn3, 0, wx.ALL | wx.CENTER, 5)
        btn3.Bind(wx.EVT_BUTTON, self.toggle_led)
        vbox.Add(hbox2, 0, wx.ALL | wx.CENTER, 5)

        vbox.Add((-1, 20))
        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        st4 = wx.StaticText(panel, label="Solenoid: ")
        hbox3.Add(st4, flag=wx.RIGHT, border=8)
        btn4 = wx.ToggleButton(panel, label="0")
        hbox3.Add(btn4, 0, wx.ALL | wx.CENTER, 5)
        btn4.Bind(wx.EVT_BUTTON, self.toggle_solenoid)
        btn5 = wx.ToggleButton(panel, label="1")
        hbox3.Add(btn5, 0, wx.ALL | wx.CENTER, 5)
        btn5.Bind(wx.EVT_BUTTON, self.toggle_solenoid)
        vbox.Add(hbox3, 0, wx.ALL | wx.CENTER, 5)

        panel.SetSizer(vbox)
        self._status["device_name"] = st1
        self._status["device_serial"] = st2

    def update(self, status):
        """
        status dictionary update
        """
        i = 0
        for k in status:
            self.lv1.InsertStringItem(i, k)
            self.lv1.SetStringItem(i, 1, status[k])

    def toggle_led(self):
        pass

    def toggle_solenoid(self):
        pass


if __name__ == "__main__":
    app = wx.App()
    f = DiagnosticFrame(None, -1, "Diagnostics", size=(400, 600))
    status = {
        "Current mode": "0",
        "Card power": "1",
        "Voltage": "1231",
    }
    f.update(status)
    app.MainLoop()
