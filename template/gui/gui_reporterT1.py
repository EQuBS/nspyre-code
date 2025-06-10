"""
GUI elements for DEER_FID_run
"""
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

class ReporterT1Widget(ExperimentWidget):
    def __init__(self):
        params_config = {
            'start': {
                'display_text': 'Start \u03C4 time',
                'widget': SpinBox(
                    value=1e-9,
                    suffix='s',
                    siPrefix=True,
                    bounds=(0, None),
                    dec=True,
                ),
            },

            'stop': {
                'display_text': 'Stop \u03C4 Time',
                'widget': SpinBox(
                    value=200e-9,
                    suffix='s',
                    siPrefix=True,
                    bounds=(0, None),
                    dec=True,
                ),
            },

            'num_pts': {
                'display_text': '# of Scan Points',
                'widget': SpinBox(value=41, int=True, bounds=(1, None), dec=True),
            },
         
            'tau_type': {
                'display_text': '\u03C4s\' type',
                'widget': QtWidgets.QLineEdit("linear"),
            },

            'runs': {
                'display_text': 'Runs (per pt.): ',
                'widget': SpinBox(
                    value = 1000,
                    int = True,
                    bounds=(1, None),
                ),
            },

            'iters': {
                'display_text': '# of Sweeps',
                'widget': SpinBox(value=10, int=True, bounds=(1, None), dec=True),
            },

            'tau0': {
                'display_text': 'DEER Tau Time: ',
                'widget': SpinBox(
                    value = 10e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1e-9, None),
                ),
            },

            'extra_pipulse': {
                'display_text': '1st DEER & Pi-Pulse Gap: ',
                'widget': SpinBox(
                    value = 10e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1e-9, None),
                ),
            },

            'nv_mw_power': {
                'display_text': 'NV MW Power: ',
                'widget': SpinBox(
                    value = -10,
                    suffix = 'dBm',
                    siPrefix = False,
                    bounds = (None, 5),
                ),
            },

            'nv_mw_freq': {
                'display_text': 'NV MW freq: ',
                'widget': SpinBox(
                    value = 2.78e9,
                    suffix = 'Hz',
                    siPrefix = True,
                    bounds = (500e6, 20e9),
                ),
            },

            'pihalf_x': {
                'display_text': '\u03C0/2_x: ',
                'widget': SpinBox(
                    value = 5e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1e-9, None),
                ),
            },

            'pihalf_y': {
                'display_text': '\u03C0/2_y: ',
                'widget': SpinBox(
                    value = 5e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1e-9, None),
                ),
            },

            'pi_x': {
                'display_text': '\u03C0_x: ',
                'widget': SpinBox(
                    value = 10e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1e-9, None),
                ),
            },

            'pi_y': {
                'display_text': '\u03C0_y: ',
                'widget': SpinBox(
                    value = 10e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1e-9, None),
                ),
            },

            'pi_electron': {
                'display_text': '\u03C0_electron: ',
                'widget': SpinBox(
                    value = 14e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (1e-9, None),
                ),
            },

            'el_mw_power': {
                'display_text': 'electron MW Power: ',
                'widget': SpinBox(
                    value = -10,
                    suffix = 'dBm',
                    siPrefix = False,
                    bounds = (None, 5),
                ),
            },

            'el_mw_freq': {
                'display_text': 'electron MW freq.: ',
                'widget': SpinBox(
                    value = 5.6e9,
                    suffix = 'Hz',
                    siPrefix = True,
                    bounds = (500e6, 20e9),
                ),
            },

            # 'dataset': {
            #     'display_text': 'Data Set',
            #     'widget': QtWidgets.QLineEdit('DEER'),
            # },
        }

        super().__init__(params_config, 
                        sm,
                        'SpinMeasurements',
                        'ReporterT1_run',
                        title='Reporter Spin T1')

