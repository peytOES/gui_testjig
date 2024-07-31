from birch.gui import OperatorGUI, JobSelectFrame, OperatorSelectFrame
from .status_frame import JaguarStatusFrame
from .job_selection_frame import JaguarJobSelectFrame


class JaguarOperatorGUI(OperatorGUI):
    def init_frames(self):
        """
        Create frames used in UI.

        Override in subclasses
        """
        # primary frame 
        self.status_frame = JaguarStatusFrame(gui_handle=self, slot_count=self.slot_count, parent=None,
                                              title=self.product_string, size=(600, 800), config=self.config)
        # suite selection
        self.testsuite_frame = JaguarJobSelectFrame(self.config, self.status_frame, -1, self.product_string,
                                                    size=(1024, 600))
        # operator selection
        self.operator_frame = OperatorSelectFrame(self.config, self.status_frame, -1, self.product_string)
