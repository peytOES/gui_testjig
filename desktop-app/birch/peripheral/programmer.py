import subprocess
import logging

from .device import Device


class Programmer(Device):
    """
    Generic device programmer - calls external programming software (e.g., jlink, stlink, openocd)
    to perform programming.

    Function calls are used to construct a command to call through a subprocess.
    """
    event_logger = logging.getLogger("event_logger")

    def __init__(self, *args, **kwargs):
        self.executable = None
        pass

    def detect_errors(self):
        return True

    def execute(self, command, timeout=5):
        """
        Execute the subprocess
        """
        self.event_logger.info("Programmer execute: %s" % " ".join(command))
        self.result = None
        try:
            if self.executable is not None:
                self.result = subprocess.run(command, capture_output=True, timeout=timeout)
                self.event_logger.info("<< %s" % self.result.stdout)
                if self.result.returncode == 1:
                    return False
                if self.detect_errors():
                    return False
                return True
        except Exception as e:
            self.event_logger.error("Programmer exception %s %s" % (command, e))
            return False
