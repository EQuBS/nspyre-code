"""
 Rolando A. Fimbres G. 7/29/2025
# gui_Scan-2.0_XZ.py
The following code is part of the GUI for the Scan-2.0 XZ application.
"""
from pyqtgraph.Qt import QtWidgets
from PyQt5.QtWidgets import QMessageBox
import numpy as np
import matplotlib.pyplot as plt
from rpyc.utils.classic import obtain
from nspyre import DataSink, DataSource
import sys
from nspyre.gui.widgets.save import save_json
from nspyre import HeatMapWidget 
import numpy as np
# import time
from TimeTagger import CHANNEL_UNUSED
from scipy.signal import convolve, deconvolve
import template.gui.Main_Scanner as Main_Scanner
from nspyre import ExperimentWidget

sys.path.append('../experiments')

class ScanXY(ExperimentWidget):
    """Scan XZ GUI for the Scan-2.0 application."""
    def __init__(self):
        
        """  Args:
            nano: The MCL Nanodrive driver.
                - handle: The handle for the MCL Nanodrive. Handle is obtained during initialization. See MCL_Madlib_Wrapper.py code line 49 for more details.
            laser: The DLnsec laser driver.
            streamer: The Swabian Pulse Streamer driver.
            tagger: The Swabian Time Tagger driver. """

        """
        try:
            if nano is None:
                self.nano = nano
            else:
                self.nano = nano
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "MCL Error", f"MCL Nanodrive not initialized: {e}\nScan functionality will be disabled.")
            self.setDisabled(True)
            return
        #self.nano = nano
        #self.handle = handle
        self.laser_driver = laser_driver
        self.ps = pulse_streamer_driver
        self.tagger = tagger
 """
        params_config = {
            'x-initial': {
                'display_text': 'X Initial Position (µm)',
                'widget': QtWidgets.QDoubleSpinBox(
                    value = 10.0,
                    suffix = 'µm',
                    minimum = -100.0,
                    maximum = 100.0,
                    singleStep = (0.003),
                    decimals = 3 
                ),
            },
            'x-final': {
                'display_text': 'X Final Position (µm)',
                'widget': QtWidgets.QDoubleSpinBox(
                    value = 10.0,
                    suffix = 'µm',
                    minimum = -100.0,
                    maximum = 100.0,
                    singleStep = (0.003),
                    decimals = 3
                ),
            },
            'x_data-points': {
                'display_text': 'X Data Points',
                'widget': QtWidgets.QSpinBox(
                    value = 10,
                    minimum = 1,
                    maximum = 70,
                    singleStep = 1
                ),
            },
            'z-initial': {
                'display_text': 'Y Initial Position (µm)',
                'widget': QtWidgets.QDoubleSpinBox(
                    value = 10.0,
                    suffix = 'µm',
                    minimum = -100.0,
                    maximum = 100.0,
                    singleStep = (0.003),
                    decimals = 3
                ),
            },
            'z-final': {
                'display_text': 'Y Final Position (µm)',
                'widget': QtWidgets.QDoubleSpinBox(
                    value = 10.0,
                    suffix = 'µm',
                    minimum = -100.0,
                    maximum = 100.0,
                    singleStep = (0.003),
                    decimals = 3
                ),
            },
            'z_data-points': {
                'display_text': 'Y Data Points',
                'widget': QtWidgets.QSpinBox(
                    value = 10,
                    minimum = 1,
                    maximum = 70,
                    singleStep = 1
                ),
            }
        }
        super().__init__(params_config,
                        Main_Scanner,
                        'MainScanner',
                        'scan_xz',
                        title='XZ Scan')

        layout = self.layout()
        layout.addWidget(QtWidgets.QLabel('Export File Path:\n/C:/Users/XieLab/Documents/Confocal_System/Exp_Nspyre Data/JSON_files/'))

        self.file_path = QtWidgets.QLineEdit(self)
        self.file_path.setPlaceholderText('File Name')
        layout.addWidget(self.file_path)

        # Export button
        self.export_button = QtWidgets.QPushButton('Export', self)
        layout.addWidget(self.export_button)
        self.export_button.clicked.connect(self.export_data)

    # Export_data function
    def export_data(self):
        sink = DataSink('XZ Scan')
        sink.start()
        sink.pop()
        data = sink.data.get('datasets')
        # Retrieve text from QLineEdit.
        file_path_str = "C:/Users/XieLab/Documents/Confocal_System/Exp_Nspyre Data/JSON_files/" + self.file_path.text() #+ ".json"
        # We use the file path to save data.
        save_json(file_path_str, data)
        print("Data exported to:", file_path_str)

class XY_ScanPlot(HeatMapWidget):
    def __init__(self):
        title = 'XZ Scan'
        #super().__init__(title=title, btm_label='X', lft_label='Y', colormap = 0.5)
        super().__init__(title=title, btm_label='X [µm]', lft_label='Y [µm]', colormap = None)

    def setup(self):
        self.sink = DataSink('XZ Scan')
        self.sink.__enter__()

    def teardown(self):
        self.sink.__exit__()

    def update(self):
        self.sink.pop() # Wait for some data to be saved to sink
        self.set_data(self.sink.datasets['xSteps'], self.sink.datasets['ySteps'], self.sink.datasets['ScanCounts'])


    