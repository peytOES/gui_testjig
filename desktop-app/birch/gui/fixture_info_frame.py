import wx
import json


# from ..manager import Config

class JsonFrame(wx.Dialog):
    """
    Dialog to display a json file
    """

    def __init__(self, obj={}, *args, **kwargs):
        wx.Dialog.__init__(self, *args, **kwargs)
        message = json.dumps(obj, indent=4, sort_keys=True)
        text = wx.TextCtrl(self, -1, message, size=(640, 640), style=wx.TE_MULTILINE | wx.TE_READONLY)

        sizer = wx.BoxSizer(wx.VERTICAL)
        btnsizer = wx.BoxSizer()

        btn = wx.Button(self, wx.ID_OK)
        btnsizer.Add(btn, 0, wx.ALL, 5)

        sizer.Add(text, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        self.SetSizerAndFit(sizer)


class FixtureInfoFrame(JsonFrame):
    def __init__(self, config, *args, **kwargs):
        super().__init__(obj=config, *args, **kwargs)


if __name__ == "__main__":
    app = wx.App()
    config = {1: 2, 2: 3, 3: {4: 5}, 4: [1, 2, 3]}
    f = FixtureInfoFrame(parent=None, config=config, title="Test fixture info", size=(800, 600))
    f.Show()
    app.MainLoop()
