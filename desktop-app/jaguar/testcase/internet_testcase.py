#   "no_internet_connection": 4000,

import time
from pathlib import Path
import subprocess
import json
import os
import socket
from pubsub import pub



from .jaguar_testcase import JaguarTestCase




class InternetConnectionTestCase(JaguarTestCase):
    """
    Just uses socket to test whether the computer can access the internet
    Tested
    """

    def __init__(self, 
                 *args, 
                 **kwargs):
        super().__init__(*args, **kwargs)
   
        self.internet_connection = False

        self.append_step("Check for Internet Connection",self.internet)


    #Check for internet connection
    def internet(self,host="8.8.8.8", port=53, timeout=3):
        """
        Host: 8.8.8.8 (google-public-dns-a.google.com)
        OpenPort: 53/tcp
        Service: domain (DNS/TCP)
        """
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            result = True
        except socket.error as ex:
            print(ex)
            result = False

        self.internet_connection = result
        if(not result):
            pub.sendMessage('status',message={'internet_warning':True})
            time.sleep(5.0)
        return {"result": result}
