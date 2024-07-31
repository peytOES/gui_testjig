import wx
import json
from .fixture_info_frame import JsonFrame


class JobInfoFrame(JsonFrame):
    def __init__(self, config, *args, **kwargs):
        super().__init__(obj=config, *args, **kwargs)
