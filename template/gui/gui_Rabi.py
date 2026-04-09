"""
GUI elements for Rabi
Tian-Xing Zheng, Sept.2023
"""

"""
To be adapted and used by EQuBS Lab.
Rolando A. Fimbres Grijalva, Aug. 20252
"""

import numpy as np

from nspyre import FlexLinePlotWidget
from nspyre import ExperimentWidget
from nspyre import DataSink
from pyqtgraph import SpinBox
from pyqtgraph.Qt import QtWidgets
from .fit_helpers import average_trace, fit_rabi_trace

#import the experiment spyrelet file
import sys
sys.path.append('../experiments')
from . import spin_measurements as sm

class RabiWidget(ExperimentWidget):
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

            'freq': {
                'display_text': 'MW Freq.: ',
                'widget': SpinBox(
                    value = 2.87e9,
                    suffix = 'Hz',
                    siPrefix = True,
                    bounds = (100.000e3, 6.000e9),
                    dec = True,
                ),
            },
            
            'iters': {
                'display_text': 'Num. of Iterations',
                'widget': SpinBox(
                    value = 1,
                    int = True,
                    bounds = (1, None),
                    dec = True,
                ),
            },

            'rf_power': {
                'display_text': 'RF Power: ',
                'widget': SpinBox(
                    value = -15,
                    suffix = 'dBm',
                    siPrefix = False,
                    bounds = (None, 2),
                ),
            },
            'start': {
                'display_text': 'Start MW Pulse Time: ',
                'widget': SpinBox(
                    value = 10e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (2e-9, None),
                    dec = True,
                ),
            },

            'stop': {
                'display_text': 'Stop MW Pulse Time: ',
                'widget': SpinBox(
                    value = 300e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (2e-9, None),
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
                    bounds = (5e-7, None),
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
                    value = 300e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                ),
            },

            'read_wait': {
                'display_text': 'Read Wait (dur. before readout): ',
                'widget': SpinBox(
                    value = 10e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                ),
            },

            'switch_delay': {
                'display_text': 'Switch Delay: ',
                'widget': SpinBox(
                    value = 0,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                ),
            },

            'seq_gap': {
                'display_text': 'Seq. Gap: ',
                'widget': SpinBox(
                    value = 0,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (0, None),
                ),
            },

            'pi_xy': {
                'display_text': 'X or Y pulse?',
                'widget': QtWidgets.QLineEdit("x"),
            },
            'rabi_type':{
                'display_text': 'Which SG?',
                'widget': QtWidgets.QLineEdit("SRS"),
            },
        }

        super().__init__(params_config, 
                        sm,
                        'SpinMeasurements',
                        'rabi_run_R3',
                        title='Rabi')

def process_Rabi_data(sink: DataSink):
    """Subtract the signal from background trace and add it as a new 'diff' dataset."""
    diff_sweeps = []
    contrast_sweeps = []
    normalized_diff_sweeps = []
    #print('\n datasets[signal] now', sink.datasets['signal'])
    #print('\n datasets[background] now', sink.datasets['background'])

    for s,_ in enumerate(sink.datasets['signal']):
        mw_times = sink.datasets['signal'][s][0]
        sig = sink.datasets['signal'][s][1]
        bg = sink.datasets['background'][s][1]
        diff_sweeps.append(np.stack([mw_times, sig - bg]))

        with np.errstate(divide='ignore', invalid='ignore'):
            contrast = (sig - bg) / (sig + bg)
            contrast = np.where(np.isfinite(contrast), contrast, 0)  # or use 0 instead of np.nan if preferred
            norm_diff = (sig - bg) / bg
            norm_diff = np.where(np.isfinite(norm_diff), norm_diff, np.nan)

        contrast_sweeps.append(np.stack([mw_times, contrast]))
        #normalized_diff = np.stack([mw_times, (sig - bg) / bg])
        normalized_diff_sweeps.append(np.stack([mw_times, norm_diff]))

    sink.datasets['diff'] = diff_sweeps
    sink.datasets['contrast'] = contrast_sweeps
    sink.datasets['normalized_diff'] = normalized_diff_sweeps

    # Fit the averaged Rabi contrast trace
    sink.datasets['rabi_fit'] = []
    if contrast_sweeps:
        x_avg, y_avg = average_trace(contrast_sweeps)
        fit_res = fit_rabi_trace(x_avg, y_avg)
        if fit_res is not None:
            sink.datasets['rabi_fit'] = [fit_res['curve']]

class FlexLinePlotWidgetWithRabi(FlexLinePlotWidget):
    """Add some default settings to the FlexSinkLinePlotWidget."""
    def __init__(self):
        super().__init__(data_processing_func=process_Rabi_data)
        # create some default average plots
        self.add_plot('sig_avg',        series='signal',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('bg_avg',         series='background',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('contrast_avg',       series='contrast',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('contrast_avg')
        self.add_plot('diff_avg',       series='diff',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('diff_avg')
        self.add_plot('normalized_diff_avg', series='normalized_diff', scan_i='', scan_j='', processing='Average')
        self.hide_plot('normalized_diff_avg')

        self.add_plot('rabi_fit', series='rabi_fit', scan_i='', scan_j='', processing='Average') # Added by Rolando A. Fimbres G. 3/30/2026
        self.hide_plot('rabi_fit')


        # create some plots that not frequently used, so we hide them
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
        
        self.add_plot('contrast_latest',    series='contrast',  scan_i='-1',    scan_j='',  processing='Average')
        self.hide_plot('contrast_latest')
        # manually set the XY range
        #self.line_plot.plot_item().setXRange(3.0, 4.0)
        #self.line_plot.plot_item().setYRange(-3000, 4500)

        # retrieve legend object
        legend = self.line_plot.plot_widget.addLegend()
        # set the legend location
        legend.setOffset((-10, -50))

        self.datasource_lineedit.setText('Rabi')
