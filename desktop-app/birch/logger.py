import sys
import json
import logging
import logging.handlers
import datetime
from datetime import timezone
from pythonjsonlogger import jsonlogger
import os
import traceback
from pathlib import Path


class EventJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(EventJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.datetime.now(timezone.utc).astimezone().isoformat()
            log_record['timestamp'] = now


class EventStreamFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(EventStreamFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.datetime.now(timezone.utc).astimezone().isoformat()
            log_record['timestamp'] = now

        if log_record.get("exception_trace"):
            log_record["exception_trace"] = "".join(traceback.format_tb(log_record["exception_trace"]))

        default_fields = ["exception_type", "exception_value", "exception_trace", "location", "slot"]

        if not log_record.get("slot"):
            log_record["slot"] = ""

        for f in default_fields:
            if not log_record.get(f):
                log_record[f] = ""

    def format(self, record):
        message_dict = {}
        if isinstance(record.msg, dict):
            message_dict = record.msg
            record.message = None
        else:
            record.message = record.getMessage()
        # only format time if needed
        if "asctime" in self._required_fields:
            record.asctime = self.formatTime(record, self.datefmt)

        # Display formatted exception, but allow overriding it in the
        # user-supplied dict.
        if record.exc_info and not message_dict.get('exc_info'):
            message_dict['exc_info'] = self.formatException(record.exc_info)
        if not message_dict.get('exc_info') and record.exc_text:
            message_dict['exc_info'] = record.exc_text

        try:
            log_record = OrderedDict()
        except NameError:
            log_record = {}

        self.add_fields(log_record, record, message_dict)
        log_record = self.process_log_record(log_record)
        return "%(slot)s %(location)s %(msg)s %(exception_type)s %(exception_value)s  %(exception_trace)s" % (
            log_record)


def log_setup(target_dir=None):
    """
    Set up logging to target_dir 
    """
    if target_dir is not None:
        if not os.path.isdir(target_dir):
            os.mkdir(target_dir)

    # result log
    result_logger = logging.getLogger("result_logger")
    result_logger.setLevel(logging.INFO)
    formatter = EventJsonFormatter('%(timestamp)s ')

    if target_dir is not None:
        logHandler = logging.handlers.RotatingFileHandler(Path(target_dir) / "result.log", maxBytes=1e7, backupCount=5)
        logHandler.setFormatter(formatter)
        result_logger.addHandler(logHandler)

    # event log
    event_logger = logging.getLogger("event_logger")
    event_logger.setLevel(logging.DEBUG)
    result_formatter = EventJsonFormatter('%(timestamp)s %(msg)s')

    if target_dir is not None:
        logHandler = logging.handlers.RotatingFileHandler(Path(target_dir) / "event.log", maxBytes=1e7, backupCount=5)
        logHandler.setFormatter(result_formatter)
        event_logger.addHandler(logHandler)

    stdout_formatter = EventStreamFormatter('>>%(asctime)s %(msg)s')  #
    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(stdout_formatter)
    event_logger.addHandler(stdout_handler)

    # if target_dir is not None:
    #    hw_log = logging.getLogger("HardwareLogger")
    #    hw_log.setLevel(level=logging.INFO)

    #    #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    #    #hw_log.setFormatter(formatter)
    #    handler = logging.handlers.RotatingFileHandler(target_dir+os.sep + "hardware.log", maxBytes=10e6, backupCount=3)
    #    f = logging.Formatter('%(asctime)s : %(message)s')
    #    handler.setFormatter(f)
    #    hw_log.addHandler(handler)

    #    proxima_log=logging.getLogger("proxima_logger")
    #    proxima_log.setLevel(level=logging.INFO)
    #    handler=logging.handlers.RotatingFileHandler(target_dir+os.sep + "proxima.log", maxBytes=1e6, backupCount=5)
    #    f=logging.Formatter('%(asctime)s : %(message)s')
    #    handler.setFormatter(f)
    #    proxima_log.addHandler(handler)
