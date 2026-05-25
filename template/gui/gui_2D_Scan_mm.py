"""
2D confocal scan GUI using Micro-Manager/Pycro-Manager stage control.

Compared with gui_2D_Scan.py, this version:
- removes duplicate params_config keys
- calls spin_measurements_mm.SpinMeasurements.Two_D_Scan_R_mm
- adds Scan_Mode selection for software Micro-Manager or hardware MCL+CBM scans
- adds Time Tagger backend/channel/trigger-level/CBM marker parameters
- adds laser/Pulse Streamer gate controls matching Two_D_Scan_R behavior
- uses one DataSink.pop() per display update
- does not subtract a hard-coded 100 um display offset
"""
from __future__ import annotations

import numpy as np
from nspyre import DataSink, ExperimentWidget, HeatMapWidget
from pyqtgraph import SpinBox
from pyqtgraph.Qt import QtCore, QtWidgets

try:
    _Signal = QtCore.Signal
except AttributeError:  # PyQt5 compatibility
    _Signal = QtCore.pyqtSignal

try:
    _QUEUED_CONNECTION = QtCore.Qt.ConnectionType.QueuedConnection
except AttributeError:  # PyQt5 compatibility
    _QUEUED_CONNECTION = QtCore.Qt.QueuedConnection

try:
    from . import spin_measurements_mm as sm
except Exception:
    import spin_measurements_mm as sm


DATASET_NAME = "2D_Scan_mm"


def _combo(items, default_text: str):
    combo = QtWidgets.QComboBox()
    combo.addItems(list(items))
    combo.setCurrentText(default_text)
    return combo


def _axis_combo(default_text: str):
    return _combo(["x", "y", "z"], default_text)


def _laser_mode_combo(default_text: str):
    return _combo(["instrument_gateway", "direct_dlnsec", "disabled"], default_text)


def _daq_mode_combo(default_text: str):
    return _combo(["instrument_gateway", "local_timetagger"], default_text)


def _scan_mode_combo(default_text: str):
    return _combo(["software_mm", "hardware_mcl_cbm"], default_text)


def _hardware_line_mode_combo(default_text: str):
    return _combo(["forward_only", "snake_single_line", "forward_backward_average"], default_text)


def _hardware_display_image_combo(default_text: str):
    return _combo(["forward", "backward", "average"], default_text)


