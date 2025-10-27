# Imports
import logging
import socket
import sys
import array
import serial
import argparse
import datetime
import time
import enum

from .SerialTransport import *
from .JaguarLogger import JaguarLogger


class JaguarFixtureLED(enum.IntEnum):
    #    | LED Number                | ID Number     |
    #    |---------------------------|---------------|
    #    | LED_NONE                  | 0             |
    #    | LED_BUSY                  | 1             |
    #    | LED_PASS                  | 2             |
    #    | LED_FAIL                  | 3             |
    #    | LED_MAX                   | 4             |

    LED_NONE = 0
    LED_BUSY = 1
    LED_PASS = 2
    LED_FAIL = 3
    LED_MAX = 4


class JaguarFixtureGPIOInput(enum.IntEnum):
    #    | GPIO Number               | ID Number     |
    #    |---------------------------|---------------|
    #    | GPIO_INPUT_NONE           | 0             |
    #    | GPIO_INPUT_DIG_OUT_RTN_0  | 1             |
    #    | GPIO_INPUT_DIG_OUT_RTN_1  | 2             |
    #    | GPIO_INPUT_DIG_OUT_RTN_2  | 3             |
    #    | GPIO_INPUT_DIG_OUT_RTN_3  | 4             |
    #    | GPIO_INPUT_SWITCH_0       | 5             |
    #    | GPIO_INPUT_SWITCH_1       | 6             |
    #    | GPIO_INPUT_SWITCH_2       | 7             |
    #    | GPIO_INPUT_SWITCH_3       | 8             |
    #    | GPIO_INPUT_DUT_DETECT     | 9             |
    #    | GPIO_INPUT_LID_DETECT     | 10            |
    #    | GPIO_INPUT_DC_STATUS      | 11            |
    #    | GPIO_INPUT_3V8_STATUS     | 12            |
    #    | GPIO_INPUT_DIG_OUT_FAULT  | 13            |
    #    | GPIO_INPUT_MAX            | 14            |

    GPIO_INPUT_NONE = 0
    GPIO_INPUT_DIG_OUT_RTN_0 = 1
    GPIO_INPUT_DIG_OUT_RTN_1 = 2
    GPIO_INPUT_DIG_OUT_RTN_2 = 3
    GPIO_INPUT_DIG_OUT_RTN_3 = 4
    GPIO_INPUT_SWITCH_0 = 5
    GPIO_INPUT_SWITCH_1 = 6
    GPIO_INPUT_SWITCH_2 = 7
    GPIO_INPUT_SWITCH_3 = 8
    GPIO_INPUT_DUT_DETECT = 9
    GPIO_INPUT_LID_DETECT = 10
    GPIO_INPUT_DC_STATUS = 11
    GPIO_INPUT_3V8_STATUS = 12
    GPIO_INPUT_DIG_OUT_FAULT = 13
    GPIO_INPUT_MAX = 14


