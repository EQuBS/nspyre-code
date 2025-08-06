#!/usr/bin/env python
"""
This is an example script that demonstrates the basic functionality of nspyre. 
"""
import logging
from pathlib import Path

import nspyre.gui.widgets.save
import nspyre.gui.widgets.load
import nspyre.gui.widgets.flex_line_plot
import nspyre.gui.widgets.subsystem
import nspyre.gui.widgets.heatmap
from nspyre import MainWidget
from nspyre import MainWidgetItem
from nspyre import nspyre_init_logger
from nspyre import nspyreApp


# in order for dynamic reloading of code to work, you must pass the specifc
# module containing your class to MainWidgetItem, since the python reload()
# function does not recursively reload modules
import template.gui.elements
from template.drivers.insmgr import MyInstrumentManager
import template.gui.gui_SigVsTime
import template.gui.gui_T1
from template.gui.spin_measurements import SpinMeasurements
#from spin_measurements import SpinMeasurements 
import template.gui.gui_dlnsec
from template.drivers.dlnsec import DLnsec
from template.drivers.ps82 import PS82
import template.gui.spin_measurements
import template.gui.gui_Nano
import template.gui.gui_Scan
import template.gui.gui_ScanXZ
from template.drivers.TimeTaggerDriver import tt20

#print(template.gui.spin_measurements.__file__)

from nspyre import InstrumentGateway

import template.gui.test_Nano

from MCL_Madlib_Wrapper import MCL_Nanodrive
""" def get_nano_handle():
    try:
        nano = MCL_Nanodrive()
        handle = nano.init_handle()
        return nano, handle
    except Exception as e:
        print(f"Error initializing MCL Nanodrive: {e}")
        return None, None """

"""Pass the nano and handle with the use of InstrumentGateway.
Rolando 7/2/2025
"""

# Pass widget
#widget = NanoWidget(nano=nano, handle=handle)

gw = InstrumentGateway(port=42068)
laser_driver = gw.laser
nano = gw.nano  # This is the proxy to your NanoDriver or MCL_Nanodrive on the instrument server
tagger = gw.daq  # Time Tagger driver
#laser_driver = DLnsec('COM4')  # Change 'COM3' to the appropriate port for your system
pulse_streamer_driver = gw.ps  #PS82() commented out by Rolando 7/2/2025, test InstrumentGateway is now used.
#pulse_streamer_driver = PS82()

_HERE = Path(__file__).parent

def main():
    # Log to the console as well as a file inside the logs folder.
    nspyre_init_logger(
        log_level=logging.INFO,
        log_path=_HERE / '../logs',
        log_path_level=logging.DEBUG,
        prefix=Path(__file__).stem,
        file_size=10_000_000,
    )

    with MyInstrumentManager() as insmgr:
        # Create Qt application and apply nspyre visual settings.
        app = nspyreApp()

        # Create the GUI.
        main_widget = MainWidget(
            {
                'ODMR': MainWidgetItem(template.gui.elements, 'ODMRWidget', stretch=(1, 1)),
                'T1': MainWidgetItem(template.gui.gui_T1, 'T1Widget', stretch=(1, 1)),
                'DLnsec': MainWidgetItem(template.gui.gui_dlnsec, 'DLnsecWidget', args=[laser_driver, pulse_streamer_driver], stretch=(1, 1)),
                'I-t': MainWidgetItem(template.gui.gui_SigVsTime, 'SigVsTimeWidget', stretch=(1, 1)),
                'Subsystems': MainWidgetItem(nspyre.gui.widgets.subsystem, 'SubsystemsWidget', args=[insmgr.subs.subsystems], stretch=(1, 1)),
                'Nano Stage': MainWidgetItem(template.gui.gui_Nano, 'NanoWidget', args=[nano], stretch=(1, 1)),
                'Scan': MainWidgetItem(template.gui.gui_Scan, 'ScanWidget', args=[nano, laser_driver, pulse_streamer_driver, tagger], stretch=(1, 1)), # Scan widget not created yet. 6/23/2025
                'XZ-Scan': MainWidgetItem(template.gui.gui_ScanXZ, 'ScanXZ', stretch=(1, 1)),
                'Plots': {
                    'FlexLinePlotDemo': MainWidgetItem(
                        template.gui.elements,
                        'FlexLinePlotWidgetWithODMRDefaults',
                        stretch=(100, 100),
                    ),
                    'FlexLinePlot': MainWidgetItem(
                        nspyre.gui.widgets.flex_line_plot,
                        'FlexLinePlotWidget',
                        stretch=(100, 100),
                    ),
                    'FlexLinePlot_SigVSTime': MainWidgetItem(
                        template.gui.gui_SigVsTime,
                        'FlexLinePlotWidgetWithSigVsTime',
                        stretch=(100, 100),
                    ),
                    'ScanPlot': MainWidgetItem(
                        template.gui.gui_Scan,
                        'ScanPlotWidget',
                        stretch=(100, 100),
                    ),
                },
                'Save': MainWidgetItem(nspyre.gui.widgets.save, 'SaveWidget', stretch=(1, 1)),
                'Load': MainWidgetItem(nspyre.gui.widgets.load, 'LoadWidget', stretch=(1, 1)),
            }
        )
        main_widget.show()

        # Run the GUI event loop.
        app.exec()


# if using the nspyre ProcessRunner, the main code must be guarded with if __name__ == '__main__':
# see https://docs.python.org/2/library/multiprocessing.html#windows
if __name__ == '__main__':
    main()
