"""
GUI element for T1
Tian-Xing Zheng, Oct.2023
Updated Omri Raz, Dec.2024
"""
from . import spin_measurements as sm
import numpy as np

from nspyre import FlexLinePlotWidget
from nspyre import ExperimentWidget
from nspyre import DataSink
from pyqtgraph import SpinBox
from pyqtgraph.Qt import QtWidgets
import pyqtgraph as pg
from nspyre import cyclic_colors
from .. fitting import exponential_decay_fitting

# import the experiment spyrelet file
import sys
sys.path.append('../')


class T1Widget(ExperimentWidget):
    def __init__(self):
        params_config = {
            'runs': {
                'display_text': 'Runs (per pt.): ',
                'widget': SpinBox(
                    value=2000,
                    int=True,
                    bounds=(1, None),
                ),
            },

            'iters': {
                'display_text': 'Exp. Iterations: ',
                'widget': SpinBox(
                    value=500,
                    int=True,
                    bounds=(1, None),
                ),
            },

            'freq': {
                'display_text': 'MW Freq.: ',
                'widget': SpinBox(
                    value=2.87e9,
                    suffix='Hz',
                    siPrefix=True,
                    bounds=(100e3, 20e9),
                    dec=True,
                ),
            },

            'rf_power': {
                'display_text': 'RF Power: ',
                'widget': SpinBox(
                    value=-15,
                    suffix='dBm',
                    siPrefix=False,
                    bounds=(None, 0),
                ),
            },
            'start': {
                'display_text': 'Start \u03C4 Time: ',
                'widget': SpinBox(
                    value=0.5e-6,
                    suffix='s',
                    siPrefix=True,
                    bounds=(1e-9, None),
                    dec=True,
                ),
            },

            'stop': {
                'display_text': 'Stop \u03C4 Time: ',
                'widget': SpinBox(
                    value=100e-6,
                    suffix='s',
                    siPrefix=True,
                    bounds=(10e-9, None),
                    dec=True,
                ),
            },

            'num_pts': {
                'display_text': '# of Points: ',
                'widget': SpinBox(
                    value=50,
                    int=True,
                    bounds=(1, None),
                    dec=True,
                ),
            },
            'tau_type': {
                'display_text': '\u03C4s\' type',
                'widget': QtWidgets.QLineEdit("exp"),
            },

            'xy': {
                'display_text': 'x or y',
                'widget': QtWidgets.QLineEdit("x"),
            },

            'pi_x': {
                'display_text': '\u03C0_x: ',
                'widget': SpinBox(
                    suffix='s',
                    siPrefix=True,
                    bounds=(1e-9, None),
                ),
            },

            'pi_y': {
                'display_text': '\u03C0_y: ',
                'widget': SpinBox(
                    suffix='s',
                    siPrefix=True,
                    bounds=(1e-9, None),
                ),
            },

            'pihalf_y': {
                'display_text': '\u03C0/2_y: ',
                'widget': SpinBox(
                    suffix='s',
                    siPrefix=True,
                    bounds=(1e-9, None),
                ),
            },


            'init_time': {
                'display_text': 'Init. Time: ',
                'widget': SpinBox(
                    value=2e-6,
                    suffix='s',
                    siPrefix=True,
                    bounds=(5e-9, None),
                ),
            },

            'read_time': {
                'display_text': 'Readout Time: ',
                'widget': SpinBox(
                    value=400e-9,
                    suffix='s',
                    siPrefix=True,
                    bounds=(5e-9, None),
                ),
            },
            
            'las_to_pulse': {
                'display_text': 'Seq. Gap: ',
                'widget': SpinBox(
                    value=0,
                    suffix='s',
                    siPrefix=True,
                    bounds=(0, None),
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

            'seq': {
                'display_text': 'sequence',
                'widget': QtWidgets.QLineEdit("Optical T1 General"),
            },
            'T1_sg': {
                'display_text': 'Which SG?',
                'widget': QtWidgets.QLineEdit("SRS"),
            },

        }

        super().__init__(params_config,
                         sm,
                         'SpinMeasurements',
                         'T1_run_R2',
                         title='T1')


def process_T1_data(sink: DataSink):
    """Subtract the signal from background trace and add it as a new 'diff' dataset."""
    diff_sweeps = []
    contrast_sweeps = []
    # print('\n datasets[ms1] now', sink.datasets['ms1'])
    # print('\n datasets[background] now', sink.datasets['background'])
    for s, _ in enumerate(sink.datasets['ms1']):
        x_axis_data = sink.datasets['ms1'][s][0]
        ms1 = sink.datasets['ms1'][s][1]
        ms0 = sink.datasets['ms0'][s][1]
        diff_sweeps.append(np.stack([x_axis_data, ms0 - ms1]))
        contrast_sweeps.append(
            np.stack([x_axis_data, (ms0 - ms1)/(ms0 + ms1)]))
        # div_sweeps.append(np.stack([mw_times, sig/bg]))
    # print(ms1)
    sink.datasets['diff'] = diff_sweeps
    sink.datasets['contrast'] = contrast_sweeps


class FlexLinePlotWidgetWithT1(FlexLinePlotWidget):
    """Add some default settings to the FlexSinkLinePlotWidget."""

    def __init__(self):
        super().__init__(data_processing_func=process_T1_data)
        # create some default average plots
        self.add_plot('ms1_avg',        series='ms1',   scan_i='',
                      scan_j='',  processing='Average')
        self.add_plot('ms0_avg',         series='ms0',
                      scan_i='',     scan_j='',  processing='Average')
        self.hide_plot('ms0_avg')
        self.add_plot('contrast_avg',       series='contrast',
                      scan_i='',      scan_j='',  processing='Average')
        self.hide_plot('contrast_avg')
        self.add_plot('diff_avg',       series='diff',  scan_i='',
                      scan_j='',  processing='Average')
        self.hide_plot('diff_avg')

        # create some plots that not frequently used, so we hide them
        self.add_plot('ms1_latest',     series='ms1',
                      scan_i='-1',   scan_j='',  processing='Average')
        self.add_plot('ms1_first',      series='ms1',
                      scan_i='0',    scan_j='1', processing='Average')
        self.add_plot('ms1_latest_10',  series='ms1',
                      scan_i='-10',  scan_j='',  processing='Average')
        self.hide_plot('ms1_latest')
        self.hide_plot('ms1_first')
        self.hide_plot('ms1_latest_10')

        self.add_plot('ms0_latest',      series='ms0',
                      scan_i='-1',   scan_j='',  processing='Average')
        self.hide_plot('ms0_latest')

        self.add_plot('diff_latest',    series='diff',
                      scan_i='-1',    scan_j='',  processing='Average')
        self.hide_plot('diff_latest')

        self.add_plot('contrast_latest',    series='contrast',
                      scan_i='-1',    scan_j='',  processing='Average')
        self.hide_plot('contrast_latest')
        # manually set the XY range
        # self.line_plot.plot_item().setXRange(3.0, 4.0)
        # self.line_plot.plot_item().setYRange(-3000, 4500)

        # retrieve legend object
        legend = self.line_plot.plot_widget.addLegend()
        # set the legend location
        legend.setOffset((-10, -50))

        self.datasource_lineedit.setText('T1')

        layout = self.layout()

        self.fit_button = QtWidgets.QPushButton("Fit")
        self.fit_button.clicked.connect(
            self.fit_fun_window)  # Connect button to function
        layout.addWidget(self.fit_button)  # Add the button to the layout

        self.stacked_plot_sett_button = QtWidgets.QStackedWidget()
        self.light_plot_button = QtWidgets.QPushButton("Light Plot Mode")
        self.light_plot_button.clicked.connect(self.light_plot)
        self.dark_plot_button = QtWidgets.QPushButton("Dark Plot Mode")
        self.dark_plot_button.clicked.connect(self.dark_plot)

        self.stacked_plot_sett_button.addWidget(self.light_plot_button)
        self.stacked_plot_sett_button.addWidget(self.dark_plot_button)

        layout.addWidget(self.stacked_plot_sett_button)

    def get_plot_items(self):
        """Get all plot items (e.g., lines, scatter plots) in the plot."""
        return self.line_plot.plot_widget.items()

    def light_plot(self):

        self.line_plot.plot_widget.setBackground('white')
        item_counter = 0
        for item in self.get_plot_items():
            # Check if the item is a PlotDataItem (or any other plot item)
            if isinstance(item, pg.PlotDataItem):
                item.setPen(pg.mkPen(color=cyclic_colors[item_counter % len(
                    cyclic_colors)], width=5))  # Set the pen to blue with width 5
                item.setSymbolBrush(pg.mkBrush(color=(10, 10, 10, 100)))
                item.setSymbolSize(0)
                item_counter += 1
        self.stacked_plot_sett_button.setCurrentIndex(1)

    def dark_plot(self):
        self.line_plot.plot_widget.setBackground('k')
        item_counter = 0
        for item in self.get_plot_items():
            # Check if the item is a PlotDataItem (or any other plot item)
            if isinstance(item, pg.PlotDataItem):
                item.setPen(
                    pg.mkPen(color=cyclic_colors[item_counter % len(cyclic_colors)], width=1))
                item.setSymbolBrush(pg.mkBrush(color=(240, 240, 240, 100)))
                item.setSymbolSize(5)
                item_counter += 1
        self.stacked_plot_sett_button.setCurrentIndex(0)

    def fit_fun_window(self):
        """Open a new window"""
        print("Opening a new window...")

        # Create a new window
        new_window = QtWidgets.QWidget()
        new_window.setWindowTitle("Fitting")
        # Set window size and position
        new_window.setGeometry(100, 100, 800, 600)

        # Create a layout for the new window
        window_layout = QtWidgets.QVBoxLayout()

        fit_plot_widget = pg.PlotWidget()
        fit_plot_widget.setBackground('white')

        # Add the plot widget to the window layout
        window_layout.addWidget(fit_plot_widget)

        # Create a horizontal layout for the label and line edit
        fit_options_layout = QtWidgets.QHBoxLayout()

        # Add a label for the fit type
        fit_label = QtWidgets.QLabel("Exponential Fit Type:")
        fit_options_layout.addWidget(fit_label)

        # Add a QLineEdit to specify the fit type
        fit_type = QtWidgets.QLineEdit('Double')
        fit_options_layout.addWidget(fit_type)

        MW_label = QtWidgets.QLabel("MW?:")
        MW = QtWidgets.QCheckBox()
        fit_options_layout.addWidget(MW_label)
        fit_options_layout.addWidget(MW)

        # Add the horizontal layout to the main layout
        window_layout.addLayout(fit_options_layout)

        # Add a button to trigger some fitting functionality
        fit_button = QtWidgets.QPushButton("Run Fit")
        fit_button.clicked.connect(lambda: self.data_fitting_fun(
            fit_type.text(), fit_plot_widget, MW.isChecked()))

        window_layout.addWidget(fit_button)

        # Set the layout to the new window
        new_window.setLayout(window_layout)

        # Show the new window
        new_window.show()

        # Keep a reference to avoid garbage collection
        self.new_window = new_window

    def data_fitting_fun(self, fit_type, fit_plot_widget, MW):
        sink = DataSink('T1')
        # Code a way to check if the dataserver has data in it. Python will crash if it does not
        sink.start()
        sink.pop()
        data = sink.data.get('datasets')
        signal_data = data.get('ms0')
        background_data = data.get('ms1')
        sink.stop()
        x_axis = signal_data[0][0]
        signal_arrays = np.array(background_data)[:, 1, :]
        plot_name = "Optical T1 " + fit_type + " exponential fit"
        if MW == True:
            signal_arrays = np.array(signal_data)[:, 1, :]
            plot_name = "MW T1 " + fit_type + " exponential fit"
        average_signal = np.nanmean(signal_arrays, axis=0)
        fitting_data = np.array([x_axis, average_signal])
        # Plot your data in the new window (example: average_signal vs. x_axis)
        fit_plot_widget.clear()
        fit_plot_widget.addLegend()
        fit_plot_widget.scatterPlot(
            x_axis, average_signal, brush=pg.mkBrush('r'), name="Average Signal")
        fit_data = exponential_decay_fitting(fitting_data, fit_type, save=True)
        fit_plot_widget.plot(
            fit_data[0], fit_data[1], name=plot_name, pen=pg.mkPen(color='blue', width=3))
        fit_plot_widget.setLabel('bottom', 'time (μs)')
        fit_plot_widget.setLabel('left', 'Signal')
