import attr
import json
from pathlib import Path
import os
import sys
import getpass

from .fixture import fixture_id
from .__version__ import VERSION


@attr.s(frozen=True)
class Config():
    """
    Fixture level configuration class
    """
    FILENAME = "fixture_conf.json"

    config_path = attr.ib()
    config_dir = attr.ib()
    testsuite_dir = attr.ib()
    image_dir = attr.ib()
    input_dir = attr.ib()
    active_dir = attr.ib()
    log_dir = attr.ib()

    description = attr.ib()
    fixture_id = attr.ib()
    fixture_number = attr.ib()
    product = attr.ib()
    test_parameters = attr.ib()
    version = attr.ib()
    run_mode = attr.ib(default="card")
    result_db = attr.ib(default=None)
    printer = attr.ib(default={})
    slot_map = attr.ib(default=None)
    debug = attr.ib(default=False)

    def to_dict(self):
        """
        Format contents as dict
        """
        d = attr.asdict(self)

        # fix posix path to string conversion
        for key in d:
            if type(d[key]) != dict:
                d[key] = str(d[key])
        return d

    @classmethod
    def load(cls, config_dir=None):
        """
        Load a configuration file.
        """

        p = Path(config_dir) / "config.json"
        with open(p, "r") as f:
            data = json.load(f)

        # determine if application is a script file or frozen exe
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(__file__)

        return cls(
            config_path=p.absolute(),
            config_dir=config_dir,
            testsuite_dir=Path(Path(config_dir).parent) / "testsuite",
            image_dir=Path(Path(config_dir).parent) / "images",
            input_dir=Path(Path(config_dir).parent) / "input",
            active_dir=Path(Path(config_dir).parent) / "active",
            log_dir=Path(Path(config_dir).parent) / "log",
            fixture_id=fixture_id(),
            version=VERSION,
            **data
        )


def find_config_dir(product="birch", company="jvdh"):
    """
    Search for the directory that contains config.json file in a number of locations
    """
    search_dir = []
    CONFIG_FILE = "config.json"
    if "BIRCH_CONFIG" in os.environ:
        search_dir.append(os.environ["BIRCH_CONFIG"])
    search_dir.append(Path("assets/conf"))

    if sys.platform == "win32":
        search_dir.append(Path(os.environ["APPDATA"]) / company / product / "conf")
    else:
        search_dir.append(Path("/home/") / getpass.getuser() / company / product / "conf")

    for d in search_dir:
        filename = d / CONFIG_FILE
        print("Loading config from %s" % filename)
        try:
            f = open(filename, "r")
            print("Found")
            return d
        except FileNotFoundError:
            # directory not found, try the next on
            pass

    return "./assets/conf"
