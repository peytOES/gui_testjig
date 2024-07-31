import enum
from pathlib import Path
import json


def load_error_codes(config_dir):
    """
    Load application specific error codes from config_dir/error_codes.json.  
    """
    f = open(Path(config_dir) / "error_codes.json", "r")
    l = json.load(f)
    e = enum.IntEnum('ErrorCode', l)
    return e
