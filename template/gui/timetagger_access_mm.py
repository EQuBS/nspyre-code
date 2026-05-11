"""
Time Tagger access helpers for the Micro-Manager/Pycro-Manager scan scripts.

The safest nspyre architecture is single-owner hardware access: the instrument
server owns the Swabian Time Tagger, while measurement processes access it via
InstrumentGateway as gw.daq. This module adds a small adapter that gives gw.daq
the same count_for_ms(...) interface used by confocal_scan_runner_mm.py.

A local/direct Time Tagger mode is still possible for standalone debugging, but
it must not be used while the nspyre instrument server already has the USB
Time Tagger open.
"""
from __future__ import annotations

import time
from typing import Any, Optional

import numpy as np

from TimeTagger import CHANNEL_UNUSED

try:
    from rpyc.utils.classic import obtain
except Exception:  # pragma: no cover
    def obtain(value):
        return value

PS_PER_MS = 1_000_000_000
PS_PER_S = 1_000_000_000_000

_GATEWAY_MODES = {
    "gateway",
    "instrument_gateway",
    "instrumentgateway",
    "nspyre",
    "gw",
    "server",
    "instrument_server",
}
_LOCAL_MODES = {
    "local",
    "direct",
    "direct_timetagger",
    "local_timetagger",
    "usb",
}


def normalize_daq_mode(mode: Optional[str]) -> str:
    """Normalize GUI/user DAQ mode text to 'gateway' or 'local'."""
    text = str(mode or "instrument_gateway").strip().lower()
    if text in _GATEWAY_MODES:
        return "gateway"
    if text in _LOCAL_MODES:
        return "local"
    raise ValueError(
        "DAQ_Control_Mode must be 'instrument_gateway' or 'local_timetagger'. "
        f"Got {mode!r}."
    )


def _call_any(obj: Any, names, *args, required: bool = False, **kwargs):
    """Call the first method in names that exists on obj."""
    last_exc = None
    for name in names:
        method = getattr(obj, name, None)
        if callable(method):
            try:
                return method(*args, **kwargs)
            except TypeError as exc:
                # RPyC/proxy methods sometimes do not preserve keyword support;
                # the caller can retry positionally where needed.
                last_exc = exc
            except Exception:
                raise
    if required:
        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"None of the required methods {tuple(names)} exist on {obj!r}.")
    return None


