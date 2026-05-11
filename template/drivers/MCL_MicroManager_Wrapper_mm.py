"""
Micro-Manager/Pycro-Manager wrapper for the Mad City Labs MCL 3D200FT.

This file replaces direct Madlib control for the Micro-Manager version of the
motion and scan GUIs. Do not use this at the same time as a Python Madlib handle
for the same controller. Micro-Manager should be the single owner of the MCL
NanoDrive when these mm scripts are used.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple, Union

Axis = Union[int, str]

AXIS_NAME_TO_NUMBER = {"x": 1, "y": 2, "z": 3}
AXIS_NUMBER_TO_NAME = {1: "x", 2: "y", 3: "z"}


@dataclass
class MCLStageConfig:
    """Configuration for the Micro-Manager MCL stage backend."""

    xy_device: str = "MCL NanoDrive XY Stage"
    z_device: str = "MCL NanoDrive Z Stage"
    axis_min_um: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    axis_max_um: Tuple[float, float, float] = (200.0, 200.0, 200.0)
    user_origin_mode: str = "center"  # center or current
    timeout_ms: int = 10000
    settling_time_ms: Optional[float] = None
    set_core_roles: bool = True
    mm_config_file: Optional[str] = None
    mm_app_path: Optional[str] = None
    port: int = 4827
    debug: bool = False


class MicroManagerMCLStage:
    """Small Pycro-Manager Core wrapper for MCL XY and Z stages.

    Public coordinates are user-centered micrometers. With the default 200 um
    travel range, user x/y/z = 0 corresponds to hardware x/y/z = 100 um.
    """

    def __init__(self, config: Optional[MCLStageConfig] = None, core=None):
        self.config = config or MCLStageConfig()
        self._headless_started = False
        if core is None:
            try:
                from pycromanager import Core
            except Exception as exc:  # pragma: no cover - hardware environment only
                raise RuntimeError(
                    "Could not import pycromanager.Core. Install pycromanager and "
                    "start Micro-Manager/Pycro-Manager before using the mm stage backend."
                ) from exc
            if self.config.mm_app_path:
                from pycromanager import start_headless
                start_headless(
                    self.config.mm_app_path,
                    config_file=self.config.mm_config_file,
                    port=int(self.config.port),
                    debug=bool(self.config.debug),
                )
                self._headless_started = True
            core = Core(port=int(self.config.port))
        self.core = core
        if self.config.mm_config_file and not self.config.mm_app_path:
            try:
                self._method("load_system_configuration", "loadSystemConfiguration")(self.config.mm_config_file)
            except Exception:
                pass

        self.axis_min = {
            1: float(self.config.axis_min_um[0]),
            2: float(self.config.axis_min_um[1]),
            3: float(self.config.axis_min_um[2]),
        }
        self.axis_max = {
            1: float(self.config.axis_max_um[0]),
            2: float(self.config.axis_max_um[1]),
            3: float(self.config.axis_max_um[2]),
        }
        self.axis_origin = {
            axis: 0.5 * (self.axis_min[axis] + self.axis_max[axis])
            for axis in (1, 2, 3)
        }

        if self.config.set_core_roles:
            self._configure_core_roles()
        if self.config.user_origin_mode.lower() == "current":
            self.zero_at_current_position()
        elif self.config.user_origin_mode.lower() != "center":
            raise ValueError("user_origin_mode must be 'center' or 'current'.")
        if self.config.settling_time_ms is not None:
            self.set_settling_time(self.config.settling_time_ms)

    # ------------------------------------------------------------------
    # Micro-Manager Core compatibility helpers

    def _method(self, snake_name: str, camel_name: str):
        if hasattr(self.core, snake_name):
            return getattr(self.core, snake_name)
        if hasattr(self.core, camel_name):
            return getattr(self.core, camel_name)
        raise AttributeError(f"MMCore has neither {snake_name} nor {camel_name}.")

    def _configure_core_roles(self):
        for snake, camel, args in (
            ("set_xy_stage_device", "setXYStageDevice", (self.config.xy_device,)),
            ("set_focus_device", "setFocusDevice", (self.config.z_device,)),
            ("set_timeout_ms", "setTimeoutMs", (int(self.config.timeout_ms),)),
        ):
            try:
                self._method(snake, camel)(*args)
            except Exception:
                # Keep going because explicit device-labeled calls below can still work.
                pass

    def _call_with_optional_device(self, snake: str, camel: str, device: str, *args):
        fn = self._method(snake, camel)
        try:
            return fn(device, *args)
        except TypeError:
            return fn(*args)

    def wait_for_xy(self):
        try:
            self._method("wait_for_device", "waitForDevice")(self.config.xy_device)
        except Exception:
            pass

    def wait_for_z(self):
        try:
            self._method("wait_for_device", "waitForDevice")(self.config.z_device)
        except Exception:
            pass

    def wait_for_all(self):
        self.wait_for_xy()
        self.wait_for_z()

    # ------------------------------------------------------------------
    # Properties

    def get_device_property_names(self, device: str):
        try:
            names = self._method("get_device_property_names", "getDevicePropertyNames")(device)
            return [str(name) for name in list(names)]
        except Exception:
            return []

    def set_property_if_present(self, device: str, prop: str, value) -> bool:
        if prop not in self.get_device_property_names(device):
            return False
        self._method("set_property", "setProperty")(device, prop, str(value))
        return True

    def set_settling_time(self, settling_time_ms: float) -> Dict[str, bool]:
        value = float(settling_time_ms)
        return {
            self.config.xy_device: self.set_property_if_present(self.config.xy_device, "Settling Time", value),
            self.config.z_device: self.set_property_if_present(self.config.z_device, "Settling Time", value),
        }

    def describe_devices(self) -> Dict[str, Dict[str, str]]:
        out: Dict[str, Dict[str, str]] = {}
        for device in (self.config.xy_device, self.config.z_device):
            props: Dict[str, str] = {}
            for name in self.get_device_property_names(device):
                try:
                    props[name] = str(self._method("get_property", "getProperty")(device, name))
                except Exception as exc:
                    props[name] = f"<error: {exc}>"
            out[device] = props
        return out

    # ------------------------------------------------------------------
    # Coordinate conversion

    @staticmethod
    def axis_number(axis: Axis) -> int:
        if isinstance(axis, str):
            key = axis.strip().lower()
            if key not in AXIS_NAME_TO_NUMBER:
                raise ValueError("axis must be x, y, z, 1, 2, or 3")
            return AXIS_NAME_TO_NUMBER[key]
        axis = int(axis)
        if axis not in (1, 2, 3):
            raise ValueError("axis must be x, y, z, 1, 2, or 3")
        return axis

    @staticmethod
    def axis_name(axis: Axis) -> str:
        return AXIS_NUMBER_TO_NAME[MicroManagerMCLStage.axis_number(axis)]

    def user_to_hw(self, axis: Axis, value_um: float) -> float:
        axis_num = self.axis_number(axis)
        return self.axis_origin[axis_num] + float(value_um)

    def hw_to_user(self, axis: Axis, value_um: float) -> float:
        axis_num = self.axis_number(axis)
        return float(value_um) - self.axis_origin[axis_num]

    def clamp_hw(self, axis: Axis, value_um: float) -> float:
        axis_num = self.axis_number(axis)
        return max(self.axis_min[axis_num], min(float(value_um), self.axis_max[axis_num]))

    def user_limits(self, axis: Axis) -> Tuple[float, float]:
        axis_num = self.axis_number(axis)
        return (
            self.hw_to_user(axis_num, self.axis_min[axis_num]),
            self.hw_to_user(axis_num, self.axis_max[axis_num]),
        )

    # ------------------------------------------------------------------
    # Reads and moves

    def read_hw(self) -> Dict[int, float]:
        x = float(self._call_with_optional_device("get_x_position", "getXPosition", self.config.xy_device))
        y = float(self._call_with_optional_device("get_y_position", "getYPosition", self.config.xy_device))
        z = float(self._call_with_optional_device("get_position", "getPosition", self.config.z_device))
        return {1: x, 2: y, 3: z, "x": x, "y": y, "z": z}

    def read_user(self) -> Dict[Axis, float]:
        hw = self.read_hw()
        x = self.hw_to_user(1, hw[1])
        y = self.hw_to_user(2, hw[2])
        z = self.hw_to_user(3, hw[3])
        return {1: x, 2: y, 3: z, "x": x, "y": y, "z": z}

    def zero_at_current_position(self) -> Dict[Axis, float]:
        hw = self.read_hw()
        self.axis_origin = {1: hw[1], 2: hw[2], 3: hw[3]}
        return self.read_user()

    def _set_xy_hw(self, x_hw: float, y_hw: float, wait: bool):
        self._call_with_optional_device(
            "set_xy_position",
            "setXYPosition",
            self.config.xy_device,
            float(x_hw),
            float(y_hw),
        )
        if wait:
            self.wait_for_xy()

    def _set_z_hw(self, z_hw: float, wait: bool):
        self._call_with_optional_device(
            "set_position",
            "setPosition",
            self.config.z_device,
            float(z_hw),
        )
        if wait:
            self.wait_for_z()

    def move_axis(self, axis: Axis, user_value_um: float, wait: bool = True):
        axis_num = self.axis_number(axis)
        hw = self.read_hw()
        target_hw = self.clamp_hw(axis_num, self.user_to_hw(axis_num, user_value_um))
        if axis_num == 1:
            self._set_xy_hw(target_hw, hw[2], wait)
        elif axis_num == 2:
            self._set_xy_hw(hw[1], target_hw, wait)
        else:
            self._set_z_hw(target_hw, wait)
        return self.read_user()

    def move_axes(self, targets_um: Mapping[Axis, float], wait: bool = True):
        hw = self.read_hw()
        x_hw = hw[1]
        y_hw = hw[2]
        z_hw = hw[3]
        do_xy = False
        do_z = False
        for axis, value in targets_um.items():
            axis_num = self.axis_number(axis)
            target_hw = self.clamp_hw(axis_num, self.user_to_hw(axis_num, float(value)))
            if axis_num == 1:
                x_hw = target_hw
                do_xy = True
            elif axis_num == 2:
                y_hw = target_hw
                do_xy = True
            else:
                z_hw = target_hw
                do_z = True
        if do_xy:
            self._set_xy_hw(x_hw, y_hw, wait=False)
        if do_z:
            self._set_z_hw(z_hw, wait=False)
        if wait:
            self.wait_for_all()
        return self.read_user()

    def move_xyz(self, x_um: float, y_um: float, z_um: float, wait: bool = True):
        return self.move_axes({1: x_um, 2: y_um, 3: z_um}, wait=wait)

    def step_axis(self, axis: Axis, delta_um: float, wait: bool = True):
        axis_num = self.axis_number(axis)
        current = self.read_user()[axis_num]
        return self.move_axis(axis_num, current + float(delta_um), wait=wait)

    def home(self, wait: bool = True):
        # User 0,0,0 is the configured origin.
        return self.move_axes({1: 0.0, 2: 0.0, 3: 0.0}, wait=wait)

    def close(self):
        if getattr(self, "_headless_started", False):
            try:
                from pycromanager import stop_headless
                stop_headless(debug=bool(self.config.debug))
            except Exception:
                pass
        return None


def print_stage_diagnostics(stage: Optional[MicroManagerMCLStage] = None) -> None:
    """Print a quick Micro-Manager/MCL connection diagnostic."""
    stage = stage or MicroManagerMCLStage()
    print("Current user position:", stage.read_user())
    print("Current hardware position:", stage.read_hw())
    for dev, props in stage.describe_devices().items():
        print("\n" + dev)
        for key, value in props.items():
            print(f"  {key}: {value}")


__all__ = ["MCLStageConfig", "MicroManagerMCLStage", "print_stage_diagnostics"]


if __name__ == "__main__":
    print_stage_diagnostics()
