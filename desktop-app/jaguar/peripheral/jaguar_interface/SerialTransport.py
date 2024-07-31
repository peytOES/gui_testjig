import enum
import logging
import sys
import threading
import time
import traceback
import binascii
from PyCRC.CRCCCITT import CRCCCITT


class RXPacketType(enum.IntEnum):
    #    | RX Packet Type            | ID Number     |
    #    |---------------------------|---------------|
    #    | RX_PACKET_TYPE_NONE       | 0             |
    #    | RX_PACKET_TYPE_TEST       | 1             |
    #    | RX_PACKET_TYPE_UPDATE     | 2             |
    #    | RX_PACKET_TYPE_ACK        | 3             |
    #    | RX_PACKET_TYPE_MAX        | 4             |

    RX_PACKET_TYPE_NONE = 0
    RX_PACKET_TYPE_TEST = 1
    RX_PACKET_TYPE_UPDATE = 2
    RX_PACKET_TYPE_ACK = 3
    RX_PACKET_TYPE_VERSION = 4
    RX_PACKET_TYPE_MAX = 5


class TXPacketType(enum.IntEnum):
    #    | TX Packet Type            | ID Number     |
    #    |---------------------------|---------------|
    #    | TX_PACKET_TYPE_NONE       | 0             |
    #    | TX_PACKET_TYPE_TEST       | 1             |
    #    | TX_PACKET_TYPE_GPIO       | 2             |
    #    | TX_PACKET_TYPE_DAC        | 3             |
    #    | TX_PACKET_TYPE_LED        | 4             |
    #    | TX_PACKET_TYPE_MAX        | 5             |

    TX_PACKET_TYPE_NONE = 0
    TX_PACKET_TYPE_TEST = 1
    TX_PACKET_TYPE_GPIO = 2
    TX_PACKET_TYPE_DAC = 3
    TX_PACKET_TYPE_LED = 4
    TX_PACKET_TYPE_VERSION = 5
    TX_PACKET_TYPE_MAX = 6


class RXPacketState(enum.IntEnum):
    PACKET_STATE_WAIT_FOR_SOF = 1
    PACKET_STATE_WAIT_FOR_DELIMITER = 2
    PACKET_STATE_WAIT_FOR_LENGTH = 3
    PACKET_STATE_WAIT_FOR_PACKET_TYPE = 4
    PACKET_STATE_WAIT_FOR_CRC = 5
    PACKET_STATE_WAIT_FOR_PAYLOAD = 6


class Transport(object):
    # Packet Offsets
    PACKET_DELIMITER_OFFSET = 0  # uint32_t 4 bytes
    PACKET_LENGTH_OFFSET = 4  # uint8_t  1 bytes
    PACKET_TYPE_OFFSET = 5  # uint8_t  1 bytes
    PACKET_CRC_OFFSET = 6  # uint16_t 2 bytes
    PACKET_PAYLOAD_OFFSET = 8  # variable length

    PACKET_LEN_HEADER = 8
    MAX_PACKET_LEN = 0xFF
    PACKET_SOF = 0x78
    PACKET_DELIMITER = 0x12345678

    # RX Packet Offsets
    RX_PAYLOAD_VERSION_OFFSET = 0  # uint8_t  1 bytes
    RX_PAYLOAD_COUNTER_OFFSET = 1  # uint8_t  1 bytes

    RX_PAYLOAD_GPIO_INPUTS_OFFSET = 2  # uint16_t  2 bytes
    RX_PAYLOAD_GPIO_OUTPUTS_OFFSET = 4  # uint32_t  4 bytes

    RX_PAYLOAD_ADC1_OFFSET = 8  # uint16_t  2 bytes
    RX_PAYLOAD_ADC2_OFFSET = 10  # uint16_t  2 bytes
    RX_PAYLOAD_ADC3_OFFSET = 12  # uint16_t  2 bytes
    RX_PAYLOAD_ADC4_OFFSET = 14  # uint16_t  2 bytes
    RX_PAYLOAD_ADC5_OFFSET = 16  # uint16_t  2 bytes
    RX_PAYLOAD_ADC6_OFFSET = 18  # uint16_t  2 bytes
    RX_PAYLOAD_ADC7_OFFSET = 20  # uint16_t  2 bytes
    RX_PAYLOAD_ADC8_OFFSET = 22  # uint16_t  2 bytes

    RX_PAYLOAD_DAC1_OFFSET = 24  # uint32_t  4 bytes
    RX_PAYLOAD_DAC2_OFFSET = 28  # uint32_t  4 bytes

    RX_PAYLOAD_LED_OFFSET = 32  # uint8_t   1 byte