class JaguarFixtureGPIOOutput(enum.IntEnum):
    #    | GPIO Number               | ID Number     |
    #    |---------------------------|---------------|
    #    | GPIO_OUTPUT_NONE          | 0             |
    #    | GPIO_OUTPUT_DIG_IN_0      | 1             |
    #    | GPIO_OUTPUT_DIG_IN_1      | 2             |
    #    | GPIO_OUTPUT_FIXTURE_DETECT| 3             |
    #    | GPIO_OUTPUT_EN_3V8        | 4             |
    #    | GPIO_OUTPUT_DC_EN         | 5             |
    #    | GPIO_OUTPUT_USB_EN        | 6             |
    #    | GPIO_OUTPUT_DIG_OUT_PWR   | 7             |
    #    | GPIO_OUTPUT_RS232_EN      | 8             |
    #    | GPIO_OUTPUT_JTAG_EN       | 9             |
    #    | GPIO_OUTPUT_4_20_PWR      | 10            |
    #    | GPIO_OUTPUT_DUT_RST       | 11            |
    #    | GPIO_OUTPUT_GPIO_EN       | 12            |
    #    | GPIO_OUTPUT_ANALOG_EN     | 13            |
    #    | GPIO_OUTPUT_CAL_LOAD_0    | 14            |
    #    | GPIO_OUTPUT_CAL_LOAD_1    | 15            |
    #    | GPIO_OUTPUT_CAL_LOAD_2    | 16            |
    #    | GPIO_OUTPUT_CAL_LOAD_3    | 17            |
    #    | GPIO_OUTPUT_CAL_LOAD_4    | 18            |
    #    | GPIO_OUTPUT_MAG_0         | 19            |
    #    | GPIO_OUTPUT_MAG_1         | 20            |
    #    | GPIO_OUTPUT_LFP_0         | 21            |
    #    | GPIO_OUTPUT_LFP_1         | 22            |
    #    | GPIO_OUTPUT_MAX           | 23            |

    GPIO_OUTPUT_NONE = 0
    GPIO_OUTPUT_DIG_IN_0 = 1
    GPIO_OUTPUT_DIG_IN_1 = 2
    GPIO_OUTPUT_FIXTURE_DETECT = 3
    GPIO_OUTPUT_EN_3V8 = 4
    GPIO_OUTPUT_DC_EN = 5
    GPIO_OUTPUT_USB_EN = 6
    GPIO_OUTPUT_DIG_OUT_PWR = 7
    GPIO_OUTPUT_RS232_EN = 8
    GPIO_OUTPUT_JTAG_EN = 9
    GPIO_OUTPUT_4_20_PWR = 10
    GPIO_OUTPUT_DUT_RST = 11
    GPIO_OUTPUT_GPIO_EN = 12
    GPIO_OUTPUT_ANALOG_EN = 13
    GPIO_OUTPUT_CAL_LOAD_0 = 14
    GPIO_OUTPUT_CAL_LOAD_1 = 15
    GPIO_OUTPUT_CAL_LOAD_2 = 16
    GPIO_OUTPUT_CAL_LOAD_3 = 17
    GPIO_OUTPUT_CAL_LOAD_4 = 18
    GPIO_OUTPUT_MAG_0 = 19
    GPIO_OUTPUT_MAG_1 = 20
    GPIO_OUTPUT_LFP_0 = 21
    GPIO_OUTPUT_LFP_1 = 22
    GPIO_OUTPUT_MAX = 23


class JaguarFixtureADC(enum.IntEnum):
    #    | ADC Number                | ID Number     |
    #    |---------------------------|---------------|
    #    | ADC_NONE                  | 0             |
    #    | ADC_BATT_CURRENT          | 1             |
    #    | ADC_DC_CURRENT            | 2             |
    #    | ADC_BATT_VOLTAGE          | 3             |
    #    | ADC_DC_VOLTAGE            | 4             |
    #    | ADC_VMDM                  | 5             |
    #    | ADC_SYS_VOLTAGE           | 6             |
    
    #    | ADC_4_20_CH0              | 7             |
    #    | ADC_4_20_CH1              | 8             |
    #    | ADC_MAX                   | 9             |

    ADC_NONE = 0
    ADC_BATT_CURRENT = 1
    ADC_DC_CURRENT = 2
    ADC_BATT_VOLTAGE = 3
    ADC_DC_VOLTAGE = 4
    ADC_VMDM = 5
    ADC_SYS_VOLTAGE = 6
    ADC_4_20_CH0 = 7
    ADC_4_20_CH1 = 8
    ADC_MAX = 9


class JaguarFixtureDAC(enum.IntEnum):
    #    | DAC Number                | ID Number     |
    #    |---------------------------|---------------|
    #    | DAC_NONE                  | 0             |
    #    | DAC_1                     | 1             |
    #    | DAC_2                     | 2             |
    #    | DAC_MAX                   | 3             |

    DAC_NONE = 0
    DAC_1 = 1
    DAC_2 = 2
    DAC_MAX = 3


