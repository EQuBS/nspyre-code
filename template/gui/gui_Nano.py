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

        ### Added by Rolando 4/3/2026  ####################
        self.axis_ranges = {
            1: float(self.nano.get_calibration(1, self.nano.handle)),
            2: float(self.nano.get_calibration(2, self.nano.handle)),
            3: float(self.nano.get_calibration(3, self.nano.handle)),
        }
        self.axis_centers = {
            axis: self.axis_ranges[axis] / 2.0
            for axis in (1, 2, 3)
        }

        

        ############################################
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
            self.x_pos_box.setText(f"{self._hw_to_user(1, x):.3f}")
            self.y_pos_box.setText(f"{self._hw_to_user(2, y):.3f}")
            self.z_pos_box.setText(f"{self._hw_to_user(3, z):.3f}")
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
        self.x_position_spinbox = SpinBox(value=0, siPrefix=False, bounds=(-self.axis_centers[1], self.axis_centers[1]), step=0.003, dec=3, int=False)
        self.x_position_spinbox.setFixedSize(120, 30)
        self.x_position_spinbox.setValue(value=0)
        layout.addWidget(self.x_position_spinbox, layout_row, 1)

        #layout_row += 1
       
        # button to move X position
        move_xbutton = QtWidgets.QPushButton('Move')
        def move_x(button):
            self.nano.monitor_n(self._user_to_hw(1, self.x_position_spinbox.value()), 1, self.nano.handle)
        move_xbutton.clicked.connect(move_x)
        layout.addWidget(move_xbutton, layout_row, 2)

        layout_row += 1

        # Step size spinbox
        layout.addWidget(QtWidgets.QLabel('X Step Size (um)'), layout_row, 0)
        self.x_step_size_spinbox = SpinBox(value=0.05, siPrefix=False, bounds=(0.000, 9.000), step=0.003, dec=3, int=False)
        self.x_step_size_spinbox.setFixedSize(120, 30)
        self.x_step_size_spinbox.setValue(value=0.05)
        layout.addWidget(self.x_step_size_spinbox, layout_row, 1)
 
        plus_xbutton = QtWidgets.QPushButton('+')
        def plus_x(button):
            read_x = self.nano.single_read_n(1, self.nano.handle)
            self.nano.monitor_n(read_x + self.x_step_size_spinbox.value(), 1, self.nano.handle)
        #plus_xbutton.clicked.connect(plus_x)
        plus_xbutton.clicked.connect(lambda _: self.step_axis(1, +self.x_step_size_spinbox.value()))
        layout.addWidget(plus_xbutton, layout_row, 2)
        plus_xbutton.setFixedSize(60, 30)
        #plus_button.clicked.connect(lambda: self.position_spinbox.setValue(self.position_spinbox.value() + 0.003))

        minus_xbutton = QtWidgets.QPushButton('-')
        def minus_x(button):
            read_x = self.nano.single_read_n(1, self.nano.handle)
            self.nano.monitor_n(read_x - self.x_step_size_spinbox.value(), 1, self.nano.handle)
        #minus_xbutton.clicked.connect(minus_x)
        minus_xbutton.clicked.connect(lambda _: self.step_axis(1, -self.x_step_size_spinbox.value()))
        layout.addWidget(minus_xbutton, layout_row, 3)
        minus_xbutton.setFixedSize(60, 30)
        #minus_button.clicked.connect(lambda: self.position_spinbox.setValue(self.position_spinbox.value() - 0.003))

        layout_row += 1


        # Y position spinbox
        layout.addWidget(QtWidgets.QLabel('Y-Position (um)'), layout_row, 0)
        self.y_position_spinbox = SpinBox(value=0, siPrefix=False, bounds=(-self.axis_centers[2], self.axis_centers[2]), step=0.003, dec=3, int=False)
        self.y_position_spinbox.setFixedSize(120, 30)
        self.y_position_spinbox.setValue(value=0)
        layout.addWidget(self.y_position_spinbox, layout_row, 1)

        #layout_row += 1
       
        # button to move X position
        move_ybutton = QtWidgets.QPushButton('Move')
        def move_y(button):
            self.nano.monitor_n(self._user_to_hw(2, self.y_position_spinbox.value()), 2, self.nano.handle)
        move_ybutton.clicked.connect(move_y)
        layout.addWidget(move_ybutton, layout_row, 2)

        layout_row += 1

        # Step size spinbox
        layout.addWidget(QtWidgets.QLabel('Y Step Size (um)'), layout_row, 0)
        self.y_step_size_spinbox = SpinBox(value=0.05, siPrefix=False, bounds=(0.000, 9.000), step=0.003, dec=3, int=False)
        self.y_step_size_spinbox.setFixedSize(120, 30)
        self.y_step_size_spinbox.setValue(value=0.05)
        layout.addWidget(self.y_step_size_spinbox, layout_row, 1)

        plus_ybutton = QtWidgets.QPushButton('+')
        def plus_y(button):
            read_y = self.nano.single_read_n(2, self.nano.handle)
            self.nano.monitor_n(read_y + self.y_step_size_spinbox.value(), 2, self.nano.handle)
        #plus_ybutton.clicked.connect(plus_y)
        plus_ybutton.clicked.connect(lambda _: self.step_axis(2, +self.y_step_size_spinbox.value()))
        layout.addWidget(plus_ybutton, layout_row, 2)
        plus_ybutton.setFixedSize(60, 30)
        #plus_button.clicked.connect(lambda: self.position_spinbox.setValue(self.position_spinbox.value() + 0.003))

        minus_ybutton = QtWidgets.QPushButton('-')
        def minus_y(button):
            read_y = self.nano.single_read_n(2, self.nano.handle)
            self.nano.monitor_n(read_y - self.y_step_size_spinbox.value(), 2, self.nano.handle)
        #minus_ybutton.clicked.connect(minus_y)
        minus_ybutton.clicked.connect(lambda _: self.step_axis(2, -self.y_step_size_spinbox.value()))
        layout.addWidget(minus_ybutton, layout_row, 3)
        minus_ybutton.setFixedSize(60, 30)
        #minus_button.clicked.connect(lambda: self.position_spinbox.setValue(self.position_spinbox.value() - 0.003))

        layout_row += 1

        # Z position spinbox
        layout.addWidget(QtWidgets.QLabel('Z-Position (um)'), layout_row, 0)
        self.z_position_spinbox = SpinBox(value=0, siPrefix=False, bounds=(-self.axis_centers[3], self.axis_centers[3]), step=0.003, dec=3, int=False)
        self.z_position_spinbox.setFixedSize(120, 30)
        self.z_position_spinbox.setValue(value=0)
        layout.addWidget(self.z_position_spinbox, layout_row, 1)

        #layout_row += 1
       
        # button to move X position
        move_zbutton = QtWidgets.QPushButton('Move')
        def move_z(button):
            self.nano.monitor_n(self._user_to_hw(3, self.z_position_spinbox.value()), 3, self.nano.handle)
        move_zbutton.clicked.connect(move_z)
        layout.addWidget(move_zbutton, layout_row, 2)

        layout_row += 1

        # Step size spinbox
        layout.addWidget(QtWidgets.QLabel('Z Step Size (um)'), layout_row, 0)
        self.z_step_size_spinbox = SpinBox(value=0.05, siPrefix=False, bounds=(0.000, 9.000), step=0.003, dec=3, int=False)
        self.z_step_size_spinbox.setFixedSize(120, 30)
        self.z_step_size_spinbox.setValue(value=0.05)
        layout.addWidget(self.z_step_size_spinbox, layout_row, 1)

        plus_zbutton = QtWidgets.QPushButton('+')
        def plus_z(button):
            read_z = self.nano.single_read_n(3, self.nano.handle)
            self.nano.monitor_n(read_z + self.z_step_size_spinbox.value(), 3, self.nano.handle)
        #plus_zbutton.clicked.connect(plus_z)
        plus_zbutton.clicked.connect(lambda _: self.step_axis(3, +self.z_step_size_spinbox.value()))
        layout.addWidget(plus_zbutton, layout_row, 2)
        plus_zbutton.setFixedSize(60, 30)
        #plus_button.clicked.connect(lambda: self.position_spinbox.setValue(self.position_spinbox.value() + 0.003))

        minus_zbutton = QtWidgets.QPushButton('-')
        def minus_z(button):
            read_z = self.nano.single_read_n(3, self.nano.handle)
            self.nano.monitor_n(read_z - self.z_step_size_spinbox.value(), 3, self.nano.handle)
        #minus_zbutton.clicked.connect(minus_z)
        minus_zbutton.clicked.connect(lambda _: self.step_axis(3, -self.z_step_size_spinbox.value()))
        layout.addWidget(minus_zbutton, layout_row, 3)
        minus_zbutton.setFixedSize(60, 30)
        #minus_button.clicked.connect(lambda: self.position_spinbox.setValue(self.position_spinbox.value() - 0.003))

        layout_row += 1

        # Home button to set all axes to 100 um 
        home_button = QtWidgets.QPushButton('Home')
        def home_axes(button):
            # Move all axes to 100 um (hardware)
            self.nano.monitor_n(self.axis_centers[1], 1, self.nano.handle)
            self._update_axis_widgets(1, actual_x)
            self.nano.monitor_n(self.axis_centers[2], 2, self.nano.handle)
            self._update_axis_widgets(2, actual_y)
            self.nano.monitor_n(self.axis_centers[3], 3, self.nano.handle)
            self._update_axis_widgets(3, actual_z)
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

    def _hw_to_user(self, axis, hw_value):
            return float(hw_value) - self.axis_centers[axis]

    def _user_to_hw(self, axis, user_value):
            return float(user_value) + self.axis_centers[axis]
    
    def _clamp_hw_target(self, axis, hw_target):
        return max(0.0, min(self.axis_ranges[axis], float(hw_target)))
    
    def move_axis_to_user(self, axis, user_target):
        hw_target = self._user_to_hw(axis, user_target)
        hw_target = self._clamp_hw_target(axis, hw_target)
        actual_hw = self.nano.monitor_n(hw_target, axis, self.nano.handle)
        self._update_axis_widgets(axis, actual_hw)
    
    def step_axis(self, axis, delta_user):
        current_hw = self.nano.single_read_n(axis, self.nano.handle)
        hw_target = self._clamp_hw_target(axis, current_hw + float(delta_user))
        actual_hw = self.nano.monitor_n(hw_target, axis, self.nano.handle)
        self._update_axis_widgets(axis, actual_hw)

    def _update_axis_widgets(self, axis, hw_value):
        user_value = self._hw_to_user(axis, hw_value)
        if axis == 1:
            self.x_pos_box.setText(f"{user_value:.4f}")
            self.x_position_spinbox.setValue(user_value)
        elif axis == 2:
            self.y_pos_box.setText(f"{user_value:.4f}")
            self.y_position_spinbox.setValue(user_value)
        elif axis == 3:
            self.z_pos_box.setText(f"{user_value:.4f}")
            self.z_position_spinbox.setValue(user_value)
    
    def _safe_call(self, func):
        try:
            return func()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Nano-Drive Error", str(e))
            return None
        