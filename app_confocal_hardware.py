#!/usr/bin/env python
"""
Minimal hardware-confocal app.

Use this if the full project app.py is still unstable.  It avoids Micro-Manager
widgets and avoids unused imports, so the direct MCL/Madlib hardware scan has
exclusive ownership of the NanoDrive through gw.nano.
"""
from __future__ import annotations

import logging
from pathlib import Path

_HERE = Path(__file__).parent


def _qt_exec(app):
    if hasattr(app, "exec"):
        return app.exec()
    return app.exec_()


def main():
    import nspyre.gui.widgets.save
    import nspyre.gui.widgets.load
    from nspyre import MainWidget, MainWidgetItem, nspyreApp, nspyre_init_logger

    import template.gui.gui_2D_Scan_hardware

    nspyre_init_logger(
        log_level=logging.INFO,
        log_path=_HERE / "../logs",
        log_path_level=logging.DEBUG,
        prefix=Path(__file__).stem,
        file_size=10_000_000,
    )

    app = nspyreApp()
    main_widget = MainWidget(
        {
            "HW Confocal": MainWidgetItem(
                template.gui.gui_2D_Scan_hardware,
                "TwoD_Hardware_Scan",
                stretch=(1, 1),
            ),
            "Plots": {
                "HW Confocal": MainWidgetItem(
                    template.gui.gui_2D_Scan_hardware,
                    "HardwareScanPlotWidget",
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
