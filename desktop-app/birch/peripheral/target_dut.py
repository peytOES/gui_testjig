"""
Target DUT.  Class to combine information gathered over the course of the tests.
"""

import attr
import json
from pathlib import Path
import logging


@attr.s()
class TargetDUT():
    """
    Super class of all DUTs
    """
    # _id = attr.ib(default="")
    serial = attr.ib(default="")

    event_logger = logging.getLogger("event_logger")

    def log_device_dict(self):
        """
        Returns device dictionary for db
        """
        return attr.asdict(self)

    def assign_token(self, token):
        return True

    def set_barcode(self, barcode):
        self.serial = barcode
        return True

    def get_barcode(self):
        return self.serial

    # @classmethod
    # def create(cls, *args, **kwargs):
    #    """
    #    Param:
    #    id : Device ID (barcode in most cases)
    #    serial : Device serial number
    #    product : Produt identifier (e.g., thunderchild)
    #    """
    #    return cls(*args, **kwargs)

    @staticmethod
    def factory(product, *args, **kwargs):
        """
        Find a subclass with the name 
         (str(product) + TargetDUT).lower()
        
        """
        for cls in TargetDUT.__subclasses__():
            print(cls.__name__, product)
            if cls.__name__.lower() == (product + "TargetDUT").lower():
                return cls(*args, **kwargs)
        raise Exception("Target %s not found" % product)


class UnitTestTargetDUT(TargetDUT):
    """
    Subclass of TargetDUT for unit testing
    """


if __name__ == "__main__":
    # create instance of UnitTestTargetDUT
    t = TargetDUT.factory("UnitTest")
    t.serial = "sn"
    t._id = "Test"
    print(t)
    print(json.dumps(t.log_device_dict()))
