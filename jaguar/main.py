import sys
import os
import logging
from jaguar.manager import JaguarManagerUI


def jaguar_production():
    if "JAGUAR_CONFIG_DIR" in os.environ:
        m = JaguarManagerUI(config_dir=os.environ["JAGUAR_CONFIG_DIR"])
    else:
        m = JaguarManagerUI()
    m.start_thread()
    m.start_gui()


if __name__ == "__main__":
    jaguar_production()