class JaguarFixture(object):

    def __init__(self, serObj=None, logger=None):

        # Handle self.logger argument defaulting
        if logger is None:
            self.logger = logging.getLogger(self.__class__.__name__)
        elif not hasattr(logger, "getChild"):
            self.logger = logger
        else:
            self.logger = logger.getChild(self.__class__.__name__)

        # Create serial transport object
        self.serial_transport = SerialTransport(serObj=serObj, rx_callback=self.parse_payload)
        if self.serial_transport is None:
            self.logger.error("%s - %s Setup failed, please restart..." % self.__class__.__name__,
                              self.__init__.__name__)

        # packet type function map for received packets
        self.rx_map = {
            RXPacketType.RX_PACKET_TYPE_TEST: None,
            RXPacketType.RX_PACKET_TYPE_UPDATE: self.rx_type_update,
            RXPacketType.RX_PACKET_TYPE_ACK: self.rx_type_ack,
            RXPacketType.RX_PACKET_TYPE_VERSION: self.rx_type_version,
        }

        # State Variables
        self.fw_version = ""
        self.version = 0

        # Input GPIOs (true = On)
        self.gpio_input_dig_out_rtn_0 = False
        self.gpio_input_dig_out_rtn_1 = False
        self.gpio_input_dig_out_rtn_2 = False
        self.gpio_input_dig_out_rtn_3 = False
        self.gpio_input_switch_0 = False
        self.gpio_input_switch_1 = False
        self.gpio_input_switch_2 = False
        self.gpio_input_switch_3 = False
        self.gpio_input_dut_detect = False
        self.gpio_input_lid_detect = False
        self.gpio_input_dc_status = False
        self.gpio_input_3v8_status = False
        self.gpio_input_dig_out_fault = False

        # Output GPIOs (true = High)
        self.gpio_output_dig_in_0 = False
        self.gpio_output_dig_in_1 = False
        self.gpio_output_fixture_detect = False
        self.gpio_output_en_3v8 = False
        self.gpio_output_dc_en = False
        self.gpio_output_usb_en = False
        self.gpio_output_dig_out_pwr = False
        self.gpio_output_rs232_en = False
        self.gpio_output_jtag_en = False
        self.gpio_output_4_20_pwr = False
        self.gpio_output_dut_rst = False
        self.gpio_output_gpio_en = False
        self.gpio_output_analog_en = False
        self.gpio_output_cal_load_0 = False
        self.gpio_output_cal_load_1 = False
        self.gpio_output_cal_load_2 = False
        self.gpio_output_cal_load_3 = False
        self.gpio_output_cal_load_4 = False
        self.gpio_output_mag_0 = False
        self.gpio_output_mag_1 = False
        self.gpio_output_lfp_0 = False
        self.gpio_output_lfp_1 = False

        # DACs
        self.dac_1 = 0
        self.dac_2 = 0

        # ADCs
        self.adc_batt_current = 0
        self.adc_dc_current = 0
        self.adc_batt_voltage = 0
        self.adc_dc_voltage = 0
        self.adc_vmdm = 0
        self.adc_sys_voltage = 0
        self.adc_4_20_ch0 = 0
        self.adc_4_20_ch1 = 0

        # LEDs (true = On)
        self.led_busy = False
        self.led_pass = False
        self.led_fail = False

    def set_gpio(self, gpio, value):
        self.logger.debug("=== Setting GPIO Pin ===")

        # Check arguments
        if (gpio == JaguarFixtureGPIOOutput.GPIO_OUTPUT_NONE) or (gpio >= JaguarFixtureGPIOOutput.GPIO_OUTPUT_MAX):
            self.logger.error("%s - %s: Invalid argument" % (self.__class__.__name__, self.set_gpio.__name__))
            return False

        # Packet Payload Structure
        # [header]                         - 8 bytes generated in Serial Transport Layer
        # [gpio_pin]                       - uint32_t, 4 bytes
        # [pin_value]                      - uint8_t,  1 byte
        gpio_pin = gpio.to_bytes(4, byteorder='little')
        pin_value = value.to_bytes(1, byteorder='little')
        payload = gpio_pin + pin_value

        # Send packet
        result = self.serial_transport.transmit_packet(TXPacketType.TX_PACKET_TYPE_GPIO, payload)
        if result == False:
            self.logger.error("%s - %s: Transmit Packet ERROR" % (self.__class__.__name__, self.set_gpio.__name__))
            return False

        self.logger.info("%s - %s: GPIO %s = %d" % (self.__class__.__name__, self.set_gpio.__name__, gpio, value))

        return True

    def set_dac(self, dac, value):

        self.logger.debug("=== Setting DAC Value ===")

        # Check arguments
        if (dac == JaguarFixtureDAC.DAC_NONE) or (dac >= JaguarFixtureDAC.DAC_MAX):
            self.logger.error("%s - %s: Invalid argument" % (self.__class__.__name__, self.set_dac.__name__))
            return False
        if (value > 255):
            return False

        # Packet Payload Structure
        # [header]                         - 8 bytes generated in Serial Transport Layer
        # [dac_pin]                        - uint8_t, 1 byte
        # [dac_value]                      - uint32_t, 4 bytes (only using 8 bits)
        dac_pin = dac.to_bytes(1, byteorder='little')
        dac_value = value.to_bytes(4, byteorder='little')
        payload = dac_pin + dac_value

        # Send packet
        result = self.serial_transport.transmit_packet(TXPacketType.TX_PACKET_TYPE_DAC, payload)
        if result == False:
            self.logger.error("%s - %s: Transmit Packet ERROR" % (self.__class__.__name__, self.set_dac.__name__))
            return False

        self.logger.info("%s - %s: DAC %s = %d" % (self.__class__.__name__, self.set_dac.__name__, dac, value))

        return True

    def set_led(self, led, value):

        self.logger.debug("=== Setting Led ===")

        # Check arguments
        if (led == JaguarFixtureLED.LED_NONE) or (led >= JaguarFixtureLED.LED_MAX):
            self.logger.error("%s - %s: Invalid argument" % (self.__class__.__name__, self.set_led.__name__))
            return False

        # Packet Payload Structure
        # [header]                         - 8 bytes generated in Serial Transport Layer
        # [led_pin]                        - uint8_t, 1 byte
        # [led_value]                      - uint8_t, 1 byte
        led_pin = led.to_bytes(1, byteorder='little')
        led_value = value.to_bytes(1, byteorder='little')
        payload = led_pin + led_value

        # Send packet
        result = self.serial_transport.transmit_packet(TXPacketType.TX_PACKET_TYPE_LED, payload)
        if result == False:
            self.logger.error("%s - %s: Transmit Packet ERROR" % (self.__class__.__name__, self.set_led.__name__))
            return False

        self.logger.info("%s - %s: LED %s = %d" % (self.__class__.__name__, self.set_led.__name__, led, value))

        return True

    def get_fw_version(self):
        result = self.serial_transport.transmit_packet(TXPacketType.TX_PACKET_TYPE_VERSION, b"\x00")
        if result == False:
            self.logger.error("%s - %s: Transmit Packet ERROR" % (self.__class__.__name__, self.set_led.__name__))
            return False
        return True

    def parse_payload(self, packetType, rxPayload):
        if packetType not in self.rx_map.keys():
            self.logger.error("Unhandled packet type %d" % packetType)
            return

        if self.rx_map[packetType] is not None:
            self.rx_map[packetType](rxPayload)

    def rx_type_echo(self, rxPayload):
        pass

    def rx_type_version(self, rxPayload):
        print("rx_type_version %s" % rxPayload)
        self.fw_version = rxPayload
        pass

    def rx_type_ack(self, rxPayload):
        pass

    def rx_type_update(self, rxPayload):
        self.logger.debug("%s - %s: %s" % (self.__class__.__name__, self.parse_payload.__name__, rxPayload.hex()))

        # Version
        self.version = int.from_bytes(
            rxPayload[Transport.RX_PAYLOAD_VERSION_OFFSET:Transport.RX_PAYLOAD_COUNTER_OFFSET], byteorder='little')
        self.counter = int.from_bytes(
            rxPayload[Transport.RX_PAYLOAD_COUNTER_OFFSET:Transport.RX_PAYLOAD_GPIO_INPUTS_OFFSET], byteorder='little')

        # GPIO Inputs
        gpio_inputs = int.from_bytes(
            rxPayload[Transport.RX_PAYLOAD_GPIO_INPUTS_OFFSET:Transport.RX_PAYLOAD_GPIO_OUTPUTS_OFFSET],
            byteorder='little')
        self.gpio_input_dig_out_rtn_0 = (bool)(gpio_inputs & (1 << 0))
        self.gpio_input_dig_out_rtn_1 = (bool)(gpio_inputs & (1 << 1))
        self.gpio_input_dig_out_rtn_2 = (bool)(gpio_inputs & (1 << 2))
        self.gpio_input_dig_out_rtn_3 = (bool)(gpio_inputs & (1 << 3))
        self.gpio_input_switch_0 = (bool)(gpio_inputs & (1 << 4))
        self.gpio_input_switch_1 = (bool)(gpio_inputs & (1 << 5))
        self.gpio_input_switch_2 = (bool)(gpio_inputs & (1 << 6))
        self.gpio_input_switch_3 = (bool)(gpio_inputs & (1 << 7))
        self.gpio_input_dut_detect = (bool)(gpio_inputs & (1 << 8))
        self.gpio_input_lid_detect = (bool)(gpio_inputs & (1 << 9))
        self.gpio_input_dc_status = (bool)(gpio_inputs & (1 << 10))
        self.gpio_input_3v8_status = (bool)(gpio_inputs & (1 << 11))
        self.gpio_input_dig_out_fault = (bool)(gpio_inputs & (1 << 12))

        # GPIO Outputs
        gpio_outputs = int.from_bytes(
            rxPayload[Transport.RX_PAYLOAD_GPIO_OUTPUTS_OFFSET:Transport.RX_PAYLOAD_ADC1_OFFSET], byteorder='little')
        self.gpio_output_dig_in_0 = (bool)(gpio_outputs & (1 << 0))
        self.gpio_output_dig_in_1 = (bool)(gpio_outputs & (1 << 1))
        self.gpio_output_fixture_detect = (bool)(gpio_outputs & (1 << 2))
        self.gpio_output_en_3v8 = (bool)(gpio_outputs & (1 << 3))
        self.gpio_output_dc_en = (bool)(gpio_outputs & (1 << 4))
        self.gpio_output_usb_en = (bool)(gpio_outputs & (1 << 5))
        self.gpio_output_dig_out_pwr = (bool)(gpio_outputs & (1 << 6))
        self.gpio_output_rs232_en = (bool)(gpio_outputs & (1 << 7))
        self.gpio_output_jtag_en = (bool)(gpio_outputs & (1 << 8))
        self.gpio_output_4_20_pwr = (bool)(gpio_outputs & (1 << 9))
        self.gpio_output_dut_rst = (bool)(gpio_outputs & (1 << 10))
        self.gpio_output_gpio_en = (bool)(gpio_outputs & (1 << 11))
        self.gpio_output_analog_en = (bool)(gpio_outputs & (1 << 12))
        self.gpio_output_cal_load_0 = (bool)(gpio_outputs & (1 << 13))
        self.gpio_output_cal_load_1 = (bool)(gpio_outputs & (1 << 14))
        self.gpio_output_cal_load_2 = (bool)(gpio_outputs & (1 << 15))
        self.gpio_output_cal_load_3 = (bool)(gpio_outputs & (1 << 16))
        self.gpio_output_cal_load_4 = (bool)(gpio_outputs & (1 << 17))
        self.gpio_output_mag_0 = (bool)(gpio_outputs & (1 << 18))
        self.gpio_output_mag_1 = (bool)(gpio_outputs & (1 << 19))
        self.gpio_output_lfp_0 = (bool)(gpio_outputs & (1 << 20))
        self.gpio_output_lfp_1 = (bool)(gpio_outputs & (1 << 21))

        # ADC - convert to pin voltage
        self.adc_batt_current = int.from_bytes(
            rxPayload[Transport.RX_PAYLOAD_ADC1_OFFSET:Transport.RX_PAYLOAD_ADC2_OFFSET],
            byteorder='little') / 4096 * 3.3
        self.adc_dc_current = int.from_bytes(
            rxPayload[Transport.RX_PAYLOAD_ADC2_OFFSET:Transport.RX_PAYLOAD_ADC3_OFFSET],
            byteorder='little') / 4096 * 3.3
        self.adc_batt_voltage = int.from_bytes(
            rxPayload[Transport.RX_PAYLOAD_ADC3_OFFSET:Transport.RX_PAYLOAD_ADC4_OFFSET],
            byteorder='little') / 4096 * 3.3
        self.adc_dc_voltage = int.from_bytes(
            rxPayload[Transport.RX_PAYLOAD_ADC4_OFFSET:Transport.RX_PAYLOAD_ADC5_OFFSET],
            byteorder='little') / 4096 * 3.3
        self.adc_vmdm = int.from_bytes(rxPayload[Transport.RX_PAYLOAD_ADC5_OFFSET:Transport.RX_PAYLOAD_ADC6_OFFSET],
                                       byteorder='little') / 4096 * 3.3
        self.adc_sys_voltage = int.from_bytes(
            rxPayload[Transport.RX_PAYLOAD_ADC6_OFFSET:Transport.RX_PAYLOAD_ADC7_OFFSET],
            byteorder='little') / 4096 * 3.3
        self.adc_4_20_ch0 = int.from_bytes(rxPayload[Transport.RX_PAYLOAD_ADC7_OFFSET:Transport.RX_PAYLOAD_ADC8_OFFSET],
                                           byteorder='little') / 4096 * 3.3
        self.adc_4_20_ch1 = int.from_bytes(rxPayload[Transport.RX_PAYLOAD_ADC8_OFFSET:Transport.RX_PAYLOAD_DAC1_OFFSET],
                                           byteorder='little') / 4096 * 3.3

        # DACs
        self.dac_1 = int.from_bytes(rxPayload[Transport.RX_PAYLOAD_DAC1_OFFSET:Transport.RX_PAYLOAD_DAC2_OFFSET],
                                    byteorder='little')
        self.dac_2 = int.from_bytes(rxPayload[Transport.RX_PAYLOAD_DAC2_OFFSET:Transport.RX_PAYLOAD_LED_OFFSET],
                                    byteorder='little')

        # LEDs
        led = int.from_bytes(rxPayload[Transport.RX_PAYLOAD_LED_OFFSET:Transport.RX_PAYLOAD_LED_OFFSET + 1],
                             byteorder='little')
        self.led_busy = (bool)(led & (1 << 0))
        self.led_pass = (bool)(led & (1 << 1))
        self.led_fail = (bool)(led & (1 << 2))
        self.print_state()

    def print_state(self):

        self.logger.info("%s - %s: Version                      | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.version))

        self.logger.info("%s - %s: gpio_input_dig_out_rtn_0     | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_dig_out_rtn_0))
        self.logger.info("%s - %s: gpio_input_dig_out_rtn_1     | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_dig_out_rtn_1))
        self.logger.info("%s - %s: gpio_input_dig_out_rtn_2     | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_dig_out_rtn_2))
        self.logger.info("%s - %s: gpio_input_dig_out_rtn_3     | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_dig_out_rtn_3))
        self.logger.info("%s - %s: gpio_input_switch_0          | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_switch_0))
        self.logger.info("%s - %s: gpio_input_switch_1          | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_switch_1))
        self.logger.info("%s - %s: gpio_input_switch_2          | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_switch_2))
        self.logger.info("%s - %s: gpio_input_switch_3          | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_switch_3))
        self.logger.info("%s - %s: gpio_input_dut_detect        | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_dut_detect))
        self.logger.info("%s - %s: gpio_input_lid_detect        | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_lid_detect))
        self.logger.info("%s - %s: gpio_input_dc_status         | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_dc_status))
        self.logger.info("%s - %s: gpio_input_3v8_status        | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_3v8_status))
        self.logger.info("%s - %s: gpio_input_dig_out_fault     | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_input_dig_out_fault))

        self.logger.info("%s - %s: gpio_output_dig_in_0         | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_dig_in_0))
        self.logger.info("%s - %s: gpio_output_dig_in_1         | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_dig_in_1))
        self.logger.info("%s - %s: gpio_output_fixture_detect   | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_fixture_detect))
        self.logger.info("%s - %s: gpio_output_en_3v8           | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_en_3v8))
        self.logger.info("%s - %s: gpio_output_dc_en            | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_dc_en))
        self.logger.info("%s - %s: gpio_output_usb_en           | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_usb_en))
        self.logger.info("%s - %s: gpio_output_dig_out_pwr      | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_dig_out_pwr))
        self.logger.info("%s - %s: gpio_output_rs232_en         | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_rs232_en))
        self.logger.info("%s - %s: gpio_output_jtag_en          | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_jtag_en))
        self.logger.info("%s - %s: gpio_output_4_20_pwr         | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_4_20_pwr))
        self.logger.info("%s - %s: gpio_output_dut_rst          | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_dut_rst))
        self.logger.info("%s - %s: gpio_output_gpio_en          | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_gpio_en))
        self.logger.info("%s - %s: gpio_output_analog_en        | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_analog_en))
        self.logger.info("%s - %s: gpio_output_cal_load_0       | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_cal_load_0))
        self.logger.info("%s - %s: gpio_output_cal_load_1       | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_cal_load_1))
        self.logger.info("%s - %s: gpio_output_cal_load_2       | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_cal_load_2))
        self.logger.info("%s - %s: gpio_output_cal_load_3       | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_cal_load_3))
        self.logger.info("%s - %s: gpio_output_cal_load_4       | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_cal_load_4))
        self.logger.info("%s - %s: gpio_output_mag_0            | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_mag_0))
        self.logger.info("%s - %s: gpio_output_mag_1            | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_mag_1))
        self.logger.info("%s - %s: gpio_output_lfp_0            | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_lfp_0))
        self.logger.info("%s - %s: gpio_output_lfp_1            | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.gpio_output_lfp_1))

        self.logger.info("%s - %s: adc_batt_current             | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.adc_batt_current))
        self.logger.info("%s - %s: adc_dc_current               | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.adc_dc_current))
        self.logger.info("%s - %s: adc_batt_voltage             | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.adc_batt_voltage))
        self.logger.info("%s - %s: adc_dc_voltage               | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.adc_dc_voltage))
        self.logger.info("%s - %s: adc_vmdm                     | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.adc_vmdm))
        self.logger.info("%s - %s: adc_sys_voltage              | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.adc_sys_voltage))
        self.logger.info("%s - %s: adc_4_20_ch0                 | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.adc_4_20_ch0))
        self.logger.info("%s - %s: adc_4_20_ch1                 | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.adc_4_20_ch1))

        self.logger.info("%s - %s: dac_1                        | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.dac_1))
        self.logger.info("%s - %s: dac_2                        | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.dac_2))

        self.logger.info("%s - %s: led_busy                     | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.led_busy))
        self.logger.info("%s - %s: led_pass                     | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.led_pass))
        self.logger.info("%s - %s: led_fail                     | %d" % (
        self.__class__.__name__, self.print_state.__name__, self.led_fail))
