import serial
import time
import re
import logging

"""
UBlox SARA LTE modem module driver
https://www.u-blox.com/sites/default/files/SARA-R4_ATCommands_UBX-17003787.pdf
"""


class LTEModule():
    event_logger = logging.getLogger("event_logger")
    pass


class UBloxSara(LTEModule):
    def __init__(self, connection):
        self.connection = connection

    def at_command(self, cmd: bytes):
        self.event_logger.info("LTE >> %s" % cmd)

        self.connection.write(cmd + b"\r\n")
        time.sleep(0.1)
        resp = self.connection.read(1024)
        tryCount =0
        while(resp == b""):
            resp = self.connection.read(1024)
            tryCount +=1
            time.sleep(0.1)
            if(tryCount>20):
                break
        if resp == b"":
            self.event_logger.info("LTE >> %s" % cmd)
            self.connection.write(cmd + b"\r\n")
            time.sleep(0.1)
            resp = self.connection.read(1024)
            tryCount =0
            while(resp == b""):
                resp = self.connection.read(1024)
                tryCount +=1
                time.sleep(0.1)
                if(tryCount>20):
                    break
        
        self.event_logger.info("LTE << %s" % resp)
        result = b"OK" in resp or b"ULSTFILE" in resp
        resp = resp.replace(cmd, b"")
        resp = resp.replace(b"OK", b"")
        resp = resp.replace(b"\"", b"")
        resp = resp.replace(b"+CCID: ", b"")
        resp = resp.replace(b"AT+CC: ", b"")
        resp = resp.strip()
        return result, resp

    def read_info(self, cmds):
        resp = self.connection.read(1024)
        info = {}
        for k in cmds:
            at_resp = self.at_command(cmds[k])
            if at_resp[0]:
                resp = at_resp[1].replace(b"\xff", b"x")
                # print(resp)
                info[k] = str(resp, "utf-8")
            else:
                info[k] = None

        return info

    def read_module_info(self):
        """
        Read module info, format as a dictionary.
        """

        cmds = {
            "manufacturer_identification": b"AT+CGMI",
            "model": b"AT+CGMM",
            "fw_version": b"AT+GMR",
            "imei": b"AT+GSN",
            "type_code": b"ATI0",
            "application_version": b"ATI9",
            "card_id": b"AT+CCID",
            "sc_lock": b'AT+CLCK="SC",2',
            "sc_pin_status": b'AT+CPIN?',
            "files": b'AT+ULSTFILE',
        }
        return self.read_info(cmds)

    def read_network_info(self):
        """
        Read connection info
        """
        cmds = {
            "operator_selection": b'AT+COPS?',
            "network_registration_status": b'AT+CREG?',
            "signal_quality": b"AT+CSQ",
            # "active_profile":b"AT&V",
        }
        return self.read_info(cmds)

    def ping(self):
        """
        Send AT, expect OK
        """
        result, resp = self.at_command(b"AT")
        return result


    # writes a command to lte port and reads the line to self.response after 1 second wait
    def write(self, msg, insert_newline=True):
        self.event_logger.info("LTE >> %s" % msg)
        if insert_newline == True:
            msg = msg + "\r\n"
        self.connection.write(str.encode(msg))
        time.sleep(0.35)
        x = self.connection.read(1024)
        self.response = x
        self.event_logger.info("LTE << %s" % x)
        return x
    
    # write entire cert file f to lte module chip 
    def send_cert(self, f, cert_type, num_bytes):
        print(f"Transferring cert {cert_type}")
        if cert_type == "aws_ca":
            print(self.write(f'AT+USECMNG=0,0,"rootCA",{num_bytes}').decode())
            cert_name = "rootCA"
        elif cert_type == "device_cert":
            print(self.write(f'AT+USECMNG=0,1,"client_cert_cs",{num_bytes}').decode())
            cert_name = "client_cert_cs"
        elif cert_type == "device_key":
            print(self.write(f'AT+USECMNG=0,2,"client_key_cs",{num_bytes}').decode())
            cert_name = "client_key_cs"
        else:
            
            print("ERROR: Incorrect cert type")
            exit()
        
        if self.read_pattern(">") == True:
            # send cert
            lines = f.readlines()
            for line in lines:
                print(self.write(line, False).decode())

        if "OK" in self.response.decode():
            self.event_logger.info(f"Certificate {cert_name} Uploaded Successfully")
            return True
        else:
            return False

    # check if the pattern allows us to respond
    def read_pattern(self, pattern):
        if self.response != b'':
            if pattern in self.response.decode()[-1]:
                return True
            else:
                return False
        else:
            return False

    #TODO: CREATE ERROR 3120
    # retrurns iccid
    def get_sim_iccid(self):
        self.write("AT+CCID?")
        print(self.response.decode())
        if "OK" in self.response.decode():
            #TODO SUCCESS LOG 
            iccid = self.response.decode().split(' ')[-1].split('\r')[0]
            self.iccid = iccid
            return self.iccid
        else:
            #TODO FAILURE PRINT ERROR
            pass


