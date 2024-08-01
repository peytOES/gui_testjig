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

        self.us_fw = wx.CheckBox(self.panel, label="US Firmware")
        self.us_fw.Bind(wx.EVT_CHECKBOX,self.on_fw_checkbox_change)
        self.headerbox.Add(self.us_fw, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)
        self.us_fw.Set3StateValue(True)


       
        self.rs232_option = wx.CheckBox(self.panel, label="RS232 Type Board")
        self.rs232_option.Bind(wx.EVT_CHECKBOX,self.on_board_type_checkbox_change)
        self.headerbox.Add(self.rs232_option, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)
        self.rs232_option.Set3StateValue(True)


        self.can_fw = wx.CheckBox(self.panel, label="Canadian Firmware")
        self.can_fw.Bind(wx.EVT_CHECKBOX,self.on_fw_checkbox_change)
        self.headerbox.Add(self.can_fw, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)

        self.hmb_option = wx.CheckBox(self.panel, label="HMB Type Board")
        self.hmb_option.Bind(wx.EVT_CHECKBOX,self.on_board_type_checkbox_change)
        self.headerbox.Add(self.hmb_option, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)
        
        self.provision_enable = wx.CheckBox(self.panel, label="Provision Disabled")
        self.provision_enable.Bind(wx.EVT_CHECKBOX,self.on_provision_checkbox_change)
        self.headerbox.Add(self.provision_enable, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0) 

        self.log_upload_enable = wx.CheckBox(self.panel, label="Log Upload Enabled")
        self.log_upload_enable.Bind(wx.EVT_CHECKBOX,self.on_log_upload_checkbox_change)
        self.headerbox.Add(self.log_upload_enable, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)

        self.rst_units = wx.Button(self.panel, label="Reset Number of Units Passed")
        self.rst_units.Bind(wx.EVT_BUTTON,self.on_units_passed_reset)
        self.headerbox.Add(self.rst_units, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)
        
        self.rst_units_tested = wx.Button(self.panel, label="Reset Number of Units Tested")
        self.rst_units_tested.Bind(wx.EVT_BUTTON,self.on_units_tested_reset)
        self.headerbox.Add(self.rst_units_tested, 1, wx.ALL | wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL, pad)
        self.headerbox.Add((1, 1), 0)

        self.vbox.Add(self.headerbox, 1, wx.EXPAND | wx.ALL, 5)

    def set_next_eui(self, eui):
        pass

    def set_eui_remaining(self, n):
        pass


    
    def disable_checkboxes(self,bool:bool):
        if(bool):
            # Disable the checkboxes initially if needed
            self.provision_enable.Disable()
            self.log_upload_enable.Disable()
            self.us_fw.Disable()
            self.can_fw.Disable()
            self.hmb_option.Disable()
            self.rs232_option.Disable()
            self.rst_units.Disable()
            self.rst_units_tested.Disable()

        pass
   

    def enable_warnings(self,bool:bool):
        self.warning_enable = bool
        self.log_upload_enable.Set3StateValue(True)
        self.log_upload_checkbox_state = True
        self.log_upload_enable.Disable()
        pass

    def set_validation_mode(self,bool:bool):
        self.provision_enable.Set3StateValue(not bool)    
        self.provision_checkbox_state = not bool
        pub.sendMessage("system", message={
                "provision_enable": self.provision_checkbox_state
        })
        
        if(self.provision_checkbox_state):
            self.provision_enable.LabelText = "Provision Enabled"
            # Create a warning for provision enable 
            if self.warning_enable:
                # Create a message dialog
                dlg = wx.MessageDialog(
                    self,
                    "Provision is enabled. This is a warning message.",
                    "Warning",
                    wx.OK | wx.ICON_WARNING
                )

                # Show the dialog
                dlg.ShowModal()

                # Destroy the dialog to free up resources
                dlg.Destroy()
                pass
                #TODO CREATE A WARNING for when the provision is enabled that user has to hit ok on to pass
        else:
            self.provision_enable.LabelText = "Provision Disabled"
            self.provision_enable.Disable()    
            self.us_fw.Set3StateValue(False)
            self.us_fw.Disable()
            self.can_fw.Set3StateValue(False)
            self.can_fw.Disable()

        pass
        
    def on_provision_checkbox_change(self, event):
        # Update the variable when the checkbox state changes
        self.provision_checkbox_state = self.provision_enable.GetValue()
        pub.sendMessage("system", message={
                "provision_enable": self.provision_checkbox_state
        })

        if(self.provision_checkbox_state):
            self.provision_enable.LabelText = "Provision Enabled"
            # Create a warning for provision enable 
            if self.warning_enable:
                # Create a message dialog
                dlg = wx.MessageDialog(
                    self,
                    "Provision is enabled. This is a warning message.",
                    "Warning",
                    wx.OK | wx.ICON_WARNING
                )

                # Show the dialog
                dlg.ShowModal()

                # Destroy the dialog to free up resources
                dlg.Destroy()
                pass
                #TODO CREATE A WARNING for when the provision is enabled that user has to hit ok on to pass
        else:
            self.provision_enable.LabelText = "Provision Disabled"

            
    def on_fw_checkbox_change(self,event):  
        # Update the variable when the checkbox state changes
        if('US' in event.EventObject.EventHandler.Label):
            self.fw = "USA"
            self.can_fw.Set3StateValue(False)
            self.us_fw.Set3StateValue(True)
            pass
        elif('Canadian' in event.EventObject.EventHandler.Label):
            self.fw = "CAN"
            self.us_fw.Set3StateValue(False)
            self.can_fw.Set3StateValue(True)
            pass

        pub.sendMessage("system", message={
                "set_fw": self.fw
            })

            
    def on_board_type_checkbox_change(self,event):  
        # Update the variable when the checkbox state changes
        if('HMB' in event.EventObject.EventHandler.Label):
            self.board_type = "HMB"
            self.rs232_option.Set3StateValue(False)
            self.hmb_option.Set3StateValue(True)
            pass
        elif('RS232' in event.EventObject.EventHandler.Label):
            self.board_type = "RS232"
            self.rs232_option.Set3StateValue(True)
            self.hmb_option.Set3StateValue(False)
            pass

        pub.sendMessage("system", message={
                "set_board_type": self.board_type
            })

       
        

    def on_log_upload_checkbox_change(self, event):
        # Update the variable when the checkbox state changes
        self.log_upload_checkbox_state = self.log_upload_enable.GetValue()
        pub.sendMessage("system", message={
                "log_upload_enable": self.log_upload_checkbox_state
            })

        if(self.log_upload_checkbox_state):
            self.log_upload_enable.LabelText = "Log Upload Enabled"
            if(self.warning_enable):
                # Create a message dialog
                dlg = wx.MessageDialog(
                    self,
                    "Log Upload is enabled. This is a warning message.",
                    "Warning. Hit OK to proceed...",
                    wx.OK | wx.ICON_WARNING
                )

                # Show the dialog
                dlg.ShowModal()

                # Destroy the dialog to free up resources
                dlg.Destroy()
                pass
                #TODO CREATE A WARNING for when the log upload is enabled that user has to hit ok on to pass
        else:
            self.log_upload_enable.LabelText = "Log Upload Disabled"
       

       
    def on_units_passed_reset(self, event):
        # Update the variable when the checkbox state changes
        pub.sendMessage("system", message={
                "reset_units_passed": True 
            })        
        pub.sendMessage("status", message={
                "units_passed": 0
            })

    def on_units_tested_reset(self, event):
        # Update the variable when the checkbox state changes
        pub.sendMessage("system", message={
                "reset_units_tested": True 
            })        
        pub.sendMessage("status", message={
                "units_tested": 0
            })

       
    def show_internet_warning(self, bool:bool):
        if(bool):
            # Create a message dialog
            dlg = wx.MessageDialog(
                self,
                "Cannot access internet, PLEASE CHECK CONNECTION",
                "Warning. Hit OK to proceed...",
                wx.OK | wx.ICON_WARNING
            )

            # Show the dialog
            dlg.ShowModal()

            # Destroy the dialog to free up resources
            dlg.Destroy()