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

class ODMR_Widget(ExperimentWidget):
    def __init__(self, pulse_streamer_driver):
        self.ps = pulse_streamer_driver
        params_config = {
            'start_freq': {
                'display_text': 'Start Frequency',
                'widget': SpinBox(
                    value = 2.4e9,
                    suffix = 'Hz',
                    siPrefix = True,
                    bounds = (100e3, 7e9),
                    dec=True,
                ),
            },
            'stop_freq': {
                'display_text': 'Stop Frequency',
                'widget': SpinBox(
                    value = 3.2e9,
                    suffix = 'Hz',
                    siPrefix = True,
                    bounds = (100e3, 7e9),
                    dec=True,
                ),
            },
            'num_points': {
                'display_text': 'Number of Points',
                'widget': SpinBox(
                    value = 40,
                    int = True,
                    bounds = (1, None),
                    dec=True,
                ),
            },
            'dwell_time': {
                'display_text': 'Dwell Time',
                'widget': SpinBox(
                    value = 200e-3,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (2e-9, None),
                    dec=True,
                ),
            },
            'runs': {
                'display_text': 'Runs (per pt.)',
                'widget': SpinBox(
                    value = 1,
                    int = True,
                    bounds = (1, None),
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
            'probe_time': {
                'display_text': 'MW Probe Time',
                'widget': SpinBox(
                    value = 50e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (10e-9, None),
                    dec=True,
                ),
            },
            'odmr_type': {
                'display_text': 'ODMR Type',
                'widget': QtWidgets.QLineEdit("CW"),
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
                'display_text': 'Init. Time: ',
                'widget': SpinBox(
                    value = 5e-6,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (5e-9, None),
                ),
            },
            'read_time': {
                'display_text': 'Readout Time: ',
                'widget': SpinBox(
                    value = 600e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (10e-9, None),
                ),
            },
            'wait_time': {
                'display_text': 'Init Wait (singlet decay): ',
                'widget': SpinBox(
                    value = 600e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                ),
            },
            'read_wait': {
                'display_text': 'Read Wait: ',
                'widget': SpinBox(
                    value = 350e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                ),
            },
            'pi_xy': {
                'display_text': 'X or Y pulse?',
                'widget': QtWidgets.QLineEdit("x"),
            },
            'pi_time': {
                'display_text': 'pi_time: ',
                'widget': SpinBox(
                    value = 10e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                ),
            },
            'dataset': {
                'display_text': 'Data Set',
                'widget': QtWidgets.QLineEdit('ODMR'),
            },
        }
        # Gate (SPCM) on button
        gate_on_button = QtWidgets.QPushButton('Gate/Laser On ')
        gate_on_button.clicked.connect(lambda: self.ps.gate_on())
        # Gate (SPCM) off button
        gate_off_button = QtWidgets.QPushButton('Gate/Laser Off')
        gate_off_button.clicked.connect(lambda: self.ps.gate_off())
        super().__init__(params_config, 
                        sm,  # No specific measurements class
                        'SpinMeasurements',  # No specific class name
                        'odmr_run_R',  # No specific run method
                        title='ODMR')\

"""                        
layout = QtWidgets.QGridLayout()
# Gate (SPCM) on button
gate_on_button = QtWidgets.QPushButton('Gate/Laser On ')
gate_on_button.clicked.connect(lambda: self.ps.gate_on())
layout.addWidget(gate_on_button, 0, 1)
# Gate (SPCM) off button
gate_off_button = QtWidgets.QPushButton('Gate/Laser Off')
gate_off_button.clicked.connect(lambda: self.ps.gate_off())
layout.addWidget(gate_off_button, 0, 2)
self.setLayout(layout)
"""
def process_ODMR_data(sink: DataSink):
    """Subtract the signal from background trace and add it as a new 'diff' dataset."""
    diff_sweeps = []
    div_sweeps = []
    divnow_sweeps = []
    for s,_ in enumerate(sink.datasets['signal']):
        freqs = sink.datasets['signal'][s][0]
        sig = sink.datasets['signal'][s][1]
        bg = sink.datasets['background'][s][1]

        # Avoid division by zero or invalid values
        # sig[sig == 0] = np.nan
        bg[bg == 0] = np.nan

        diff_sweeps.append(np.stack([freqs/1E9, sig - bg]))
        div_sweeps.append(np.stack([freqs/1E9, sig/bg]))
        #divnow_sweeps.append(np.stack([freqs, np.mean(sink.datasets['signal'][:s][1],axis=0)/np.mean(sink.datasets['background'][:s][1],axis=0)]))
    sink.datasets['diff'] = diff_sweeps
    sink.datasets['div'] = div_sweeps
    sink.datasets['div_now'] = divnow_sweeps

class FlexLinePlotWidgetWithODMR(FlexLinePlotWidget):
    """Add some default settings to the FlexSinkLinePlotWidget."""
    def __init__(self):
        super().__init__(data_processing_func=process_ODMR_data)
        # create some default average plots
        self.add_plot('sig_avg',        series='signal',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('bg_avg',         series='background',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('div_avg',       series='div',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('div_avg')
        self.add_plot('div_now',       series='div_now',  scan_i='-1',      scan_j='',  processing='Average')
        self.hide_plot('div_now')
        self.add_plot('diff_avg',       series='diff',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('diff_avg')
        # create some plot that not frequently used, so we hide them
        self.add_plot('sig_latest',     series='signal',   scan_i='-1',   scan_j='',  processing='Average')
        self.add_plot('sig_first',      series='signal',   scan_i='0',    scan_j='1', processing='Average')
        self.add_plot('sig_latest_10',  series='signal',   scan_i='-10',  scan_j='',  processing='Average')
        self.hide_plot('sig_latest')
        self.hide_plot('sig_first')
        self.hide_plot('sig_latest_10')

        self.add_plot('bg_latest',      series='background',   scan_i='-1',   scan_j='',  processing='Average')
        self.hide_plot('bg_latest')

        
        self.add_plot('diff_latest',    series='diff',  scan_i='-1',    scan_j='',  processing='Average')
        self.hide_plot('diff_latest')
        
        self.add_plot('div_latest',    series='div',  scan_i='-1',    scan_j='',  processing='Average')
        self.hide_plot('div_latest')
        # manually set the XY range
        #self.line_plot.plot_item().setXRange(3.0, 4.0)
        #self.line_plot.plot_item().setYRange(-3000, 4500)

        # retrieve legend object
        legend = self.line_plot.plot_widget.addLegend()
        # set the legend location
        legend.setOffset((-10, -50))

        self.datasource_lineedit.setText('ODMR')        
