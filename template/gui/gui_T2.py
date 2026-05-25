import numpy as np

from nspyre import FlexLinePlotWidget
from nspyre import ExperimentWidget
from nspyre import DataSink
from pyqtgraph import SpinBox
from pyqtgraph.Qt import QtWidgets

#import the experiment spyrelet file
import sys
sys.path.append('../')
from . import spin_measurements as sm

class T2Widget(ExperimentWidget):
    def __init__(self):

        self.T2_type_combo = QtWidgets.QComboBox()
        self.T2_type_combo.addItems(['Ramsey', 'Spin Echo'])
        self.T2_type_combo.setCurrentText('Ramsey')

        self.tau_type_combo = QtWidgets.QComboBox()
        self.tau_type_combo.addItems(['exp', 'linear'])
        self.tau_type_combo.setCurrentText('exp')

        params_config = {
            'runs': {
                'display_text': 'Runs (per pt.): ',
                'widget': SpinBox(
                    value = 2000,
                    int = True,
                    bounds=(1, None),
                ),
            },

            'iters': {
                'display_text': 'Exp. Iterations: ',
                'widget': SpinBox(
                    value = 50,
                    int = True,
                    bounds=(1, None),
                ),
            },

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
            'start': {
                'display_text': 'Start \u03C4 Time: ',
                'widget': SpinBox(
                    value = 0.5e-6,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                    dec = True,
                ),
            },

            'stop': {
                'display_text': 'Stop \u03C4 Time: ',
                'widget': SpinBox(
                    value = 10e-6,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (10e-9, None),
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
            'tau_type': {
                'display_text': '\u03C4s\' type',
                'widget': self.tau_type_combo,
            },

            'half_pi': {
                'display_text': '\u03C0/2: ',
                'widget': SpinBox(
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1e-9, None),
                ),
            },

            'pihalf_x': {
                'display_text': '\u03C0/2_x: ',
                'widget': SpinBox(
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1e-9, None),
                ),
            },

            'pihalf_y': {
                'display_text': '\u03C0/2_y: ',
                'widget': SpinBox(
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1e-9, None),
                ),
            },

            'pi_x': {
                'display_text': '\u03C0_x: ',
                'widget': SpinBox(
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1e-9, None),
                ),
            },

            'pi_y': {
                'display_text': '\u03C0_y: ',
                'widget': SpinBox(
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1e-9, None),
                ),
            },

            'pulse_axis': {
                'display_text': 'Pulse Axis:',
                'widget': QtWidgets.QLineEdit("Y"),
            },

            'n': {
                'display_text': '# of Seq. (n): ',
                'widget': SpinBox(
                    value = 1,
                    int = True,
                    bounds=(1, None),
                ),
            },

            'init_time': {
                'display_text': 'Init. Time: ',
                'widget': SpinBox(
                    value = 2e-6,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (5e-7, None),
                ),
            },

            'read_time': {
                'display_text': 'Readout Time: ',
                'widget': SpinBox(
                    value = 400e-9,
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
                    bounds = (10e-9, None),
                ),
            },
            'read_wait': {
                'display_text': 'Read Wait',
                'widget': SpinBox(
                    value = 10e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                ),
            },
            'seq_gap': {
                'display_text': 'Seq. Gap: ',
                'widget': SpinBox(
                    value=0,
                    suffix='s',
                    siPrefix=True,
                    bounds=(0, None),
                ),
            },
            'pi_xy': {
                'display_text': 'X or Y pulse?',
                'widget': QtWidgets.QLineEdit("x"),
            },
            'seq': {
                'display_text': 'sequence',
                'widget': self.T2_type_combo,
            },
        }

        super().__init__(params_config, 
                        sm,
                        'SpinMeasurements',
                        'T2_run',
                        title='T2')




def process_T2_data(sink: DataSink):
    """Subtract the signal from background trace and add it as a new 'diff' dataset."""
    diff_sweeps = []
    contrast_sweeps = []
    #print('\n datasets[signal] now', sink.datasets['signal'])
    #print('\n datasets[background] now', sink.datasets['background'])
    for s,_ in enumerate(sink.datasets['ms1']):
        x_axis_data = sink.datasets['ms1'][s][0]
        ms1 = sink.datasets['ms1'][s][1]
        ms0 = sink.datasets['ms0'][s][1]
        diff_sweeps.append(np.stack([x_axis_data, ms0 - ms1]))
        contrast_sweeps.append(np.stack([x_axis_data, (ms0 - ms1)/(ms0 + ms1)]))
        #div_sweeps.append(np.stack([mw_times, sig/bg]))
    sink.datasets['diff'] = diff_sweeps
    sink.datasets['contrast'] = contrast_sweeps

class FlexLinePlotWidgetWithT2(FlexLinePlotWidget):
    """Add some default settings to the FlexSinkLinePlotWidget."""
    def __init__(self):
        super().__init__(data_processing_func=process_T2_data)
        # create some default average plots
        self.add_plot('ms1_avg',        series='ms1',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('ms0_avg',         series='ms0',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('contrast_avg',       series='contrast',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('contrast_avg')
        self.add_plot('diff_avg',       series='diff',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('diff_avg')

        # create some plots that not frequently used, so we hide them
        self.add_plot('ms1_latest',     series='ms1',   scan_i='-1',   scan_j='',  processing='Average')
        self.add_plot('ms1_first',      series='ms1',   scan_i='0',    scan_j='1', processing='Average')
        self.add_plot('ms1_latest_10',  series='ms1',   scan_i='-10',  scan_j='',  processing='Average')
        self.hide_plot('ms1_latest')
        self.hide_plot('ms1_first')
        self.hide_plot('ms1_latest_10')

        self.add_plot('ms0_latest',      series='ms0',   scan_i='-1',   scan_j='',  processing='Average')
        self.hide_plot('ms0_latest')
        
        self.add_plot('diff_latest',    series='diff',  scan_i='-1',    scan_j='',  processing='Average')
        self.hide_plot('diff_latest')
        
        self.add_plot('contrast_latest',    series='contrast',  scan_i='-1',    scan_j='',  processing='Average')
        self.hide_plot('contrast_latest')
        # manually set the XY range
        #self.line_plot.plot_item().setXRange(3.0, 4.0)
        #self.line_plot.plot_item().setYRange(-3000, 4500)

        # retrieve legend object
        legend = self.line_plot.plot_widget.addLegend()
        # set the legend location
        legend.setOffset((-10, -50))

        self.datasource_lineedit.setText('T2')