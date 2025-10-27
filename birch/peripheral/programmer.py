import subprocess
import logging

from .device import Device


class Programmer(Device):
    """
    Generic device programmer wrapper that invokes an external tool (e.g., STM32_Programmer_CLI,
    st-flash, openocd, jlink). Subclasses build command lines and optionally override
    detect_errors() to scan stdout/stderr for tool-specific error strings.
    """

    event_logger = logging.getLogger("event_logger")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executable = None
        self.result = None

    def detect_errors(self) -> bool:
        """
        Return True if an error is detected (so execute() returns False).
        Base implementation: assume no error (subclasses should tighten this).
        """
        return False

    def execute(self, command, timeout=5):
        """
        Execute an external command. Captures stdout/stderr and sets self.result.

        Returns:
          True  on success (exit code == 0 and detect_errors() == False)
          False on failure
        """
        self.event_logger.info("Programmer execute: %s" % " ".join(command))
        self.result = None
        try:
            if self.executable is not None or (command and isinstance(command, list)):
                self.result = subprocess.run(command, capture_output=True, timeout=timeout)
                # Log outputs to aid debugging
                self.event_logger.info("<< %s" % (self.result.stdout,))
                if self.result.stderr:
                    self.event_logger.info("<<ERR %s" % (self.result.stderr,))

                # Fail on any non-zero exit
                if self.result.returncode != 0:
                    return False

                # Tool-specific scan
                if self.detect_errors():
                    return False

                return True

            # No executable/command configured
            self.event_logger.error("No executable/command provided to Programmer.execute")
            return False

        except Exception as e:
            self.event_logger.error("Programmer exception %s %s" % (command, e))
            return False
