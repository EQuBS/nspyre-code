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
from .fit_helpers import average_trace, fit_odmr_trace
# import the experiment 
import sys
sys.path.append('../experiments')

class ODMR_Widget(ExperimentWidget):
    def __init__(self, pulse_streamer_driver):
        self.ps = pulse_streamer_driver

        self.odmr_type_combo = QtWidgets.QComboBox()
        self.odmr_type_combo.addItems(['CW', 'CW-Test', 'CW-OnOff', 'CW-SideMod', 'Pulsed', 'Pulsed-Cnst', 'Pulsed2']) #, 'P_list', 'CW_list', 'P2_list'])
        self.odmr_type_combo.setCurrentText('CW')

        params_config = {
            'start_freq': {
                'display_text': 'Start Frequency',
                'widget': SpinBox(
                    value = 2.67e9,
                    suffix = 'Hz',
                    siPrefix = True,
                    bounds = (100e3, 7e9),
                    dec=True,
                ),
            },
            'stop_freq': {
                'display_text': 'Stop Frequency',
                'widget': SpinBox(
                    value = 3.07e9,
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
            'CW_Buffer_Time': {
                'display_text': 'CW Buffer Time',
                'widget': SpinBox(
                    value = 1e-3,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (10e-9, None),
                    dec=True,
                ),
            },
            'sideband_mod_freq': {
                'display_text': 'SideMod IF',
                'widget': SpinBox(
                    value = 30e6,
                    suffix = 'Hz',
                    siPrefix = True,
                    bounds = (1, 100e6),
                    dec=True,
                ),
            },
            'sideband_iq_amplitude': {
                'display_text': 'SideMod IQ Amp',
                'widget': SpinBox(
                    value = 0.45,
                    suffix = 'V',
                    siPrefix = False,
                    bounds = (0, 0.5),
                    dec=True,
                ),
            },
            'sideband': {
                'display_text': 'Sideband',
                'widget': QtWidgets.QLineEdit("upper"),
            },
            'sideband_samples_per_period': {
                'display_text': 'SideMod Samples/Period',
                'widget': SpinBox(
                    value = 8,
                    int = True,
                    bounds = (4, 128),
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
                    bounds = (None, 4),
                ),
            },
            'probe_time': {
                'display_text': 'MW Probe Time',
                'widget': SpinBox(
                    value = 50e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (2e-9, None),
                    dec=True,
                ),
            },
            'odmr_type': {
                'display_text': 'ODMR Type',
                'widget': self.odmr_type_combo,
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
                        'odmr_run_R3',  # No specific run method
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
    ratio = []
    contrast_sweeps = []

    for s, _ in enumerate(sink.datasets['signal']):
        freqs = sink.datasets['signal'][s][0]
        sig = np.asarray(sink.datasets['signal'][s][1], dtype=float)
        bg  = np.asarray(sink.datasets['background'][s][1], dtype=float)

        bg_safe = bg.copy()
        bg_safe[bg_safe == 0] = np.nan

        with np.errstate(divide='ignore', invalid='ignore'):
            ratio_now = sig / bg_safe
            contrast_now = (bg_safe - sig) / bg_safe

        ratio.append(np.stack([freqs, ratio_now]))
        contrast_sweeps.append(np.stack([freqs, contrast_now]))

    sink.datasets['div'] = ratio
    sink.datasets['contrast'] = contrast_sweeps

    # Keep old names as aliases only
    sink.datasets['norm_avg'] = contrast_sweeps

    if sink.datasets['signal'] and sink.datasets['background']:
        freqs = sink.datasets['signal'][0][0]

        sig_mean = np.nanmean(
            np.array([x[1] for x in sink.datasets['signal']]),
            axis=0
        )
        bg_mean = np.nanmean(
            np.array([x[1] for x in sink.datasets['background']]),
            axis=0
        )

        with np.errstate(divide='ignore', invalid='ignore'):
            contrast_from_avg = np.where(
                bg_mean != 0,
                (bg_mean - sig_mean) / bg_mean,
                np.nan
            )

        sink.datasets['contrast_from_avg'] = [
            np.stack([freqs, contrast_from_avg])
        ]

        sink.datasets['norm_from_avg'] = [
            np.stack([freqs, contrast_from_avg])
        ]

    sink.datasets['odmr_fit'] = []
    # """Subtract the signal from background trace and add it as a new 'diff' dataset."""
    # ratio = []
    # norm_sweeps = [] #create normalization plot -A.K 11/19/2025
    # contrast_sweeps = []

    # for s,_ in enumerate(sink.datasets['signal']):
    #     freqs = sink.datasets['signal'][s][0]
    #     sig = np.asarray(sink.datasets['signal'][s][1], dtype=float)
    #     bg  = np.asarray(sink.datasets['background'][s][1], dtype=float)


    #     bg_safe = bg.copy()
    #     bg_safe[bg_safe == 0] = np.nan

    #     with np.errstate(divide='ignore', invalid='ignore'):
    #         div = sig / bg_safe
    #         contrast = (bg_safe - sig) / bg_safe

    #     ratio.append(np.stack([freqs, div]))
    #     contrast_sweeps.append(np.stack([freqs, contrast]))

    #     # Keep old plot name, but make it identical to physical contrast.
    #     norm_sweeps.append(np.stack([freqs, contrast]))

    # sink.datasets['div'] = ratio
    # sink.datasets['contrast'] = contrast_sweeps
    # sink.datasets['norm_avg'] = norm_sweeps

    # if sink.datasets['signal'] and sink.datasets['background']:
    #     freqs = sink.datasets['signal'][0][0]

    #     sig_mean = np.nanmean(
    #         np.array([x[1] for x in sink.datasets['signal']]),
    #         axis=0
    #     )
    #     bg_mean = np.nanmean(
    #         np.array([x[1] for x in sink.datasets['background']]),
    #         axis=0
    #     )

    #     # with np.errstate(divide='ignore', invalid='ignore'):
    #     #     norm_from_avg = np.where(
    #     #         (sig_mean + bg_mean) != 0,
    #     #         np.abs(sig_mean - bg_mean) / (sig_mean + bg_mean),
    #     #         np.nan
    #     #     )

    #     # sink.datasets['norm_from_avg'] = [
    #     #     np.stack([freqs, norm_from_avg])
    #     # ]
    #     with np.errstate(divide='ignore', invalid='ignore'):
    #         contrast_from_avg = np.where(
    #             bg_mean != 0,
    #             (bg_mean - sig_mean) / bg_mean,
    #             np.nan
    #         )

    #     sink.datasets['contrast_from_avg'] = [
    #         np.stack([freqs, contrast_from_avg])
    #     ]

    #     # Keep old plotting name if needed
    #     sink.datasets['norm_from_avg'] = [
    #         np.stack([freqs, contrast_from_avg])
    #     ]
        

    #     with np.errstate(divide='ignore', invalid='ignore'):
    #         # Contrast calculated after averaging signal and background traces
    #         norm_from_avg = np.where(
    #             bg_mean != 0,
    #             (bg_mean - sig_mean) / bg_mean,
    #             np.nan
    #         )

    #     sink.datasets['norm_from_avg'] = [
    #         np.stack([freqs, norm_from_avg])
    #     ]

    # # Fit the averaged normalized ODMR trace. Added by Rolando A. Fimbres G. 3/30/2026
    # """sink.datasets['odmr_fit'] = []
    # if norm_sweeps:
    #     x_avg, y_avg = average_trace(norm_sweeps)
    #     fit_res = fit_odmr_trace(x_avg, y_avg, n_dips=2)
    #     if fit_res is not None:
    #         sink.datasets['odmr_fit'] = [fit_res['curve']]
    # """ 
    # # Following line added to ensure the fit is applied after 
    # # a few sweeps have been collected, 
    # # and to attempt a single dip fit if the 2 dip fit fails. Rolando A. Fimbres G. 4/9/2026

    # if len(sink.datasets['signal']) >= 3 and len(sink.datasets['background']) >= 3:

    #     sink.datasets['odmr_fit'] = []
    #     if sink.datasets['signal'] and sink.datasets['background']:
    #         x_sig, y_sig = average_trace(sink.datasets['signal'])
    #         x_bg, y_bg = average_trace(sink.datasets['background'])

    #         # with np.errstate(divide='ignore', invalid='ignore'):
    #         #     y_norm = np.where(y_bg != 0, y_sig / y_bg, np.nan)
    #         with np.errstate(divide='ignore', invalid='ignore'):
    #             # Fit signed ODMR contrast
    #             y_norm = np.where(y_bg != 0, (y_bg - y_sig) / y_bg, np.nan)

    #         # Commented to update and NOT force '2 dips' fit. Rolando A. Fimbres G. 4/9/2026
    #         """ valid = np.isfinite(y_norm)
    #         if np.count_nonzero(valid) > 4:
    #             fit_res = fit_odmr_trace(x_sig[valid], y_norm[valid], n_dips=2)
    #             if fit_res is not None:
    #                 sink.datasets['odmr_fit'] = [fit_res['curve']]  """
    #         valid = np.isfinite(y_norm)
    #         if np.count_nonzero(valid) > 8:
    #             fit_res = fit_odmr_trace(x_sig[valid], y_norm[valid], n_dips=2)
    #             if fit_res is None:
    #                 fit_res = fit_odmr_trace(x_sig[valid], y_norm[valid], n_dips=1)

    #             if fit_res is not None:
    #                 sink.datasets['odmr_fit'] = [fit_res['curve']]
        

class FlexLinePlotWidgetWithODMR(FlexLinePlotWidget):
    """Add some default settings to the FlexSinkLinePlotWidget."""
    def __init__(self):
        super().__init__(data_processing_func=process_ODMR_data)
        # create some default average plots
        self.add_plot('sig_avg',        series='signal',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('bg_avg',         series='background',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('norm_avg',       series='norm_avg',  scan_i='',      scan_j='',  processing='Average') # add normalized plot to main plots -A.K 11/19/2025
        self.hide_plot('norm_avg')
        self.add_plot('contrast',       series='contrast',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('contrast')
        self.add_plot('contrast_from_avg', series='contrast_from_avg', scan_i='', scan_j='', processing='Average')
        self.hide_plot('contrast_from_avg')

        #self.add_plot('odmr_fit', series = 'odmr_fit', scan_i='', scan_j='', processing='Average') # Added by Rolando A. Fimbres G. 3/30/2026
        #self.hide_plot('odmr_fit')

        """ self.add_plot('s1_avg',        series='s1_avg_sweeps',  scan_i='',     scan_j='',  processing='Average')
        self.add_plot('s2_avg',        series='s2_avg_sweeps',  scan_i='',     scan_j='',  processing='Average')
        self.add_plot('s3_avg',        series='s3_avg_sweeps',  scan_i='',     scan_j='',  processing='Average')
        self.add_plot('s4_avg',        series='s4_avg_sweeps',  scan_i='',     scan_j='',  processing='Average')
        self.hide_plot('s1_avg')
        self.hide_plot('s2_avg')
        self.hide_plot('s3_avg')
        self.hide_plot('s4_avg') """

        self.add_plot('ratio_avg',       series='div',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('ratio_avg')

        self.add_plot(
            'norm_from_avg',
            series='norm_from_avg',
            scan_i='',
            scan_j='',
            processing='Average'
        )
        self.hide_plot('norm_from_avg')

        """ self.add_plot('div_avg',       series='div',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('div_avg')
        self.add_plot('div_now',       series='div_now',  scan_i='-1',      scan_j='',  processing='Average')
        self.hide_plot('div_now')
        self.add_plot('diff_avg',       series='diff',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('diff_avg') """
        # create some plot that not frequently used, so we hide them
        """ self.add_plot('sig_latest',     series='signal',   scan_i='-1',   scan_j='',  processing='Average')
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

        self.add_plot('norm_latest',    series='norm',  scan_i='-1',    scan_j='',  processing='Average')
        self.hide_plot('norm_latest') """
        # manually set the XY range
        #self.line_plot.plot_item().setXRange(3.0, 4.0)
        #self.line_plot.plot_item().setYRange(-3000, 4500)

        # retrieve legend object
        legend = self.line_plot.plot_widget.addLegend()
        # set the legend location
        legend.setOffset((-10, -50))

        self.datasource_lineedit.setText('ODMR')        