class TwoD_Scan_mm(ExperimentWidget):
    """nspyre ExperimentWidget for Micro-Manager + Time Tagger 2D scans."""

    def __init__(self):
        bidirectional = QtWidgets.QCheckBox()
        bidirectional.setChecked(True)
        normalize_to_cps = QtWidgets.QCheckBox()
        normalize_to_cps.setChecked(True)
        return_to_start = QtWidgets.QCheckBox()
        return_to_start.setChecked(False)

        laser_enable = QtWidgets.QCheckBox()
        laser_enable.setChecked(True)
        laser_gate = QtWidgets.QCheckBox()
        laser_gate.setChecked(True)
        laser_shutdown = QtWidgets.QCheckBox()
        laser_shutdown.setChecked(True)
        ps_reset = QtWidgets.QCheckBox()
        ps_reset.setChecked(True)
        laser_fail = QtWidgets.QCheckBox()
        laser_fail.setChecked(True)

        hardware_bind_pixel_clock = QtWidgets.QCheckBox()
        hardware_bind_pixel_clock.setChecked(True)
        hardware_iss_reset = QtWidgets.QCheckBox()
        hardware_iss_reset.setChecked(False)
        hardware_slow_monitor = QtWidgets.QCheckBox()
        hardware_slow_monitor.setChecked(True)
        hardware_use_bin_widths = QtWidgets.QCheckBox()
        hardware_use_bin_widths.setChecked(True)
        hardware_auto_align_reverse = QtWidgets.QCheckBox()
        hardware_auto_align_reverse.setChecked(False)
        hardware_auto_align_snake = QtWidgets.QCheckBox()
        hardware_auto_align_snake.setChecked(False)

        params_config = {
            "Dataset_Name": {
                "display_text": "Dataset Name",
                "widget": QtWidgets.QLineEdit(DATASET_NAME),
            },
            "Scan_Mode": {
                "display_text": "Scan Mode",
                "widget": _scan_mode_combo("software_mm"),
            },
            "Axis_1": {
                "display_text": "Fast Axis",
                "widget": _axis_combo("x"),
            },
            "Axis_2": {
                "display_text": "Slow Axis",
                "widget": _axis_combo("y"),
            },
            "Data_Points": {
                "display_text": "Num. of Data Points",
                "widget": SpinBox(value=10, int=True, bounds=(2, 9999), dec=True),
            },
            "Axis_Min_1": {
                "display_text": "Min. Value Axis 1 (um)",
                "widget": SpinBox(value=-10.0, siPrefix=False, bounds=(-100.0, 100.0), step=0.003, dec=3, int=False),
            },
            "Axis_Max_1": {
                "display_text": "Max. Value Axis 1 (um)",
                "widget": SpinBox(value=10.0, siPrefix=False, bounds=(-100.0, 100.0), step=0.003, dec=3, int=False),
            },
            "Axis_Min_2": {
                "display_text": "Min. Value Axis 2 (um)",
                "widget": SpinBox(value=-10.0, siPrefix=False, bounds=(-100.0, 100.0), step=0.003, dec=3, int=False),
            },
            "Axis_Max_2": {
                "display_text": "Max. Value Axis 2 (um)",
                "widget": SpinBox(value=10.0, siPrefix=False, bounds=(-100.0, 100.0), step=0.003, dec=3, int=False),
            },
            "Dwell_Time": {
                "display_text": "Dwell / WFMA Step (ms)",
                "widget": SpinBox(value=5.0, siPrefix=False, bounds=(0.05, 10000.0), step=0.1, dec=3, int=False),
            },
            "Average_Per_Pixel": {
                "display_text": "Average per pixel",
                "widget": SpinBox(value=1, int=True, bounds=(1, 100000), dec=True),
            },
            "Bidirectional": {
                "display_text": "Bidirectional Raster",
                "widget": bidirectional,
            },
            "Normalize_to_cps": {
                "display_text": "Normalize to counts/s",
                "widget": normalize_to_cps,
            },
            "Return_to_Start": {
                "display_text": "Return stage to start position",
                "widget": return_to_start,
            },

            # Laser / Pulse Streamer controls. The default path matches the
            # original Two_D_Scan_R: gw.laser.cw_mode(), set_power(), on(),
            # then gw.ps.spcm_laser_on(), with power-off/PS reset at the end.
            "Laser_Enable": {
                "display_text": "Enable Laser During Scan",
                "widget": laser_enable,
            },
            "Laser_Control_Mode": {
                "display_text": "Laser Control Mode",
                "widget": _laser_mode_combo("instrument_gateway"),
            },
            "Laser_Power": {
                "display_text": "Laser Power (%)",
                "widget": SpinBox(value=1, int=True, suffix="%", siPrefix=False, bounds=(0, 100), step=1, dec=True),
            },
            "Enable_SPCM_Gate": {
                "display_text": "Enable PS SPCM/Laser Gate",
                "widget": laser_gate,
            },
            "Laser_Warmup_ms": {
                "display_text": "Laser Warmup (ms)",
                "widget": SpinBox(value=100.0, siPrefix=False, bounds=(0.0, 10000.0), step=10.0, dec=1, int=False),
            },
            "Laser_Shutdown_On_Finish": {
                "display_text": "Laser Off After Scan",
                "widget": laser_shutdown,
            },
            "PS_Reset_On_Finish": {
                "display_text": "Pulse Streamer Reset After Scan",
                "widget": ps_reset,
            },
            "Laser_Serial_Port": {
                "display_text": "DLnsec Serial Port (direct mode only)",
                "widget": QtWidgets.QLineEdit(""),
            },
            "Laser_Fail_On_Error": {
                "display_text": "Abort If Laser Setup Fails",
                "widget": laser_fail,
            },

            # Time Tagger controls. Default backend uses gw.daq from the
            # nspyre instrument server to avoid a second tt.createTimeTagger()
            # call in the measurement subprocess. Use local_timetagger only
            # when the instrument server is not holding the Time Tagger.
            "DAQ_Control_Mode": {
                "display_text": "Time Tagger Control Mode",
                "widget": _daq_mode_combo("instrument_gateway"),
            },
            # Defaults match the old Two_D_Scan_R convention: SPCM on channel 3
            # with approximately 1 V threshold.
            "Photon_Channel": {
                "display_text": "Time Tagger Photon/SPCM Channel",
                "widget": SpinBox(value=3, int=True, bounds=(-64, 64), dec=True),
            },
            "Trigger_Level": {
                "display_text": "Photon Trigger Level (V)",
                "widget": SpinBox(value=1.0, siPrefix=False, bounds=(-5.0, 5.0), step=0.05, dec=3, int=False),
            },

            # Hardware MCL + CountBetweenMarkers controls. These are used only
            # when Scan_Mode = hardware_mcl_cbm. The default CBM style matches
            # the original Two_D_Scan_R: MCL ISS pixel clock on Time Tagger
            # channel 4, begin-only CountBetweenMarkers, SPCM on channel 3.
            "CBM_Begin_Channel": {
                "display_text": "CBM Begin / Pixel Marker Channel",
                "widget": SpinBox(value=4, int=True, bounds=(-64, 64), dec=True),
            },
            "CBM_End_Channel": {
                "display_text": "CBM End Channel (0 = unused)",
                "widget": SpinBox(value=0, int=True, bounds=(-64, 64), dec=True),
            },
            "Marker_Trigger_Level": {
                "display_text": "Marker Trigger Level (V)",
                "widget": SpinBox(value=1.1, siPrefix=False, bounds=(-5.0, 5.0), step=0.05, dec=3, int=False),
            },
            "Hardware_Line_Mode": {
                "display_text": "Hardware Line Mode",
                "widget": _hardware_line_mode_combo("forward_only"),
            },
            "Hardware_Display_Image": {
                "display_text": "HW Display Image",
                "widget": _hardware_display_image_combo("forward"),
            },
            "Hardware_Reverse_Line_Shift_px": {
                "display_text": "Reverse-Line Shift (pixels)",
                "widget": SpinBox(value=0.0, siPrefix=False, bounds=(-1000.0, 1000.0), step=0.1, dec=3, int=False),
            },
            "Hardware_Auto_Align_Reverse": {
                "display_text": "Auto-align F/B Lines",
                "widget": hardware_auto_align_reverse,
            },
            "Hardware_Auto_Align_Snake_Rows": {
                "display_text": "Auto-align Snake Reverse Rows",
                "widget": hardware_auto_align_snake,
            },
            "Hardware_Auto_Align_Max_Shift_px": {
                "display_text": "Max Auto-align Shift (pixels)",
                "widget": SpinBox(value=10.0, siPrefix=False, bounds=(0.0, 1000.0), step=1.0, dec=1, int=False),
            },
            "Hardware_Edge_Blank_Pixels": {
                "display_text": "Blank Edge Pixels",
                "widget": SpinBox(value=0, int=True, bounds=(0, 9999), dec=True),
            },
            "Hardware_Use_Bin_Widths": {
                "display_text": "Normalize Using CBM Bin Widths",
                "widget": hardware_use_bin_widths,
            },
            "Hardware_Bind_Pixel_Clock": {
                "display_text": "Bind MCL ISS Pixel Clock",
                "widget": hardware_bind_pixel_clock,
            },
            "Hardware_Pixel_Clock": {
                "display_text": "MCL ISS Pixel Clock Number",
                "widget": SpinBox(value=1, int=True, bounds=(1, 4), dec=True),
            },
            "Hardware_Pixel_Clock_Mode": {
                "display_text": "MCL ISS Pixel Clock Mode",
                "widget": SpinBox(value=2, int=True, bounds=(2, 4), dec=True),
            },
            "Hardware_ISS_Reset_Defaults": {
                "display_text": "Reset MCL ISS Defaults First",
                "widget": hardware_iss_reset,
            },
            "Hardware_Slow_Axis_Monitor": {
                "display_text": "Use monitor_n for Slow Axis",
                "widget": hardware_slow_monitor,
            },
            "Hardware_Line_Settle_ms": {
                "display_text": "Hardware Line Settle (ms)",
                "widget": SpinBox(value=0.0, siPrefix=False, bounds=(0.0, 1000.0), step=0.1, dec=3, int=False),
            },
            "Hardware_Poll_Interval_ms": {
                "display_text": "CBM Poll Interval (ms)",
                "widget": SpinBox(value=1.0, siPrefix=False, bounds=(0.1, 1000.0), step=0.1, dec=3, int=False),
            },
            "Hardware_Line_Timeout_s": {
                "display_text": "CBM Line Timeout (s)",
                "widget": SpinBox(value=30.0, siPrefix=False, bounds=(0.0, 3600.0), step=1.0, dec=3, int=False),
            },
            "Hardware_Max_Waveform_Points": {
                "display_text": "MCL Max Waveform Points",
                "widget": SpinBox(value=10000, int=True, bounds=(2, 10000), dec=True),
            },

            # Micro-Manager / MCL stage controls.
            "Settling_Time": {
                "display_text": "Stage Settling Time (ms)",
                "widget": SpinBox(value=2.0, siPrefix=False, bounds=(0.0, 1000.0), step=0.1, dec=3, int=False),
            },
            "Stage_Range_um": {
                "display_text": "MCL Stage Range (um)",
                "widget": SpinBox(value=200.0, siPrefix=False, bounds=(1.0, 1000.0), step=1.0, dec=3, int=False),
            },
            "User_Origin_Mode": {
                "display_text": "User Origin Mode: center/current",
                "widget": QtWidgets.QLineEdit("center"),
            },
            "MM_Config_File": {
                "display_text": "MM Config File (optional)",
                "widget": QtWidgets.QLineEdit(""),
            },
            "MM_App_Path": {
                "display_text": "MM App Path for headless mode (optional)",
                "widget": QtWidgets.QLineEdit(""),
            },
        }

        # Parameters listed here remain part of params_config and are still
        # passed to Two_D_Scan_R_mm, but they are hidden in the normal view.
        # Click the Advanced Settings button to show/edit them.
        self._advanced_param_keys = [
            "Return_to_Start",
            "Laser_Enable",
            "Laser_Control_Mode",
            "Enable_SPCM_Gate",
            "Laser_Warmup_ms",
            "Laser_Shutdown_On_Finish",
            "PS_Reset_On_Finish",
            "Laser_Serial_Port",
            "Laser_Fail_On_Error",
            "DAQ_Control_Mode",
            "Photon_Channel",
            "Trigger_Level",
            "CBM_Begin_Channel",
            "CBM_End_Channel",
            "Marker_Trigger_Level",
            "Hardware_Line_Mode",
            "Hardware_Display_Image",
            "Hardware_Reverse_Line_Shift_px",
            "Hardware_Auto_Align_Reverse",
            "Hardware_Auto_Align_Snake_Rows",
            "Hardware_Auto_Align_Max_Shift_px",
            "Hardware_Edge_Blank_Pixels",
            "Hardware_Use_Bin_Widths",
            "Hardware_Bind_Pixel_Clock",
            "Hardware_Pixel_Clock",
            "Hardware_Pixel_Clock_Mode",
            "Hardware_ISS_Reset_Defaults",
            "Hardware_Slow_Axis_Monitor",
            "Hardware_Line_Settle_ms",
            "Hardware_Poll_Interval_ms",
            "Hardware_Line_Timeout_s",
            "Hardware_Max_Waveform_Points",
            "Settling_Time",
            "Stage_Range_um",
            "User_Origin_Mode",
            "MM_Config_File",
            "MM_App_Path",
        ]
        self._scan_params_config = params_config

        super().__init__(
            params_config,
            sm,
            "SpinMeasurements",
            "Two_D_Scan_R_mm",
            title="2D_Scan_mm",
        )

        self._install_advanced_settings_toggle(params_config, self._advanced_param_keys)
        self._make_compact()


    def _make_compact(self):
        """Reduce vertical spacing without changing any scan behavior."""
        self.setStyleSheet("""
            QLabel {
                font-size: 8pt;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                font-size: 8pt;
                min-height: 18px;
                max-height: 22px;
                padding: 0px 3px;
            }
            QCheckBox {
                font-size: 8pt;
                spacing: 3px;
            }
            QPushButton {
                font-size: 8pt;
                min-height: 20px;
                padding: 1px 6px;
            }
        """)

        for widget in self.findChildren(QtWidgets.QWidget):
            if isinstance(
                widget,
                (
                    QtWidgets.QLineEdit,
                    QtWidgets.QComboBox,
                    QtWidgets.QSpinBox,
                    QtWidgets.QDoubleSpinBox,
                    QtWidgets.QCheckBox,
                    QtWidgets.QPushButton,
                ),
            ):
                widget.setMaximumHeight(24)

        for layout in self._iter_layouts(self.layout()):
            layout.setSpacing(2)
            layout.setContentsMargins(2, 2, 2, 2)

    def _install_advanced_settings_toggle(self, params_config, advanced_keys):
        """Add an in-widget Advanced Settings toggle and hide advanced rows."""
        self._advanced_settings_button = QtWidgets.QPushButton("Advanced Settings")
        self._advanced_settings_button.setCheckable(True)
        self._advanced_settings_button.setChecked(False)
        self._advanced_settings_button.setToolTip(
            "Show or hide hardware/backend settings that usually stay fixed."
        )
        self._advanced_settings_button.clicked.connect(self._toggle_advanced_settings)

        layout = self.layout()
        if layout is not None:
            try:
                layout.insertWidget(0, self._advanced_settings_button)
            except Exception:
                layout.addWidget(self._advanced_settings_button)

        self._advanced_widgets = self._find_param_row_widgets(params_config, advanced_keys)
        self._toggle_advanced_settings(False)

    def _toggle_advanced_settings(self, checked=None):
        """Show/hide the advanced parameter rows."""
        if checked is None:
            checked = bool(self._advanced_settings_button.isChecked())
        else:
            checked = bool(checked)

        for widget in getattr(self, "_advanced_widgets", []):
            try:
                widget.setVisible(checked)
            except RuntimeError:
                pass

        self._advanced_settings_button.setChecked(checked)
        self._advanced_settings_button.setText(
            "Hide Advanced Settings" if checked else "Advanced Settings"
        )
        self.updateGeometry()

    def _find_param_row_widgets(self, params_config, advanced_keys):
        """Find both field widgets and their labels/row containers.

        ExperimentWidget creates the actual Qt layout internally. This helper is
        intentionally defensive: it first uses layout geometry when available,
        and then falls back to matching QLabel text against display_text.
        """
        found = []
        seen = set()

        def add(widget):
            if widget is None:
                return
            if widget is self or widget is getattr(self, "_advanced_settings_button", None):
                return
            ident = id(widget)
            if ident not in seen:
                seen.add(ident)
                found.append(widget)

        for key in advanced_keys:
            cfg = params_config.get(key, {})
            field_widget = cfg.get("widget")
            display_text = self._normalize_label_text(cfg.get("display_text", ""))
            add(field_widget)

            # Best case: locate the row containing this field widget and hide
            # the paired label/container as well.
            for layout in self._iter_layouts(self.layout()):
                self._add_matching_layout_row_widgets(layout, field_widget, add)

            # Fallback: hide QLabel objects with the same visible text.
            if display_text:
                for label in self.findChildren(QtWidgets.QLabel):
                    if self._normalize_label_text(label.text()) == display_text:
                        add(label)

        return found

    @staticmethod
    def _normalize_label_text(text):
        return str(text).replace("&", "").replace(":", "").strip().lower()

    def _iter_layouts(self, layout, _seen=None):
        """Yield a layout and all nested layouts, including layouts owned by widgets."""
        if _seen is None:
            _seen = set()
        if layout is None or id(layout) in _seen:
            return
        _seen.add(id(layout))
        yield layout
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if item is None:
                continue
            child_layout = item.layout()
            if child_layout is not None:
                yield from self._iter_layouts(child_layout, _seen)
            child_widget = item.widget()
            if child_widget is not None and child_widget.layout() is not None:
                yield from self._iter_layouts(child_widget.layout(), _seen)

    def _widget_contains(self, container, child):
        if container is None or child is None:
            return False
        if container is child:
            return True
        try:
            return child in container.findChildren(QtWidgets.QWidget)
        except Exception:
            return False

    def _add_matching_layout_row_widgets(self, layout, field_widget, add):
        """Add widgets in the same form/grid row as field_widget."""
        if layout is None or field_widget is None:
            return

        # QFormLayout: hide both label and field for the row.
        if isinstance(layout, QtWidgets.QFormLayout):
            try:
                label_role = QtWidgets.QFormLayout.ItemRole.LabelRole
                field_role = QtWidgets.QFormLayout.ItemRole.FieldRole
            except AttributeError:  # PyQt5
                label_role = QtWidgets.QFormLayout.LabelRole
                field_role = QtWidgets.QFormLayout.FieldRole

            for row in range(layout.rowCount()):
                field_item = layout.itemAt(row, field_role)
                field = field_item.widget() if field_item is not None else None
                if self._widget_contains(field, field_widget):
                    label_item = layout.itemAt(row, label_role)
                    label = label_item.widget() if label_item is not None else None
                    add(label)
                    add(field)
            return

        # QGridLayout: hide every widget on the same row as field_widget.
        if isinstance(layout, QtWidgets.QGridLayout):
            matching_rows = set()
            for index in range(layout.count()):
                item = layout.itemAt(index)
                widget = item.widget() if item is not None else None
                if self._widget_contains(widget, field_widget):
                    try:
                        row, _col, _row_span, _col_span = layout.getItemPosition(index)
                        matching_rows.add(row)
                    except Exception:
                        pass

            if matching_rows:
                for index in range(layout.count()):
                    item = layout.itemAt(index)
                    widget = item.widget() if item is not None else None
                    try:
                        row, _col, _row_span, _col_span = layout.getItemPosition(index)
                    except Exception:
                        continue
                    if row in matching_rows:
                        add(widget)


