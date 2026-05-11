"""
Confocal scan helpers using Micro-Manager/Pycro-Manager stage control and a
Swabian Time Tagger detector.

This module is intentionally GUI-independent. The nspyre/Qt GUI can call these
functions, and so can a console script for hardware debugging.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Mapping, Optional

import numpy as np

try:
    from template.drivers.MCL_MicroManager_Wrapper_mm import MicroManagerMCLStage
    from template.drivers.TimeTaggerDriver_mm import tt20
except Exception:
    from template.drivers.MCL_MicroManager_Wrapper_mm import MicroManagerMCLStage
    from template.drivers.TimeTaggerDriver_mm import tt20


@dataclass
class SoftwareRasterScanPlan:
    axis_1: str = "x"          # fast axis: x, y, or z
    axis_2: str = "y"          # slow axis: x, y, or z
    axis_1_min_um: float = -10.0
    axis_1_max_um: float = 10.0
    axis_2_min_um: float = -10.0
    axis_2_max_um: float = 10.0
    data_points: int = 10
    dwell_time_ms: float = 5.0
    photon_channel: int = 1
    trigger_level_v: Optional[float] = None
    bidirectional: bool = True
    normalize_to_cps: bool = True
    fixed_axes_um: Dict[str, float] = field(default_factory=dict)

    def validate(self) -> None:
        axes = [self.axis_1.lower(), self.axis_2.lower()]
        if any(axis not in ("x", "y", "z") for axis in axes):
            raise ValueError("axis_1 and axis_2 must be x, y, or z.")
        if axes[0] == axes[1]:
            raise ValueError("axis_1 and axis_2 must be different.")
        if int(self.data_points) < 2:
            raise ValueError("data_points must be at least 2.")
        if float(self.dwell_time_ms) <= 0:
            raise ValueError("dwell_time_ms must be positive.")

    @property
    def x_steps(self):
        return np.linspace(float(self.axis_1_min_um), float(self.axis_1_max_um), int(self.data_points))

    @property
    def y_steps(self):
        return np.linspace(float(self.axis_2_min_um), float(self.axis_2_max_um), int(self.data_points))


def _empty_dataset(plan: SoftwareRasterScanPlan):
    x_steps = plan.x_steps
    y_steps = plan.y_steps
    image = np.full((len(y_steps), len(x_steps)), np.nan, dtype=float)
    return {
        "title": "2D_Scan_mm",
        "xSteps": x_steps,
        "ySteps": y_steps,
        "Scan_Forward": image.copy(),
        "Scan_Backward": np.full_like(image, np.nan),
        "Scan_Averaged": image.copy(),
        "xLabel": f"{plan.axis_1.lower()} (um)",
        "yLabel": f"{plan.axis_2.lower()} (um)",
        "units": "counts/s" if plan.normalize_to_cps else "counts",
        "scan_backend": "micro-manager-pycromanager-software-raster",
    }


def software_raster_scan(stage: MicroManagerMCLStage,
                         detector: tt20,
                         plan: SoftwareRasterScanPlan,
                         publish_callback: Optional[Callable[[dict, int, int], None]] = None,
                         stop_requested: Optional[Callable[[], bool]] = None) -> dict:
    """Run a software-timed raster scan.

    The stage is moved through Micro-Manager. The detector counts one Time Tagger
    channel for each pixel dwell. The returned dataset is compatible with the
    ScanPlotWidget in gui_2D_Scan_mm.py.
    """
    plan.validate()
    axis_fast = plan.axis_1.lower()
    axis_slow = plan.axis_2.lower()
    x_steps = plan.x_steps
    y_steps = plan.y_steps
    dataset = _empty_dataset(plan)
    image = dataset["Scan_Forward"]

    # Move non-scanned axes, if requested.
    fixed_targets = {
        axis.lower(): float(value)
        for axis, value in plan.fixed_axes_um.items()
        if axis.lower() in ("x", "y", "z") and axis.lower() not in (axis_fast, axis_slow)
    }
    if fixed_targets:
        stage.move_axes(fixed_targets, wait=True)

    if publish_callback is not None:
        publish_callback(dataset, -1, -1)

    for row, slow_value in enumerate(y_steps):
        if stop_requested is not None and stop_requested():
            break

        if plan.bidirectional and row % 2:
            col_order = range(len(x_steps) - 1, -1, -1)
        else:
            col_order = range(len(x_steps))

        for col in col_order:
            if stop_requested is not None and stop_requested():
                break
            fast_value = float(x_steps[col])
            stage.move_axes({axis_slow: float(slow_value), axis_fast: fast_value}, wait=True)
            counts = detector.count_for_ms(
                channel=int(plan.photon_channel),
                dwell_ms=float(plan.dwell_time_ms),
                trigger_level=plan.trigger_level_v,
                normalized=bool(plan.normalize_to_cps),
            )
            image[row, col] = counts
            dataset["Scan_Averaged"] = image.copy()
            if publish_callback is not None:
                publish_callback(dataset, row, col)

    return dataset


def hardware_gated_scan(detector: tt20,
                        click_channel: int,
                        begin_channel: int,
                        end_channel: int,
                        nx: int,
                        ny: int,
                        start_callback: Callable[[], None],
                        x_steps=None,
                        y_steps=None,
                        timeout_s: Optional[float] = None,
                        partial_callback: Optional[Callable[[np.ndarray], None]] = None) -> dict:
    """Run a hardware-gated scan using Time Tagger CountBetweenMarkers.

    start_callback must start the stage waveform or external scanner that emits
    the marker pulses. The function does not itself program MCL ISS/waveforms.
    """
    image = detector.count_between_markers_image(
        click_channel=click_channel,
        begin_channel=begin_channel,
        end_channel=end_channel,
        nx=nx,
        ny=ny,
        start_callback=start_callback,
        timeout_s=timeout_s,
        partial_callback=partial_callback,
    )
    if x_steps is None:
        x_steps = np.arange(nx, dtype=float)
    if y_steps is None:
        y_steps = np.arange(ny, dtype=float)
    return {
        "title": "2D_Scan_mm_hardware_gated",
        "xSteps": np.asarray(x_steps, dtype=float),
        "ySteps": np.asarray(y_steps, dtype=float),
        "Scan_Forward": image,
        "Scan_Backward": np.full_like(image, np.nan),
        "Scan_Averaged": image.copy(),
        "xLabel": "x (um)",
        "yLabel": "y (um)",
        "units": "counts/pixel",
        "scan_backend": "micro-manager-pycromanager-hardware-gated-cbm",
    }
