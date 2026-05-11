"""
Dedicated hardware-confocal scan GUI.

This is a thin wrapper around gui_2D_Scan_mm that defaults the scan engine to
hardware_mcl_cbm and the dataset to Confocal_Hardware.  It keeps the same
advanced settings, unidirectional/snake/forward-backward line modes, laser
safety handling, and direct-MCL CountBetweenMarkers scan path from the mm
hardware version.
"""
from __future__ import annotations

try:
    from .gui_2D_Scan_mm import TwoD_Scan_mm, ScanPlotWidget_mm
except Exception:
    from gui_2D_Scan_mm import TwoD_Scan_mm, ScanPlotWidget_mm


DATASET_NAME = "Confocal_Hardware"


class TwoD_Hardware_Scan(TwoD_Scan_mm):
    """Hardware-first confocal scan GUI.

    Fast axis is driven by direct MCL WFMA waveform control and the Time Tagger
    uses CountBetweenMarkers when Scan_Mode remains hardware_mcl_cbm.
    """

    def __init__(self):
        super().__init__()
        cfg = getattr(self, "_scan_params_config", {})
        if "Dataset_Name" in cfg:
            cfg["Dataset_Name"]["widget"].setText(DATASET_NAME)
        if "Scan_Mode" in cfg:
            cfg["Scan_Mode"]["widget"].setCurrentText("hardware_mcl_cbm")
        if "DAQ_Control_Mode" in cfg:
            cfg["DAQ_Control_Mode"]["widget"].setCurrentText("instrument_gateway")
        if "Hardware_Line_Mode" in cfg:
            cfg["Hardware_Line_Mode"]["widget"].setCurrentText("forward_only")
        if "Hardware_Display_Image" in cfg:
            cfg["Hardware_Display_Image"]["widget"].setCurrentText("forward")
        if "Bidirectional" in cfg:
            cfg["Bidirectional"]["widget"].setChecked(False)
        self.setWindowTitle("Hardware Confocal Scan")


class HardwareScanPlotWidget(ScanPlotWidget_mm):
    """Plot widget for the hardware-confocal default dataset."""

    def __init__(self):
        super().__init__(dataset_name=DATASET_NAME)


# Friendly aliases for MainWidgetItem.
TwoD_Scan = TwoD_Hardware_Scan
ScanPlotWidget = HardwareScanPlotWidget
