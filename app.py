#!/usr/bin/env python
"""
Safe project app launcher.

Main fixes relative to the previous app.py:
    1. No InstrumentGateway connection is created at module import time.
       This is important on Windows because nspyre/multiprocessing re-imports
       the main module in experiment subprocesses.
    2. Risky/unused imports are not executed globally.  Widgets are imported
       inside main() after the __main__ guard is active.
    3. A dedicated Hardware Confocal tab is added.  It defaults to the direct
       MCL/Madlib + Time Tagger CountBetweenMarkers scan path.
"""
from __future__ import annotations

import logging
from pathlib import Path

_HERE = Path(__file__).parent


def _qt_exec(app):
    """Run the Qt event loop with PyQt5/PyQt6 compatibility."""
    if hasattr(app, "exec"):
        return app.exec()
    return app.exec_()


def main():
    # Imports stay inside main() so subprocesses spawned by nspyre do not
    # create GUI widgets, InstrumentGateway connections, or hardware proxies
    # merely by importing this file as __mp_main__.
    import nspyre.gui.widgets.save
    import nspyre.gui.widgets.load
    import nspyre.gui.widgets.flex_line_plot
    import nspyre.gui.widgets.subsystem
    from nspyre import InstrumentGateway, MainWidget, MainWidgetItem, nspyreApp, nspyre_init_logger

    import template.gui.elements
    from template.drivers.insmgr import MyInstrumentManager
    import template.gui.gui_SigVsTime
    import template.gui.gui_dlnsec
    import template.gui.gui_2D_Scan_mm
    import template.gui.gui_2D_Scan_hardware
    import template.gui.gui_TRSDF
    import template.gui.gui_Nano3
    import template.gui.gui_ODMR
    import template.gui.gui_Rabi
    import template.gui.gui_Rabi_test
    import template.gui.gui_T1
    import template.gui.gui_T2
    import template.gui.gui_Calibrate

    nspyre_init_logger(
        log_level=logging.INFO,
        log_path=_HERE / "../logs",
        log_path_level=logging.DEBUG,
        prefix=Path(__file__).stem,
        file_size=10_000_000,
    )

    # Keep the gateway lifetime scoped to the GUI lifetime.  Do not create this
    # at module import level, because Windows multiprocessing re-imports app.py
    # in scan subprocesses.
    with MyInstrumentManager() as insmgr, InstrumentGateway(port=42068) as gw:
        laser_driver = gw.laser
        pulse_streamer_driver = gw.ps

        app = nspyreApp()

        main_widget = MainWidget(
            {
                "DLnsec": MainWidgetItem(
                    template.gui.gui_dlnsec,
                    "DLnsecWidget",
                    args=[laser_driver, pulse_streamer_driver],
                    stretch=(1, 1),
                ),
                "I-t": MainWidgetItem(
                    template.gui.gui_SigVsTime,
                    "SigVsTimeWidget",
                    stretch=(1, 1),
                ),
                "Subsystems": MainWidgetItem(
                    nspyre.gui.widgets.subsystem,
                    "SubsystemsWidget",
                    args=[insmgr.subs.subsystems],
                    stretch=(1, 1),
                ),
                # Motion ctrl through MCL_Wrapper
                "MCL Nano": MainWidgetItem(
                    template.gui.gui_Nano3,
                    "NanoWidget",
                    args=[gw.nano],
                    stretch=(1, 1),
                ),
                # Micro-Manager/Pycro-Manager motion and scan widgets.
                # For the direct hardware MCL/CBM scan, close Micro-Manager or
                # avoid opening the Micro-Manager Nano widget to prevent handle
                # competition with gw.nano.
                #"µM Nano": MainWidgetItem(
                #    template.gui.gui_Nano3_mm,
                #    "NanoWidget",
                #    stretch=(1, 1),
                #),
                "µM Scan": MainWidgetItem(
                    template.gui.gui_2D_Scan_mm,
                    "TwoD_Scan",
                    stretch=(1, 1),
                ),

                # Hardware-fast direct-MCL confocal scan.  This tab defaults to
                # Scan_Mode = hardware_mcl_cbm and includes snake scan support.
                "HW Confocal": MainWidgetItem(
                    template.gui.gui_2D_Scan_hardware,
                    "TwoD_Hardware_Scan",
                    stretch=(1, 1),
                ),

                "T1": MainWidgetItem(
                    template.gui.gui_T1,
                    "T1Widget",
                    stretch=(1, 1),
                ),

                "T2": MainWidgetItem(
                    template.gui.gui_T2,
                    "T2Widget",
                    stretch=(1, 1),
                ),

                "TRSDF": MainWidgetItem(
                    template.gui.gui_TRSDF,
                    "TRSDF_Widget",
                    stretch=(1, 1),
                ),

                "ODMR": MainWidgetItem(
                    template.gui.gui_ODMR,
                    "ODMR_Widget",
                    args=[pulse_streamer_driver],
                    stretch=(1, 1),
                ),
                "Rabi": MainWidgetItem(
                    template.gui.gui_Rabi,
                    "RabiWidget",
                    stretch=(1, 1),
                ),

                "Rabi-test": MainWidgetItem(
                    template.gui.gui_Rabi_test,
                    "RabiWidget",
                    stretch=(1, 1),
                ),

                "Plots": {
                    "FlexLinePlotDemo": MainWidgetItem(
                        template.gui.elements,
                        "FlexLinePlotWidgetWithODMRDefaults",
                        stretch=(100, 100),
                    ),
                    "FlexLinePlot": MainWidgetItem(
                        nspyre.gui.widgets.flex_line_plot,
                        "FlexLinePlotWidget",
                        stretch=(100, 100),
                    ),
                    "FlexLinePlot_SigVSTime": MainWidgetItem(
                        template.gui.gui_SigVsTime,
                        "FlexLinePlotWidgetWithSigVsTime",
                        stretch=(100, 100),
                    ),
                    "Calibrate (laser lag)": MainWidgetItem(
                        template.gui.gui_Calibrate,
                        "FlexLinePlotWidgetWithCali",
                        stretch=(100, 100),
                    ),
                    "µM Scan": MainWidgetItem(
                        template.gui.gui_2D_Scan_mm,
                        "ScanPlotWidget_mm",
                        stretch=(100, 100),
                    ),
                    "HW Confocal": MainWidgetItem(
                        template.gui.gui_2D_Scan_hardware,
                        "HardwareScanPlotWidget",
                        stretch=(100, 100),
                    ),
                    "ODMRPlot": MainWidgetItem(
                        template.gui.gui_ODMR,
                        "FlexLinePlotWidgetWithODMR",
                        stretch=(100, 100),
                    ),
                    "RabiPlot": MainWidgetItem(
                        template.gui.gui_Rabi,
                        "FlexLinePlotWidgetWithRabi",
                        stretch=(100, 100),
                    ),
                    "T1Plot": MainWidgetItem(
                        template.gui.gui_T1,
                        "FlexLinePlotWidgetWithT1",
                        stretch=(100, 100),
                    ),
                    "T2Plot": MainWidgetItem(
                        template.gui.gui_T2,
                        "FlexLinePlotWidgetWithT2",
                        stretch=(100, 100),
                    ),
                    "TRSDFPlot": MainWidgetItem(
                        template.gui.gui_TRSDF,
                        "FlexLinePlotWidgetWithTRSDF",
                        stretch=(100, 100),
                    ),
                },
                "Save": MainWidgetItem(nspyre.gui.widgets.save, "SaveWidget", stretch=(1, 1)),
                "Load": MainWidgetItem(nspyre.gui.widgets.load, "LoadWidget", stretch=(1, 1)),
            }
        )
        main_widget.show()
        _qt_exec(app)


if __name__ == "__main__":
    main()
