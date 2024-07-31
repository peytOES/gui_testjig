import enum
import logging
import datetime


# Abstract class for filters and endpoints
class ReceiveFilter(object):

    # All filters should be sub-classes of ReceiveFilter that provide their own implementation of parse
    # The parse methods should perform some operation and call self.notify() to forward the remaining data onto the next filter
    # Endpoints do not require a call to self.notify()
    # Note that every filter has its own set of callbacks registered to it

    def __init__(self):

        self.callback_list = []

    def notify(self, *args, **kwargs):

        for fp in self.callback_list:
            if fp is not None:
                fp(*args, **kwargs)

    def register_callback(self, fp):

        if fp is not None:
            if fp not in self.callback_list:
                self.callback_list.append(fp)

    def deregister_callback(self, fp):

        if fp is not None:
            if fp in self.callback_list:
                self.callback_list.remove(fp)

    def parse(self, data):

        raise NotImplementedError


# Forwards data along filter chain
class PassThroughFilter(ReceiveFilter):

    def __init__(self):
        self.callback_list = []

    def parse(self, data):
        self.notify(data)


# Appends data to buffer to be dumped or cleared after a set of tests
class BufferSink(ReceiveFilter):

    def __init__(self):
        self.callback_list = []
        self.buffer = ""

    def parse(self, data):
        self.buffer += data
        self.notify(data)

    def clear(self):
        self.buffer = ""

    def retrieve(self):
        return self.buffer


# Collects data and passes it along as complete lines
class LineFilter(ReceiveFilter):

    def __init__(self):

        self.callback_list = []
        self.line_buffer = ""

    def parse(self, data):

        for c in data:
            if c == '\n':
                self.notify(self.line_buffer)
                self.line_buffer = ""
            else:
                self.line_buffer += chr(c)


#########################

# Endpoint to write all data into a log file
class LogEndpoint(ReceiveFilter):

    def __init__(self, filename):
        self.fptr = open(filename, 'wb')
        logging.info("Opened log file...")

    def parse(self, data):
        data += "\n"
        self.fptr.write(data)

    def close(self):
        self.fptr.close()
        logging.info("Closed log file...")


# Endpoint to print out all data
class PrintEndpoint(ReceiveFilter):

    def parse(self, *args, **kwargs):
        print(args, kwargs)


# Do nothing Endpoint
class SinkEndpoint(ReceiveFilter):

    def parse(self, data):
        pass
