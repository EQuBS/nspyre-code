"""
GUI for a Scanning procedure.

Rolando A. Fimbres Grijalva 6/23/2025
"""
from pyqtgraph.Qt import QtWidgets
from pyqtgraph import SpinBox
from MCL_Madlib_Wrapper import MCL_Nanodrive
from PyQt5.QtWidgets import QMessageBox

"""
Modification will be added in order to keep the following instruments to interfere with each other
when other widgets (that use them) are open.

INSTRUMENTS:
1) MCL Nano-3D200FT
2) DLnsec Laser
3) Swabian Pulse Streamer PS82
4) Swabian Time Tagger 

6/23/2025 Modifications have NOT CREATED YET.
"""

class ScanWidget(QtWidgets.QWidget):
    """Qt widget for controlling a scanning procedure."""

    def __init__(self, nano=None, handle=None):
        """
        Args:
            nano_driver: The MCL Nanodrive driver.
        """
        super().__init__()
        if nano is None or handle is None:
            self.nano = MCL_Nanodrive()
            self.handle = self.nano.init_handle()
        else:
            self.nano = nano
            self.handle = handle
    
        # top level layout
        layout = QtWidgets.QGridLayout()
        layout_row = 0

        #layout_row += 1

        # Create Labels for the Start/Stop and Num. of datapoints in the Scan for X, Y, Z positions.

        # Row 0: Labels
        layout.addWidget(QtWidgets.QLabel(''), layout_row, 0)
        layout.addWidget(QtWidgets.QLabel('Min.'), layout_row, 1)
        layout.addWidget(QtWidgets.QLabel('Max.'), layout_row, 2)
        layout.addWidget(QtWidgets.QLabel('N'), layout_row, 3)
        layout_row += 1
        # Row 1: X position
        layout.addWidget(QtWidgets.QLabel('X'), layout_row, 0)
        self.x_min_box = QtWidgets.QDoubleSpinBox()
        self.x_max_box = QtWidgets.QDoubleSpinBox()
        self.x_n_box = QtWidgets.QSpinBox()
        self.x_min_box.setRange(0.000, 200.000)
        self.x_min_box.setDecimals(3)
        self.x_min_box.setSingleStep(0.003)
        self.x_max_box.setRange(0.000, 200.000)
        self.x_max_box.setDecimals(3)
        self.x_max_box.setSingleStep(0.003)
        self.x_n_box.setRange(0, 10000)
        layout.addWidget(self.x_min_box, layout_row, 1)
        layout.addWidget(self.x_max_box, layout_row, 2)
        layout.addWidget(self.x_n_box, layout_row, 3)
        layout_row += 1
        # Row 2: Y position
        layout.addWidget(QtWidgets.QLabel('Y'), layout_row, 0)
        self.y_min_box = QtWidgets.QDoubleSpinBox()
        self.y_max_box = QtWidgets.QDoubleSpinBox()
        self.y_n_box = QtWidgets.QSpinBox()
        self.y_min_box.setRange(0.000, 200.000)
        self.y_min_box.setDecimals(3)
        self.y_min_box.setSingleStep(0.003)
        self.y_max_box.setRange(0.000, 200.000)
        self.y_max_box.setDecimals(3)
        self.y_max_box.setSingleStep(0.003)
        self.y_n_box.setRange(0, 10000)
        layout.addWidget(self.y_min_box, layout_row, 1)
        layout.addWidget(self.y_max_box, layout_row, 2)
        layout.addWidget(self.y_n_box, layout_row, 3)
        layout_row += 1
        # Row 3: Z position
        layout.addWidget(QtWidgets.QLabel('Z'), layout_row, 0)
        self.z_min_box = QtWidgets.QDoubleSpinBox()
        self.z_max_box = QtWidgets.QDoubleSpinBox()
        self.z_n_box = QtWidgets.QSpinBox()
        self.z_min_box.setRange(0.000, 200.000)
        self.z_min_box.setDecimals(3)
        self.z_min_box.setSingleStep(0.003)
        self.z_max_box.setRange(0.000, 200.000)
        self.z_max_box.setDecimals(3)
        self.z_max_box.setSingleStep(0.003)
        self.z_n_box.setRange(0, 10000)
        layout.addWidget(self.z_min_box, layout_row, 1)
        layout.addWidget(self.z_max_box, layout_row, 2)
        layout.addWidget(self.z_n_box, layout_row, 3)
        layout_row += 1
        # Add stretch to keep widgets at the top
        layout.setRowStretch(layout_row, 1)

        self.setLayout(layout)