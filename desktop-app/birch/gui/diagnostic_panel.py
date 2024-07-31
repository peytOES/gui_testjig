import wx

from . import LedPanel


class DiagnosticPanel(wx.Panel):
    def __init__(self, index, *args, **kwds):
        self.index = index
        kwds["style"] = wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, *args, **kwds)

        vbox = wx.BoxSizer(wx.VERTICAL)

        # slot name
        slot_name = wx.StaticText(self, label="%d" % index)
        font = wx.Font(24, wx.SWISS, wx.NORMAL, wx.BOLD)
        slot_name.SetFont(font)

        vbox.Add(slot_name, 0, wx.ALIGN_CENTER_HORIZONTAL, 5)
