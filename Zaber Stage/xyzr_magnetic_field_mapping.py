from __future__ import annotations

"""
Python version of the MATLAB function `XYZR_MagnetfieldMapingV2`.

This script keeps the same overall behavior:
- open the 3MTS teslameter
- set the sensor range
- expand a 3D scan box outward from a center point
- scan X/Y/Z/R in a snake pattern
- average multiple magnetic-field readings per point
- skip the already-scanned inner box on later passes
- save each pass as rawdataN.mat (and rawdataN.csv)

It is based on the usage patterns in `wrapper_test.py` and `TM_Wrapper.py`.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Sequence, Tuple
import ctypes as C
import json
import math
import time

import numpy as np

try:
    from scipy.io import savemat
except Exception:  # pragma: no cover - optional dependency
    savemat = None

from zaber_motion import Units
from zaber_motion.ascii import Connection
import TM_Wrapper


CM = Units.LENGTH_CENTIMETRES
DEG = Units.ANGLE_DEGREES

RANGE_CODE = {
    "0.1": 0,
    "0.5": 1,
    "3": 2,
    "20": 3,
    0.1: 0,
    0.5: 1,
    3: 2,
    20: 3,
}


class TeslaMeterError(RuntimeError):
    """Raised when the 3MTS SDK returns a non-zero error status."""


@dataclass(frozen=True)
class Bounds3D:
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float


@dataclass(frozen=True)
class ScanConfig:
    # Communication
    com_port: str
    dll_path: str
    output_dir: str

    # Device assignment: indices in the list returned by conn.detect_devices().
    # wrapper_test.py uses X=0, Y=1, Z=3, R=2.
    device_order: Tuple[int, int, int, int] = (0, 1, 3, 2)
    teslameter_device_number: int = 0

    # Teslameter settings
    sensor_range_t: str = "0.5"
    samples_per_point: int = 10
    clear_buffer_before_scan: bool = True
    settle_time_s: float = 0.1
    retry_delay_s: float = 0.01
    max_no_new_value_retries_per_sample: int = 100

    # Global scan region in cm / degrees
    x_min_cm: float = 0.0
    x_max_cm: float = 1.0
    y_min_cm: float = 0.0
    y_max_cm: float = 1.0
    z_min_cm: float = 0.0
    z_max_cm: float = 1.0
    r_min_deg: float = 0.0
    r_max_deg: float = 0.0

    # Center point and initial cube size in cm
    x_center_cm: float = 0.5
    y_center_cm: float = 0.5
    z_center_cm: float = 0.5
    base_dim_cm: float = 0.5

    # Points per axis for each pass
    n_x: int = 5
    n_y: int = 5
    n_z: int = 5
    n_r: int = 1

    # Output / behavior
    convert_ut_to_gauss: bool = True
    save_csv_copy: bool = True
    save_metadata_json: bool = True
    wait_until_idle: bool = True
    enable_alerts: bool = True
    home_axes_before_scan: bool = False


class TeslaWrapperFlexible(TM_Wrapper.Tesla_Wrapper):
    """
    Compatibility wrapper around TM_Wrapper.Tesla_Wrapper that accepts a DLL path
    and exposes status-checked methods.
    """

    def __init__(self, dll_path: str):
        self.A3mtslib = C.CDLL(str(dll_path))
        self.device_number = C.c_int()
        self.timestamp = C.c_ulong()
        self.sensor_x = C.c_float()
        self.sensor_y = C.c_float()
        self.sensor_z = C.c_float()
        self._configure_signatures()

    def _configure_signatures(self) -> None:
        self.A3mtslib.count_devices.argtypes = [C.POINTER(C.c_ushort)]
        self.A3mtslib.count_devices.restype = C.c_int

        self.A3mtslib.open_device.argtypes = [C.POINTER(C.c_int)]
        self.A3mtslib.open_device.restype = C.c_int

        self.A3mtslib.close_device.argtypes = [C.POINTER(C.c_int)]
        self.A3mtslib.close_device.restype = C.c_int

        self.A3mtslib.get_sensor_count.argtypes = [C.POINTER(C.c_int), C.POINTER(C.c_int)]
        self.A3mtslib.get_sensor_count.restype = C.c_int

        self.A3mtslib.get_sensor_values_fl.argtypes = [
            C.POINTER(C.c_int),
            C.POINTER(C.c_ulong),
            C.POINTER(C.c_float),
            C.POINTER(C.c_float),
            C.POINTER(C.c_float),
        ]
        self.A3mtslib.get_sensor_values_fl.restype = C.c_int

        self.A3mtslib.set_range.argtypes = [C.POINTER(C.c_int), C.c_ushort]
        self.A3mtslib.set_range.restype = C.c_int

        self.A3mtslib.get_range.argtypes = [C.POINTER(C.c_int), C.POINTER(C.c_ushort)]
        self.A3mtslib.get_range.restype = C.c_int

        self.A3mtslib.clear_buffer.argtypes = [C.POINTER(C.c_int)]
        self.A3mtslib.clear_buffer.restype = C.c_int

        self.A3mtslib.get_device_name_ch.argtypes = [C.POINTER(C.c_int), C.c_char_p]
        self.A3mtslib.get_device_name_ch.restype = C.c_int

    @staticmethod
    def _check_status(status: int, context: str, allow_no_new_value: bool = False) -> None:
        if status == 0:
            return
        if status == 0x0001 and allow_no_new_value:
            return
        if status == 0x0001:
            raise TeslaMeterError(f"{context}: no new value available from teslameter buffer (status=0x0001)")
        if status == 0x8000:
            raise TeslaMeterError(f"{context}: device not initialized (status=0x8000)")
        if status == 0x8001:
            raise TeslaMeterError(f"{context}: range outside valid value range (status=0x8001)")
        raise TeslaMeterError(f"{context}: SDK returned status {status:#06x}")

    def count_devices_checked(self) -> int:
        count = C.c_ushort()
        status = int(self.A3mtslib.count_devices(C.byref(count)))
        self._check_status(status, "count_devices")
        return int(count.value)

    def open_device_checked(self, device_number: int = 0) -> int:
        self.device_number = C.c_int(device_number)
        status = int(self.A3mtslib.open_device(C.byref(self.device_number)))
        self._check_status(status, "open_device")
        return int(self.device_number.value)

    def close_device_checked(self) -> int:
        status = int(self.A3mtslib.close_device(C.byref(self.device_number)))
        self._check_status(status, "close_device")
        return int(self.device_number.value)

    def set_range_checked(self, range_code: int) -> None:
        status = int(self.A3mtslib.set_range(C.byref(self.device_number), C.c_ushort(range_code)))
        self._check_status(status, "set_range")

    def clear_buffer_checked(self) -> None:
        status = int(self.A3mtslib.clear_buffer(C.byref(self.device_number)))
        self._check_status(status, "clear_buffer")

    def get_device_name_checked(self) -> str:
        buf = C.create_string_buffer(40)
        status = int(self.A3mtslib.get_device_name_ch(C.byref(self.device_number), buf))
        self._check_status(status, "get_device_name_ch")
        return buf.value.decode(errors="replace")

    def get_sensor_values_checked(self, allow_no_new_value: bool = False) -> Tuple[int, int, float, float, float]:
        status = int(
            self.A3mtslib.get_sensor_values_fl(
                C.byref(self.device_number),
                C.byref(self.timestamp),
                C.byref(self.sensor_x),
                C.byref(self.sensor_y),
                C.byref(self.sensor_z),
            )
        )
        self._check_status(status, "get_sensor_values_fl", allow_no_new_value=allow_no_new_value)
        return (
            status,
            int(self.timestamp.value),
            float(self.sensor_x.value),
            float(self.sensor_y.value),
            float(self.sensor_z.value),
        )

    def average_sensor_value_checked(
        self,
        n_samples_to_avg: int,
        retry_delay_s: float = 0.01,
        max_no_new_value_retries_per_sample: int = 100,
    ) -> Tuple[float, float, float]:
        if n_samples_to_avg <= 0:
            raise ValueError("n_samples_to_avg must be >= 1")

        total_x = 0.0
        total_y = 0.0
        total_z = 0.0
        samples_collected = 0
        no_new_value_retries = 0

        while samples_collected < n_samples_to_avg:
            status, _, x, y, z = self.get_sensor_values_checked(allow_no_new_value=True)

            if status == 0x0001:
                no_new_value_retries += 1
                if no_new_value_retries > max_no_new_value_retries_per_sample:
                    raise TeslaMeterError(
                        "Exceeded maximum retries while waiting for a new teslameter sample."
                    )
                time.sleep(retry_delay_s)
                continue

            total_x += x
            total_y += y
            total_z += z
            samples_collected += 1
            no_new_value_retries = 0

        return (
            total_x / n_samples_to_avg,
            total_y / n_samples_to_avg,
            total_z / n_samples_to_avg,
        )

    def __enter__(self) -> "TeslaWrapperFlexible":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self.close_device_checked()
        except Exception:
            pass


def resolve_range_code(sensor_range_t: str | float | int) -> int:
    if sensor_range_t in RANGE_CODE:
        return RANGE_CODE[sensor_range_t]

    sensor_range_str = str(sensor_range_t).strip()
    if sensor_range_str in RANGE_CODE:
        return RANGE_CODE[sensor_range_str]

    raise ValueError(
        f"Unsupported sensor range {sensor_range_t!r}. Use one of 0.1, 0.5, 3, 20."
    )


def compute_axis_bounds(center: float, sweep_length: float, global_min: float, global_max: float) -> Tuple[float, float]:
    """
    Replicates the MATLAB edge-handling logic:
    - start with a centered interval
    - if it crosses an edge, shift it so the interval keeps the same length when possible
    - if the requested sweep exceeds the global range, clamp to the full range
    """
    min_s = center - sweep_length / 2.0
    max_s = center + sweep_length / 2.0

    counter = 0
    if min_s <= global_min:
        min_s = global_min
        max_s = min_s + sweep_length
        counter += 1

    if max_s >= global_max:
        max_s = global_max
        min_s = max_s - sweep_length
        counter += 1

    if counter == 2:
        min_s = global_min
        max_s = global_max

    min_s = max(min_s, global_min)
    max_s = min(max_s, global_max)
    return min_s, max_s


def compute_scan_bounds(config: ScanConfig, pass_index: int) -> Bounds3D:
    sweep_length_cm = (2 ** pass_index) * config.base_dim_cm

    x_min, x_max = compute_axis_bounds(config.x_center_cm, sweep_length_cm, config.x_min_cm, config.x_max_cm)
    y_min, y_max = compute_axis_bounds(config.y_center_cm, sweep_length_cm, config.y_min_cm, config.y_max_cm)
    z_min, z_max = compute_axis_bounds(config.z_center_cm, sweep_length_cm, config.z_min_cm, config.z_max_cm)

    return Bounds3D(
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        z_min=z_min,
        z_max=z_max,
    )


def same_bounds(a: Bounds3D, b: Bounds3D, tol: float = 1e-12) -> bool:
    return (
        math.isclose(a.x_min, b.x_min, abs_tol=tol)
        and math.isclose(a.x_max, b.x_max, abs_tol=tol)
        and math.isclose(a.y_min, b.y_min, abs_tol=tol)
        and math.isclose(a.y_max, b.y_max, abs_tol=tol)
        and math.isclose(a.z_min, b.z_min, abs_tol=tol)
        and math.isclose(a.z_max, b.z_max, abs_tol=tol)
    )


def point_inside_bounds(x_cm: float, y_cm: float, z_cm: float, bounds: Bounds3D) -> bool:
    return (
        bounds.x_min <= x_cm <= bounds.x_max
        and bounds.y_min <= y_cm <= bounds.y_max
        and bounds.z_min <= z_cm <= bounds.z_max
    )


def maybe_wait(axis) -> None:
    if hasattr(axis, "wait_until_idle"):
        axis.wait_until_idle()


def move_all_axes(axis_x, axis_y, axis_z, axis_r, x_cm: float, y_cm: float, z_cm: float, r_deg: float, wait_until_idle: bool) -> None:
    axis_x.move_absolute(float(x_cm), CM)
    axis_y.move_absolute(float(y_cm), CM)
    axis_z.move_absolute(float(z_cm), CM)
    axis_r.move_absolute(float(r_deg), DEG)

    if wait_until_idle:
        maybe_wait(axis_x)
        maybe_wait(axis_y)
        maybe_wait(axis_z)
        maybe_wait(axis_r)


def read_positions(axis_x, axis_y, axis_z, axis_r) -> Tuple[float, float, float, float]:
    return (
        float(axis_x.get_position(CM)),
        float(axis_y.get_position(CM)),
        float(axis_z.get_position(CM)),
        float(axis_r.get_position(DEG)),
    )


def save_scan_pass(
    output_dir: Path,
    pass_index: int,
    rawdata: np.ndarray,
    config: ScanConfig,
    bounds: Bounds3D,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_dir / f"rawdata{pass_index}"

    field_unit = "G" if config.convert_ut_to_gauss else "uT"
    columns = [
        "x_cm",
        "y_cm",
        "z_cm",
        "r_deg",
        f"bx_{field_unit}",
        f"by_{field_unit}",
        f"bz_{field_unit}",
    ]

    metadata = {
        "pass_index": pass_index,
        "bounds_cm": asdict(bounds),
        "config": asdict(config),
        "columns": columns,
    }

    if savemat is not None:
        savemat(
            str(stem.with_suffix(".mat")),
            {
                "rawdata": rawdata,
                "columns": np.asarray(columns, dtype=object),
                "metadata_json": json.dumps(metadata, indent=2),
            },
        )

    if config.save_csv_copy:
        header = ",".join(columns)
        np.savetxt(str(stem.with_suffix(".csv")), rawdata, delimiter=",", header=header, comments="")

    if config.save_metadata_json:
        with open(stem.with_name(stem.name + "_meta.json"), "w", encoding="utf-8") as fh:
            json.dump(metadata, fh, indent=2)


def xyzr_magnetfield_mapping_v2(config: ScanConfig) -> list[np.ndarray]:
    """
    Run the expanding-box magnetic-field scan.

    Returns
    -------
    list[np.ndarray]
        One array per pass. Each row is:
        [x_cm, y_cm, z_cm, r_deg, bx, by, bz]
    """
    if config.samples_per_point < 1:
        raise ValueError("samples_per_point must be >= 1")
    if min(config.n_x, config.n_y, config.n_z, config.n_r) < 1:
        raise ValueError("n_x, n_y, n_z, and n_r must all be >= 1")
    if config.base_dim_cm <= 0:
        raise ValueError("base_dim_cm must be > 0")

    global_bounds = Bounds3D(
        x_min=config.x_min_cm,
        x_max=config.x_max_cm,
        y_min=config.y_min_cm,
        y_max=config.y_max_cm,
        z_min=config.z_min_cm,
        z_max=config.z_max_cm,
    )

    output_dir = Path(config.output_dir)
    all_passes: list[np.ndarray] = []
    previous_bounds: Optional[Bounds3D] = None

    with Connection.open_serial_port(config.com_port) as conn:
        if config.enable_alerts:
            conn.enable_alerts()

        device_list = conn.detect_devices()
        if len(device_list) < 4:
            raise RuntimeError(f"Expected at least 4 Zaber devices, found {len(device_list)}")

        max_requested_index = max(config.device_order)
        if max_requested_index >= len(device_list):
            raise RuntimeError(
                f"device_order={config.device_order} requires at least {max_requested_index + 1} devices, "
                f"but only {len(device_list)} were detected"
            )

        dev_x = device_list[config.device_order[0]]
        dev_y = device_list[config.device_order[1]]
        dev_z = device_list[config.device_order[2]]
        dev_r = device_list[config.device_order[3]]

        axis_x = dev_x.get_axis(1)
        axis_y = dev_y.get_axis(1)
        axis_z = dev_z.get_axis(1)
        axis_r = dev_r.get_axis(1)

        if config.home_axes_before_scan:
            for axis in (axis_x, axis_y, axis_z, axis_r):
                if hasattr(axis, "home"):
                    axis.home()
            if config.wait_until_idle:
                for axis in (axis_x, axis_y, axis_z, axis_r):
                    maybe_wait(axis)

        with TeslaWrapperFlexible(config.dll_path) as tm:
            detected_tm_devices = tm.count_devices_checked()
            print(f"Teslameter devices detected: {detected_tm_devices}")

            tm.open_device_checked(config.teslameter_device_number)
            tm.set_range_checked(resolve_range_code(config.sensor_range_t))
            if config.clear_buffer_before_scan:
                tm.clear_buffer_checked()

            try:
                print(f"Teslameter name: {tm.get_device_name_checked()}")
            except Exception:
                pass

            pass_index = 0
            while True:
                current_bounds = compute_scan_bounds(config, pass_index)

                x_forward = np.linspace(current_bounds.x_min, current_bounds.x_max, config.n_x).tolist()
                y_forward = np.linspace(current_bounds.y_min, current_bounds.y_max, config.n_y).tolist()
                z_forward = np.linspace(current_bounds.z_min, current_bounds.z_max, config.n_z).tolist()
                r_forward = np.linspace(config.r_min_deg, config.r_max_deg, config.n_r).tolist()

                y_backward = list(reversed(y_forward))
                z_backward = list(reversed(z_forward))
                r_backward = list(reversed(r_forward))

                rows: list[list[float]] = []
                point_counter = 0

                print(
                    f"Starting pass {pass_index}: "
                    f"X[{current_bounds.x_min:.4f}, {current_bounds.x_max:.4f}] cm, "
                    f"Y[{current_bounds.y_min:.4f}, {current_bounds.y_max:.4f}] cm, "
                    f"Z[{current_bounds.z_min:.4f}, {current_bounds.z_max:.4f}] cm"
                )

                for i, x_target in enumerate(x_forward):
                    y_range = y_backward if (i % 2 == 1) else y_forward

                    for j, y_target in enumerate(y_range):
                        z_range = z_backward if (j % 2 == 1) else z_forward

                        for k, z_target in enumerate(z_range):
                            r_range = r_backward if (k % 2 == 1) else r_forward

                            # Match MATLAB behavior: skip points inside the previously scanned inner box.
                            if previous_bounds is not None and point_inside_bounds(x_target, y_target, z_target, previous_bounds):
                                continue

                            for r_target in r_range:
                                move_all_axes(
                                    axis_x,
                                    axis_y,
                                    axis_z,
                                    axis_r,
                                    x_target,
                                    y_target,
                                    z_target,
                                    r_target,
                                    wait_until_idle=config.wait_until_idle,
                                )

                                x_value, y_value, z_value, r_value = read_positions(axis_x, axis_y, axis_z, axis_r)
                                time.sleep(config.settle_time_s)

                                bx_ut, by_ut, bz_ut = tm.average_sensor_value_checked(
                                    config.samples_per_point,
                                    retry_delay_s=config.retry_delay_s,
                                    max_no_new_value_retries_per_sample=config.max_no_new_value_retries_per_sample,
                                )

                                if config.convert_ut_to_gauss:
                                    bx_out = bx_ut / 100.0
                                    by_out = by_ut / 100.0
                                    bz_out = bz_ut / 100.0
                                else:
                                    bx_out = bx_ut
                                    by_out = by_ut
                                    bz_out = bz_ut

                                rows.append([
                                    x_value,
                                    y_value,
                                    z_value,
                                    r_value,
                                    bx_out,
                                    by_out,
                                    bz_out,
                                ])
                                point_counter += 1

                rawdata = np.asarray(rows, dtype=float)
                save_scan_pass(output_dir, pass_index, rawdata, config, current_bounds)
                all_passes.append(rawdata)
                print(f"Completed pass {pass_index}. Saved {point_counter} points.")

                previous_bounds = current_bounds
                if same_bounds(current_bounds, global_bounds):
                    break

                pass_index += 1

    return all_passes


if __name__ == "__main__":
    # Replace these example values with your real hardware setup.
    config = ScanConfig(
        com_port="COM4",
        dll_path=r"C:\path\to\a3mtslib64.dll",
        output_dir=r"C:\path\to\RawData",
        device_order=(0, 1, 3, 2),  # matches wrapper_test.py
        sensor_range_t="0.5",
        samples_per_point=10,
        x_min_cm=0.0,
        x_max_cm=3.0,
        y_min_cm=0.0,
        y_max_cm=3.0,
        z_min_cm=0.0,
        z_max_cm=3.0,
        r_min_deg=0.0,
        r_max_deg=90.0,
        x_center_cm=1.5,
        y_center_cm=1.5,
        z_center_cm=1.5,
        base_dim_cm=0.5,
        n_x=11,
        n_y=11,
        n_z=11,
        n_r=3,
        convert_ut_to_gauss=True,
        save_csv_copy=True,
        save_metadata_json=True,
        wait_until_idle=True,
        enable_alerts=True,
        home_axes_before_scan=False,
    )

    xyzr_magnetfield_mapping_v2(config)
