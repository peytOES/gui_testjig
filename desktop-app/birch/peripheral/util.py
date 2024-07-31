"""
Utility function to find a port
"""
import logging

import serial.tools.list_ports as list_ports


def find_port(vid: str = None, pid: str = None, port_name: str = None):
    event_logger = logging.getLogger("event_logger")

    ports = list_ports.comports()
    if port_name:
        for p in ports:
            if p.device.lower() == port_name.lower():
                event_logger.info("find_port: vid: %s pid: %s port_name %s found" % (vid, pid, port_name))
                return port_name

    if vid is not None and pid is not None:
        for p in ports:
            if p.vid is None or p.pid is None:
                continue
            # print("%04x"%p.vid, "%04x"%p.pid, p.device)
            str_vid = "%04x" % p.vid
            str_pid = "%04x" % p.pid
            # print(repr(str_vid), repr(vid), repr(str_pid), repr(pid), p.device)
            # print(str_vid ==  vid, str_pid == pid)
            if str_vid == vid and str_pid == pid:
                event_logger.info("find_port: vid: %s pid: %s port_name %s found: %s" % (vid, pid, port_name, p.device))
                return p.device

    event_logger.info("find_port: vid: %s pid: %s port_name %s not found" % (vid, pid, port_name))
    return None


if __name__ == "__main__":
    test_ports = [
        # {"port_name": "/dev/ttyUSB0"},
        # {"port_name": "/dev/ttyUSB1"},
        {"vid": "2458", "pid": "0001"},
        # {"vid": "067b", "pid": "2303"},
        # {"vid": "067c", "pid": "2303"},
        # {"vid": "067b", "pid": "230c"},
        # {"vid": "067b"}
    ]
    for p in test_ports:
        print(p, find_port(**p))
