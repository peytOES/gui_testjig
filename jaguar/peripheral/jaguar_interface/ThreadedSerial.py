import threading
import serial
import logging
import traceback
import sys
from .StoppableThread import StoppableThread


class ThreadedSerial(object):

    def __init__(self, port, baudrate=115200, bytesize=8, parity='N', stopbits=1,
                 read_timeout=0.01, write_timeout=0.05, logger=None, name=""):

        # Serial port object
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = baudrate
        self.ser.timeout = read_timeout
        self.ser.write_timeout = write_timeout
        self.ser.bytesize = bytesize
        self.ser.parity = parity
        self.ser.stopbits = stopbits
        self.threadObj_name = name
        #
        # Handle self.logger argument defaulting
        #
        if logger is None:
            self.logger = logging.getLogger(self.__class__.__name__)
        elif not hasattr(logger, "getChild"):
            self.logger = logger
        else:
            self.logger = logger.getChild(self.__class__.__name__)

        # Callback list
        self.callback_list = []

        # Threading objects
        self.threadObj = None

    def open(self):

        # Open serial port
        self.logger.info("%s - %s: Opening serial port..." % (self.__class__.__name__, self.open.__name__))
        self.ser.open()
        self.logger.info("%s - %s: Successful!" % (self.__class__.__name__, self.open.__name__))

        # Flush buffers
        self.ser.flushInput()
        self.ser.flushOutput()

        # Start thread
        self.threadObj = SerialMonitorThread(self.ser, self.callback_list, self.logger)
        self.threadObj.daemon = True
        if self.threadObj_name != "":
            self.threadObj.name = self.threadObj_name
        self.threadObj.start()

    def close(self):

        # Stop threading
        self.threadObj.stop()
        self.threadObj.join()
        self.threadObj = None

        # Close serial port
        self.logger.info("%s -%s: Closing serial port!" % (self.__class__.__name__, self.close.__name__))
        self.ser.close()
        self.logger.info("%s - %s: Successful!" % (self.__class__.__name__, self.close.__name__))

    def write(self, data, *args, **kwargs):

        if (self.ser is not None):
            self.ser.write(data, *args, **kwargs)
            self.logger.info("%s: >> %s" % (self.__class__.__name__, data))
        else:
            return None

    def register_callback(self, fp):

        if fp is not None:
            if fp not in self.callback_list:
                self.callback_list.append(fp)

    def deregister_callback(self, fp):

        if fp is not None:
            if fp in self.callback_list:
                self.callback_list.remove(fp)


class SerialMonitorThread(StoppableThread):

    def __init__(self, ser, callback_list, logger):

        super(SerialMonitorThread, self).__init__()

        self.serObj = ser
        self.callback_list = callback_list
        self.logger = logger

    def read(self, *args, **kwargs):

        if (self.serObj is not None):
            rd = self.serObj.read(*args, **kwargs)
            return rd
        else:
            return None

    def run(self):

        self.logger.info("%s - %s: Started serial monitor thread..." % (self.__class__.__name__, self.run.__name__))

        while not self.stopped():
            # Read from serial
            x = self.read(1)
            if x is not None and len(x) > 0:

                # Post callbacks
                for fp in self.callback_list:
                    if fp is not None:
                        try:
                            fp(x)
                        except:
                            exc_type, exc_value, exc_trace = sys.exc_info()
                            self.logger.error("%s: Exception %s %s Traceback : %s" % (
                            self.__class__.__name__, exc_type, exc_value, repr(traceback.extract_tb(exc_trace))))

        self.logger.info("%s - %s: Exited serial monitor thread..." % (self.__class__.__name__, self.run.__name__))
