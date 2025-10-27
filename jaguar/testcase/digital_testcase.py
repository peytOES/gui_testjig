import time

from .jaguar_testcase import JaguarTestCase


class DigitalTestCase(JaguarTestCase):
    """
    Test case for exercising digital GPIOs on Jaguar board.

    Power behavior:
      - V1: DC ON, Battery OFF, GPIO/RS232 ON (legacy)
      - V2: DC ON, Battery OFF, GPIO/RS232 ON (cleaned; redundant enables removed)
      - V3: DC OFF, Battery ON (and v3_power_en(True) if available), GPIO/RS232 ON
    """

    def __init__(self, board_type='V1', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.board_type = board_type
        # V1 keeps legacy extra IO steps
        if 'V1' in self.board_type:
            self.append_step("Digital input", self.digital_in)
            self.append_step("Digital output", self.digital_out)
        self.append_step("Magnetic switch", self.magnetic_switch)

        # Remove Pulse for V3; keep for V1/V2
        if 'V3' not in self.board_type:
            self.append_step("Pulse", self.pulse_input)

    # --------------------- Power sequencing ---------------------

    def _setup_v1(self):
        # Legacy V1: DC on, Battery off, GPIO/RS232 on
        try:
            self.interface.dc_power_en(True)
        except Exception:
            pass
        try:
            self.interface.gpio_enable(True)
        except Exception:
            pass
        try:
            self.interface.rs232_enable(True)
        except Exception:
            pass
        try:
            self.interface.battery_power_en(False)
        except Exception:
            pass
        time.sleep(0.5)

    def _setup_v2(self):
        # V2: same as legacy, but WITHOUT any redundant re-enables
        try:
            self.interface.dc_power_en(True)
        except Exception:
            pass
        try:
            self.interface.gpio_enable(True)
        except Exception:
            pass
        try:
            self.interface.rs232_enable(True)
        except Exception:
            pass
        try:
            self.interface.battery_power_en(False)
        except Exception:
            pass
        time.sleep(0.5)

    def _setup_v3(self):
        # V3: battery-powered path; DC OFF, optional v3 rail ON
        try:
            self.interface.dc_power_en(False)
        except Exception:
            pass
        # ensure battery was off, then bring it up cleanly
        try:
            self.interface.battery_power_en(False)
        except Exception:
            pass
        time.sleep(0.1)
        try:
            if hasattr(self.interface, "v3_power_en"):
                self.interface.v3_power_en(True)
        except Exception:
            pass
        try:
            self.interface.battery_power_en(True)
        except Exception:
            pass
        try:
            self.interface.gpio_enable(True)
        except Exception:
            pass
        try:
            self.interface.rs232_enable(True)
        except Exception:
            pass
        time.sleep(0.5)

    def setup(self):
        if 'V3' in self.board_type:
            self._setup_v3()
        elif 'V2' in self.board_type:
            self._setup_v2()   # Duplicate of V2 path (clean), as requested
        else:
            self._setup_v1()

    def teardown(self):
        # Common shutdown
        try:
            self.interface.gpio_enable(False)
        except Exception:
            pass
        try:
            self.interface.rs232_enable(False)
        except Exception:
            pass

        # Power down rails safely
        if 'V3' in self.board_type:
            try:
                self.interface.battery_power_en(False)
            except Exception:
                pass
            try:
                if hasattr(self.interface, "v3_power_en"):
                    self.interface.v3_power_en(False)
            except Exception:
                pass
            try:
                self.interface.dc_power_en(False)
            except Exception:
                pass
        else:
            try:
                self.interface.dc_power_en(False)
            except Exception:
                pass
            try:
                self.interface.battery_power_en(False)
            except Exception:
                pass

    # --------------------- Test steps ---------------------

    def digital_in(self):
        """
        DIGIN1, DIGIN2 to jaguar, read back via serial
        """
        result = True
        delay = 0.2

        # DIGIN1 = B4
        self.interface.set_dig_in(0, False)
        time.sleep(delay)
        self.interface.set_dig_in(1, False)
        time.sleep(delay)
        resp = self.target.read_pin("B", 4)
        if resp != 0:
            self.log_error(self.ErrorCode.digin1_clear_failed)
            result = False

        self.interface.set_dig_in(0, True)
        time.sleep(delay)
        resp = self.target.read_pin("B", 4)
        if resp != 1:
            self.log_error(self.ErrorCode.digin1_set_failed)
            result = False

        resp = self.target.read_pin("B", 3)
        time.sleep(delay)
        if resp != 0:
            self.log_error(self.ErrorCode.digin2_clear_failed)
            result = False

        self.interface.set_dig_in(1, True)
        time.sleep(delay)
        resp = self.target.read_pin("B", 3)
        if resp != 1:
            self.log_error(self.ErrorCode.digin2_set_failed)
            result = False

        self.interface.set_dig_in(0, False)
        time.sleep(delay)
        self.interface.set_dig_in(1, False)
        time.sleep(delay)

        return {"result": result}

    def digital_out(self):
        """
        Test DIG_OUT[1..4] on Jaguar.
        Pins:
            DIG_OUT1 : A15
            DIG_OUT2 : C0
            DIG_OUT3 : C11
            DIG_OUT4 : C12

        0) GPIO enable
        1) enable Digital out power
        2) for each pin
            - set low
            - set high
            - compare
        """
        result = True
        d = 0.2
        self.interface.dig_out_power_enable(True)
        self.target.set_pin("A", 15, 0)
        time.sleep(d)
        self.target.set_pin("C", 0, 0)
        time.sleep(d)
        self.target.set_pin("C", 11, 0)
        time.sleep(d)
        self.target.set_pin("C", 12, 0)
        time.sleep(d)

        # all clear
        dig_out = self.interface.read_dig_out()
        if dig_out != (True, True, True, True):
            self.log_error(self.ErrorCode.digout_clear_failed)
            result = False

        # DIG_OUT1
        self.target.set_pin("A", 15, 1)
        time.sleep(d)
        dig_out = self.interface.read_dig_out()
        if dig_out[0] is not False:
            self.log_error(self.ErrorCode.digout1_set_failed)
            result = False
        self.target.set_pin("A", 15, 0)

        # C0
        self.target.set_pin("C", 0, 1)
        time.sleep(d)
        dig_out = self.interface.read_dig_out()
        if dig_out[1] is not False:
            self.log_error(self.ErrorCode.digout2_set_failed)
            result = False
        self.target.set_pin("C", 0, 0)

        # C11
        self.target.set_pin("C", 11, 1)
        time.sleep(d)
        dig_out = self.interface.read_dig_out()
        if dig_out[2] is not False:
            self.log_error(self.ErrorCode.digout3_set_failed)
            result = False
        self.target.set_pin("C", 11, 0)

        # C12
        self.target.set_pin("C", 12, 1)
        time.sleep(d)
        dig_out = self.interface.read_dig_out()
        if dig_out[3] is not False:
            self.log_error(self.ErrorCode.digout4_set_failed)
            result = False
        self.target.set_pin("C", 12, 0)

        self.interface.dig_out_power_enable(False)
        return {"result": result}

    def magnetic_switch(self):
        """
        Enable, disable electromagnet, read back pin.
        """
        result = True
        d = 1

        self.interface.set_electromagnet(0, False)
        time.sleep(d)
        readback = self.target.read_pin("A", 0)
        if readback != 1:
            result = False
            self.log_error(self.ErrorCode.mag_sense)
        self.interface.set_electromagnet(0, True)
        time.sleep(d)
        readback = self.target.read_pin("A", 0)
        if readback != 0:
            result = False
            self.log_error(self.ErrorCode.mag_sense)
        result = True
        return {"result": result}

    def pulse_input(self):
        """
        Read pulse counter, toggle pin, read pulse counter with detailed logging.
        (This step is not appended for V3.)
        """
        result = True
        count_log = {}

        # Clear counter
        try:
            start_count = self.target.read_pulse_count()
            print(f"[PULSE] Initial counter reset -> {start_count}")
        except Exception as e:
            print(f"[PULSE][ERROR] Failed to clear counter: {e}")
            self.log_error(self.ErrorCode.pulse_count_mismatch)
            return {"result": False}

        # 1, 5, and 10 pulses
        for i in [1, 5, 10]:
            d = 0.05
            print(f"\n[PULSE] --- Generating {i} pulses ---")

            for j in range(i):
                try:
                    self.interface.pulse(1, 0)
                    print(f"[PULSE] Toggle {j+1}/{i} -> LOW")
                    time.sleep(d)
                    self.interface.pulse(1, 1)
                    print(f"[PULSE] Toggle {j+1}/{i} -> HIGH")
                    time.sleep(d)
                except Exception as e:
                    print(f"[PULSE][ERROR] Toggle {j+1} failed: {e}")
                    self.log_error(self.ErrorCode.pulse_count_mismatch)
                    result = False

            try:
                count = self.target.read_pulse_count()
                print(f"[PULSE] Expected={i}, Read={count}")
            except Exception as e:
                print(f"[PULSE][ERROR] Failed to read pulse count after {i}: {e}")
                self.log_error(self.ErrorCode.pulse_count_mismatch)
                result = False
                count = -1

            if count != i:
                diff = count - i
                print(f"[PULSE][FAIL] Count mismatch: got {count}, expected {i} (Δ={diff})")
                result = False
                self.log_error(self.ErrorCode.pulse_count_mismatch)
            else:
                print(f"[PULSE][OK] Count matched: {count}")

            count_log[i] = count

        print(f"\n[PULSE] Final results: {count_log}\n")
        return {"result": result, **count_log}
