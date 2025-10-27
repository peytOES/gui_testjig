import wx
from birch.gui import OperatorGUI
from birch.gui import StatusFrame
from birch.gui import SlotSummaryPanel
from jaguar.gui.slot_summary import JaguarSlotSummaryPanel
from pubsub import pub


class JaguarStatusFrame(StatusFrame):
    def setup_slots(self):
        pass
        self.slotgrid = wx.GridSizer(rows=1, cols=self.slot_count, hgap=2, vgap=2)
        for i in range(self.slot_count):
            self.slotpanel[i] = JaguarSlotSummaryPanel(self.config, i, True, self.panel, wx.ID_ANY)
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
        Creates and configures self.headerbox, adds it to self.vbox.
        The header box contains job and system status.
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

        self.us_fw = wx.CheckBox(self.panel, label="US Firmware")
        self.us_fw.Bind(wx.EVT_CHECKBOX, self.on_fw_checkbox_change)
        self.headerbox.Add(self.us_fw, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)
        self.us_fw.Set3StateValue(True)

        self.boardv1_option = wx.CheckBox(self.panel, label="BrightLync V1")
        self.boardv1_option.Bind(wx.EVT_CHECKBOX, self.on_board_type_checkbox_change)
        self.headerbox.Add(self.boardv1_option, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)
        self.boardv1_option.Set3StateValue(True)

        self.can_fw = wx.CheckBox(self.panel, label="Canadian Firmware")
        self.can_fw.Bind(wx.EVT_CHECKBOX, self.on_fw_checkbox_change)
        self.headerbox.Add(self.can_fw, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)

        self.boardv2_option = wx.CheckBox(self.panel, label="BrightLync V2")
        self.boardv2_option.Bind(wx.EVT_CHECKBOX, self.on_board_type_checkbox_change)
        self.headerbox.Add(self.boardv2_option, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)

        # --- MOVED EARLIER: Provisioning before V3 ---
        self.provision_enable = wx.CheckBox(self.panel, label="Provision Disabled")
        self.provision_enable.Bind(wx.EVT_CHECKBOX, self.on_provision_checkbox_change)
        self.headerbox.Add(self.provision_enable, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)

        # --- BrightLync V3 option (now after Provision) ---
        self.boardv3_option = wx.CheckBox(self.panel, label="BrightLync V3")
        self.boardv3_option.Bind(wx.EVT_CHECKBOX, self.on_board_type_checkbox_change)
        self.headerbox.Add(self.boardv3_option, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)

        self.log_upload_enable = wx.CheckBox(self.panel, label="Log Upload Enabled")
        self.log_upload_enable.Bind(wx.EVT_CHECKBOX, self.on_log_upload_checkbox_change)
        self.headerbox.Add(self.log_upload_enable, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)

        self.rst_units = wx.Button(self.panel, label="Reset Number of Units Passed")
        self.rst_units.Bind(wx.EVT_BUTTON, self.on_units_passed_reset)
        self.headerbox.Add(self.rst_units, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)

        self.rst_units_tested = wx.Button(self.panel, label="Reset Number of Units Tested")
        self.rst_units_tested.Bind(wx.EVT_BUTTON, self.on_units_tested_reset)
        self.headerbox.Add(self.rst_units_tested, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)

        self.vbox.Add(self.headerbox, 1, wx.EXPAND | wx.ALL, 5)

        # ---- Default to V3; show V1/V2 but disable them ----
        self.board_type = "V3"
        self.boardv3_option.Set3StateValue(True)
        self.boardv1_option.Set3StateValue(False)
        self.boardv2_option.Set3StateValue(False)
        self.boardv1_option.Disable()
        self.boardv2_option.Disable()

        # Defer the publish until frame is shown so subscribers exist
        self._sent_defaults = False
        self.Bind(wx.EVT_SHOW, self._on_first_show)

    def _on_first_show(self, evt):
        if evt.IsShown() and not self._sent_defaults:
            self._sent_defaults = True
            wx.CallAfter(pub.sendMessage, "system", message={"set_board_type": "V3"})
        evt.Skip()

    def set_next_eui(self, eui):
        pass

    def set_eui_remaining(self, n):
        pass

    def disable_checkboxes(self, bool: bool):
        if bool:
            self.provision_enable.Disable()
            self.log_upload_enable.Disable()
            self.us_fw.Disable()
            self.can_fw.Disable()
            self.boardv2_option.Disable()
            self.boardv1_option.Disable()
            if hasattr(self, "boardv3_option"):
                self.boardv3_option.Disable()
            self.rst_units.Disable()
            self.rst_units_tested.Disable()
        pass

    def enable_warnings(self, bool: bool):
        self.warning_enable = bool
        self.log_upload_enable.Set3StateValue(True)
        self.log_upload_checkbox_state = True
        self.log_upload_enable.Disable()
        pass

    def set_validation_mode(self, bool: bool):
        self.provision_enable.Set3StateValue(not bool)
        self.provision_checkbox_state = not bool
        pub.sendMessage("system", message={"provision_enable": self.provision_checkbox_state})

        if self.provision_checkbox_state:
            self.provision_enable.LabelText = "Provision Enabled"
            if self.warning_enable:
                dlg = wx.MessageDialog(
                    self,
                    "Provision is enabled. This is a warning message.",
                    "Warning",
                    wx.OK | wx.ICON_WARNING
                )
                dlg.ShowModal()
                dlg.Destroy()
        else:
            self.provision_enable.LabelText = "Provision Disabled"
            self.provision_enable.Disable()
            self.us_fw.Set3StateValue(False)
            self.us_fw.Disable()
            self.can_fw.Set3StateValue(False)
            self.can_fw.Disable()

        pass

    def on_provision_checkbox_change(self, event):
        self.provision_checkbox_state = self.provision_enable.GetValue()
        pub.sendMessage("system", message={"provision_enable": self.provision_checkbox_state})

        if self.provision_checkbox_state:
            self.provision_enable.LabelText = "Provision Enabled"
            if self.warning_enable:
                dlg = wx.MessageDialog(
                    self,
                    "Provision is enabled. This is a warning message.",
                    "Warning",
                    wx.OK | wx.ICON_WARNING
                )
                dlg.ShowModal()
                dlg.Destroy()
        else:
            self.provision_enable.LabelText = "Provision Disabled"

    def on_fw_checkbox_change(self, event):
        if ('US' in event.EventObject.EventHandler.Label):
            self.fw = "USA"
            self.can_fw.Set3StateValue(False)
            self.us_fw.Set3StateValue(True)
        elif ('Canadian' in event.EventObject.EventHandler.Label):
            self.fw = "CAN"
            self.us_fw.Set3StateValue(False)
            self.can_fw.Set3StateValue(True)

        pub.sendMessage("system", message={"set_fw": self.fw})

    def on_board_type_checkbox_change(self, event):
        if ('V3' in event.EventObject.EventHandler.Label):
            self.board_type = "V3"
            self.boardv1_option.Set3StateValue(False)
            self.boardv2_option.Set3StateValue(False)
            self.boardv3_option.Set3StateValue(True)
        elif ('V2' in event.EventObject.EventHandler.Label):
            self.board_type = "V2"
            self.boardv1_option.Set3StateValue(False)
            self.boardv2_option.Set3StateValue(True)
            if hasattr(self, "boardv3_option"):
                self.boardv3_option.Set3StateValue(False)
        elif ('V1' in event.EventObject.EventHandler.Label):
            self.board_type = "V1"
            self.boardv1_option.Set3StateValue(True)
            self.boardv2_option.Set3StateValue(False)
            if hasattr(self, "boardv3_option"):
                self.boardv3_option.Set3StateValue(False)

        pub.sendMessage("system", message={"set_board_type": self.board_type})

    def on_log_upload_checkbox_change(self, event):
        self.log_upload_checkbox_state = self.log_upload_enable.GetValue()
        pub.sendMessage("system", message={"log_upload_enable": self.log_upload_checkbox_state})

        if self.log_upload_checkbox_state:
            self.log_upload_enable.LabelText = "Log Upload Enabled"
            if self.warning_enable:
                dlg = wx.MessageDialog(
                    self,
                    "Log Upload is enabled. This is a warning message.",
                    "Warning. Hit OK to proceed...",
                    wx.OK | wx.ICON_WARNING
                )
                dlg.ShowModal()
                dlg.Destroy()
        else:
            self.log_upload_enable.LabelText = "Log Upload Disabled"

    def on_units_passed_reset(self, event):
        pub.sendMessage("system", message={"reset_units_passed": True})
        pub.sendMessage("status", message={"units_passed": 0})

    def on_units_tested_reset(self, event):
        pub.sendMessage("system", message={"reset_units_tested": True})
        pub.sendMessage("status", message={"units_tested": 0})

    def show_internet_warning(self, bool: bool):
        if bool:
            dlg = wx.MessageDialog(
                self,
                "Cannot access internet, PLEASE CHECK CONNECTION",
                "Warning. Hit OK to proceed...",
                wx.OK | wx.ICON_WARNING
            )
            dlg.ShowModal()
            dlg.Destroy()
