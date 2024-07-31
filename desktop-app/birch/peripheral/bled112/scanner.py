import sys, optparse, serial, struct, time, datetime, re, signal, string
import enum
import binascii

from . import bglib

uuid_service = [0x28, 0x00]  # 0x2800
uuid_client_characteristic_configuration = [0x29, 0x02]  # 0x2902


class BleState(enum.IntEnum):
    STANDBY = 0
    CONNECTING = 1
    FINDING_SERVICES = 2
    FINDING_ATTRIBUTES = 3


class BLED112():
    def __init__(self, port, baudrate=115200):
        self.port = port
        self.baud = baudrate
        self.state = BleState.STANDBY

        self.ble = bglib.BGLib()
        self.ble.ble_rsp_connection_disconnect += self.disconnect_handler
        self.ble.ble_evt_gap_scan_response += self.ble_evt_gap_scan_response_handler
        self.ble.ble_evt_connection_status += self.ble_evt_connection_status_handler
        self.ble.ble_evt_attclient_group_found += self.ble_evt_attclient_group_found_handler
        self.ble.ble_evt_attclient_find_information_found += self.ble_evt_attclient_find_information_found_handler
        self.ble.ble_evt_attclient_procedure_completed += self.ble_evt_attclient_procedure_completed_handler
        self.ble.ble_evt_attclient_attribute_value += self.ble_evt_attclient_attribute_value_handler
        self.ble.debug = False
        self.peripheral_list = dict()
        self.target = None

    def send_command(self, cmd):
        self.ble.send_command(self.ser, cmd)
        self.check_activity()

    def check_activity(self, *args, **kwargs):
        self.ble.check_activity(self.ser, *args)

    def open(self):
        self.ser = serial.Serial(port=self.port, baudrate=self.baud, timeout=0.1, write_timeout=0.1)

        self.ser.flushInput()
        self.ser.flushOutput()

        # disconnect if we are connected already
        self.send_command(self.ble.ble_cmd_connection_disconnect(0))
        # stop advertising if we are advertising already
        self.send_command(self.ble.ble_cmd_gap_set_mode(0, 0))
        self.check_activity(1)

        # stop scanning if we are scanning already
        self.send_command(self.ble.ble_cmd_gap_end_procedure())
        self.check_activity(1)

    def close(self):
        """
        Disconnect and close serial port
        """
        # disconnect if we are connected already
        self.send_command(self.ble.ble_cmd_connection_disconnect(0))
        # stop advertising if we are advertising already
        self.send_command(self.ble.ble_cmd_gap_set_mode(0, 0))
        self.check_activity(1)

        # stop scanning if we are scanning already
        self.send_command(self.ble.ble_cmd_gap_end_procedure())
        self.check_activity(1)

        self.ser.close()

    def scan(self, timeout: int = 5, target: str = None):
        self.target = target

        # add handlers for BGAPI events

        # set scan parameters
        self.send_command(self.ble.ble_cmd_gap_set_scan_parameters(0xC8, 0xC8, 0))
        self.check_activity(1)

        # start scan
        self.send_command(self.ble.ble_cmd_gap_discover(1))
        self.check_activity(1)

        self.peripheral_list = dict()
        start = time.time()
        while time.time() - start < timeout:
            # check for all incoming data (no timeout, non-blocking)
            self.check_activity()

            time.sleep(0.05)
            if self.state > BleState.CONNECTING:
                # connected, return connection data
                return
            # don't burden the CPU

        return self.peripheral_list

    def connect(self, addr, address_type=1):
        # connect to this device using very fast connection parameters (7.5ms - 15ms range)
        self.send_command(self.ble.ble_cmd_gap_connect_direct(addr, address_type, 0x20, 0x30, 0x100, 0))
        self.check_activity(1)
        self.state = BleState.CONNECTING

    def disconnect_handler(self, sender, kwargs):
        print(">>disconnect", sender, kwargs)

    def ble_evt_gap_scan_response_handler(self, sender, args):
        # print(binascii.hexlify(args["sender"][::-1]), args["rssi"])
        # pull all advertised service info from ad packet
        ad_services = []
        this_field = []
        bytes_left = 0
        for b in args['data']:
            if bytes_left == 0:
                bytes_left = b
                this_field = []
            else:
                this_field.append(b)
                bytes_left = bytes_left - 1
                if bytes_left == 0:
                    if this_field[0] == 0x02 or this_field[0] == 0x03:  # partial or complete list of 16-bit UUIDs
                        for i in range((len(this_field) - 1) // 2):
                            ad_services.append(this_field[-1 - i * 2: -3 - i * 2: -1])
                    if this_field[0] == 0x04 or this_field[0] == 0x05:  # partial or complete list of 32-bit UUIDs
                        for i in range((len(this_field) - 1) // 4):
                            ad_services.append(this_field[-1 - i * 4: -5 - i * 4: -1])
                    if this_field[0] == 0x06 or this_field[0] == 0x07:  # partial or complete list of 128-bit UUIDs
                        for i in range((len(this_field) - 1) // 16):
                            ad_services.append(this_field[-1 - i * 16: -17 - i * 16: -1])

        if not args['sender'] in self.peripheral_list:
            self.peripheral_list[args['sender']] = args["rssi"]
        else:
            self.peripheral_list[args['sender']] = (args["rssi"] * 3 + self.peripheral_list[args['sender']]) / 4

        # if a target has been defined, connect
        if args['sender'] is not None and self.target is not None:
            if args['sender'] == self.target:
                print(">>>> connecting")
                # self.send_command(self.ble.ble_cmd_gap_connect_direct(addr, address_type, 0x06, 0x0C, 0x100, 0))
                self.send_command(
                    self.ble.ble_cmd_gap_connect_direct(args['sender'], args['address_type'], 0x20, 0x30, 0x100, 0))
                self.check_activity(1)
                self.state = BleState.CONNECTING
            else:
                print(args['sender'], self.target)

    def ble_evt_connection_status_handler(self, sender, args):
        if (args['flags'] & 0x05) == 0x05:
            # connected, now perform service discovery
            # print("Connected to %s" % ':'.join(['%02X' % b for b in args['address'][::-1]]))
            connection_handle = args['connection']
            # NOTE: BGLib command expects little-endian UUID byte order, so it must be reversed for using
            # NOTE2: must be put inside "list()" so that it is once again iterable
            self.send_command(self.ble.ble_cmd_attclient_read_by_group_type(args['connection'], 0x0001, 0xFFFF,
                                                                            list(reversed(uuid_service))))
            self.state = BleState.FINDING_SERVICES
            self.check_activity(1)
        pass

    def ble_evt_attclient_group_found_handler(self, sender, args):
        print("ble_evt_attclient_group_found_handler", sender, args)
        pass

    def ble_evt_attclient_find_information_found_handler(self, sender, args):
        print(sys._getframe())
        pass

    def ble_evt_attclient_procedure_completed_handler(self, sender, args):
        print(sys._getframe())
        pass

    def ble_evt_attclient_attribute_value_handler(self, sender, args):
        print(sys._getframe())
        pass

    def disconnect(self):
        self.send_command(self.ble.ble_cmd_connection_disconnect(0))
        self.check_activity(1)

    def connected(self):
        return self.state > BleState.CONNECTING


if __name__ == "__main__":
    #
    addr = b'\xbc\x98\xf6\xc6\xdfs'  # b'\x9fs9\xaf\xa7}'
    b = BLED112("/dev/ttyACM1", 115200)
    b.open()
    b.scan()
    b.scantar(addr)
    b.close()
