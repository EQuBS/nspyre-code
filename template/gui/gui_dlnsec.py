"""
Qt GUI for Swabian/LABS electronics DLnsec laser.

Copyright (c) 2022, Benjamin Soloway, Jacob Feder
All rights reserved.

Tian-Xing Zheng: Add button for turn on the trigger from pulse streamer
Sept.2023
"""
import logging

from pyqtgraph.Qt import QtWidgets
from pyqtgraph import SpinBox
from template.drivers.dlnsec import DLnsec
from template.drivers.ps82 import PS82
from nspyre import InstrumentGateway

#gw = InstrumentGateway(port=42068)
#laser_driver = gw.laser #.open()  # Change 'COM3' to the appropriate port for your system
#laser_driver.open()

#laser_driver = DLnsec('COM3')
#laser_driver.open()  # Open the connection to the laser
#pulse_streamer_driver = PS82() 
#print(type(laser_driver))

class DLnsecWidget(QtWidgets.QWidget):
    """Qt widget for controlling DLnsec lasers."""
    
    def __init__(self, laser_driver, pulse_streamer_driver):
        """
        Args:
            laser_driver:            The dlnsec driver.
            pulse_streamer_driver:   The Swabian Pulse Streamer driver (User defined for pulse sequences)
        """
        super().__init__()
        self.laser = laser_driver
        self.ps = pulse_streamer_driver

        # top level layout
        layout = QtWidgets.QGridLayout()
        layout_row = 0

        # button to turn the laser off
        off_button = QtWidgets.QPushButton('Off')
        off_button.clicked.connect(lambda: self.laser.off())
        layout.addWidget(off_button, layout_row, 0)

        # button to turn the laser on
        on_button = QtWidgets.QPushButton('On')
        on_button.clicked.connect(lambda: self.laser.on())
        layout.addWidget(on_button, layout_row, 1)

        layout_row += 1

        # power spinbox
        layout.addWidget(QtWidgets.QLabel('Power %'), layout_row, 0)
        self.power_spinbox = SpinBox(value=0, siPrefix=False, bounds=(0, 100), int=True)
        self.power_spinbox.setValue(value=0)
        layout.addWidget(self.power_spinbox, layout_row, 2)

        # power get button
        #power_get_button = QtWidgets.QPushButton('Get')
        #def get_power(button):
        #    self.power_spinbox.setValue(self.laser.get_power())
        #get_power(None)
        #power_get_button.clicked.connect(get_power)
        #layout.addWidget(power_get_button, layout_row, 1)

        # power set button
        power_set_button = QtWidgets.QPushButton('Set')
        def set_power(button):
            self.laser.set_power(self.power_spinbox.value())
        power_set_button.clicked.connect(set_power)
        layout.addWidget(power_set_button, layout_row, 3)

        layout_row += 1

        # modulation label
        layout.addWidget(QtWidgets.QLabel('Modulation'), layout_row, 0)

        # modulation combobox
        self.modulation_dropdown = QtWidgets.QComboBox()
        las_state_text = 'LAS'
        external_trigger_modulation_state_text = 'Ext'
        internal_trigger_modulation_state_text = 'Int'
        self.modulation_dropdown.addItem(las_state_text) # index 1
        self.modulation_dropdown.addItem(external_trigger_modulation_state_text) # index 2
        self.modulation_dropdown.addItem(internal_trigger_modulation_state_text) # index 3
        layout.addWidget(self.modulation_dropdown, layout_row, 2)

        # modulation set button
        modulation_set_button = QtWidgets.QPushButton('Set')
        def set_modulation(button):
            mode = self.modulation_dropdown.currentText()
            if mode == las_state_text:
                self.laser.cw_mode()
            elif mode == external_trigger_modulation_state_text:
                self.laser.trig_mode()
            elif mode == internal_trigger_modulation_state_text:
                self.laser.int_mode()
            else:
                raise RuntimeError('Modulation mode error.')

        modulation_set_button.clicked.connect(set_modulation)
        layout.addWidget(modulation_set_button, layout_row, 3)

        layout_row += 1
        # Pulse Streamer trigger label
        layout.addWidget(QtWidgets.QLabel('Trigger'), layout_row, 0)
        
        # Trigger on button
        trigger_on_button = QtWidgets.QPushButton('On')
        trigger_on_button.clicked.connect(lambda: self.ps.laser_on())
        layout.addWidget(trigger_on_button, layout_row, 1)
        
        layout_row += 1
        # take up any additional space in the final column with padding
        layout.setColumnStretch(2, 1)
        # take up any additional space in the final row with padding
        layout.setRowStretch(layout_row, 1)

        

        self.setLayout(layout)
