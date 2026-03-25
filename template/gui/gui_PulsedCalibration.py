"""
Rolando A. Fimbres G. 8/7/2025

The following script is mostly based on Tian-Xing Zheng's script,
it has been adapted for our equipment.

This script will contain the necessary parameters and push them in order to perform an
ODMR measurement.

    -   In order to make this work we should adapt the necessary functions in 
        the 'spin_measurements' script.

"""
import numpy as np
from nspyre import FlexLinePlotWidget, InstrumentGateway
from nspyre import ExperimentWidget
from nspyre import DataSink
from pyqtgraph import SpinBox
from pyqtgraph.Qt import QtWidgets
from . import spin_measurements as sm
# import the experiment 
import sys
sys.path.append('../experiments')

class PulsedCalibrationWidget(ExperimentWidget):
    def __init__(self, pulse_streamer_driver):
        self.ps = pulse_streamer_driver
        params_config = {
            'set_freq': {
                'display_text': 'Start Frequency',
                'widget': SpinBox(
                    value = 2.87e9,
                    suffix = 'Hz',
                    siPrefix = True,
                    bounds = (100e3, 7e9),
                    dec=True,
                ),
            },
            'iterations': {
                'display_text': 'Num. of Iterations',
                'widget': SpinBox(
                    value = 1,
                    int = True,
                    bounds = (1, None),
                    dec = True,
                ),
            },
            'mw_power': {
                'display_text': 'Microwave Power',
                'widget': SpinBox(
                    value = -15,
                    suffix = 'dBm',
                    siPrefix = False,
                ),
            },
            'laser_power': {
                'display_text': 'Laser Power [%]',
                'widget': SpinBox(
                    value = 5,
                    int = True,
                    bounds = (0, 100),
                    dec = True,
                ),
            },
            'init_time': {
                'display_text': 'Laser Init. Time: ',
                'widget': SpinBox(
                    value = 5e-6,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (5e-9, None),
                ),
            },
            'wait_time': {
                'display_text': 'Init Wait Time: ',
                'widget': SpinBox(
                    value = 600e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                ),
            },
            'time_resolution': {
                'display_text': 'Time Resolution: ',
                'widget': SpinBox(
                    value = 10,
                    suffix = 'ns',
                    siPrefix = True,
                    bounds = (1, 100),
                ),
            },
            'pi_xy': {
                'display_text': 'X or Y pulse?',
                'widget': QtWidgets.QLineEdit("x"),
            },
            'dataset': {
                'display_text': 'Data Set',
                'widget': QtWidgets.QLineEdit('Pulsed Calibration'),
            },
        }

        super().__init__(params_config, 
                        sm,  # No specific measurements class
                        'SpinMeasurements',  # No specific class name
                        'pulsed_calibration_run',  # No specific run method
                        title='Pulsed Calibration')
        

def process_data(sink: DataSink):
    for s,_ in enumerate(sink.datasets['Bright |0>']):
        bright_t = sink.datasets['Bright |0>'][s][0]
        dark_t = sink.datasets['Dark |+/-1>'][s][0]
        bright = sink.datasets['Bright |0>'][s][1]
        dark = sink.datasets['Dark |+/-1>'][s][1]

        # Avoid division by zero or invalid values
        bright[bright == 0] = np.nan
        dark[dark == 0] = np.nan

class FlexLinePlotWidgetWithPulsedCalibration(FlexLinePlotWidget):
    """Add some default settings to the FlexSinkLinePlotWidget."""
    def __init__(self):
        super().__init__(data_processing_func=process_data)
        # create some default average plots
        self.add_plot('bright_avg',        series='Bright |0>',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('dark_avg',         series='Dark |+/-1>',   scan_i='',     scan_j='',  processing='Average')
        #self.add_plot('norm_avg',       series='norm',  scan_i='',      scan_j='',  processing='Average') # add normalized plot to main plots -A.K 11/19/2025
        # manually set the XY range
        #self.line_plot.plot_item().setXRange(3.0, 4.0)
        #self.line_plot.plot_item().setYRange(-3000, 4500)

        # retrieve legend object
        legend = self.line_plot.plot_widget.addLegend()
        # set the legend location
        legend.setOffset((-10, -50))

        self.datasource_lineedit.setText('Pulsed Calibration')