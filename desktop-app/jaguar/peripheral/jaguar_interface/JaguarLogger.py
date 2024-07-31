from .Filter import *


# Filter chain object to write data to a log file
class JaguarLogger(object):

    def __init__(self, serObj=None, logfile=None):
        # Fetch threaded serial port object
        self.serObj = serObj

        # Create filter objects
        self.linefilter = LineFilter()

        # Create endpoints
        self.log = LogEndpoint(logfile)

        # Define filter chain + endpoints
        self.serObj.register_callback(self.linefilter.parse)
        self.linefilter.register_callback(self.log.parse)

    def close(self):
        self.log.close()
