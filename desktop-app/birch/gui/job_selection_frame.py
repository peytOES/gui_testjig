import wx
import os
import time
from pubsub import pub


class JobSelectFrame(wx.Frame):
    """
    Frame to select test job.
    
    A list of suites, their descriptions and (if applicable) number of tokens remaining
    is presented to the operator.  

    Once a test suite has been selected, click button to proceed.
    """

    def __init__(self, config=None, *args, **kwds):
        wx.Frame.__init__(self, *args, **kwds)
        self.config = config
        if config is not None:
            self.icon = wx.Icon(str(self.config.image_dir / "icon.png"))
            self.SetIcon(self.icon)

        self.jobmgr = None
        self.panel = wx.Panel(self, wx.ID_ANY)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        st1 = wx.StaticText(self.panel, label="Select job:")
        self.vbox.Add(st1, 1, wx.ALL | wx.EXPAND, 15)

        self.lb = wx.ListCtrl(self.panel,
                              style=wx.LC_REPORT | wx.LC_SINGLE_SEL
                              )

        self.vbox.Add(self.lb, 8, wx.ALL | wx.EXPAND, 15)

        self.lb.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.on_list_focus_change)

        self.description = wx.StaticText(self.panel, label="")

        self.hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.hbox.Add((1, 1), 4)

        button = wx.Button(self.panel, id=wx.ID_ANY, label="Start")
        button.Bind(wx.EVT_BUTTON, self.on_start)
        button.SetFocus()

        self.hbox.Add(button, 1, wx.ALL, 15)
        self.vbox.Add(self.hbox, 1, wx.ALL | wx.EXPAND, 0)

        self.panel.SetSizer(self.vbox)
        self.Layout()
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_pressed)
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_key_pressed(self, event):
        code = event.GetKeyCode()
        if code == wx.WXK_RETURN:
            self.on_start(event)
        elif code == wx.WXK_DOWN:
            index = self.lb.GetFirstSelected()
            if index < self.lb.GetItemCount() - 1:
                index += 1
                self.lb.Select(index)
        elif code == wx.WXK_UP:
            index = self.lb.GetFirstSelected()
            if index > 0:
                index -= 1
                self.lb.Select(index)

    def on_close(self, event):
        """
        Close frame event

        If the frame has a parent object, notify it of the close event
        If no parent, when called standalone, just destroy self.
        """
        try:
            self.GetParent().Close()
        except AttributeError:
            self.Destroy()

    def on_start(self, event):
        """
        If start button is pressed, try to load the job file. 
        """
        index = self.lb.GetFirstSelected()
        if index >= 0:
            pub.sendMessage("system", message={
                "job_select": self.lb.GetFirstSelected()
            })

    def on_list_focus_change(self, event):
        pass

    def set_suite_list(self, l):
        """
        Set the list of test suites to offer for testing

        Every list item is a list of
        [name, cib remaining, cib total, description]
        """
        self.jobmgr = l
        self.lb.ClearAll()
        self.lb.InsertColumn(0, "Name", width=250)
        self.lb.InsertColumn(1, "Description", width=300)
        self.lb.InsertColumn(2, "Tokens remaining", width=150)
        self.lb.InsertColumn(3, "Tokens total", width=150)
        self.lb.InsertColumn(4, "Units passed", width=150)
        index = 0
        for text in self.jobmgr.get_job_stats():
            for c in range(len(text)):
                if text[c] == None:
                    text[c] = ""
            self.lb.Append(text)
        self.lb.Select(0)
