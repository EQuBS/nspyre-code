"""
Qt GUI for the Nano-3D200FT from MadCity Labs.

Rolando A. Fimbres Grijalva 6/12/2025
"""
from pyqtgraph.Qt import QtWidgets
from pyqtgraph import SpinBox
from MCL_Madlib_Wrapper import MCL_Nanodrive 
import time

class NanoWidget(QtWidgets.QWidget):
    """Qt widget for controlling the Nano-3D200FT from MadCity Labs."""

    def __init__(self, nano): #, nano=None, handle=None
        """
        Args:
            nano_driver: The MCL Nanodrive driver.
        """
        super().__init__()
        self.nano = nano
        """ if nano is None or handle is None:
            self.nano = MCL_Nanodrive()
            self.handle = self.nano.init_handle()
        else:
            self.nano = nano
            self.handle = handle """
        
        #handle = nano.init_handle()

        # top level layout
        layout = QtWidgets.QGridLayout()
        layout_row = 0

        # Following buttons are commented out because the Nano is always on when powered. 6/23/2025
        """ 
        # Plus button to turn the Nano off
        #off_button = QtWidgets.QPushButton('+')
        #off_button.clicked.connect(lambda: self.nano.off())
        #layout.addWidget(off_button, layout_row, 0)

        # Minus button to turn the Nano on
        #on_button = QtWidgets.QPushButton('-')
        #on_button.clicked.connect(lambda: self.nano.on())
        #layout.addWidget(on_button, layout_row, 1)
        """

        layout_row += 1

         # Create textboxes for X, Y, Z positions
        self.x_pos_box = QtWidgets.QLineEdit()
        self.y_pos_box = QtWidgets.QLineEdit()
        self.z_pos_box = QtWidgets.QLineEdit()
        self.x_pos_box.setReadOnly(True)
        self.y_pos_box.setReadOnly(True)
        self.z_pos_box.setReadOnly(True)

        # Button to read the current position
        read_button = QtWidgets.QPushButton('Read Position')
        def read_position(button):
            x = self.nano.single_read_n(1, self.nano.handle) #self.nano.handle
            y = self.nano.single_read_n(2, self.nano.handle) #self.nano.handle
            z = self.nano.single_read_n(3, self.nano.handle) #self.nano.handle
            self.x_pos_box.setText(f"{-100+(x):.4f}")
            self.y_pos_box.setText(f"{-100+(y):.4f}")
            self.z_pos_box.setText(f"{-100+(z):.4f}")
        read_button.clicked.connect(read_position)

        # Add widgets to layout
        layout.addWidget(QtWidgets.QLabel('X-Position (um)'), layout_row, 0)
        layout.addWidget(self.x_pos_box, layout_row, 1)
        layout.addWidget(read_button, layout_row, 2)
        layout_row += 1

        layout.addWidget(QtWidgets.QLabel('Y-Position (um)'), layout_row, 0)
        layout.addWidget(self.y_pos_box, layout_row, 1)
        layout_row += 1

        layout.addWidget(QtWidgets.QLabel('Z-Position (um)'), layout_row, 0)
        layout.addWidget(self.z_pos_box, layout_row, 1)
        layout_row += 1 

        #sb = SpinBox()
        #sb.setFixedSize(80, 30)

        # X position spinbox
        layout.addWidget(QtWidgets.QLabel('X-Position (um)'), layout_row, 0)
        self.x_position_spinbox = SpinBox(value=0, siPrefix=False, bounds=(-100.000, 100.000), step=0.003, dec=4, int=False)
        self.x_position_spinbox.setFixedSize(120, 30)
        self.x_position_spinbox.setValue(value=0)
        layout.addWidget(self.x_position_spinbox, layout_row, 1)

        #layout_row += 1
       
        # button to move X position
        move_xbutton = QtWidgets.QPushButton('Move')
        def move_x(button):
            self.nano.monitor_n(100 + (self.x_position_spinbox.value()), 1, self.nano.handle)
        move_xbutton.clicked.connect(move_x)
        layout.addWidget(move_xbutton, layout_row, 2)

        layout_row += 1

        # Step size spinbox
        layout.addWidget(QtWidgets.QLabel('X Step Size (um)'), layout_row, 0)
        self.x_step_size_spinbox = SpinBox(value=0.05, siPrefix=False, bounds=(0.000, 200.000), step=0.003, dec=4, int=False)
        self.x_step_size_spinbox.setFixedSize(120, 30)
        self.x_step_size_spinbox.setValue(value=0)
        layout.addWidget(self.x_step_size_spinbox, layout_row, 1)
 
        plus_xbutton = QtWidgets.QPushButton('+')
        def plus_x(button):
            read_x = self.nano.single_read_n(1, self.nano.handle)
            self.nano.monitor_n(read_x + self.x_step_size_spinbox.value(), 1, self.nano.handle)
        plus_xbutton.clicked.connect(plus_x)
        layout.addWidget(plus_xbutton, layout_row, 2)
        plus_xbutton.setFixedSize(60, 30)
        #plus_button.clicked.connect(lambda: self.position_spinbox.setValue(self.position_spinbox.value() + 0.003))

        minus_xbutton = QtWidgets.QPushButton('-')
        def minus_x(button):
            read_x = self.nano.single_read_n(1, self.nano.handle)
            self.nano.monitor_n(read_x - self.x_step_size_spinbox.value(), 1, self.nano.handle)
        minus_xbutton.clicked.connect(minus_x)
        layout.addWidget(minus_xbutton, layout_row, 3)
        minus_xbutton.setFixedSize(60, 30)
        #minus_button.clicked.connect(lambda: self.position_spinbox.setValue(self.position_spinbox.value() - 0.003))

        layout_row += 1


        # Y position spinbox
        layout.addWidget(QtWidgets.QLabel('Y-Position (um)'), layout_row, 0)
        self.y_position_spinbox = SpinBox(value=0, siPrefix=False, bounds=(-100.000, 100.000), step=0.003, dec=4, int=False)
        self.y_position_spinbox.setFixedSize(120, 30)
        self.y_position_spinbox.setValue(value=0)
        layout.addWidget(self.y_position_spinbox, layout_row, 1)

        #layout_row += 1
       
        # button to move X position
        move_ybutton = QtWidgets.QPushButton('Move')
        def move_y(button):
            self.nano.monitor_n(100 + (self.y_position_spinbox.value()), 2, self.nano.handle)
        move_ybutton.clicked.connect(move_y)
        layout.addWidget(move_ybutton, layout_row, 2)

        layout_row += 1

        # Step size spinbox
        layout.addWidget(QtWidgets.QLabel('Y Step Size (um)'), layout_row, 0)
        self.y_step_size_spinbox = SpinBox(value=0.05, siPrefix=False, bounds=(0.000, 200.000), step=0.003, dec=4, int=False)
        self.y_step_size_spinbox.setFixedSize(120, 30)
        self.y_step_size_spinbox.setValue(value=0)
        layout.addWidget(self.y_step_size_spinbox, layout_row, 1)

        plus_ybutton = QtWidgets.QPushButton('+')
        def plus_y(button):
            read_y = self.nano.single_read_n(2, self.nano.handle)
            self.nano.monitor_n(read_y + self.y_step_size_spinbox.value(), 2, self.nano.handle)
        plus_ybutton.clicked.connect(plus_y)
        layout.addWidget(plus_ybutton, layout_row, 2)
        plus_ybutton.setFixedSize(60, 30)
        #plus_button.clicked.connect(lambda: self.position_spinbox.setValue(self.position_spinbox.value() + 0.003))

        minus_ybutton = QtWidgets.QPushButton('-')
        def minus_y(button):
            read_y = self.nano.single_read_n(2, self.nano.handle)
            self.nano.monitor_n(read_y - self.y_step_size_spinbox.value(), 2, self.nano.handle)
        minus_ybutton.clicked.connect(minus_y)
        layout.addWidget(minus_ybutton, layout_row, 3)
        minus_ybutton.setFixedSize(60, 30)
        #minus_button.clicked.connect(lambda: self.position_spinbox.setValue(self.position_spinbox.value() - 0.003))

        layout_row += 1

        # Z position spinbox
        layout.addWidget(QtWidgets.QLabel('Z-Position (um)'), layout_row, 0)
        self.z_position_spinbox = SpinBox(value=0, siPrefix=False, bounds=(-100.000, 100.000), step=0.003, dec=4, int=False)
        self.z_position_spinbox.setFixedSize(120, 30)
        self.z_position_spinbox.setValue(value=0)
        layout.addWidget(self.z_position_spinbox, layout_row, 1)

        #layout_row += 1
       
        # button to move X position
        move_zbutton = QtWidgets.QPushButton('Move')
        def move_z(button):
            self.nano.monitor_n(100 + (self.z_position_spinbox.value()), 3, self.nano.handle)
        move_zbutton.clicked.connect(move_z)
        layout.addWidget(move_zbutton, layout_row, 2)

        layout_row += 1

        # Step size spinbox
        layout.addWidget(QtWidgets.QLabel('Z Step Size (um)'), layout_row, 0)
        self.z_step_size_spinbox = SpinBox(value=0.05, siPrefix=False, bounds=(0.000, 200.000), step=0.003, dec=4, int=False)
        self.z_step_size_spinbox.setFixedSize(120, 30)
        self.z_step_size_spinbox.setValue(value=0)
        layout.addWidget(self.z_step_size_spinbox, layout_row, 1)

        plus_zbutton = QtWidgets.QPushButton('+')
        def plus_z(button):
            read_z = self.nano.single_read_n(3, self.nano.handle)
            self.nano.monitor_n(read_z + self.z_step_size_spinbox.value(), 3, self.nano.handle)
        plus_zbutton.clicked.connect(plus_z)
        layout.addWidget(plus_zbutton, layout_row, 2)
        plus_zbutton.setFixedSize(60, 30)
        #plus_button.clicked.connect(lambda: self.position_spinbox.setValue(self.position_spinbox.value() + 0.003))

        minus_zbutton = QtWidgets.QPushButton('-')
        def minus_z(button):
            read_z = self.nano.single_read_n(3, self.nano.handle)
            self.nano.monitor_n(read_z - self.z_step_size_spinbox.value(), 3, self.nano.handle)
        minus_zbutton.clicked.connect(minus_z)
        layout.addWidget(minus_zbutton, layout_row, 3)
        minus_zbutton.setFixedSize(60, 30)
        #minus_button.clicked.connect(lambda: self.position_spinbox.setValue(self.position_spinbox.value() - 0.003))

        layout_row += 1

        # Home button to set all axes to 100 um 
        home_button = QtWidgets.QPushButton('Home')
        def home_axes(button):
            # Move all axes to 100 um (hardware)
            self.nano.monitor_n(100.0, 1, self.nano.handle)  # X
            self.nano.monitor_n(100.0, 2, self.nano.handle)  # Y
            self.nano.monitor_n(100.0, 3, self.nano.handle)  # Z
        home_button.clicked.connect(home_axes)
        layout.addWidget(home_button, layout_row, 0, 1, 2)  # Spans two columns for visibility
        layout_row += 1

        self.setLayout(layout)
    
    def closeEvent(self, event):
        try:
            if hasattr(self.nano, 'dll') and hasattr(self.nano, 'handle'):
                self.nano.dll.MCL_ReleaseHandle(self.nano.handle)
                print("Nano-Drive handle released.")
        except Exception as e:
            print(f"Error releasing Nano-Drive handle: {e}")
        super().closeEvent(event)
    
        