import time
import socket

from .jaguar_testcase import JaguarTestCase


class InternetConnectionTestCase(JaguarTestCase):
    """
    Quick, low-latency internet connectivity probe.

    Changes:
      • No global socket.setdefaulttimeout side effects
      • Close sockets reliably
      • Try multiple endpoints (443 preferred; 53 as secondary)
      • Small per-attempt timeout (<= 0.8s) and no extra sleep on failure
      • Log concise diagnostics; raise no_internet_connection on total fail
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.internet_connection = False
        self.append_step("Check for Internet Connection", self.internet)

    # ---- tiny helpers -------------------------------------------------
    def _try_connect(self, host: str, port: int, timeout: float):
        """
        Attempt a single TCP connect; return (ok:bool, latency:float|None, err:str|None).
        """
        start = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=timeout) as s:
                # If we reached here, connect() succeeded.
                latency = time.perf_counter() - start
                return True, latency, None
        except Exception as e:
            return False, None, f"{host}:{port} {type(e).__name__}: {e}"

    # ---- main step ----------------------------------------------------
    def internet(self):
        """
        Try a few robust endpoints quickly. Prefer 443 to avoid TCP/53 firewall blocks.
        """
        self.event_logger.info("NET: probe start")

        # Order matters: try fast/likely-allowed ports first.
        # 1.1.1.1 / 8.8.8.8 / 9.9.9.9 are anycast resolver IPs that generally answer on 443.
        candidates = [
            ("1.1.1.1",   443),
            ("8.8.8.8",   443),
            ("9.9.9.9",   443),
            ("1.1.1.1",    53),
            ("8.8.8.8",    53),
            ("9.9.9.9",    53),
        ]

        # Keep each attempt very short to avoid test-suite stalls.
        per_attempt_timeout = 0.8

        diagnostics = []
        for host, port in candidates:
            ok, latency, err = self._try_connect(host, port, per_attempt_timeout)
            if ok:
                self.internet_connection = True
                ms = int(latency * 1000.0)
                self.event_logger.info(f"NET: ok via {host}:{port} ~{ms}ms")
                self.event_logger.info("NET: probe end (success)")
                return {"result": True, "endpoint": f"{host}:{port}", "latency_ms": ms}
            else:
                diagnostics.append(err)

        # If we got here, all probes failed quickly.
        self.internet_connection = False
        self.event_logger.info("NET: all probes failed")
        # Emit a compact single-line summary (first 3 errors to keep logs short)
        brief = "; ".join(diagnostics[:3])
        self.event_logger.info(f"NET: causes (partial): {brief}")
        # Log framework error code so the suite can surface it
        self.log_error(self.ErrorCode.no_internet_connection)

        # Return diagnostic payload (no extra sleep)
        return {
            "result": False,
            "errors_sample": diagnostics[:3],
            "attempted": [f"{h}:{p}" for h, p in candidates],
        }