class SerialTransport(Transport):

    def __init__(self, serObj=None, rx_callback=None, logger=None):

        # Fetch threaded serial port object
        self.serObj = serObj

        # Handle self.logger argument defaulting
        if logger is None:
            self.logger = logging.getLogger(self.__class__.__name__)
        elif not hasattr(logger, "getChild"):
            self.logger = logger
        else:
            self.logger = logger.getChild(self.__class__.__name__)

        # Define filter chain + endpoints
        self.serObj.register_callback(self.receive_cb)

        # Define RX callback
        self.rx_callback = rx_callback

        # Set up variables
        self.cv = threading.Condition()
        self.packet_state = RXPacketState.PACKET_STATE_WAIT_FOR_SOF
        self.packet_rx_len = 0
        self.packet_rx_buf = bytes()

    def generate_header(self, packetType, bytePayload):

        self.logger.debug(
            "%s - %s: bytePayload = %s" % (self.__class__.__name__, self.generate_header.__name__, bytePayload))

        # Packet Header Structure
        # [start-of-packet-delimiter]   - uint32_t, 4 bytes
        # [length]                      - uint8_t,  1 byte
        # [packet-type]                 - uint8_t   1 byte
        # [crc]                         - uint16_t, 2 bytes
        # [payload]                     - sequence of data bytes, number == [length]

        # Generate hex strings for different components of header
        strDelimiter = self.PACKET_DELIMITER.to_bytes(4, byteorder='little')
        strLength = len(bytePayload).to_bytes(1, byteorder='little')
        strType = packetType.to_bytes(1, byteorder='little')
        strCRC = (CRCCCITT(version="FFFF").calculate(bytePayload)).to_bytes(2, byteorder='little')

        strHeader = strDelimiter + strLength + strType + strCRC
        self.logger.debug(
            "%s - %s: header = %s" % (self.__class__.__name__, self.generate_header.__name__, strHeader.hex()))

        return strHeader

    def transmit_packet(self, packetType, bytePayload):

        self.logger.debug(
            "%s - %s: bytePayload = %s" % (self.__class__.__name__, self.transmit_packet.__name__, bytePayload.hex()))

        # Check arguments
        if (packetType == TXPacketType.TX_PACKET_TYPE_NONE) or (packetType >= TXPacketType.TX_PACKET_TYPE_MAX):
            logger.error("%s - %s: Packet type ERROR" % (self.__class__.__name__, self.transmit_packet.__name__))
            return False

        if (len(bytePayload) >= self.MAX_PACKET_LEN):
            logger.error("%s - %s: Payload length ERROR" % (self.__class__.__name__, self.transmit_packet.__name__))
            return False

        # Generate the packet
        txHeader = self.generate_header(packetType, bytePayload)
        txPacket = txHeader + bytePayload

        self.logger.info("%s - %s: txPacket = %s" % (self.__class__.__name__, self.transmit_packet.__name__, txPacket))
        self.serObj.write(txPacket)

        return True

    def receive_cb(self, data):

        self.logger.debug("%s - %s: data = %s" % (self.__class__.__name__, self.receive_cb.__name__, data.hex()))

        # Move data to local buffer
        self.packet_rx_buf += data
        self.packet_rx_len += len(data)

        if self.packet_state == RXPacketState.PACKET_STATE_WAIT_FOR_SOF:
            self.packetType = RXPacketType.RX_PACKET_TYPE_NONE
            if (self.packet_rx_len >= 1):

                packetSOF = self.packet_rx_buf[0]

                if (packetSOF == self.PACKET_SOF):
                    self.packet_state = RXPacketState.PACKET_STATE_WAIT_FOR_DELIMITER
                else:
                    self.packet_state = RXPacketState.PACKET_STATE_WAIT_FOR_SOF
                    self.packet_rx_buf = bytes()
                    self.packet_rx_len = 0

        if self.packet_state == RXPacketState.PACKET_STATE_WAIT_FOR_DELIMITER:
            if (self.packet_rx_len >= 4):

                packetDelimiter = (self.packet_rx_buf[3] << 24) | (self.packet_rx_buf[2] << 16) | (
                            self.packet_rx_buf[1] << 8) | self.packet_rx_buf[0]

                if (packetDelimiter == self.PACKET_DELIMITER):
                    self.packet_state = RXPacketState.PACKET_STATE_WAIT_FOR_LENGTH
                else:
                    self.packet_state = RXPacketState.PACKET_STATE_WAIT_FOR_SOF
                    self.packet_rx_buf = bytes()
                    self.packet_rx_len = 0

        if self.packet_state == RXPacketState.PACKET_STATE_WAIT_FOR_LENGTH:
            if (self.packet_rx_len >= 5):

                packetLength = self.packet_rx_buf[4]

                if (packetLength > 0 and packetLength <= (self.MAX_PACKET_LEN - self.PACKET_LEN_HEADER)):
                    self.packet_state = RXPacketState.PACKET_STATE_WAIT_FOR_PACKET_TYPE
                else:
                    self.packet_state = RXPacketState.PACKET_STATE_WAIT_FOR_SOF
                    self.packet_rx_buf = bytes()
                    self.packet_rx_len = 0

        if self.packet_state == RXPacketState.PACKET_STATE_WAIT_FOR_PACKET_TYPE:
            if (self.packet_rx_len >= 6):

                self.packetType = self.packet_rx_buf[5]

                if (
                        self.packetType > RXPacketType.RX_PACKET_TYPE_NONE and self.packetType < RXPacketType.RX_PACKET_TYPE_MAX):
                    self.packet_state = RXPacketState.PACKET_STATE_WAIT_FOR_CRC
                else:
                    self.packet_state = RXPacketState.PACKET_STATE_WAIT_FOR_SOF
                    self.packet_rx_buf = bytes()
                    self.packet_rx_len = 0

        if self.packet_state == RXPacketState.PACKET_STATE_WAIT_FOR_CRC:
            if (self.packet_rx_len >= 8):
                self.packet_state = RXPacketState.PACKET_STATE_WAIT_FOR_PAYLOAD

        if self.packet_state == RXPacketState.PACKET_STATE_WAIT_FOR_PAYLOAD:
            packetLength = self.packet_rx_buf[4]

            if (self.packet_rx_len >= (self.PACKET_LEN_HEADER + packetLength)):

                result = self.decode_header(self.packet_rx_buf)
                if result == True:
                    # If required, use self.PACKET_type to determine next method call
                    # Fire RX callback to update Jaguar Fixture instance
                    try:
                        self.rx_callback(self.packetType, self.packet_rx_buf[self.PACKET_PAYLOAD_OFFSET:])
                    except:
                        exc_type, exc_value, exc_trace = sys.exc_info()
                        self.logger.error("%s: Exception %s %s Traceback : %s" % (
                        self.__class__.__name__, exc_type, exc_value, repr(traceback.extract_tb(exc_trace))))

                # Reset state to receive next packet
                self.packet_state = RXPacketState.PACKET_STATE_WAIT_FOR_SOF
                self.packet_rx_buf = bytes()
                self.packet_rx_len = 0

        with self.cv:
            self.cv.notify_all()

    def decode_header(self, rxPacket):

        self.logger.debug("%s - %s: rxPacket = %s, rxPacket length = %d" % (
        self.__class__.__name__, self.decode_header.__name__, rxPacket.hex(), len(rxPacket)))
        # print(binascii.hexlify(rxPacket))
        # Validate that we received a full header
        if len(rxPacket) < self.PACKET_PAYLOAD_OFFSET:
            self.logger.error("%s - %s: Header length ERROR" % (self.__class__.__name__, self.decode_header.__name__))
            return False

        # Packet Header Structure
        # [start-of-packet-delimiter]   - uint32_t, 4 bytes
        # [length]                      - uint8_t,  1 byte
        # [packet-type]                 - uint8_t   1 byte
        # [crc]                         - uint16_t, 2 bytes
        # [payload]                     - sequence of data bytes, number == [length]

        packetDelimiter = (rxPacket[3] << 24) | (rxPacket[2] << 16) | (rxPacket[1] << 8) | rxPacket[0]
        packetLength = rxPacket[4]
        packetType = rxPacket[5]
        packetCRC = (rxPacket[7] << 8) | rxPacket[6]
        packetPayload = rxPacket[self.PACKET_PAYLOAD_OFFSET:]

        # Validate delimiter, length, packet type and CRC
        if (packetDelimiter != self.PACKET_DELIMITER):
            self.logger.error("%s - %s: Frame delimiter ERROR" % (self.__class__.__name__, self.decode_header.__name__))
            return False

        expectLen = len(packetPayload)
        if (packetLength != expectLen) or (packetLength < 0) or (
                packetLength > (self.MAX_PACKET_LEN - self.PACKET_LEN_HEADER)):
            self.logger.error(
                "%s - %s: Frame payload length ERROR" % (self.__class__.__name__, self.decode_header.__name__))
            return False

        if (packetType == RXPacketType.RX_PACKET_TYPE_NONE) or (packetType >= RXPacketType.RX_PACKET_TYPE_MAX):
            self.logger.error("%s - %s: Frame type ERROR" % (self.__class__.__name__, self.decode_header.__name__))
            return False

        expectCrc = CRCCCITT(version="FFFF").calculate(packetPayload)
        if (packetCRC != expectCrc):
            self.logger.error("%s - %s: Frame CRC ERROR" % (self.__class__.__name__, self.decode_header.__name__))
            return False

        return True
