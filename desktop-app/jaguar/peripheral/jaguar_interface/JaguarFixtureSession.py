# Imports
import logging
import sys
import os
import argparse

from .ThreadedSerial import ThreadedSerial
from .JaguarLogger import JaguarLogger
from .JaguarFixture import JaguarFixture


# Class to initialize an Jaguar Fixture Session
class JaguarFixtureSession(object):

    def __init__(self, mcuPort=None, mcuLog=None, logger=None):

        # Handle self.logger argument defaulting
        if logger is None:
            self.logger = logging.getLogger(self.__class__.__name__)
        elif not hasattr(logger, "getChild"):
            self.logger = logger
        else:
            self.logger = logger.getChild(self.__class__.__name__)

        # Create threaded serial port object
        self.jaguarCom = ThreadedSerial(port=mcuPort)
        if self.jaguarCom is None:
            self.logger.error("%s - %s: Setup failed, please restart..." % self.__class__.__name__,
                              self.__init__.__name__)

        # Create logger objects
        if mcuLog is not None:
            self.jaguarLogger = JaguarLogger(serObj=self.jaguarCom, logfile=mcuLog)
        else:
            self.jaguarLogger = None

        # Generate an instance of the Jaguar Fixture class
        self.jaguarFixture = JaguarFixture(serObj=self.jaguarCom)
        if self.jaguarFixture is None:
            self.logger.error("%s - %s: Setup failed, please restart..." % self.__class__.__name__,
                              self.__init__.__name__)

        # Open the com port
        self.jaguarCom.open()

    def close(self):

        self.logger.info("Exiting...")

        # Close com port
        self.jaguarCom.close()

        # Close log file
        if self.jaguarLogger is not None:
            self.jaguarLogger.close()


# Function to exit gracefully
def exit():
    jaguarSession.close()
    sys.exit()


if __name__ == "__main__":
    # Set the logging level
    # Currently the default is set to INFO to only print neccesary information to the user
    logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)s:\t%(message)s', level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

    # Arguments, only port is required
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', help="comport of Jaguar Fixture", required=True)
    parser.add_argument('-f', '--log', help="path to Jaguar Fixture log file", default=None)
    args = parser.parse_args()

    # Create battery monitor session
    jaguarSession = JaguarFixtureSession(args.port, args.log)

    # Tell the user setup is complete
    logging.info("Setup complete, waiting for input...")

    fx = jaguarSession.jaguarFixture
    # time.sleep(1)
    # fx.set_led(2,1)
    # time.sleep(1)
    # fx.set_led(2,0)
    # time.sleep(1)
    # fx.set_led(2,1)
    # time.sleep(1)

    # jaguarSession.close()
