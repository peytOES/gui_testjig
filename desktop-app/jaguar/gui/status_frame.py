import wx
from birch.gui import OperatorGUI
from birch.gui import StatusFrame
from birch.gui import SlotSummaryPanel
from jaguar.gui.slot_summary import JaguarSlotSummaryPanel


class JaguarStatusFrame(StatusFrame):
    def setup_slots(self):
        pass
        self.slotgrid = wx.GridSizer(rows=1, cols=self.slot_count, hgap=2, vgap=2)
        for i in range(self.slot_count):
            self.slotpanel[i] = JaguarSlotSummaryPanel(self.config, i, True, self.panel, wx.ID_ANY, )
            self.slotgrid.Add(self.slotpanel[i], 1, wx.EXPAND)
            self.slotpanel[i].reset_display()
        self.vbox.Add(self.slotgrid, 10, wx.ALL | wx.EXPAND, 5)

    def heading(self):
        font = wx.Font(14, wx.SWISS, wx.NORMAL, wx.NORMAL)
        font2 = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL)

        self.units_passed = wx.StaticText(self.panel, label="Units passed: ")
        self.units_passed.SetFont(font)
        self.units_passed_value = wx.StaticText(self.panel, label="0")
        self.units_passed_value.SetFont(font)

        self.units_tested = wx.StaticText(self.panel, label="Units tested: ")
        self.units_tested.SetFont(font)
        self.units_tested_value = wx.StaticText(self.panel, label="")
        self.units_tested_value.SetFont(font)

        self.job_id = wx.StaticText(self.panel, label="Job: ")
        self.job_id.SetFont(font)
        self.job_id_value = wx.StaticText(self.panel, label="")
        self.job_id_value.SetFont(font)

        self.testsuite = wx.StaticText(self.panel, label="Test suite: ")
        self.testsuite.SetFont(font)
        self.testsuite_value = wx.StaticText(self.panel, label="")
        self.testsuite_value.SetFont(font)

    def setup_headerbox(self):
        """
        Creates and configures self.headerbox, adds it to self.vbox

        The header box contains job and system status
        (e.g. tokens remaining, job title)

        Default display as for Ohm - horizontal layout of Job, units passed, units tested, eui_remaining.
        """
        pad = 5
        self.headerbox = wx.GridSizer(4, gap=wx.Size(0, 0))

        self.headerbox.Add(self.testsuite, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add(self.testsuite_value, 1, wx.ALL | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)
        self.headerbox.Add((1, 1), 0)

        self.headerbox.Add(self.job_id, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add(self.job_id_value, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)
        self.headerbox.Add((1, 1), 0)

        self.headerbox.Add(self.units_passed, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add(self.units_passed_value, 1, wx.ALL | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)
        self.headerbox.Add((1, 1), 0)

        self.headerbox.Add(self.units_tested, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add(self.units_tested_value, 1, wx.ALL | wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)
        self.headerbox.Add((1, 1), 0)

        self.vbox.Add(self.headerbox, 1, wx.EXPAND | wx.ALL, 5)

    def set_next_eui(self, eui):
        pass

    def set_eui_remaining(self, n):
        pass
