"""
Rolando A. Fimbres Grijalva 6/1/2026

The following gui elements defined here work as initial parameters to run as sequence
to capture Time-Resolved Spin-Dependent Fluorescence in NV Centers data.
"""
import numpy as np
from nspyre import FlexLinePlotWidget, InstrumentGateway
from nspyre import ExperimentWidget
from nspyre import DataSink
from pyqtgraph import SpinBox
from pyqtgraph.Qt import QtWidgets
from . import spin_measurements as sm
import sys
sys.path.append('../experiments')

class TRSDF_Widget(ExperimentWidget):
    def __init__(self):
        self.pi_type_combo = QtWidgets.QComboBox()
        self.pi_type_combo.addItems(['x', 'y']) 
        self.pi_type_combo.setCurrentText('x')
        params_config = {

            'freq': {
                'display_text': 'MW Freq.: ',
                'widget': SpinBox(
                    value = 2.87e9,
                    suffix = 'Hz',
                    siPrefix = True,
                    bounds = (100e3, 20e9),
                    dec = True,
                ),
            },

            'rf_power': {
                'display_text': 'RF Power: ',
                'widget': SpinBox(
                    value = -15,
                    suffix = 'dBm',
                    siPrefix = False,
                    bounds = (None, 0),
                ),
            },

            'laser_power': {
                'display_text': 'Laser Power [%]',
                'widget': SpinBox(
                    value=5,
                    int=True,
                    bounds=(0, 100),
                    dec=True,
                ),
            },

            'pi_duration': {
                'display_text': '\u03C0 duration: ',
                'widget': SpinBox(
                    value = 40e-6,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (8e-9, None),
                ),
            },

            'pi_xy': {
                'display_text': 'X or Y pulse?',
                'widget': self.pi_type_combo,
            },

            'init_time': {
                'display_text': 'Init. Time: ',
                'widget': SpinBox(
                    value = 3e-6,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (5e-7, None),
                ),
            },

            'tau_delay': {
                'display_text': 'Tau Delay: ',
                'widget': SpinBox(
                    value = 500e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (10e-9, None),
                ),
            },

            'readout_time': {
                'display_text': 'Readout Time: ',
                'widget': SpinBox(
                    value = 1000e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (10e-9, None),
                ),
            },

            'dead_time': {
                'display_text': 'Dead Time: ',
                'widget': SpinBox(
                    value = 2000e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                ),
            },

            'n_bins': {
                'display_text': 'Num. Bins: ',
                'widget': SpinBox(
                    value = 1000,
                    int = True,
                    bounds=(1, None),
                    dec = True,
                ),
            },

            'bin_width_ps': {
                'display_text': 'Bin Width [ps]: ',
                'widget': SpinBox(
                    value = 1000,
                    int = True,
                    bounds=(1, None),
                    dec = True,
                ),
            },

            #'integration_time_sec': {
            #    'display_text': 'Integration Time [s]: ',
            #    'widget': SpinBox(
            #        value = 10.0,
            #       suffix = 's',
            #        siPrefix = True,
            #        bounds = (1.0, None),
            #        dec = True,
            #    ),
            #},

            'interleave_interval_sec': {
                'display_text': 'Interl. Integ. per cycle [s]: ',
                'widget': SpinBox(
                    value = 4.0,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1.0, None),
                    dec = True,
                ),
            },

            'cycles': {
                'display_text': 'Num. Cycles: ',
                'widget': SpinBox(
                    value = 10,
                    int = True,
                    bounds=(1, None),
                    dec = True,
                ),
            },

            'refocus_cycle': {
                'display_text': 'Refocus per Cycle: ',
                'widget': SpinBox(
                    value = 5,
                    int = True,
                    bounds=(1, None),
                    dec = True,
                ),
            },
        }

        super().__init__(params_config, 
                        sm,
                        'SpinMeasurements',
                        'time_res_sdf_run',
                        title='Time-Resolved SDF Data')
        
def process_TRSDF_data(sink: DataSink):
    for s,_ in enumerate(sink.datasets['bright']):
        time = sink.datasets['bright'][s][0]
        bright = sink.datasets['bright'][s][1]
        dark = sink.datasets['dark'][s][1]

class FlexLinePlotWidgetWithTRSDF(FlexLinePlotWidget):
    """Add some default settings to the FlexSinkLinePlotWidget."""
    def __init__(self):
        super().__init__(data_processing_func=process_TRSDF_data)
        
        self.add_plot('bright, ms=0',        series='bright',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('dark, ms=+/-1',         series='dark',   scan_i='',     scan_j='',  processing='Average')

        # retrieve legend object
        legend = self.line_plot.plot_widget.addLegend()
        # set the legend location
        legend.setOffset((-10, -50))

        self.datasource_lineedit.setText('Time-Resolved SDF Data')