import attr
import logging


class LogObject():
    def __init__(self, prefix="", logger=None):
        self.prefix = prefix
        self.logger = logger
        if self.logger is None:
            self.logger = logging.getLogger("event_logger")
        self.logger.setLevel(logging.INFO)

    def log_debug(self, *args, **kwargs):
        try:
            self.logger.debug(*args, **kwargs)
        except AttributeError:
            pass

    def log_info(self, *args, **kwargs):
        try:
            self.logger.info(*args, **kwargs)
        except AttributeError:
            pass


@attr.s
class BirchObject(LogObject):
    enabled = attr.ib()
    logger = attr.ib()

    def stop(self):
        self.log_info("Stop")
        pass
