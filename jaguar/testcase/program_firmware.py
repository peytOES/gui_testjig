import time
import hashlib
from pathlib import Path

from .jaguar_testcase import JaguarTestCase


class ProgramFirmwareTestCase(JaguarTestCase):
    """
    Programs firmware using STM32CubeProgrammer via self.programmer.
    Powers target via V3 + Battery (no DC) to match AnalogTestCase behavior.
    Adds detailed debug so we can see *why* a run failed.
    """

    # Conservative SWD speed (kHz) if your programmer wrapper supports it
    SWD_SAFE_FREQ_KHZ = 100

    def __init__(self, firmware_list: list, erase=True, US_FW="", CAN_FW="", get_iot=True, fw="US", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.firmware_list = firmware_list
        self.fw = fw
        self.US_FW = US_FW
        self.CAN_FW = CAN_FW
        self._used_v3_power = False
        self._held_reset = False

        if erase:
            self.append_step("Erase", self.erase)
        self.append_step("Flash", self.flash)
        if get_iot:
            self.append_step("Get IOT Number", self.get_iot)

    # ------------------------ utils ------------------------

    def _li(self, msg: str):
        try:
            self.event_logger.info(msg)
        except Exception:
            print(msg)

    def _sha256_file(self, p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    # ------------------ power / connect --------------------

    def _target_power_on(self):
        # DC OFF
        try:
            self.interface.dc_power_en(False)
            self._li("PFW SETUP: dc_power=DIS")
        except Exception:
            self._li("PFW SETUP: dc_power_en not available (ok)")

        # V3 rail ON (if present)
        try:
            if hasattr(self.interface, "v3_power_en"):
                self.interface.v3_power_en(True)
                self._used_v3_power = True
                self._li("PFW SETUP: v3_power=EN")
        except Exception as e:
            self._li(f"PFW SETUP: v3_power_en ignored: {e}")

        # Battery ON (explicit; matches AnalogTestCase)
        try:
            self.interface.battery_power_en(True)
            self._li("PFW SETUP: battery=EN")
        except Exception as e:
            self._li(f"PFW SETUP: battery_power_en failed/absent: {e}")

        # Optional helpful rails (mirror AnalogTestCase tone—non-fatal)
        for fn_name, desc in [
            ("gpio_enable", "gpio=EN"),
            ("rs232_enable", "rs232=EN"),
        ]:
            try:
                getattr(self.interface, fn_name)(True)
                self._li(f"PFW SETUP: {desc}")
            except Exception:
                pass

        # Let rails settle so ST-Link sees stable Vtarget
        time.sleep(0.5)

    def _prep_connect_path(self):
        # Lower SWD speed if wrapper supports it
        if hasattr(self.programmer, "set_swd_freq_khz"):
            try:
                self.programmer.set_swd_freq_khz(self.SWD_SAFE_FREQ_KHZ)
                self._li(f"PFW SETUP: swd_freq={self.SWD_SAFE_FREQ_KHZ} kHz")
            except Exception as e:
                self._li(f"PFW SETUP: set_swd_freq_khz ignored: {e}")

        # Connect-under-reset if wrapper has a mode setter
        for attr in ("set_connect_mode", "set_connect_opts"):
            if hasattr(self.programmer, attr):
                try:
                    getattr(self.programmer, attr)("UR")  # UR = under reset
                    self._li("PFW SETUP: connect_mode=UR")
                    break
                except Exception as e:
                    self._li(f"PFW SETUP: {attr} ignored: {e}")

    def _hold_reset_if_available(self, hold: bool):
        if hasattr(self.interface, "reset_hold"):
            try:
                self.interface.reset_hold(hold)
                self._held_reset = hold
                self._li(f"PFW SETUP: reset={'HOLD' if hold else 'RELEASE'}")
            except Exception as e:
                self._li(f"PFW SETUP: reset_hold ignored: {e}")

    # ------------------ UART sniff helper ------------------

    def _uart_sniff(self, seconds: float = 1.0, max_lines: int = 8):
        """
        Best-effort UART sniff for quick sanity after flashing.
        No-op if no target/serial is available.
        """
        if not hasattr(self, "target"):
            return
        self._li("PFW UART: sniff start")
        deadline = time.time() + seconds
        lines = 0
        while time.time() < deadline and lines < max_lines:
            raw = None
            try:
                if hasattr(self.target, "readline"):
                    raw = self.target.readline()
                elif hasattr(self.target, "read"):
                    raw = self.target.read(128)
            except Exception:
                raw = None
            if not raw:
                continue
            try:
                s = raw.decode("ascii", "ignore").strip()
            except Exception:
                s = str(raw)
            if s:
                self._li(f"PFW UART: {s}")
                lines += 1
        self._li("PFW UART: sniff done")

    # --------------------- testcase steps ------------------

    def setup(self):
        """
        Programming setup:
        - DC OFF, V3 ON, Battery ON (mirror AnalogTestCase power path)
        - Optional: hold reset, lower SWD, select UR connect
        - Enable JTAG/SWD
        """
        self._li("PFW SETUP: start")

        self._target_power_on()
        self._hold_reset_if_available(True)
        self._prep_connect_path()

        # Enable JTAG/SWD on fixture
        try:
            self.interface.jtag_enable(True)
            self._li("PFW SETUP: jtag=EN")
        except Exception as e:
            self._li(f"PFW SETUP: jtag=EN ignored: {e}")

        # Release reset to let programmer attach in UR path
        if self._held_reset:
            time.sleep(0.1)
            self._hold_reset_if_available(False)

        # Optional: read/log target voltage if wrapper exposes it
        v = None
        for attr in ("get_target_voltage", "read_voltage", "target_voltage"):
            if hasattr(self.programmer, attr):
                try:
                    v = getattr(self.programmer, attr)()
                    break
                except Exception:
                    v = None
        if v is not None:
            self._li(f"PFW SETUP: stlink_v={v}V")

        self._li("PFW SETUP: done")

    def erase(self):
        self._li("PFW ERASE: set_rdp(L0)")
        ok = self.programmer.set_rdp(0)
        if not ok:
            self._li("CAUSE: set_rdp returned False")
            self.log_error(self.ErrorCode.dut_unlock_failed)
            return {"result": False, "erase": False}

        self._li("PFW ERASE: mass erase")
        ok = self.programmer.erase()
        if not ok:
            self._li("CAUSE: mass erase returned False")
            self.log_error(self.ErrorCode.dut_erase_failed)
            return {"result": False, "erase": False}

        self._li("PFW ERASE: ok")
        return {"result": True, "erase": True}

    def flash(self):
        result = True
        base_dir = Path(self.config.active_dir) / Path(self.job._id)
        self._li(f"PFW FLASH: base_dir={base_dir}")

        for f in self.firmware_list:
            address = f.get("address")
            file_rel = f.get("file", "")
            if "production" in file_rel:
                if "USA" in self.fw:
                    file_rel = self.US_FW or file_rel
                elif "CAN" in self.fw:
                    file_rel = self.CAN_FW or file_rel

            file_abs = base_dir / file_rel
            exists = file_abs.exists()
            size = file_abs.stat().st_size if exists else -1
            sha = self._sha256_file(file_abs) if exists else "MISSING"
            self._li(f"PFW FLASH: file={file_abs} exists={exists} size={size} sha256={sha} addr={address}")

            if not exists or size <= 0:
                self._li("CAUSE: firmware file missing/empty")
                self.log_error(self.ErrorCode.dut_program_failed)
                return {"result": False}

            ok = False
            try:
                ok = bool(self.programmer.write(str(file_abs), address))
            except Exception as e:
                self._li(f"CAUSE: programmer.write exception: {e}")
            if not ok:
                self.log_error(self.ErrorCode.dut_program_failed)
                return {"result": False}

            try:
                base = int(address, 16) if isinstance(address, str) else int(address)
                if base in (0x08000000, 0x08004000):
                    self._vector_sanity(base)
            except Exception:
                pass

            time.sleep(0.2)

        # Best-effort UART sniff; safe even if no UART
        try:
            self._uart_sniff(seconds=1.2, max_lines=6)
        except Exception as e:
            self._li(f"PFW UART: sniff skipped: {e}")

        self._li("PFW FLASH: ok")
        return {"result": result, "firmware_list": self.firmware_list}

    def get_iot(self):
        self._li("PFW IOT: start")
        try:
            iot = self.programmer.extract_iot()
        except Exception as e:
            self._li(f"CAUSE: extract_iot exception: {e}")
            self.log_error(self.ErrorCode.iot_validate_failed)
            return {"result": False, "iot": "iotNotRead"}

        ok_shape = isinstance(iot, str) and iot.startswith("iot")
        hex_part = iot[3:] if ok_shape else ""
        ok_hex = all(c in "0123456789ABCDEFabcdef" for c in hex_part)
        min_hex_len = 16
        ok_len = len(hex_part) >= min_hex_len and (len(hex_part) % 2 == 0)

        nonzero_nibbles = sum(1 for c in hex_part if c != "0")
        nz_ratio = nonzero_nibbles / max(1, len(hex_part))
        ok_content = nz_ratio > 0.05

        ok = ok_shape and ok_hex and ok_len and ok_content

        try:
            nbytes = len(hex_part) // 2
            self._li(f"PFW IOT: '{iot}' bytes={nbytes} nz_ratio={nz_ratio:.2f} ok={ok}")
        except Exception:
            self._li(f"PFW IOT: '{iot}' ok={ok}")

        if not ok:
            self.log_error(self.ErrorCode.iot_validate_failed)
            return {"result": False, "iot": "iotNotRead"}

        return {"result": True, "iot": iot}

    def teardown(self):
        """
        Power down to leave fixture in a known state (mirrors AnalogTestCase).
        """
        self._li("PFW TEARDOWN: start")

        for fn_name, desc in [
            ("gpio_enable", "gpio=DIS"),
            ("rs232_enable", "rs232=DIS"),
        ]:
            try:
                getattr(self.interface, fn_name)(False)
                self._li(f"PFW TEARDOWN: {desc}")
            except Exception:
                pass

        try:
            self.interface.battery_power_en(False)
            self._li("PFW TEARDOWN: battery=DIS")
        except Exception:
            pass

        if self._used_v3_power:
            try:
                self.interface.v3_power_en(False)
                self._li("PFW TEARDOWN: v3_power=DIS")
            except Exception:
                pass

        try:
            self.interface.dc_power_en(False)
            self._li("PFW TEARDOWN: dc_power=DIS")
        except Exception:
            pass

        self._li("PFW TEARDOWN: done")
