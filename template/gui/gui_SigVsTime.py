"""
GUI for Signal vs Time experiment
Tian-Xing Zheng, Aug.31.2023
"""
import numpy as np

from nspyre import FlexLinePlotWidget
from nspyre import ExperimentWidget
from nspyre import DataSink
from nspyre import InstrumentGateway

from pyqtgraph import SpinBox
from pyqtgraph.Qt import QtWidgets
import sys

#import spin_measurements

#sm = spin_measurements.SpinMeasurements()

from . import spin_measurements as sm
# from . import spin_measurements

# print(spin_measurements.__file__)

#from template.gui.spin_measurements import SpinMeasurements as sm

# PyQt5 for GUI buttons and checkboxes
# from PyQt5.QtWidgets import QPushButton, QLabel, QLineEdit, QComboBox, QCheckBox, QRadioButton, QProgressBar
# from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QFormLayout, QGridLayout
# from PyQt5.QtWidgets import QWidget, QGraphicsOpacityEffect
# from PyQt5.QtCore import Qt, QObject, QThread, pyqtSignal, pyqtSlot
# from PyQt5.QtGui import QColor

import sys
sys.path.append('../experiments')


class SigVsTimeWidget(ExperimentWidget):
    def __init__(self):
        params_config = {
            'sampling_rate': {
                    'display_text': 'Sampling Rate: ',
                    'widget': SpinBox(
                        value = 10,
                        suffix = 'Hz',
                        siPrefix = True,
                        bounds = (None, 1e6),
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
        }

        super().__init__(params_config, 
                        sm,
                        'SpinMeasurements',
                        'sigvstime_run',
                        title='Signal vs Time',
                        kill = True)

    #     self.toggle_laser_checkbox = QCheckBox("Laser on")
    #     self.toggle_laser_checkbox.setChecked(False)
    #     self.toggle_laser_checkbox.stateChanged.connect(lambda: self.toggle_laser())
    
    # def toggle_laser(self):
    #     if self.toggle_laser_checkbox.isChecked() == True:
    #         with InstrumentGateway() as gw:
    #             gw.laser.set_power(10)
    #             gw.laser.on()
    #             gw.laser.set_mode('LAS')
    #     else:
    #         with InstrumentGateway() as gw:
    #             gw.laser.off()

def process_SigVsTime_data(sink: DataSink):
    """Don't need to do any data processing for Signal Vs Time experiments"""
    # diff_sweeps = []
    # for s,_ in enumerate(sink.datasets['signal']):
    #     freqs = sink.datasets['signal'][s][0]
    #     sig = sink.datasets['signal'][s][1]
    #     bg = sink.datasets['background'][s][1]
    #     diff_sweeps.append(np.stack([freqs, sig - bg]))
    # sink.datasets['diff'] = diff_sweeps
    # pass

class FlexLinePlotWidgetWithSigVsTime(FlexLinePlotWidget):
    """Add some default settings to the FlexSinkLinePlotWidget."""
    def __init__(self):
        super().__init__(data_processing_func=process_SigVsTime_data)
        self.add_plot('fluorescence',  series = 'SigVsT_data',   scan_i='',   scan_j='',  processing='Append')

        # manually set the XY range
        #self.line_plot.plot_item().setXRange(3.0, 4.0)
        #self.line_plot.plot_item().setYRange(-3000, 4500)

        # retrieve legend object
        legend = self.line_plot.plot_widget.addLegend()
        # set the legend location
        legend.setOffset((-10, -50))

        # Make sure the datasource name matches with the name that you defined in the spyrelet file!
        self.datasource_lineedit.setText('SigVsTime')
        
        # Set the default processing as 0: Average, 1: Append
        # Since we are doing Signal vs Time experiment data plotting here, we use Append 
        self.plot_processing_dropdown.setCurrentIndex(1)