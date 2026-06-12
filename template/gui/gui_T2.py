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
                    bounds = (1e-9, None),
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

            'laser_power': {
                'display_text': 'Laser Power [%]',
                'widget': SpinBox(
                    value=5,
                    int=True,
                    bounds=(0, 100),
                    dec=True,
                ),
            },

            'half_pi': {
                'display_text': 'π/2: ',
                'widget': SpinBox(
                    value = 24e-9,
                    suffix = 's',
                    siPrefix = True,
                    bounds = (8e-9, None),
                    dec = True,
                ),
            },

            # 'pihalf_x': {
            #     'display_text': '\u03C0/2_x: ',
            #     'widget': SpinBox(
            #         suffix = 's',
            #         siPrefix = True,
            #         bounds = (1e-9, None),
            #     ),
            # },

            # 'pihalf_y': {
            #     'display_text': '\u03C0/2_y: ',
            #     'widget': SpinBox(
            #         suffix = 's',
            #         siPrefix = True,
            #         bounds = (1e-9, None),
            #     ),
            # },

            # 'pi_x': {
            #     'display_text': '\u03C0_x: ',
            #     'widget': SpinBox(
            #         suffix = 's',
            #         siPrefix = True,
            #         bounds = (1e-9, None),
            #     ),
            # },

            # 'pi_y': {
            #     'display_text': '\u03C0_y: ',
            #     'widget': SpinBox(
            #         suffix = 's',
            #         siPrefix = True,
            #         bounds = (1e-9, None),
            #     ),
            # },

            # 'pulse_axis': {
            #     'display_text': 'Pulse Axis:',
            #     'widget': QtWidgets.QLineEdit("Y"),
            # },

            # 'n': {
            #     'display_text': '# of Seq. (n): ',
            #     'widget': SpinBox(
            #         value = 1,
            #         int = True,
            #         bounds=(1, None),
            #     ),
            # },

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
                        'T2_run_R',
                        title='T2')




