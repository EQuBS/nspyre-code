"""
GUI elements for Calibration
Tian-Xing Zheng, Dec.2023
"""
import numpy as np

from nspyre import FlexLinePlotWidget
from nspyre import ExperimentWidget
from nspyre import DataSink
from pyqtgraph import SpinBox
from pyqtgraph.Qt import QtWidgets

#import the experiment spyrelet file
import sys
sys.path.append('../experiments')
from . import spin_measurements as sm

class CalibrateWidget(ExperimentWidget):
    def __init__(self):
        params_config = {
            'runs': {
                'display_text': 'Runs (per pt.): ',
                'widget': SpinBox(
                    value = 200,
                    int = True,
                    bounds=(1, None),
                ),
            },

            'iters': {
                'display_text': 'Exp. Iterations: ',
                'widget': SpinBox(
                    value = 10,
                    int = True,
                    bounds=(1, None),
                ),
            },

            'Read_Start_Time': {
                'display_text': 'First Read Window: ',
                'widget': SpinBox(
                    value = 1e-6,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                    dec = True,
                ),
            },

            'Read_Stop_Time': {
                'display_text': 'Last Read Window: ',
                'widget': SpinBox(
                    value = 50e-6,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                    dec = True,
                ),
            },

            'num_pts': {
                'display_text': '# of Points: ',
                'widget': SpinBox(
                    value = 20,
                    int = True,
                    bounds=(1, None),
                    dec = True,
                ),
            },

            'read_window': {
                'display_text': 'Read Window: ',
                'widget': SpinBox(
                    value = 50e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (10e-9, None),
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

            'laser_start': {
                'display_text': 'Laser Start: ',
                'widget': SpinBox(
                    value = 1e-6,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (10e-9, None),
                ),
            },

            'laser_window': {
                'display_text': 'Laser Window: ',
                'widget': SpinBox(
                    value = 2e-6,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (10e-9, None),
                ),
            },
        }

        super().__init__(params_config, 
                        sm,
                        'SpinMeasurements',
                        'cal_lag_run_R',
                        title='Calibrate Laser_lag')

def process_Calibrate_data(sink: DataSink):
    pass
    

class FlexLinePlotWidgetWithCali(FlexLinePlotWidget):
    """Add some default settings to the FlexSinkLinePlotWidget."""
    def __init__(self):
        super().__init__(data_processing_func=process_Calibrate_data)
        # create some default average plots
        self.add_plot('sig_avg',        series='signal',   scan_i='',     scan_j='',  processing='Average')
        

        # retrieve legend object
        legend = self.line_plot.plot_widget.addLegend()
        # set the legend location
        legend.setOffset((-10, -50))

        self.datasource_lineedit.setText('Calibration')