TwoD_Scan = TwoD_Scan_mm


def _extract_datasets(sink: DataSink):
    datasets = getattr(sink, "datasets", None)
    if datasets is not None:
        return datasets
    data = getattr(sink, "data", {})
    if isinstance(data, dict):
        return data.get("datasets", data)
    raise RuntimeError("DataSink update did not contain a datasets dictionary.")


def _coerce_image_shape(image, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    img = np.asarray(image, dtype=float)
    expected_shape = (len(y), len(x))
    if img.shape == expected_shape:
        return img
    if img.size == len(x) * len(y):
        return img.reshape(expected_shape)
    if img.T.shape == expected_shape:
        return img.T
    raise ValueError(f"Image shape {img.shape} does not match axes {expected_shape}.")


def process_2D_Scan_data(sink: DataSink):
    datasets = _extract_datasets(sink)
    x = np.asarray(datasets["xSteps"], dtype=float)
    y = np.asarray(datasets["ySteps"], dtype=float)
    scan_display = _coerce_image_shape(datasets.get("Scan_Display", datasets["Scan_Forward"]), x, y)
    scan_forward = _coerce_image_shape(datasets["Scan_Forward"], x, y)
    scan_backward = _coerce_image_shape(datasets.get("Scan_Backward", scan_forward), x, y)
    scan_averaged = _coerce_image_shape(datasets.get("Scan_Averaged", scan_forward), x, y)
    finite_values = np.concatenate([
        scan_forward[np.isfinite(scan_forward)].ravel(),
        scan_backward[np.isfinite(scan_backward)].ravel(),
        scan_averaged[np.isfinite(scan_averaged)].ravel(),
    ])
    vmin = float(np.min(finite_values)) if finite_values.size else 0.0
    vmax = float(np.max(finite_values)) if finite_values.size else 0.0
    return {
        "x": x,
        "y": y,
        "scan_display": scan_display,
        "scan_forward": scan_forward,
        "scan_backward": scan_backward,
        "scan_averaged": scan_averaged,
        "extent": (x[0], x[-1], y[0], y[-1]),
        "vmin": vmin,
        "vmax": vmax,
    }


class ScanPlotWidget_mm(HeatMapWidget):
    """HeatMapWidget that displays the Micro-Manager scan dataset.

    nspyre may call update() from a worker thread. Qt widgets must only be
    touched from the GUI thread, so update() only reads DataSink data and emits
    a queued signal. _apply_data_to_gui() performs the actual plot update in
    the widget's own thread.
    """

    _data_ready = _Signal(object)

    def __init__(self, dataset_name: str = DATASET_NAME):
        self.dataset_name = dataset_name
        super().__init__(title="2D_Scan_mm", btm_label="Axis 1 (um)", lft_label="Axis 2 (um)", colormap=None)
        self.pointClicked.connect(self._on_point_clicked)
        self._data_ready.connect(self._apply_data_to_gui, _QUEUED_CONNECTION)

    def setup(self):
        self.sink = DataSink(self.dataset_name)
        self.sink.__enter__()

    def teardown(self):
        try:
            self.sink.__exit__()
        except AttributeError:
            pass

    def update(self):
        # Do not call set_data(), setLabel(), or any other Qt/pyqtgraph method
        # here. This function can be invoked outside the GUI thread.
        self.sink.pop()
        datasets = _extract_datasets(self.sink)
        x = np.asarray(datasets["xSteps"], dtype=float)
        y = np.asarray(datasets["ySteps"], dtype=float)
        image_key = "Scan_Display" if "Scan_Display" in datasets else "Scan_Forward"
        img = _coerce_image_shape(datasets[image_key], x, y)

        payload = {
            "x": x,
            "y": y,
            "img": img,
            "xLabel": str(datasets.get("xLabel", "Axis 1 (um)")),
            "yLabel": str(datasets.get("yLabel", "Axis 2 (um)")),
            "imageKey": image_key,
            "displaySource": str(datasets.get("Scan_Display_Source", image_key)),
        }
        self._data_ready.emit(payload)

    def _apply_data_to_gui(self, payload):
        try:
            self.plot_item.setLabel("bottom", payload["xLabel"])
            self.plot_item.setLabel("left", payload["yLabel"])
        except Exception:
            pass
        self.set_data(payload["x"], payload["y"], payload["img"])

    def _on_point_clicked(self, x, y, value, ix, iy, iz):
        print(f"Heatmap click -> axis1={x:.3f} um, axis2={y:.3f} um, value={value:.0f} (ix={ix}, iy={iy})")


ScanPlotWidget = ScanPlotWidget_mm