def process_T2_data(sink: DataSink):

    """
    Process T2 data for Ramsey / Spin Echo.

    Expected preferred dataset names from T2_run_R:
        signal      -> MW/sequence signal trace
        background  -> reference trace

    Legacy accepted names:
        ms1
        ms0

    Creates:
        diff
        contrast
        contrast_from_avg
        ramsey_fringe_norm_from_avg
        spin_echo_bright_dark_norm_from_avg
        spin_echo_pointwise_norm_from_avg
    """

    # Accept current T2_run_R names and older legacy names.
    signal_key = 'signal' if 'signal' in sink.datasets else 'ms1'
    background_key = 'background' if 'background' in sink.datasets else 'ms0'

    if signal_key not in sink.datasets or background_key not in sink.datasets:
        return

    signal_data = sink.datasets[signal_key]
    background_data = sink.datasets[background_key]

    if not signal_data or not background_data:
        return

    diff_sweeps = []
    contrast_sweeps = []

    n_sweeps = min(len(signal_data), len(background_data))

    for s in range(n_sweeps):
        x_axis_data = np.asarray(signal_data[s][0], dtype=float)
        ms1 = np.asarray(signal_data[s][1], dtype=float)
        ms0 = np.asarray(background_data[s][1], dtype=float)

        # Avoid crashing if a malformed sweep got pushed.
        n = min(x_axis_data.size, ms1.size, ms0.size)
        if n == 0:
            continue

        x_axis_data = x_axis_data[:n]
        ms1 = ms1[:n]
        ms0 = ms0[:n]

        diff = ms0 - ms1

        with np.errstate(divide='ignore', invalid='ignore'):
            contrast = np.where(
                (ms0 + ms1) != 0,
                (ms0 - ms1) / (ms0 + ms1),
                np.nan
            )

        diff_sweeps.append(np.stack([x_axis_data, diff]))
        contrast_sweeps.append(np.stack([x_axis_data, contrast]))

    sink.datasets['diff'] = diff_sweeps
    sink.datasets['contrast'] = contrast_sweeps

    if not diff_sweeps:
        return

    # Build averaged traces safely.
    x_axis_data = np.asarray(signal_data[0][0], dtype=float)

    signal_stack = []
    background_stack = []

    for s in range(n_sweeps):
        x = np.asarray(signal_data[s][0], dtype=float)
        y_sig = np.asarray(signal_data[s][1], dtype=float)
        y_bg = np.asarray(background_data[s][1], dtype=float)

        n = min(x_axis_data.size, x.size, y_sig.size, y_bg.size)
        if n == x_axis_data.size:
            signal_stack.append(y_sig[:n])
            background_stack.append(y_bg[:n])

    if not signal_stack or not background_stack:
        return

    ms1_mean = np.nanmean(np.asarray(signal_stack, dtype=float), axis=0)
    ms0_mean = np.nanmean(np.asarray(background_stack, dtype=float), axis=0)

    n = min(x_axis_data.size, ms1_mean.size, ms0_mean.size)
    x_axis_data = x_axis_data[:n]
    ms1_mean = ms1_mean[:n]
    ms0_mean = ms0_mean[:n]

    with np.errstate(divide='ignore', invalid='ignore'):
        contrast_from_avg = np.where(
            (ms0_mean + ms1_mean) != 0,
            (ms0_mean - ms1_mean) / (ms0_mean + ms1_mean),
            np.nan
        )

    sink.datasets['contrast_from_avg'] = [
        np.stack([x_axis_data, contrast_from_avg])
    ]

    # Ramsey normalization:
    # C(tau) = (I(tau) - I_mid) / A
    I_tau = ms1_mean

    I_max = np.nanpercentile(I_tau, 95)
    I_min = np.nanpercentile(I_tau, 5)

    I_mid = 0.5 * (I_max + I_min)
    A = 0.5 * (I_max - I_min)

    if np.isfinite(A) and A != 0:
        ramsey_fringe_norm_from_avg = (I_tau - I_mid) / A
    else:
        ramsey_fringe_norm_from_avg = np.full_like(I_tau, np.nan, dtype=float)

    sink.datasets['ramsey_fringe_norm_from_avg'] = [
        np.stack([x_axis_data, ramsey_fringe_norm_from_avg])
    ]

    # Spin Echo normalization:
    # C(tau) = (I(tau) - I_dark) / (I_bright - I_dark)
    I_dark = np.nanpercentile(ms1_mean, 5)
    I_bright = np.nanpercentile(ms0_mean, 95)
    denom = I_bright - I_dark

    if np.isfinite(denom) and denom != 0:
        spin_echo_bright_dark_norm_from_avg = (I_tau - I_dark) / denom
    else:
        spin_echo_bright_dark_norm_from_avg = np.full_like(I_tau, np.nan, dtype=float)

    sink.datasets['spin_echo_bright_dark_norm_from_avg'] = [
        np.stack([x_axis_data, spin_echo_bright_dark_norm_from_avg])
    ]

    # Optional pointwise normalization if background is a tau-dependent reference.
    with np.errstate(divide='ignore', invalid='ignore'):
        spin_echo_pointwise_norm_from_avg = np.where(
            (ms0_mean - I_dark) != 0,
            (I_tau - I_dark) / (ms0_mean - I_dark),
            np.nan
        )

    sink.datasets['spin_echo_pointwise_norm_from_avg'] = [
        np.stack([x_axis_data, spin_echo_pointwise_norm_from_avg])
    ]

    # """Subtract the signal from background trace and add it as a new 'diff' dataset."""
    # diff_sweeps = []
    # contrast_sweeps = []
    # #print('\n datasets[signal] now', sink.datasets['signal'])
    # #print('\n datasets[background] now', sink.datasets['background'])
    # for s,_ in enumerate(sink.datasets['signal']):
    #     x_axis_data = sink.datasets['signal'][s][0]
    #     ms1 = sink.datasets['signal'][s][1]
    #     ms0 = sink.datasets['background'][s][1]
    #     diff_sweeps.append(np.stack([x_axis_data, ms0 - ms1]))
    #     contrast_sweeps.append(np.stack([x_axis_data, (ms0 - ms1)/(ms0 + ms1)]))
    #     #div_sweeps.append(np.stack([mw_times, sig/bg]))
    # sink.datasets['diff'] = diff_sweeps
    # sink.datasets['contrast'] = contrast_sweeps

    # if sink.datasets['signal'] and sink.datasets['background']:
    #     x_axis_data = sink.datasets['signal'][0][0]

    #     ms1_mean = np.nanmean(
    #         np.array([x[1] for x in sink.datasets['signal']]),
    #         axis=0
    #     )
    #     ms0_mean = np.nanmean(
    #         np.array([x[1] for x in sink.datasets['background']]),
    #         axis=0
    #     )

    #     with np.errstate(divide='ignore', invalid='ignore'):
    #         contrast_from_avg = np.where(
    #             (ms0_mean + ms1_mean) != 0,
    #             (ms0_mean - ms1_mean) / (ms0_mean + ms1_mean),
    #             np.nan
    #         )

    #     sink.datasets['contrast_from_avg'] = [
    #         np.stack([x_axis_data, contrast_from_avg])
    #     ]

    # if sink.datasets['signal'] and sink.datasets['background']:
    #     x_axis_data = sink.datasets['signal'][0][0]

    #     ms1_mean = np.nanmean(
    #         np.array([x[1] for x in sink.datasets['signal']]),
    #         axis=0
    #     )
    #     ms0_mean = np.nanmean(
    #         np.array([x[1] for x in sink.datasets['background']]),
    #         axis=0
    #     )

    #     # Ramsey normalization:
    #     # C(tau) = (I(tau) - I_mid) / A
    #     # I_mid = (I_max + I_min)/2
    #     # A = (I_max - I_min)/2
    #     I_tau = ms1_mean

    #     I_max = np.nanpercentile(I_tau, 95)
    #     I_min = np.nanpercentile(I_tau, 5)

    #     I_mid = 0.5 * (I_max + I_min)
    #     A = 0.5 * (I_max - I_min)

    #     if np.isfinite(A) and A != 0:
    #         ramsey_fringe_norm_from_avg = (I_tau - I_mid) / A
    #     else:
    #         ramsey_fringe_norm_from_avg = np.full_like(I_tau, np.nan, dtype=float)

    #     sink.datasets['ramsey_fringe_norm_from_avg'] = [
    #         np.stack([x_axis_data, ramsey_fringe_norm_from_avg])
    #     ]

    #     # Spin Echo normalization:
    #     # C(tau) = (I(tau) - I_dark) / (I_bright - I_dark)
    #     I_dark = np.nanpercentile(ms1_mean, 5)
    #     I_bright = np.nanpercentile(ms0_mean, 95)

    #     denom = I_bright - I_dark

    #     if np.isfinite(denom) and denom != 0:
    #         spin_echo_bright_dark_norm_from_avg = (I_tau - I_dark) / denom
    #     else:
    #         spin_echo_bright_dark_norm_from_avg = np.full_like(I_tau, np.nan, dtype=float)

    #     sink.datasets['spin_echo_bright_dark_norm_from_avg'] = [
    #         np.stack([x_axis_data, spin_echo_bright_dark_norm_from_avg])
    #     ]

    #     # Optional pointwise Spin Echo normalization if ms0 is a tau-dependent bright reference
    #     with np.errstate(divide='ignore', invalid='ignore'):
    #         spin_echo_pointwise_norm_from_avg = np.where(
    #             (ms0_mean - I_dark) != 0,
    #             (I_tau - I_dark) / (ms0_mean - I_dark),
    #             np.nan
    #         )

    #     sink.datasets['spin_echo_pointwise_norm_from_avg'] = [
    #         np.stack([x_axis_data, spin_echo_pointwise_norm_from_avg])
    #     ]