def process_ReporterT1_data(sink: DataSink):
    """Subtract the signal from background trace and add it as a new 'diff' dataset."""
    echo_contrast_sweeps = []
    dark_contrast_sweeps = []
    #DEER_contrast_sweeps = []
    DEER_diff_sweeps = []
    # s looping over each iterations?
    for s,_ in enumerate(sink.datasets['dark_ms1']):
        tau_times = sink.datasets['dark_ms1'][s][0]
        dark_ms1 = sink.datasets['dark_ms1'][s][1]
        dark_ms0 = sink.datasets['dark_ms0'][s][1]
        echo_ms1 = sink.datasets['echo_ms1'][s][1]
        echo_ms0 = sink.datasets['echo_ms0'][s][1]
        # We used DEER FID code for it. For Reporter T1 Sequence, we don't need the contrast
        # We need the difference of the ms0 and ms1 and the difference of the difference. Therefore
        # the contrast operation will be changed
        #dark_contr = (dark_ms0 - dark_ms1)/(dark_ms0 + dark_ms1)
        #echo_contr = (echo_ms0 - echo_ms1)/(echo_ms0 + echo_ms1)

        echo_contr = echo_ms0 - echo_ms1
        dark_contr = dark_ms0 - dark_ms1

        echo_contrast_sweeps.append(np.stack([tau_times, echo_contr]))
        dark_contrast_sweeps.append(np.stack([tau_times, dark_contr]))
        #DEER_contrast_sweeps.append(np.stack([freqs, dark_contr/echo_contr]))
        DEER_diff_sweeps.append(np.stack([tau_times, echo_contr - dark_contr]))
    sink.datasets['dark_contrast'] = dark_contrast_sweeps
    sink.datasets['echo_contrast'] = echo_contrast_sweeps
    #sink.datasets['DEER_contrast'] = DEER_contrast_sweeps
    sink.datasets['DEER_diff'] = DEER_diff_sweeps

class FlexLinePlotWidgetWithReporterT1(FlexLinePlotWidget):
    """Add some default settings to the FlexSinkLinePlotWidget."""
    def __init__(self):
        super().__init__(data_processing_func=process_ReporterT1_data)
        # create some default average plots
        self.add_plot('echo_diff',        series='echo_contrast',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('dark_diff',         series='dark_contrast',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('contrast_diff',       series='DEER_diff',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('contrast_diff')
        
        # create some plot that not frequently used, so we hide them
        self.add_plot('dark_latest',     series='dark_contrast',   scan_i='-1',   scan_j='',  processing='Average')
        self.add_plot('echo_latest',     series='echo_contrast',   scan_i='-1',   scan_j='',  processing='Average')
        self.hide_plot('dark_latest')
        self.hide_plot('echo_latest')

        self.add_plot('dark_ms1_avg',      series='dark_ms1',   scan_i='',   scan_j='',  processing='Average')
        self.hide_plot('dark_ms1_avg')
        self.add_plot('dark_ms0_avg',      series='dark_ms0',   scan_i='',   scan_j='',  processing='Average')
        self.hide_plot('dark_ms0_avg')
        self.add_plot('echo_ms1_avg',      series='echo_ms1',   scan_i='',   scan_j='',  processing='Average')
        self.hide_plot('echo_ms1_avg')
        self.add_plot('echo_ms0_avg',      series='echo_ms0',   scan_i='',   scan_j='',  processing='Average')
        self.hide_plot('echo_ms0_avg')
        self.add_plot('DEER_avg_latest10',  series='DEER_diff',   scan_i='-10',  scan_j='',  processing='Average')
        self.hide_plot('DEER_avg_latest10')
        # manually set the XY range
        #self.line_plot.plot_item().setXRange(3.0, 4.0)
        #self.line_plot.plot_item().setYRange(-3000, 4500)

        # retrieve legend object
        legend = self.line_plot.plot_widget.addLegend()
        # set the legend location
        legend.setOffset((-10, -50))

        self.datasource_lineedit.setText('reporterT1')
