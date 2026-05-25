"""
nspyre measurement shim for the modern 2D confocal scan GUI.

Two scan engines are available through gui_2D_Scan_mm.py -> Scan_Mode:

    software_mm
        Pycro-Manager/Micro-Manager point-by-point raster.  This is the safe
        fallback/debug mode.

    hardware_mcl_cbm
        Direct MCL/Madlib waveform scan through InstrumentGateway.gw.nano plus
        Swabian Time Tagger CountBetweenMarkers through InstrumentGateway.gw.daq.
        This path is intended for fast line scans and preserves axis independence
        by commanding only the selected fast and slow axes.

The laser/Pulse Streamer gate path mirrors the original spin_measurements.
Two_D_Scan_R behavior: configure the laser in CW mode, set power, turn it on,
enable the SPCM/laser gate, then force power/gate shutdown at scan end.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

try:
    from template.drivers.MCL_MicroManager_Wrapper_mm import MCLStageConfig, MicroManagerMCLStage
    from template.drivers.TimeTaggerDriver_mm import tt20
except Exception:
    try:
        from template.drivers.MCL_MicroManager_Wrapper_mm import MCLStageConfig, MicroManagerMCLStage
        from template.drivers.TimeTaggerDriver_mm import tt20
    except Exception:
        from template.drivers.MCL_MicroManager_Wrapper_mm import MCLStageConfig, MicroManagerMCLStage
        from template.drivers.TimeTaggerDriver_mm import tt20

try:
    from .confocal_scan_runner_mm import SoftwareRasterScanPlan, software_raster_scan
    from .laser_control_mm import LaserControl, LaserControlConfig
    from .timetagger_access_mm import GatewayTimeTaggerAdapter, normalize_daq_mode
    from .mcl_hardware_scan_mm import HardwareCBMScanPlan, run_mcl_hardware_cbm_scan, resolve_mcl_handle
except Exception:
    try:
        from template.gui.confocal_scan_runner_mm import SoftwareRasterScanPlan, software_raster_scan
        from template.gui.laser_control_mm import LaserControl, LaserControlConfig
        from template.gui.timetagger_access_mm import GatewayTimeTaggerAdapter, normalize_daq_mode
        from template.gui.mcl_hardware_scan_mm import HardwareCBMScanPlan, run_mcl_hardware_cbm_scan, resolve_mcl_handle
    except Exception:
        from confocal_scan_runner_mm import SoftwareRasterScanPlan, software_raster_scan
        from laser_control_mm import LaserControl, LaserControlConfig
        from timetagger_access_mm import GatewayTimeTaggerAdapter, normalize_daq_mode
        from mcl_hardware_scan_mm import HardwareCBMScanPlan, run_mcl_hardware_cbm_scan, resolve_mcl_handle

try:
    from nspyre import DataSource, InstrumentGateway, experiment_widget_process_queue
except Exception:  # pragma: no cover - nspyre exists on the lab machine
    DataSource = None
    InstrumentGateway = None
    experiment_widget_process_queue = None


DEFAULT_DATASET = "2D_Scan_mm"


# ---------------------------------------------------------------------------
# Generic GUI-value parsing helpers
# ---------------------------------------------------------------------------
def _unwrap(value):
    if isinstance(value, dict) and "widget" in value:
        value = value["widget"]
    for name in ("isChecked", "currentText", "value", "text"):
        if hasattr(value, name):
            try:
                return getattr(value, name)()
            except Exception:
                pass
    return value


def _as_bool(value, default=False):
    value = _unwrap(value)
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("1", "true", "yes", "on", "checked"):
            return True
        if text in ("0", "false", "no", "off", "unchecked", "disabled", "none"):
            return False
    return bool(value)


def _as_float(value, default=0.0):
    value = _unwrap(value)
    if value is None or value == "":
        return float(default)
    return float(value)


def _as_int(value, default=0):
    return int(round(_as_float(value, default)))


def _as_text(value, default=""):
    value = _unwrap(value)
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _get(params: Dict[str, Any], key: str, default=None):
    return params[key] if key in params and params[key] is not None else default


def _get_any(params: Dict[str, Any], keys, default=None):
    for key in keys:
        if key in params and params[key] is not None:
            return params[key]
    return default


def _axis_text(value, default):
    text = _as_text(value, default).strip().lower() or default
    axis = text[0]
    if axis not in ("x", "y", "z"):
        raise ValueError(f"Invalid axis {value!r}; use x, y, or z.")
    return axis


def _scan_mode_from_params(params: Dict[str, Any]) -> str:
    raw = _as_text(_get(params, "Scan_Mode", "software_mm"), "software_mm")
    text = raw.strip().lower().replace(" ", "_").replace("/", "_").replace("+", "_")
    aliases = {
        "software": "software_mm",
        "software_mm": "software_mm",
        "micro_manager": "software_mm",
        "micromanager": "software_mm",
        "pycromanager": "software_mm",
        "mm": "software_mm",
        "hardware": "hardware_mcl_cbm",
        "hardware_mcl": "hardware_mcl_cbm",
        "hardware_mcl_cbm": "hardware_mcl_cbm",
        "mcl_cbm": "hardware_mcl_cbm",
        "madlib_cbm": "hardware_mcl_cbm",
        "countbetweenmarkers": "hardware_mcl_cbm",
    }
    if text not in aliases:
        raise ValueError("Scan_Mode must be 'software_mm' or 'hardware_mcl_cbm'.")
    return aliases[text]


def _laser_config_from_params(params: Dict[str, Any]) -> LaserControlConfig:
    enabled = _as_bool(_get_any(params, ("Laser_Enable", "Use_Laser"), True), True)
    mode = _as_text(_get_any(params, ("Laser_Control_Mode", "Laser_Backend"), "gateway"), "gateway")
    if not enabled:
        mode = "disabled"

    if "Laser_Warmup_ms" in params:
        warmup_s = max(0.0, _as_float(params["Laser_Warmup_ms"], 0.0) / 1000.0)
    else:
        warmup_s = max(0.0, _as_float(_get(params, "Laser_Warmup_Time", 0.0), 0.0))

    shutdown = _as_bool(_get(params, "Laser_Shutdown_On_Finish", True), True)

    return LaserControlConfig(
        enabled=enabled,
        mode=mode,
        laser_mode=_as_text(_get(params, "Laser_Mode", "cw"), "cw"),
        power=_as_float(_get(params, "Laser_Power", 1.0), 1.0),
        serial_port=_as_text(_get(params, "Laser_Serial_Port", ""), ""),
        warmup_s=warmup_s,
        enable_spcm_gate=_as_bool(_get_any(params, ("Enable_SPCM_Gate", "Enable_SPCM_Laser_Gate"), True), True),
        shutdown_on_finish=shutdown,
        ps_reset_on_finish=_as_bool(_get(params, "PS_Reset_On_Finish", shutdown), shutdown),
        fail_on_error=_as_bool(_get(params, "Laser_Fail_On_Error", True), True),
    )


def _daq_mode_from_params(params: Dict[str, Any]) -> str:
    # Default to InstrumentGateway to avoid trying tt.createTimeTagger() in the
    # measurement subprocess while the instrument server already owns the USB TT.
    raw = _get_any(
        params,
        ("DAQ_Control_Mode", "Detector_Control_Mode", "TimeTagger_Backend", "Time_Tagger_Backend"),
        "instrument_gateway",
    )
    return normalize_daq_mode(_as_text(raw, "instrument_gateway"))


def _software_plan_from_params(params: Dict[str, Any], axis_1: str, axis_2: str,
                               photon_channel: int, trigger_level: Optional[float]) -> SoftwareRasterScanPlan:
    return SoftwareRasterScanPlan(
        axis_1=axis_1,
        axis_2=axis_2,
        axis_1_min_um=_as_float(_get(params, "Axis_Min_1", -10.0), -10.0),
        axis_1_max_um=_as_float(_get(params, "Axis_Max_1", 10.0), 10.0),
        axis_2_min_um=_as_float(_get(params, "Axis_Min_2", -10.0), -10.0),
        axis_2_max_um=_as_float(_get(params, "Axis_Max_2", 10.0), 10.0),
        data_points=_as_int(_get(params, "Data_Points", 10), 10),
        dwell_time_ms=_as_float(_get(params, "Dwell_Time", 5.0), 5.0),
        photon_channel=photon_channel,
        trigger_level_v=trigger_level,
        bidirectional=_as_bool(_get(params, "Bidirectional", True), True),
        normalize_to_cps=_as_bool(_get(params, "Normalize_to_cps", True), True),
    )


def _hardware_plan_from_params(params: Dict[str, Any], axis_1: str, axis_2: str,
                               photon_channel: int, trigger_level: Optional[float]) -> HardwareCBMScanPlan:
    axis_max = _as_float(_get_any(params, ("Stage_Range_um", "Stage_Travel_um"), 200.0), 200.0)
    marker_level = _get_any(params, ("CBM_Begin_Trigger_Level", "Marker_Trigger_Level"), 1.1)
    marker_level = None if marker_level in (None, "") else _as_float(marker_level, 1.1)
    return HardwareCBMScanPlan(
        axis_1=axis_1,
        axis_2=axis_2,
        axis_1_min_um=_as_float(_get(params, "Axis_Min_1", -10.0), -10.0),
        axis_1_max_um=_as_float(_get(params, "Axis_Max_1", 10.0), 10.0),
        axis_2_min_um=_as_float(_get(params, "Axis_Min_2", -10.0), -10.0),
        axis_2_max_um=_as_float(_get(params, "Axis_Max_2", 10.0), 10.0),
        data_points=_as_int(_get(params, "Data_Points", 10), 10),
        dwell_time_ms=_as_float(_get(params, "Dwell_Time", 5.0), 5.0),
        average_per_pixel=_as_int(_get(params, "Average_Per_Pixel", 1), 1),
        photon_channel=photon_channel,
        photon_trigger_level_v=trigger_level,
        begin_channel=_as_int(_get_any(params, ("CBM_Begin_Channel", "Pixel_Marker_Channel"), 4), 4),
        begin_trigger_level_v=marker_level,
        end_channel=_as_int(_get_any(params, ("CBM_End_Channel", "Pixel_End_Channel"), 0), 0),
        bidirectional=_as_bool(_get(params, "Bidirectional", True), True),
        normalize_to_cps=_as_bool(_get(params, "Normalize_to_cps", True), True),
        use_bin_widths=_as_bool(_get(params, "Hardware_Use_Bin_Widths", True), True),
        line_mode=_as_text(_get(params, "Hardware_Line_Mode", "forward_only"), "forward_only"),
        display_image=_as_text(_get(params, "Hardware_Display_Image", "forward"), "forward"),
        reverse_line_shift_px=_as_float(_get(params, "Hardware_Reverse_Line_Shift_px", 0.0), 0.0),
        auto_align_reverse=_as_bool(_get(params, "Hardware_Auto_Align_Reverse", False), False),
        auto_align_snake_rows=_as_bool(_get(params, "Hardware_Auto_Align_Snake_Rows", False), False),
        auto_align_max_shift_px=_as_float(_get(params, "Hardware_Auto_Align_Max_Shift_px", 10.0), 10.0),
        edge_blank_pixels=_as_int(_get(params, "Hardware_Edge_Blank_Pixels", 0), 0),
        user_origin_mode=_as_text(_get_any(params, ("User_Origin_Mode", "Origin_Mode"), "center"), "center"),
        stage_range_um=axis_max,
        pixel_clock=_as_int(_get(params, "Hardware_Pixel_Clock", 1), 1),
        pixel_clock_mode=_as_int(_get(params, "Hardware_Pixel_Clock_Mode", 2), 2),
        bind_pixel_clock=_as_bool(_get(params, "Hardware_Bind_Pixel_Clock", True), True),
        iss_reset_defaults=_as_bool(_get(params, "Hardware_ISS_Reset_Defaults", False), False),
        slow_axis_use_monitor=_as_bool(_get(params, "Hardware_Slow_Axis_Monitor", True), True),
        line_settle_ms=_as_float(_get(params, "Hardware_Line_Settle_ms", 0.0), 0.0),
        poll_interval_ms=_as_float(_get(params, "Hardware_Poll_Interval_ms", 1.0), 1.0),
        line_timeout_s=_as_float(_get(params, "Hardware_Line_Timeout_s", 30.0), 30.0),
        max_waveform_points=_as_int(_get(params, "Hardware_Max_Waveform_Points", 10000), 10000),
    )


def _axis_id(axis: str) -> int:
    return {"x": 1, "y": 2, "z": 3}[axis]


class SpinMeasurements:
    """nspyre-compatible class containing the scan methods."""

    def __init__(self, queue_to_exp=None, queue_from_exp=None, *args, **kwargs):
        self.queue_to_exp = queue_to_exp
        self.queue_from_exp = queue_from_exp

    def _stop_requested_func(self):
        seen = {"stop": False}

        def _stop_requested():
            if seen["stop"]:
                return True
            if experiment_widget_process_queue is None or self.queue_to_exp is None:
                return False
            try:
                if experiment_widget_process_queue(self.queue_to_exp) == "stop":
                    seen["stop"] = True
                    return True
            except Exception:
                return False
            return False

        return _stop_requested

    def Two_D_Scan_R_mm(self, **params):
        dataset_name = _as_text(_get(params, "Dataset_Name", DEFAULT_DATASET), DEFAULT_DATASET)
        scan_mode = _scan_mode_from_params(params)

        axis_1 = _axis_text(_get_any(params, ("Axis_1_Name", "Axis_1", "Scan_Axis_1"), "x"), "x")
        axis_2 = _axis_text(_get_any(params, ("Axis_2_Name", "Axis_2", "Scan_Axis_2"), "y"), "y")
        if axis_1 == axis_2:
            raise ValueError("Axis 1 and Axis 2 must be different axes.")

        photon_channel = _as_int(_get(params, "Photon_Channel", 3), 3)
        trigger_level = _get_any(params, ("Photon_Trigger_Level", "Trigger_Level"), None)
        trigger_level = None if trigger_level in (None, "") else _as_float(trigger_level, 1.0)

        if scan_mode == "hardware_mcl_cbm":
            return self._run_hardware_mcl_cbm(
                params=params,
                dataset_name=dataset_name,
                axis_1=axis_1,
                axis_2=axis_2,
                photon_channel=photon_channel,
                trigger_level=trigger_level,
            )

        return self._run_software_mm(
            params=params,
            dataset_name=dataset_name,
            axis_1=axis_1,
            axis_2=axis_2,
            photon_channel=photon_channel,
            trigger_level=trigger_level,
        )

    def _run_software_mm(self, *, params: Dict[str, Any], dataset_name: str, axis_1: str,
                         axis_2: str, photon_channel: int, trigger_level: Optional[float]):
        axis_max = _as_float(_get_any(params, ("Stage_Range_um", "Stage_Travel_um"), 200.0), 200.0)
        stage_config = MCLStageConfig(
            xy_device=_as_text(_get(params, "MM_XY_Device", "MCL NanoDrive XY Stage"), "MCL NanoDrive XY Stage"),
            z_device=_as_text(_get(params, "MM_Z_Device", "MCL NanoDrive Z Stage"), "MCL NanoDrive Z Stage"),
            axis_max_um=(axis_max, axis_max, axis_max),
            user_origin_mode=_as_text(_get_any(params, ("User_Origin_Mode", "Origin_Mode"), "center"), "center"),
            settling_time_ms=_as_float(_get_any(params, ("Settling_Time", "Settling_Time_ms"), 2.0), 2.0),
            mm_config_file=_as_text(_get(params, "MM_Config_File", ""), "") or None,
            mm_app_path=_as_text(_get(params, "MM_App_Path", ""), "") or None,
        )

        plan = _software_plan_from_params(params, axis_1, axis_2, photon_channel, trigger_level)
        laser_config = _laser_config_from_params(params)
        daq_mode = _daq_mode_from_params(params)
        return_to_start = _as_bool(_get(params, "Return_to_Start", False), False)
        stop_requested = self._stop_requested_func()

        stage: Optional[MicroManagerMCLStage] = None
        detector = None
        detector_owned_locally = False
        gateway_cm = None
        gw = None
        start_position: Optional[dict] = None

        try:
            stage = MicroManagerMCLStage(config=stage_config)

            if daq_mode == "gateway":
                if InstrumentGateway is None:
                    raise RuntimeError(
                        "DAQ_Control_Mode='instrument_gateway' requires nspyre.InstrumentGateway. "
                        "Start the instrument server, or set DAQ_Control_Mode='local_timetagger' "
                        "only when no other process owns the Time Tagger."
                    )
                gateway_cm = InstrumentGateway()
                gw = gateway_cm.__enter__()
                detector = GatewayTimeTaggerAdapter(getattr(gw, "daq", None))
            else:
                # Standalone/debug mode only. This will fail if the instrument
                # server or any other process already owns the USB Time Tagger.
                detector = tt20()
                detector_owned_locally = True

            if return_to_start:
                pos = stage.read_user()
                start_position = pos.as_dict() if hasattr(pos, "as_dict") else dict(pos)

            with LaserControl(laser_config) as laser: # , gateway=gw
                laser_meta = laser.metadata

                if DataSource is None:
                    dataset = software_raster_scan(stage, detector, plan, stop_requested=stop_requested)
                    dataset["laser"] = laser_meta
                    dataset["scan_mode"] = "software_mm"
                    dataset["daq_backend"] = daq_mode
                    return dataset

                with DataSource(dataset_name) as source:
                    def publish(dataset, row, col):
                        dataset = dict(dataset)
                        dataset["title"] = dataset_name
                        dataset["last_pixel"] = (int(row), int(col))
                        dataset["scan_mode"] = "software_mm"
                        dataset["stage_backend"] = "Micro-Manager/Pycro-Manager MCL_NanoDrive"
                        dataset["daq_backend"] = daq_mode
                        dataset["time_tagger_channel"] = photon_channel
                        dataset["time_tagger_trigger_level_v"] = trigger_level
                        dataset["laser"] = laser.metadata
                        dataset.update(laser.metadata)
                        source.push({"datasets": dataset})

                    dataset = software_raster_scan(
                        stage,
                        detector,
                        plan,
                        publish_callback=publish,
                        stop_requested=stop_requested,
                    )
                    dataset["laser"] = laser.metadata
                    dataset["scan_mode"] = "software_mm"
                    dataset["daq_backend"] = daq_mode
                    dataset.update(laser.metadata)
                    print("Scan finished.")
                    return dataset
        finally:
            if return_to_start and start_position is not None and stage is not None:
                try:
                    stage.move_axes(start_position, wait=True)
                except Exception:
                    pass
            if detector is not None and detector_owned_locally:
                try:
                    detector.free_time_tagger()
                except Exception:
                    pass
            if stage is not None:
                try:
                    stage.close()
                except Exception:
                    pass
            if gateway_cm is not None:
                try:
                    gateway_cm.__exit__(None, None, None)
                except Exception:
                    pass

    def _run_hardware_mcl_cbm(self, *, params: Dict[str, Any], dataset_name: str,
                              axis_1: str, axis_2: str, photon_channel: int,
                              trigger_level: Optional[float]):
        daq_mode = _daq_mode_from_params(params)
        if daq_mode != "gateway":
            raise RuntimeError(
                "Scan_Mode='hardware_mcl_cbm' requires DAQ_Control_Mode='instrument_gateway'. "
                "The hardware scan must use the Time Tagger owned by the nspyre instrument server."
            )
        if InstrumentGateway is None:
            raise RuntimeError("Scan_Mode='hardware_mcl_cbm' requires nspyre.InstrumentGateway.")

        plan = _hardware_plan_from_params(params, axis_1, axis_2, photon_channel, trigger_level)
        laser_config = _laser_config_from_params(params)
        return_to_start = _as_bool(_get(params, "Return_to_Start", False), False)
        stop_requested = self._stop_requested_func()

        gateway_cm = None
        gw = None
        start_positions = None
        mcl_handle_for_return = None
        fast_axis_id = _axis_id(axis_1)
        slow_axis_id = _axis_id(axis_2)

        try:
            gateway_cm = InstrumentGateway()
            gw = gateway_cm.__enter__()
            nano = getattr(gw, "nano", None)
            if nano is None:
                raise RuntimeError(
                    "InstrumentGateway does not expose gw.nano. Hardware MCL + CBM mode requires "
                    "the direct MCL_Madlib_Wrapper driver to be loaded as 'nano' in the instrument server."
                )
            detector = GatewayTimeTaggerAdapter(getattr(gw, "daq", None))

            if return_to_start:
                mcl_handle_for_return, _, _ = resolve_mcl_handle(nano)
                start_positions = {}
                for axis_id in (fast_axis_id, slow_axis_id):
                    try:
                        start_positions[axis_id] = float(nano.single_read_n(axis_id, mcl_handle_for_return))
                    except Exception:
                        pass

            with LaserControl(laser_config) as laser: # , gateway=gw
                laser_meta = laser.metadata

                if DataSource is None:
                    dataset = run_mcl_hardware_cbm_scan(
                        nano,
                        detector,
                        plan,
                        stop_requested=stop_requested,
                    )
                    dataset["laser"] = laser_meta
                    dataset.update(laser_meta)
                    return dataset

                with DataSource(dataset_name) as source:
                    def publish(dataset, row, col):
                        dataset = dict(dataset)
                        dataset["title"] = dataset_name
                        dataset["last_pixel"] = (int(row), int(col))
                        dataset["time_tagger_channel"] = photon_channel
                        dataset["time_tagger_trigger_level_v"] = trigger_level
                        dataset["laser"] = laser.metadata
                        dataset.update(laser.metadata)
                        source.push({"datasets": dataset})

                    dataset = run_mcl_hardware_cbm_scan(
                        nano,
                        detector,
                        plan,
                        publish_callback=publish,
                        stop_requested=stop_requested,
                    )
                    dataset["laser"] = laser.metadata
                    dataset.update(laser.metadata)
                    source.push({"datasets": dict(dataset, title=dataset_name)})
                    print("Scan finished.")
                    return dataset
        finally:
            if return_to_start and start_positions is not None and gw is not None:
                nano = getattr(gw, "nano", None)
                if nano is not None:
                    # Return only the selected axes.  The unscanned axis remains untouched.
                    if mcl_handle_for_return is None:
                        try:
                            mcl_handle_for_return, _, _ = resolve_mcl_handle(nano)
                        except Exception:
                            mcl_handle_for_return = None
                    for axis_id, pos in start_positions.items():
                        if mcl_handle_for_return is None:
                            break
                        try:
                            if callable(getattr(nano, "monitor_n", None)):
                                nano.monitor_n(float(pos), int(axis_id), mcl_handle_for_return)
                            else:
                                nano.single_write_n(float(pos), int(axis_id), mcl_handle_for_return)
                        except Exception:
                            pass
            if gateway_cm is not None:
                try:
                    gateway_cm.__exit__(None, None, None)
                except Exception:
                    pass

    def Two_D_Scan_mm(self, **params):
        return self.Two_D_Scan_R_mm(**params)


SpinMeasurements_mm = SpinMeasurements