class FlexLinePlotWidgetWithT2(FlexLinePlotWidget):
    """Add some default settings to the FlexSinkLinePlotWidget."""
    def __init__(self):
        super().__init__(data_processing_func=process_T2_data)
        # create some default average plots
        self.add_plot('sig_avg',        series='signal',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('bg_avg',         series='background',   scan_i='',     scan_j='',  processing='Average')
        self.add_plot('contrast_avg',       series='contrast',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('contrast_avg')
        self.add_plot('diff_avg',       series='diff',  scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('diff_avg')

        # (Rolando A. Fimbres G. 2026-5-25) contrast from average, ramsey fringe norm from average, and spin echo norm from average 
        self.add_plot(
            'contrast_from_avg',
            series='contrast_from_avg',
            scan_i='',
            scan_j='',
            processing='Average'
        )
        self.hide_plot('contrast_from_avg')

        self.add_plot(
            'ramsey_fringe_norm_from_avg',
            series='ramsey_fringe_norm_from_avg',
            scan_i='',
            scan_j='',
            processing='Average'
        )
        self.hide_plot('ramsey_fringe_norm_from_avg')

        self.add_plot(
            'spin_echo_bright_dark_norm_from_avg',
            series='spin_echo_bright_dark_norm_from_avg',
            scan_i='',
            scan_j='',
            processing='Average'
        )
        self.hide_plot('spin_echo_bright_dark_norm_from_avg')

        self.add_plot(
            'spin_echo_pointwise_norm_from_avg',
            series='spin_echo_pointwise_norm_from_avg',
            scan_i='',
            scan_j='',
            processing='Average'
        )
        self.hide_plot('spin_echo_pointwise_norm_from_avg')
        ####################################################################


        # create some plots that not frequently used, so we hide them
        self.add_plot(
            'sig_latest',
            series='signal',
            scan_i='-1',
            scan_j='',
            processing='Average'
        )
        self.hide_plot('sig_latest')

        self.add_plot(
            'bg_latest',
            series='background',
            scan_i='-1',
            scan_j='',
            processing='Average'
        )
        self.hide_plot('bg_latest')

        self.add_plot(
            'contrast_latest',
            series='contrast',
            scan_i='-1',
            scan_j='',
            processing='Average'
        )
        self.hide_plot('contrast_latest')

        # retrieve legend object
        legend = self.line_plot.plot_widget.addLegend()
        # set the legend location
        legend.setOffset((-10, -50))

        self.datasource_lineedit.setText('T2')