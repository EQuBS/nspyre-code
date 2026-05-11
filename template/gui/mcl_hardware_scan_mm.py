"""
Direct MCL/Madlib hardware waveform + Swabian CountBetweenMarkers scan path.

This module is intentionally separate from the Micro-Manager/Pycro-Manager
software raster path.  The fast mode uses the direct MCL NanoDrive object
exposed by nspyre InstrumentGateway as gw.nano, and the Time Tagger object
exposed as gw.daq.  That matches the ownership model used by the original
spin_measurements.Two_D_Scan_R implementation while keeping the newer GUI and
laser/back-end handling.

Axis-safety rule:
    Only the two requested axes are commanded.  The unscanned axis is never
    used in wfma_setup(), single_write_n(), or monitor_n().
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any, Callable, Dict, Iterable, Optional, Tuple

import numpy as np

try:
    from rpyc.utils.classic import obtain
except Exception:  # pragma: no cover
    def obtain(value):
        return value


CHANNEL_UNUSED = 0
_AXIS_TO_ID = {"x": 1, "y": 2, "z": 3}
_ID_TO_AXIS = {1: "x", 2: "y", 3: "z"}


@dataclass
class HardwareCBMScanPlan:
    """Parameters for a direct MCL waveform + CountBetweenMarkers 2D scan."""

    axis_1: str = "x"                 # fast waveform axis
    axis_2: str = "y"                 # slow row axis
    axis_1_min_um: float = -10.0
    axis_1_max_um: float = 10.0
    axis_2_min_um: float = -10.0
    axis_2_max_um: float = 10.0
    data_points: int = 10
    dwell_time_ms: float = 5.0         # passed to MCL_WfmaSetup; same convention as original code
    photon_channel: int = 3
    photon_trigger_level_v: Optional[float] = 1.0
    begin_channel: int = 4             # MCL pixel-clock input at Time Tagger
    begin_trigger_level_v: Optional[float] = 1.1
    end_channel: int = CHANNEL_UNUSED  # begin-only CBM by default
    bidirectional: bool = True         # snake if line_mode == "snake_single_line"
    normalize_to_cps: bool = True
    use_bin_widths: bool = True
    line_mode: str = "forward_only"       # "forward_only", "snake_single_line", or "forward_backward_average"
    display_image: str = "forward"        # "forward", "backward", or "average" for live display
    reverse_line_shift_px: float = 0.0     # manual correction applied to reverse-direction data after coordinate reversal
    auto_align_reverse: bool = False       # align backward lines to forward lines before averaging/display
    auto_align_snake_rows: bool = False    # align reverse snake rows to the previous row before display
    auto_align_max_shift_px: float = 10.0  # maximum absolute shift searched by auto alignment
    edge_blank_pixels: int = 0             # blank unreliable pixels at both ends after alignment
    user_origin_mode: str = "center"      # "center" or "current"
    stage_range_um: float = 200.0
    pixel_clock: int = 1
    pixel_clock_mode: int = 2          # 2 = low-to-high pulse, MCL ISS convention
    bind_pixel_clock: bool = True
    iss_reset_defaults: bool = False
    slow_axis_use_monitor: bool = True
    line_settle_ms: float = 0.0
    poll_interval_ms: float = 1.0
    line_timeout_s: float = 30.0
    max_waveform_points: int = 10000

    def validate(self) -> None:
        self.axis_1 = _normalize_axis(self.axis_1)
        self.axis_2 = _normalize_axis(self.axis_2)
        if self.axis_1 == self.axis_2:
            raise ValueError("Hardware scan requires two different axes.")
        if int(self.data_points) < 2:
            raise ValueError("Hardware scan requires Data_Points >= 2.")
        if float(self.dwell_time_ms) <= 0:
            raise ValueError("Dwell_Time must be positive for hardware scans.")
        if int(self.max_waveform_points) < 2:
            raise ValueError("Hardware_Max_Waveform_Points must be >= 2.")
        if int(self.data_points) + 1 > int(self.max_waveform_points):
            raise ValueError(
                "The MCL hardware waveform uses Data_Points + 1 points for begin-only CBM. "
                f"Requested {int(self.data_points) + 1}, limit is {int(self.max_waveform_points)}."
            )
        mode = str(self.line_mode or "forward_only").strip().lower()
        if mode not in ("forward_only", "snake_single_line", "forward_backward_average"):
            raise ValueError(
                "Hardware_Line_Mode must be 'forward_only', 'snake_single_line', or "
                f"'forward_backward_average'. Got {self.line_mode!r}."
            )
        self.line_mode = mode
        display = str(self.display_image or "forward").strip().lower()
        if display not in ("forward", "backward", "average"):
            raise ValueError("Hardware_Display_Image must be 'forward', 'backward', or 'average'.")
        self.display_image = display
        self.reverse_line_shift_px = float(self.reverse_line_shift_px or 0.0)
        self.auto_align_max_shift_px = max(0.0, float(self.auto_align_max_shift_px or 0.0))
        self.edge_blank_pixels = max(0, int(self.edge_blank_pixels or 0))
        origin = str(self.user_origin_mode or "center").strip().lower()
        if origin not in ("center", "current"):
            raise ValueError("User_Origin_Mode for hardware scans must be 'center' or 'current'.")
        self.user_origin_mode = origin


def _normalize_axis(axis: Any) -> str:
    text = str(axis or "").strip().lower()
    if not text:
        raise ValueError("Axis text is empty.")
    axis = text[0]
    if axis not in _AXIS_TO_ID:
        raise ValueError(f"Invalid axis {axis!r}; use x, y, or z.")
    return axis


def _axis_id(axis: str) -> int:
    return _AXIS_TO_ID[_normalize_axis(axis)]


def _axis_label(axis: str) -> str:
    return _normalize_axis(axis).upper()


def _as_array(value: Any) -> np.ndarray:
    return np.asarray(obtain(value), dtype=float).reshape(-1)


def _call_optional(obj: Any, name: str, *args, **kwargs):
    method = getattr(obj, name, None)
    if callable(method):
        return method(*args, **kwargs)
    return None


def _safe_getattr(obj: Any, name: str, default: Any = None) -> Any:
    """getattr() that tolerates RPyC remote AttributeError wrappers."""
    try:
        return getattr(obj, name)
    except Exception:
        return default


def resolve_mcl_handle(nano: Any) -> Tuple[int, str, bool]:
    """Return (handle, source, acquired_here) for a direct MCL NanoDrive object.

    Some instrument-server deployments expose gw.nano.handle, while others expose
    only the Madlib methods.  The hardware scan must not assume the attribute is
    present.  When no attribute is found, request a handle through the remote
    NanoDrive object and pass that integer explicitly into all MCL calls.
    """
    for attr in ("handle", "_handle", "hdl"):
        value = _safe_getattr(nano, attr, None)
        if value not in (None, 0, ""):
            try:
                return int(obtain(value)), f"gw.nano.{attr}", False
            except Exception:
                pass

    for method_name in ("get_handle", "init_handle_or_get_existing", "init_handle"):
        method = _safe_getattr(nano, method_name, None)
        if callable(method):
            try:
                handle = int(obtain(method()))
            except Exception as exc:
                last_exc = exc
                continue
            if handle != 0:
                return handle, f"gw.nano.{method_name}()", True

    method = _safe_getattr(nano, "grab_all_handles", None)
    get_all = _safe_getattr(nano, "get_all_handles", None)
    if callable(method) and callable(get_all):
        try:
            n_handles = int(obtain(method()))
            if n_handles > 0:
                result = obtain(get_all(n_handles))
                # Many wrappers return (num_handles, handles_array).
                if isinstance(result, tuple) and len(result) >= 2:
                    handles = obtain(result[1])
                    handle = int(obtain(handles[0]))
                else:
                    handle = int(obtain(result[0]))
                if handle != 0:
                    return handle, "gw.nano.grab_all_handles()/get_all_handles()", True
        except Exception:
            pass

    raise AttributeError(
        "Could not resolve an MCL NanoDrive handle from gw.nano. Expected either "
        "gw.nano.handle or one of init_handle_or_get_existing(), init_handle(), "
        "or grab_all_handles()/get_all_handles(). Restart the instrument server "
        "after updating MCL_Madlib_Wrapper.py if those methods are missing."
    )


def release_mcl_handle_if_needed(nano: Any, handle: int, acquired_here: bool, release: bool = False) -> None:
    """Optionally release a handle acquired only for this scan.

    The default is conservative: do not release handles in the instrument server,
    because init_handle_or_get_existing() may have returned an already-controlled
    handle.  Set release=True only if your server driver does not keep the handle
    between calls and you want one-scan ownership.
    """
    if not (acquired_here and release):
        return
    method = _safe_getattr(nano, "release_handle", None)
    if callable(method):
        try:
            method(int(handle))
        except Exception:
            pass


def _physical_tagger_channel(channel: int) -> Optional[int]:
    channel = int(channel)
    if channel == 0:
        return None
    return abs(channel)


def _set_trigger_level_if_possible(daq: Any, channel: int, level: Optional[float]) -> None:
    physical = _physical_tagger_channel(channel)
    if physical is None or level is None:
        return
    method = getattr(daq, "set_trigger_level", None)
    if not callable(method):
        method = getattr(daq, "setTriggerLevel", None)
    if callable(method):
        method(int(physical), float(level))


def _calibration_um(nano: Any, axis_id: int, handle: int, fallback: float) -> float:
    try:
        return float(nano.get_calibration(int(axis_id), int(handle)))
    except Exception:
        return float(fallback)


def _read_axis_um(nano: Any, axis_id: int, handle: int, fallback: float = 0.0) -> float:
    try:
        return float(nano.single_read_n(int(axis_id), int(handle)))
    except Exception:
        return float(fallback)


def _origin_offsets(nano: Any, plan: HardwareCBMScanPlan, handle: int) -> Dict[int, float]:
    offsets: Dict[int, float] = {}
    for axis_id in (1, 2, 3):
        if plan.user_origin_mode == "current":
            offsets[axis_id] = _read_axis_um(nano, axis_id, handle, fallback=0.5 * float(plan.stage_range_um))
        else:
            offsets[axis_id] = 0.5 * _calibration_um(nano, axis_id, handle, fallback=float(plan.stage_range_um))
    return offsets


def _user_to_hw(user_um: float, axis_id: int, origin_offsets: Dict[int, float]) -> float:
    return float(user_um) + float(origin_offsets[int(axis_id)])


def _validate_hw_position(nano: Any, axis_id: int, hw_um: float, plan: HardwareCBMScanPlan, handle: int) -> None:
    cal = _calibration_um(nano, axis_id, handle, fallback=float(plan.stage_range_um))
    # Allow a small numerical tolerance for values like 200.00000000003.
    tol = 1e-9
    if float(hw_um) < -tol or float(hw_um) > cal + tol:
        axis = _ID_TO_AXIS[int(axis_id)].upper()
        raise ValueError(
            f"Requested {axis} hardware position {hw_um:.6f} um is outside the calibrated range "
            f"0..{cal:.6f} um. Check scan limits and User_Origin_Mode."
        )


def _move_axis(nano: Any, axis_id: int, hw_um: float, handle: int, use_monitor: bool = True) -> float:
    axis_id = int(axis_id)
    hw_um = float(hw_um)
    handle = int(handle)
    if use_monitor and callable(_safe_getattr(nano, "monitor_n", None)):
        return float(nano.monitor_n(hw_um, axis_id, handle))
    nano.single_write_n(hw_um, axis_id, handle)
    return hw_um


def _wfma_setup_one_axis(nano: Any, axis_id: int, waveform_hw: np.ndarray,
                         dwell_time_ms: float, handle: int, iterations: int = 1) -> None:
    values = [float(v) for v in np.asarray(waveform_hw, dtype=float).reshape(-1)]
    n = int(len(values))
    if axis_id == 1:
        nano.wfma_setup(values, None, None, n, float(dwell_time_ms), int(iterations), int(handle))
    elif axis_id == 2:
        nano.wfma_setup(None, values, None, n, float(dwell_time_ms), int(iterations), int(handle))
    elif axis_id == 3:
        nano.wfma_setup(None, None, values, n, float(dwell_time_ms), int(iterations), int(handle))
    else:
        raise ValueError(f"Invalid MCL axis id {axis_id!r}.")


def _wait_for_cbm_ready(daq: Any, timeout_s: float, poll_interval_ms: float,
                        stop_requested: Optional[Callable[[], bool]] = None) -> None:
    t0 = time.monotonic()
    sleep_s = max(0.0001, float(poll_interval_ms) / 1000.0)
    while not bool(daq.cbm_ready()):
        if stop_requested is not None and stop_requested():
            raise KeyboardInterrupt("Stop requested during hardware CBM line scan.")
        if float(timeout_s) > 0 and (time.monotonic() - t0) > float(timeout_s):
            raise TimeoutError("Timed out waiting for Time Tagger CountBetweenMarkers line.")
        time.sleep(sleep_s)


def _start_cbm_line(daq: Any, plan: HardwareCBMScanPlan, n_values: int) -> None:
    daq.start_cbm(
        int(plan.photon_channel),
        int(plan.begin_channel),
        int(plan.end_channel),
        int(n_values),
    )
    # Newer adapter accepts clear=True; older original driver accepts no args.
    try:
        daq.CBM_start(clear=True)
    except TypeError:
        if callable(getattr(daq, "cbm_clear", None)):
            daq.cbm_clear()
        daq.CBM_start()
    sync = getattr(daq, "sync", None)
    if callable(sync):
        sync()


def _read_cbm_line(daq: Any, n_values: int, normalize_to_cps: bool,
                   use_bin_widths: bool, dwell_time_ms: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    raw_counts = _as_array(daq.count_BM())
    if raw_counts.size < int(n_values):
        raise RuntimeError(f"CountBetweenMarkers returned {raw_counts.size} bins; expected {n_values}.")
    counts = raw_counts[:int(n_values)].astype(float, copy=True)

    try:
        raw_widths = _as_array(daq.cbm_get_BinWidths())
    except Exception:
        raw_widths = np.full(int(n_values), float(dwell_time_ms) * 1e9, dtype=float)  # ps
    if raw_widths.size < int(n_values):
        widths_ps = np.full(int(n_values), float(dwell_time_ms) * 1e9, dtype=float)
    else:
        widths_ps = raw_widths[:int(n_values)].astype(float, copy=True)

    if normalize_to_cps:
        if use_bin_widths and np.all(widths_ps > 0):
            values = counts / (widths_ps * 1e-12)
        else:
            values = counts / (float(dwell_time_ms) * 1e-3)
    else:
        values = counts.copy()
    return values, counts, widths_ps


def _shift_line(line: np.ndarray, shift_px: float, fill_value: float = np.nan) -> np.ndarray:
    """Return a copy of line shifted by shift_px display pixels.

    Positive shift moves image features toward larger fast-axis coordinate
    indices. Fractional-pixel shifts are handled by linear interpolation.
    """
    arr = np.asarray(line, dtype=float).reshape(-1)
    n = arr.size
    shift_px = float(shift_px or 0.0)
    if n == 0 or abs(shift_px) < 1e-12:
        return arr.copy()
    x = np.arange(n, dtype=float)
    sample_x = x - shift_px
    finite = np.isfinite(arr)
    if finite.sum() < 2:
        return arr.copy()
    return np.interp(sample_x, x[finite], arr[finite], left=fill_value, right=fill_value)


def _blank_edges(line: np.ndarray, n_blank: int) -> np.ndarray:
    arr = np.asarray(line, dtype=float).reshape(-1).copy()
    n_blank = max(0, int(n_blank or 0))
    if n_blank <= 0 or arr.size == 0:
        return arr
    n_blank = min(n_blank, arr.size // 2)
    if n_blank > 0:
        arr[:n_blank] = np.nan
        arr[-n_blank:] = np.nan
    return arr


def _score_line_alignment(reference: np.ndarray, moving_shifted: np.ndarray) -> float:
    ref = np.asarray(reference, dtype=float).reshape(-1)
    mov = np.asarray(moving_shifted, dtype=float).reshape(-1)
    mask = np.isfinite(ref) & np.isfinite(mov)
    if mask.sum() < max(4, min(ref.size, mov.size) // 5):
        return -np.inf
    r = ref[mask] - np.nanmean(ref[mask])
    m = mov[mask] - np.nanmean(mov[mask])
    denom = float(np.linalg.norm(r) * np.linalg.norm(m))
    if denom <= 0:
        return -np.inf
    return float(np.dot(r, m) / denom)


def _estimate_shift_pixels(reference: np.ndarray, moving: np.ndarray, max_shift_px: float) -> float:
    """Estimate integer-pixel shift that best aligns moving to reference.

    The returned value uses the same convention as _shift_line(): positive
    values move moving toward larger fast-axis coordinates.
    """
    ref = np.asarray(reference, dtype=float).reshape(-1)
    mov = np.asarray(moving, dtype=float).reshape(-1)
    if ref.size != mov.size or ref.size < 4:
        return 0.0
    max_shift = int(max(0, round(float(max_shift_px or 0.0))))
    if max_shift <= 0:
        return 0.0
    best_shift = 0
    best_score = _score_line_alignment(ref, mov)
    for shift in range(-max_shift, max_shift + 1):
        shifted = _shift_line(mov, float(shift))
        score = _score_line_alignment(ref, shifted)
        if score > best_score:
            best_score = score
            best_shift = shift
    return float(best_shift)


def _nanmean2(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    stacked = np.vstack([np.asarray(a, dtype=float), np.asarray(b, dtype=float)])
    with np.errstate(invalid="ignore"):
        return np.nanmean(stacked, axis=0)


def _select_display_line(display_image: str, forward: np.ndarray, backward: np.ndarray, average: np.ndarray) -> np.ndarray:
    if display_image == "backward":
        return np.asarray(backward, dtype=float).copy()
    if display_image == "average":
        return np.asarray(average, dtype=float).copy()
    return np.asarray(forward, dtype=float).copy()


def _empty_dataset(plan: HardwareCBMScanPlan, fast_user: np.ndarray, slow_user: np.ndarray) -> Dict[str, Any]:
    shape = (len(slow_user), len(fast_user))
    nan_image = np.full(shape, np.nan, dtype=float)
    return {
        "xSteps": np.asarray(fast_user, dtype=float),
        "ySteps": np.asarray(slow_user, dtype=float),
        "Scan_Forward": nan_image.copy(),
        "Scan_Backward": nan_image.copy(),
        "Scan_Averaged": nan_image.copy(),
        "Scan_Display": nan_image.copy(),
        "Scan_Raw_Counts": nan_image.copy(),
        "Scan_BinWidths_ps": nan_image.copy(),
        "Line_Shift_px": np.full(len(slow_user), np.nan, dtype=float),
        "Line_Direction": [None for _ in range(len(slow_user))],
        "xLabel": f"{_axis_label(plan.axis_1)} (um)",
        "yLabel": f"{_axis_label(plan.axis_2)} (um)",
        "zLabel": "Counts/s" if plan.normalize_to_cps else "Counts",
        "scan_mode": "hardware_mcl_cbm",
        "stage_backend": "Direct MCL/Madlib WFMA via InstrumentGateway.gw.nano",
        "daq_backend": "InstrumentGateway.gw.daq CountBetweenMarkers",
        "hardware_line_mode": plan.line_mode,
        "hardware_display_image": plan.display_image,
        "hardware_reverse_line_shift_px": float(plan.reverse_line_shift_px),
        "hardware_auto_align_reverse": bool(plan.auto_align_reverse),
        "hardware_auto_align_snake_rows": bool(plan.auto_align_snake_rows),
        "hardware_edge_blank_pixels": int(plan.edge_blank_pixels),
        "fast_axis": plan.axis_1,
        "slow_axis": plan.axis_2,
        "unscanned_axis": next(a for a in ("x", "y", "z") if a not in (plan.axis_1, plan.axis_2)),
        "cbm_click_channel": int(plan.photon_channel),
        "cbm_begin_channel": int(plan.begin_channel),
        "cbm_end_channel": int(plan.end_channel),
    }


def run_mcl_hardware_cbm_scan(
    nano: Any,
    daq: Any,
    plan: HardwareCBMScanPlan,
    publish_callback: Optional[Callable[[Dict[str, Any], int, int], None]] = None,
    stop_requested: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """Run a line-by-line direct-MCL hardware scan with Time Tagger CBM.

    Args:
        nano: Direct Madlib NanoDrive object, usually InstrumentGateway().nano.
        daq: Time Tagger driver/adapter, usually InstrumentGateway().daq or a
            GatewayTimeTaggerAdapter.
        plan: HardwareCBMScanPlan.
        publish_callback: optional callback(dataset, row, col) called after each
            completed row.  col is set to -1 for row-level updates.
        stop_requested: optional function returning True when the GUI requested
            stop.

    Returns:
        Dataset dictionary compatible with ScanPlotWidget_mm.
    """
    if nano is None:
        raise RuntimeError("Hardware scan requires gw.nano, the direct MCL/Madlib NanoDrive object.")
    if daq is None:
        raise RuntimeError("Hardware scan requires gw.daq, the Time Tagger driver object.")

    plan.validate()
    mcl_handle, mcl_handle_source, mcl_handle_acquired_here = resolve_mcl_handle(nano)

    fast_axis_id = _axis_id(plan.axis_1)
    slow_axis_id = _axis_id(plan.axis_2)
    if fast_axis_id == slow_axis_id:
        raise ValueError("Fast and slow axes must be different.")

    nx = int(plan.data_points)
    ny = int(plan.data_points)
    fast_user = np.linspace(float(plan.axis_1_min_um), float(plan.axis_1_max_um), nx)
    slow_user = np.linspace(float(plan.axis_2_min_um), float(plan.axis_2_max_um), ny)

    origin_offsets = _origin_offsets(nano, plan, mcl_handle)
    fast_hw = np.array([_user_to_hw(v, fast_axis_id, origin_offsets) for v in fast_user], dtype=float)
    slow_hw = np.array([_user_to_hw(v, slow_axis_id, origin_offsets) for v in slow_user], dtype=float)

    for value in fast_hw:
        _validate_hw_position(nano, fast_axis_id, value, plan, mcl_handle)
    for value in slow_hw:
        _validate_hw_position(nano, slow_axis_id, value, plan, mcl_handle)

    # Begin-only CBM needs one extra marker to close the last bin.  The original
    # scan did this by appending a dummy duplicate of the final waveform point.
    fast_forward_hw = np.append(fast_hw, fast_hw[-1])
    fast_backward_hw = fast_forward_hw[::-1]

    dataset = _empty_dataset(plan, fast_user, slow_user)
    dataset["mcl_handle_source"] = mcl_handle_source
    dataset["mcl_handle_acquired_here"] = bool(mcl_handle_acquired_here)
    forward_img = dataset["Scan_Forward"]
    backward_img = dataset["Scan_Backward"]
    averaged_img = dataset["Scan_Averaged"]
    raw_counts_img = dataset["Scan_Raw_Counts"]
    widths_img = dataset["Scan_BinWidths_ps"]
    display_img = dataset["Scan_Display"]
    line_shift_px = dataset["Line_Shift_px"]
    line_direction = dataset["Line_Direction"]

    _set_trigger_level_if_possible(daq, int(plan.photon_channel), plan.photon_trigger_level_v)
    _set_trigger_level_if_possible(daq, int(plan.begin_channel), plan.begin_trigger_level_v)
    _set_trigger_level_if_possible(daq, int(plan.end_channel), plan.begin_trigger_level_v)

    if plan.iss_reset_defaults and callable(getattr(nano, "iss_reset_defaults", None)):
        nano.iss_reset_defaults(mcl_handle)

    if plan.bind_pixel_clock:
        if not callable(getattr(nano, "iss_bind_clock_to_axis", None)):
            raise RuntimeError("gw.nano does not expose iss_bind_clock_to_axis(); hardware CBM mode needs MCL ISS.")
        nano.iss_bind_clock_to_axis(
            int(plan.pixel_clock),
            int(plan.pixel_clock_mode),
            int(fast_axis_id),
            int(mcl_handle),
        )

    # Initial selected-axis moves only.  The unscanned axis is never touched.
    _move_axis(nano, slow_axis_id, float(slow_hw[0]), mcl_handle, use_monitor=bool(plan.slow_axis_use_monitor))
    _move_axis(nano, fast_axis_id, float(fast_hw[0]), mcl_handle, use_monitor=True)
    if float(plan.line_settle_ms) > 0:
        time.sleep(float(plan.line_settle_ms) / 1000.0)

    last_fast_end: Optional[float] = None

    try:
        for row in range(ny):
            if stop_requested is not None and stop_requested():
                break

            _move_axis(nano, slow_axis_id, float(slow_hw[row]), mcl_handle, use_monitor=bool(plan.slow_axis_use_monitor))
            if float(plan.line_settle_ms) > 0:
                time.sleep(float(plan.line_settle_ms) / 1000.0)

            if plan.line_mode == "forward_backward_average":
                # Acquire a forward trace and a backward trace at the same slow-axis row.
                # The backward trace is reversed into forward fast-axis order, then optionally
                # shifted before averaging. Without this alignment, direction-dependent dynamic
                # lag/hysteresis can make one physical feature appear twice in the average.
                if last_fast_end is None or not math.isclose(last_fast_end, float(fast_hw[0]), abs_tol=1e-9):
                    _move_axis(nano, fast_axis_id, float(fast_hw[0]), mcl_handle, use_monitor=True)
                if float(plan.line_settle_ms) > 0:
                    time.sleep(float(plan.line_settle_ms) / 1000.0)

                _wfma_setup_one_axis(nano, fast_axis_id, fast_forward_hw, plan.dwell_time_ms, mcl_handle)
                _start_cbm_line(daq, plan, nx)
                nano.wfma_trigger(mcl_handle)
                _wait_for_cbm_ready(daq, plan.line_timeout_s, plan.poll_interval_ms, stop_requested)
                f_values, f_counts, f_widths = _read_cbm_line(
                    daq, nx, plan.normalize_to_cps, plan.use_bin_widths, plan.dwell_time_ms
                )
                if callable(getattr(daq, "cbm_clear", None)):
                    daq.cbm_clear()
                last_fast_end = float(fast_hw[-1])

                _wfma_setup_one_axis(nano, fast_axis_id, fast_backward_hw, plan.dwell_time_ms, mcl_handle)
                _start_cbm_line(daq, plan, nx)
                nano.wfma_trigger(mcl_handle)
                _wait_for_cbm_ready(daq, plan.line_timeout_s, plan.poll_interval_ms, stop_requested)
                b_values_raw, b_counts_raw, b_widths_raw = _read_cbm_line(
                    daq, nx, plan.normalize_to_cps, plan.use_bin_widths, plan.dwell_time_ms
                )
                if callable(getattr(daq, "cbm_clear", None)):
                    daq.cbm_clear()

                # Reverse backward data into displayed fast-axis coordinate order.
                b_values = b_values_raw[::-1]
                b_counts = b_counts_raw[::-1]
                b_widths = b_widths_raw[::-1]

                shift_px = float(plan.reverse_line_shift_px)
                if bool(plan.auto_align_reverse):
                    shift_px += _estimate_shift_pixels(f_values, b_values, plan.auto_align_max_shift_px)
                if abs(shift_px) > 1e-12:
                    b_values = _shift_line(b_values, shift_px)
                    b_counts = _shift_line(b_counts, shift_px)
                    b_widths = _shift_line(b_widths, shift_px)
                if int(plan.edge_blank_pixels) > 0:
                    f_values = _blank_edges(f_values, plan.edge_blank_pixels)
                    b_values = _blank_edges(b_values, plan.edge_blank_pixels)
                    f_counts = _blank_edges(f_counts, plan.edge_blank_pixels)
                    b_counts = _blank_edges(b_counts, plan.edge_blank_pixels)
                    f_widths = _blank_edges(f_widths, plan.edge_blank_pixels)
                    b_widths = _blank_edges(b_widths, plan.edge_blank_pixels)

                avg_values = _nanmean2(f_values, b_values)
                display_line = _select_display_line(plan.display_image, f_values, b_values, avg_values)

                forward_img[row, :] = f_values
                backward_img[row, :] = b_values
                averaged_img[row, :] = avg_values
                display_img[row, :] = display_line
                raw_counts_img[row, :] = f_counts
                widths_img[row, :] = f_widths
                line_shift_px[row] = shift_px
                line_direction[row] = "forward+backward"
                last_fast_end = float(fast_hw[0])

            elif plan.line_mode == "forward_only":
                # Acquire only forward-going data. This is the safest hardware mode when
                # direction-dependent lag makes reverse data appear shifted. It still uses
                # the MCL hardware waveform for the fast axis, but it does not mix forward
                # and reverse photon bins in one displayed image.
                line_start = float(fast_hw[0])
                line_end = float(fast_hw[-1])
                if last_fast_end is None or not math.isclose(last_fast_end, line_start, abs_tol=1e-9):
                    _move_axis(nano, fast_axis_id, line_start, mcl_handle, use_monitor=True)
                if float(plan.line_settle_ms) > 0:
                    time.sleep(float(plan.line_settle_ms) / 1000.0)

                _wfma_setup_one_axis(nano, fast_axis_id, fast_forward_hw, plan.dwell_time_ms, mcl_handle)
                _start_cbm_line(daq, plan, nx)
                nano.wfma_trigger(mcl_handle)
                _wait_for_cbm_ready(daq, plan.line_timeout_s, plan.poll_interval_ms, stop_requested)
                values, counts, widths_ps = _read_cbm_line(
                    daq, nx, plan.normalize_to_cps, plan.use_bin_widths, plan.dwell_time_ms
                )
                if callable(getattr(daq, "cbm_clear", None)):
                    daq.cbm_clear()
                last_fast_end = line_end

                if int(plan.edge_blank_pixels) > 0:
                    values = _blank_edges(values, plan.edge_blank_pixels)
                    counts = _blank_edges(counts, plan.edge_blank_pixels)
                    widths_ps = _blank_edges(widths_ps, plan.edge_blank_pixels)

                forward_img[row, :] = values
                averaged_img[row, :] = values
                display_img[row, :] = values
                raw_counts_img[row, :] = counts
                widths_img[row, :] = widths_ps
                line_shift_px[row] = 0.0
                line_direction[row] = "forward"

            else:
                # snake_single_line: alternate fast-axis direction row-by-row and reverse odd
                # rows into the common display coordinate order. This is fastest, but if the
                # scanner has direction-dependent lag, odd rows may need a manual/auto shift.
                reverse_line = bool(plan.bidirectional and (row % 2 == 1))
                line_waveform = fast_backward_hw if reverse_line else fast_forward_hw
                line_start = float(fast_hw[-1] if reverse_line else fast_hw[0])
                line_end = float(fast_hw[0] if reverse_line else fast_hw[-1])

                if last_fast_end is None or not math.isclose(last_fast_end, line_start, abs_tol=1e-9):
                    _move_axis(nano, fast_axis_id, line_start, mcl_handle, use_monitor=True)
                if float(plan.line_settle_ms) > 0:
                    time.sleep(float(plan.line_settle_ms) / 1000.0)

                _wfma_setup_one_axis(nano, fast_axis_id, line_waveform, plan.dwell_time_ms, mcl_handle)
                _start_cbm_line(daq, plan, nx)
                nano.wfma_trigger(mcl_handle)
                _wait_for_cbm_ready(daq, plan.line_timeout_s, plan.poll_interval_ms, stop_requested)
                values, counts, widths_ps = _read_cbm_line(
                    daq, nx, plan.normalize_to_cps, plan.use_bin_widths, plan.dwell_time_ms
                )
                if callable(getattr(daq, "cbm_clear", None)):
                    daq.cbm_clear()
                last_fast_end = line_end

                shift_px = 0.0
                direction_label = "backward" if reverse_line else "forward"
                if reverse_line:
                    values = values[::-1]
                    counts = counts[::-1]
                    widths_ps = widths_ps[::-1]
                    shift_px = float(plan.reverse_line_shift_px)
                    if bool(plan.auto_align_snake_rows) and row > 0:
                        shift_px += _estimate_shift_pixels(display_img[row - 1, :], values, plan.auto_align_max_shift_px)
                    if abs(shift_px) > 1e-12:
                        values = _shift_line(values, shift_px)
                        counts = _shift_line(counts, shift_px)
                        widths_ps = _shift_line(widths_ps, shift_px)
                if int(plan.edge_blank_pixels) > 0:
                    values = _blank_edges(values, plan.edge_blank_pixels)
                    counts = _blank_edges(counts, plan.edge_blank_pixels)
                    widths_ps = _blank_edges(widths_ps, plan.edge_blank_pixels)

                forward_img[row, :] = values
                averaged_img[row, :] = values
                display_img[row, :] = values
                raw_counts_img[row, :] = counts
                widths_img[row, :] = widths_ps
                line_shift_px[row] = shift_px
                line_direction[row] = direction_label

            dataset["Scan_Forward"] = forward_img.copy()
            dataset["Scan_Backward"] = backward_img.copy()
            dataset["Scan_Averaged"] = averaged_img.copy()
            dataset["Scan_Display"] = display_img.copy()
            dataset["Scan_Raw_Counts"] = raw_counts_img.copy()
            dataset["Scan_BinWidths_ps"] = widths_img.copy()
            dataset["Line_Shift_px"] = np.asarray(line_shift_px, dtype=float).copy()
            dataset["Line_Direction"] = list(line_direction)
            dataset["Scan_Display_Source"] = plan.display_image if plan.line_mode == "forward_backward_average" else plan.line_mode
            dataset["last_completed_row"] = int(row)
            dataset["last_pixel"] = (int(row), -1)
            if publish_callback is not None:
                publish_callback(dict(dataset), row, -1)

    except KeyboardInterrupt:
        dataset["stopped"] = True
    finally:
        # Stop waveform if the driver exposes the call.  Do not release the
        # instrument-server handle here; gw.nano owns it.
        try:
            if callable(_safe_getattr(nano, "wfma_stop", None)):
                nano.wfma_stop(mcl_handle)
        except Exception:
            pass
        release_mcl_handle_if_needed(nano, mcl_handle, mcl_handle_acquired_here, release=False)

    return dataset
