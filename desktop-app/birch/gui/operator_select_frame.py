import wx

import time
from pubsub import pub


class OperatorSelectFrame(wx.Frame):
    """
    Frame to select operator.
    
    A list of operators names are read from operator.json and passed in 

    Once a name has been selected, click button to proceed.
    """

    def __init__(self, config=None, *args, **kwds):
        wx.Frame.__init__(self, *args, **kwds)
        self.config = config
        if config is not None:
            self.icon = wx.Icon(str(self.config.image_dir / "icon.png"))
            self.SetIcon(self.icon)

        self.operator_list = None
        self.panel = wx.Panel(self, wx.ID_ANY)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        st1 = wx.StaticText(self.panel, label="Select operator:")

        self.vbox.Add(st1, 1, wx.ALL | wx.EXPAND, 15)

        self.lb = wx.ListCtrl(self.panel,
                              style=wx.LC_LIST | wx.LC_SINGLE_SEL
                              )
        self.vbox.Add(self.lb, 8, wx.LEFT | wx.RIGHT | wx.EXPAND, 15)

        self.lb.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.on_list_focus_change)

        button = wx.Button(self.panel, id=wx.ID_ANY, label="Sign in")
        button.Bind(wx.EVT_BUTTON, self.on_button)

        self.vbox.Add(button, 1, wx.ALL | wx.ALIGN_RIGHT, 15)
        button.SetFocus()

        self.panel.SetSizer(self.vbox)
        self.Layout()
        self.Centre()
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_pressed)
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_button(self, event):
        if self.lb.GetFirstSelected() >= 0:
            pub.sendMessage("system", message={
                "operator": self.lb.GetFirstSelected()
            })
            self.Hide()

    def on_close(self, event):
        self.GetParent().Close()

    def on_key_pressed(self, event):
        code = event.GetKeyCode()
        if code == wx.WXK_RETURN:
            self.on_button(event)
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

    def on_list_focus_change(self, event):
        pass

    def set_operator_list(self, l):
        self.operator_list = l

        self.lb.ClearAll()
        for i in self.operator_list.get_operator_names():
            self.lb.Append([i])

        self.lb.Select(0)


if __name__ == "__main__":
    def select_callback(i):
        print("Callback: ", i)


    app = wx.App()
    f = OperatorSelectFrame(select_callback, None, -1, "Test fixture")
    f.set_operator_list(["name1", "name2", "name3", "name4"])
    f.Show()

    app.MainLoop()
