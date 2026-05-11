"""
Laser and Pulse Streamer gate helper for the Micro-Manager/Pycro-Manager scan
scripts.

The original non-mm Two_D_Scan_R turns the laser on through nspyre's
InstrumentGateway, enables the Pulse Streamer SPCM/laser gate, and then forces
both back to a safe off/reset state at the end of the scan. This helper keeps
that behavior available to the mm scan path without making the stage or Time
Tagger drivers depend on InstrumentGateway.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Optional


_DISABLED_MODES = {"", "none", "off", "disabled", "false", "0"}
_GATEWAY_MODES = {"gateway", "instrument_gateway", "instrumentgateway", "nspyre", "gw"}
_SERIAL_MODES = {"serial", "dlnsec", "dlnsec_serial", "direct_dlnsec", "direct", "direct_serial"}


@dataclass
class LaserControlConfig:
    """Configuration for optional laser control during a scan."""

    enabled: bool = True
    mode: str = "gateway"
    laser_mode: str = "cw"              # cw, triggered, or internal
    power: float = 1.0                   # DLnsec-compatible percentage, 0-100
    serial_port: str = ""
    timeout_s: float = 1.0
    warmup_s: float = 0.0
    enable_spcm_gate: bool = True
    shutdown_on_finish: bool = True
    ps_reset_on_finish: bool = True
    fail_on_error: bool = True

    def normalized_mode(self) -> str:
        mode = str(self.mode or "").strip().lower()
        if not self.enabled or mode in _DISABLED_MODES:
            return "disabled"
        if mode in _GATEWAY_MODES:
            return "gateway"
        if mode in _SERIAL_MODES:
            return "serial"
        raise ValueError("Laser_Control_Mode must be gateway, serial, or none.")

    def power_percent(self) -> int:
        power = int(round(float(self.power)))
        if power < 0 or power > 100:
            raise ValueError("Laser_Power must be between 0 and 100 percent.")
        return power

    def metadata(self) -> dict:
        mode = self.normalized_mode()
        return {
            "laser_enabled": bool(self.enabled and mode != "disabled"),
            "laser_control_mode": mode,
            "laser_mode": str(self.laser_mode or "cw"),
            "laser_power_percent": self.power_percent() if mode != "disabled" else 0,
            "spcm_gate_enabled": bool(self.enable_spcm_gate and mode == "gateway"),
            "laser_shutdown_after_scan": bool(self.shutdown_on_finish),
        }


class LaserControl:
    """Context manager that starts and stops the laser safely."""

    def __init__(self, config: Optional[LaserControlConfig] = None):
        self.config = config or LaserControlConfig(enabled=False)
        self.mode = "disabled"
        self._gateway_cm = None
        self.gw = None
        self.laser = None
        self.ps = None
        self.active = False
        self._serial_laser = None

    def __enter__(self):
        try:
            self.mode = self.config.normalized_mode()
            if self.mode == "disabled":
                return self
            if self.mode == "gateway":
                self._start_gateway()
            elif self.mode == "serial":
                self._start_serial()
            if float(self.config.warmup_s) > 0:
                time.sleep(float(self.config.warmup_s))
            self.active = True
            return self
        except Exception:
            self._safe_shutdown()
            if self.config.fail_on_error:
                raise
            print("WARNING: laser startup failed; continuing with laser disabled because Laser_Fail_On_Error is False.")
            self.mode = "disabled"
            self.active = False
            return self

    @property
    def metadata(self) -> dict:
        data = self.config.metadata()
        data.update({"active": bool(self.active), "runtime_mode": self.mode})
        return data

    def as_dict(self) -> dict:
        return self.metadata

    def __exit__(self, exc_type, exc, tb):
        if self.config.shutdown_on_finish:
            self._safe_shutdown()
        else:
            self._close_gateway()
        return False

    def _start_gateway(self) -> None:
        try:
            from nspyre import InstrumentGateway
        except Exception as exc:  # pragma: no cover - lab dependency
            raise RuntimeError(
                "Laser_Control_Mode='gateway' requires nspyre.InstrumentGateway. "
                "Start the instrument server or set Laser_Control_Mode to none/serial."
            ) from exc

        self._gateway_cm = InstrumentGateway()
        self.gw = self._gateway_cm.__enter__()
        self.laser = getattr(self.gw, "laser", None)
        if self.laser is None:
            raise RuntimeError("InstrumentGateway does not expose gw.laser.")

        self._configure_laser_mode(self.laser)
        self._safe_call(self.laser, "get_power")
        self._call_any(self.laser, ("set_power",), self.config.power_percent(), required=True)
        self._call_any(self.laser, ("on", "laser_on"), required=True)

        self.ps = getattr(self.gw, "ps", None)
        if self.config.enable_spcm_gate:
            if self.ps is None:
                raise RuntimeError("Enable_PulseStreamer_Gate=True, but InstrumentGateway does not expose gw.ps.")
            self._call_any(self.ps, ("spcm_laser_on", "laser_on"), required=True)

    def _start_serial(self) -> None:
        serial_port = str(self.config.serial_port or "").strip()
        if not serial_port:
            raise ValueError("Laser_Control_Mode='serial' requires Laser_Serial_Port, e.g. COM4.")
        try:
            try:
                from template.drivers.dlnsec import DLnsec
            except Exception:
                from template.drivers.dlnsec import DLnsec
        except Exception as exc:  # pragma: no cover - lab dependency
            raise RuntimeError("Could not import dlnsec.DLnsec for serial laser control.") from exc

        self._serial_laser = DLnsec(serial_port, timeout=float(self.config.timeout_s))
        self._serial_laser.open()
        self.laser = self._serial_laser
        self._configure_laser_mode(self.laser)
        self._safe_call(self.laser, "get_power")
        self._call_any(self.laser, ("set_power",), self.config.power_percent(), required=True)
        self._call_any(self.laser, ("on", "laser_on"), required=True)
        if self.config.enable_spcm_gate:
            print("WARNING: serial laser mode cannot call gw.ps.spcm_laser_on(); enable the SPCM gate elsewhere.")

    def _configure_laser_mode(self, laser: Any) -> None:
        mode = str(self.config.laser_mode or "cw").strip().lower()
        if mode in ("cw", "continuous", "continuous_wave", "continuous-wave"):
            if self._call_any(laser, ("cw_mode", "las_mode")):
                return
            if self._call_any(laser, ("set_modulation_state",), "cw"):
                return
            raise RuntimeError("The laser driver does not expose cw_mode(), las_mode(), or set_modulation_state('cw').")
        if mode in ("triggered", "trigger", "external", "ext"):
            if self._call_any(laser, ("trig_mode", "trigger_mode", "external_mode")):
                return
            raise RuntimeError("The laser driver does not expose trig_mode(), trigger_mode(), or external_mode().")
        if mode in ("internal", "int"):
            if self._call_any(laser, ("int_mode", "internal_mode")):
                return
            raise RuntimeError("The laser driver does not expose int_mode() or internal_mode().")
        raise ValueError("Laser_Mode must be cw, triggered, or internal.")

    @staticmethod
    def _call_any(obj: Any, names, *args, required: bool = False) -> bool:
        for name in names:
            method = getattr(obj, name, None)
            if callable(method):
                method(*args)
                return True
        if required:
            raise RuntimeError(f"None of the required methods {tuple(names)} exist on {obj!r}.")
        return False

    @staticmethod
    def _safe_call(obj: Any, name: str, *args) -> bool:
        method = getattr(obj, name, None)
        if not callable(method):
            return False
        try:
            method(*args)
            return True
        except Exception as exc:
            print(f"WARNING: {name}() failed during laser cleanup/control: {exc}")
            return False

    def _safe_shutdown(self) -> None:
        # Match the original scan's safety pattern: power to 0, laser off, then
        # close/clear Pulse Streamer outputs and reset where available.
        if self.laser is not None:
            self._safe_call(self.laser, "set_power", 0)
            self._safe_call(self.laser, "get_power")
            self._safe_call(self.laser, "off")
            self._safe_call(self.laser, "laser_off")

        if self.ps is not None and self.config.enable_spcm_gate:
            for name in ("constant_off", "gate_off", "just_gate_off"):
                self._safe_call(self.ps, name)
            if self.config.ps_reset_on_finish:
                if not self._safe_call(self.ps, "ps_reset"):
                    pulser = getattr(self.ps, "Pulser", None)
                    if pulser is not None:
                        self._safe_call(pulser, "reset")

        if self._serial_laser is not None:
            self._safe_call(self._serial_laser, "close")
            self._serial_laser = None

        self._close_gateway()
        self.active = False
        self.mode = "disabled"

    def _close_gateway(self) -> None:
        if self._gateway_cm is not None:
            try:
                self._gateway_cm.__exit__(None, None, None)
            except Exception:
                pass
            self._gateway_cm = None
        self.gw = None
        self.ps = None


__all__ = ["LaserControlConfig", "LaserControl"]


def laser_config_from_params(params: dict) -> LaserControlConfig:
    """Build LaserControlConfig from gui_2D_Scan_mm.py/nspyre params."""
    def get_any(*keys, default=None):
        for key in keys:
            if key in params and params[key] is not None:
                return params[key]
        return default

    def text(value, default=""):
        if value is None:
            return default
        if hasattr(value, "currentText"):
            try:
                return str(value.currentText())
            except Exception:
                pass
        if hasattr(value, "text"):
            try:
                return str(value.text())
            except Exception:
                pass
        return str(value)

    def boolean(value, default=False):
        if value is None:
            return bool(default)
        if isinstance(value, bool):
            return value
        if hasattr(value, "isChecked"):
            try:
                return bool(value.isChecked())
            except Exception:
                pass
        if isinstance(value, str):
            value_l = value.strip().lower()
            if value_l in ("1", "true", "yes", "on", "checked"):
                return True
            if value_l in ("0", "false", "no", "off", "unchecked", "disabled"):
                return False
        return bool(value)

    def number(value, default=0.0):
        if value is None or value == "":
            return float(default)
        if hasattr(value, "value"):
            try:
                return float(value.value())
            except Exception:
                pass
        return float(value)

    mode = text(get_any("Laser_Control_Mode", "Laser_Backend", "Laser_Source", default="gateway"), "gateway")
    if mode.strip().lower() == "instrument_gateway":
        mode = "gateway"
    enabled = boolean(get_any("Laser_Enable", "Use_Laser", default=True), True)
    if not enabled:
        mode = "disabled"
    laser_mode = "cw" if boolean(get_any("Laser_CW_Mode", default=True), True) else text(get_any("Laser_Mode", default="cw"), "cw")
    return LaserControlConfig(
        enabled=enabled,
        mode=mode,
        laser_mode=laser_mode,
        power=number(get_any("Laser_Power", default=1.0), 1.0),
        serial_port=text(get_any("Laser_Serial_Port", "Laser_COM_Port", default=""), "").strip(),
        warmup_s=number(get_any("Laser_Warmup_Time", default=0.0), 0.0),
        enable_spcm_gate=boolean(get_any("Enable_SPCM_Laser_Gate", "Enable_SPCM_Gate", default=True), True),
        shutdown_on_finish=boolean(get_any("Laser_Shutdown_On_Finish", default=True), True),
        ps_reset_on_finish=boolean(get_any("PS_Reset_On_Finish", default=True), True),
        fail_on_error=boolean(get_any("Laser_Fail_On_Error", default=True), True),
    )


@classmethod
def _laser_control_from_params(cls, params: dict):
    return cls(laser_config_from_params(params))


LaserControl.from_params = _laser_control_from_params
LaserAndGateController = LaserControl
__all__ = ["LaserControlConfig", "LaserControl", "LaserAndGateController", "laser_config_from_params"]