class GatewayTimeTaggerAdapter:
    """Adapter for a Time Tagger driver exposed as nspyre InstrumentGateway.gw.daq.

    The adapter intentionally does not free the Time Tagger on close. The
    instrument server owns the hardware handle and should keep it available for
    future measurements.
    """

    backend = "instrument_gateway"

    def __init__(self, daq: Any):
        if daq is None:
            raise RuntimeError("InstrumentGateway did not expose gw.daq.")
        self.daq = daq

    def __getattr__(self, name: str):
        return getattr(self.daq, name)

    def set_trigger_level(self, channel, voltage):
        return self.daq.set_trigger_level(int(channel), float(voltage))

    def set_in_delay(self, channel, delay_ps):
        method = getattr(self.daq, "set_in_delay", None) or getattr(self.daq, "setInputDelay", None)
        if not callable(method):
            raise AttributeError("gw.daq does not expose set_in_delay/setInputDelay.")
        return method(int(channel), int(delay_ps))

    def sync(self):
        method = getattr(self.daq, "sync", None)
        if callable(method):
            return method()
        return None

    def clear_counter(self):
        method = getattr(self.daq, "clear_counter", None)
        if callable(method):
            return method()
        return None

    def count_for_ms(self, channel, dwell_ms, trigger_level=None, clear=True, normalized=False):
        """Count one pixel dwell through gw.daq.

        If the instrument-server driver is already the newer TimeTaggerDriver_mm,
        this delegates to gw.daq.count_for_ms(...). If the server still uses the
        older TimeTaggerDriver.py, it falls back to start_counter/sFor_Counter and
        count_data_Norm/get_counter_data.
        """
        channel = int(channel)
        dwell_ms = float(dwell_ms)
        dwell_ps = int(round(dwell_ms * PS_PER_MS))
        if dwell_ps <= 0:
            raise ValueError("dwell_ms must be positive.")

        if trigger_level is not None:
            self.set_trigger_level(channel, trigger_level)

        direct = getattr(self.daq, "count_for_ms", None)
        if callable(direct):
            try:
                value = direct(channel=channel, dwell_ms=dwell_ms,
                               trigger_level=trigger_level, clear=clear,
                               normalized=normalized)
            except TypeError:
                value = direct(channel, dwell_ms, trigger_level, clear, normalized)
            return float(np.asarray(obtain(value), dtype=float).reshape(-1)[0])

        # Compatibility path for the original TimeTaggerDriver.py used by the
        # instrument server in many nspyre setups.
        self.daq.start_counter([channel], dwell_ps, 1)
        self.daq.sFor_Counter(dwell_ps)
        try:
            if normalized and callable(getattr(self.daq, "count_data_Norm", None)):
                data = obtain(self.daq.count_data_Norm())
                return float(np.asarray(data, dtype=float).reshape(-1)[0])

            data = obtain(self.daq.get_counter_data())
            raw_counts = float(np.asarray(data, dtype=float).reshape(-1)[0])
            if normalized:
                return raw_counts / (dwell_ms / 1000.0)
            return raw_counts
        finally:
            self.clear_counter()

    # CountBetweenMarkers compatibility methods -----------------------
    def start_cbm(self, click_channel, begin_channel, end_channel=CHANNEL_UNUSED, n_values=1000, tagger=None):
        if tagger is None:
            return self.daq.start_cbm(int(click_channel), int(begin_channel), CHANNEL_UNUSED, int(n_values))
        return self.daq.start_cbm(int(click_channel), int(begin_channel), CHANNEL_UNUSED, int(n_values), tagger)

    def CBM_start(self, clear=True):
        if clear and callable(getattr(self.daq, "cbm_clear", None)):
            self.daq.cbm_clear()
        method = getattr(self.daq, "CBM_start", None)
        if not callable(method):
            raise AttributeError("gw.daq does not expose CBM_start().")
        try:
            return method(clear)
        except TypeError:
            return method()

    def cbm_clear(self):
        method = getattr(self.daq, "cbm_clear", None)
        if callable(method):
            return method()
        cbm = getattr(self.daq, "cbm", None)
        if cbm is not None and callable(getattr(cbm, "clear", None)):
            return cbm.clear()
        return None

    def cbm_ready(self) -> bool:
        method = getattr(self.daq, "cbm_ready", None)
        if not callable(method):
            raise AttributeError("gw.daq does not expose cbm_ready().")
        return bool(method())

    def count_BM(self):
        method = getattr(self.daq, "count_BM", None)
        if not callable(method):
            raise AttributeError("gw.daq does not expose count_BM().")
        return obtain(method())

    def cbm_get_BinWidths(self):
        method = getattr(self.daq, "cbm_get_BinWidths", None)
        if not callable(method):
            raise AttributeError("gw.daq does not expose cbm_get_BinWidths().")
        return obtain(method())

    def count_between_markers_image(self, click_channel, begin_channel, end_channel,
                                    nx, ny, start_callback=None, poll_interval_s=0.02,
                                    timeout_s=None, partial_callback=None):
        nx = int(nx)
        ny = int(ny)
        n_values = nx * ny
        self.start_cbm(click_channel, begin_channel, end_channel, n_values)
        self.CBM_start(clear=True)
        self.sync()
        if start_callback is not None:
            start_callback()
        t0 = time.monotonic()
        while not self.cbm_ready():
            if partial_callback is not None:
                data = np.asarray(obtain(self.count_BM()), dtype=float)
                if data.size >= n_values:
                    partial_callback(data[:n_values].reshape((ny, nx)))
            if timeout_s is not None and (time.monotonic() - t0) > float(timeout_s):
                raise TimeoutError("Timed out waiting for CountBetweenMarkers image.")
            time.sleep(float(poll_interval_s))
        data = np.asarray(obtain(self.count_BM()), dtype=float)
        return data[:n_values].reshape((ny, nx))

    def free_time_tagger(self):
        """No-op: the nspyre instrument server owns the hardware handle."""
        return None

    close = free_time_tagger


def physical_channel(channel: int) -> Optional[int]:
    channel = int(channel)
    if channel == 0:
        return None
    return abs(channel)
