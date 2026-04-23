"""
Qt GUI for the Nano-3D200FT from MadCity Labs.

Rolando A. Fimbres Grijalva 4/17/2026

3rd version.
"""
from pyqtgraph.Qt import QtWidgets
from pyqtgraph import SpinBox
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                             QPushButton, QLabel, QHBoxLayout,
                             QGridLayout, QPushButton, QGroupBox,
                             QLineEdit)
from MCL_Madlib_Wrapper import MCL_Nanodrive 


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
        self.axis_min = {1: 0.0, 2: 0.0, 3: 0.0}
        self.axis_max = {
            1: float(self.nano.get_calibration(1, self.nano.handle)),
            2: float(self.nano.get_calibration(2, self.nano.handle)),
            3: float(self.nano.get_calibration(3, self.nano.handle)),
        }
        self.axis_centers = {
            axis: 0.5 * (self.axis_min[axis] + self.axis_max[axis])
            for axis in (1, 2, 3)
        }

        master_layout = QHBoxLayout()
        # Nanostage Controls (Grouped)
        nanostage_group = QGroupBox("Nanostage Controls")
        nanostage_vbox = QGridLayout()
        # Reduce vertical/horizontal gaps (default is often 10px)
        nanostage_vbox.setVerticalSpacing(2) 
        nanostage_vbox.setContentsMargins(5, 5, 5, 5)

        # --- Section 1: Read ---
        nanostage_vbox.addWidget(QLabel("X (µm)"), 0, 0)
        self.x_read = QLineEdit(); nanostage_vbox.addWidget(self.x_read, 0, 1)
        nanostage_vbox.addWidget(QLabel("Y (µm)"), 1, 0)
        self.y_read = QLineEdit(); nanostage_vbox.addWidget(self.y_read, 1, 1)
        nanostage_vbox.addWidget(QLabel("Z (µm)"), 2, 0)
        self.z_read = QLineEdit(); nanostage_vbox.addWidget(self.z_read, 2, 1)
        read_btn = QPushButton("Read")
        nanostage_vbox.addWidget(read_btn, 0, 2, 3, 1) # Spans 3 rows vertically

        # --- Section 2: Step Size (Condensed) ---
        step_label = QLabel("<b>Step Size</b>")
        nanostage_vbox.addWidget(step_label, 3, 0)
        self.step_val = SpinBox(value=0.025, siPrefix=False, bounds=(0.003, 9.000), step=0.003, dec=3)
        nanostage_vbox.addWidget(self.step_val, 3, 1, 1, 2) # Spans 2 columns

        # X, Y, Z Buttons on single rows
        """ for i, axis in enumerate(["X", "Y", "Z"], start=4):
            nanostage_vbox.addWidget(QLabel(axis), i, 0)
            nanostage_vbox.addWidget(QPushButton("+"), i, 1)
            nanostage_vbox.addWidget(QPushButton("-"), i, 2) """
        nanostage_vbox.addWidget(QLabel("X"), 4, 0)
        x_plus = QPushButton("+"); nanostage_vbox.addWidget(x_plus, 4, 1)
        x_minus = QPushButton("-"); nanostage_vbox.addWidget(x_minus, 4, 2)
        nanostage_vbox.addWidget(QLabel("Y"), 5, 0)
        y_plus = QPushButton("+"); nanostage_vbox.addWidget(y_plus, 5, 1)
        y_minus = QPushButton("-"); nanostage_vbox.addWidget(y_minus, 5, 2)
        nanostage_vbox.addWidget(QLabel("Z"), 6, 0)
        z_plus = QPushButton("+"); nanostage_vbox.addWidget(z_plus, 6, 1)
        z_minus = QPushButton("-"); nanostage_vbox.addWidget(z_minus, 6, 2)

        # --- Section 3: Set Position (Directly following) ---
        set_label = QLabel("<b>Set Position</b>")
        nanostage_vbox.addWidget(set_label, 7, 0, 1, 3)
        
        nanostage_vbox.addWidget(QLabel("X"), 8, 0)
        self.x_position_spinbox = SpinBox(value=0,
            siPrefix=False,
            bounds=(-self.axis_centers[1], self.axis_centers[1]),
            step=0.003,
            dec=3,
            int=False,)
        nanostage_vbox.addWidget(self.x_position_spinbox, 8, 1)
        nanostage_vbox.addWidget(QLabel("Y"), 9, 0)
        self.y_position_spinbox = SpinBox(value=0,
            siPrefix=False,
            bounds=(-self.axis_centers[2], self.axis_centers[2]),
            step=0.003,
            dec=3,
            int=False,)
        nanostage_vbox.addWidget(self.y_position_spinbox, 9, 1)
        nanostage_vbox.addWidget(QLabel("Z"), 10, 0)
        self.z_position_spinbox = SpinBox(value=0,
            siPrefix=False,
            bounds=(-self.axis_centers[3], self.axis_centers[3]),
            step=0.003,
            dec=3,
            int=False,)
        nanostage_vbox.addWidget(self.z_position_spinbox, 10, 1)
        set_button = QPushButton("Set")
        nanostage_vbox.addWidget(set_button, 8, 2, 3, 1) # Spans 3 rows
        home_button = QPushButton("Home")
        nanostage_vbox.addWidget(home_button, 10, 2)

        # Crucial: This pushes all rows to the top
        nanostage_vbox.setRowStretch(11, 1) 
        
        nanostage_group.setLayout(nanostage_vbox)
        master_layout.addWidget(nanostage_group)
        self.setLayout(master_layout)

        self.edited_axes = set()

        self.x_position_spinbox.editingFinished.connect(lambda: self.edited_axes.add(1))
        self.y_position_spinbox.editingFinished.connect(lambda: self.edited_axes.add(2))
        self.z_position_spinbox.editingFinished.connect(lambda: self.edited_axes.add(3))

        #################################
        # Button connections

        # Home
        home_button.clicked.connect(
            lambda _=False: self._safe_call(self._home_axes)
        )

        # Set Position
        set_button.clicked.connect(lambda _=False: self._safe_call(self._set_edited_axes))

        # Step buttons
        x_plus.clicked.connect(lambda _=False: self._safe_call(self._step_axis, 1, self.step_val.value()))
        x_minus.clicked.connect(lambda _=False: self._safe_call(self._step_axis, 1, -self.step_val.value()))
        y_plus.clicked.connect(lambda _=False: self._safe_call(self._step_axis, 2, self.step_val.value()))
        y_minus.clicked.connect(lambda _=False: self._safe_call(self._step_axis, 2, -self.step_val.value()))
        z_plus.clicked.connect(lambda _=False: self._safe_call(self._step_axis, 3, self.step_val.value()))
        z_minus.clicked.connect(lambda _=False: self._safe_call(self._step_axis, 3, -self.step_val.value()))
        
        # Read button
        read_btn.clicked.connect(lambda _=False: self._safe_call(self._refresh_positions))

    #################################
    # Motion functions

    def _hw_to_user(self, axis, hw_value):
        return float(hw_value) - self.axis_centers[axis]

    def _user_to_hw(self, axis, user_value):
        return self.axis_centers[axis] + float(user_value)

    def _clamp_hw(self, axis, hw_target):
        return max(self.axis_min[axis], min(float(hw_target), self.axis_max[axis]))

    def _set_axis_widgets(self, axis, hw_value):
        user_value = self._hw_to_user(axis, hw_value)
        if axis == 1:
            self.x_read.setText(f"{user_value:.3f}")
            self.x_position_spinbox.setValue(user_value)
        elif axis == 2:
            self.y_read.setText(f"{user_value:.3f}")
            self.y_position_spinbox.setValue(user_value)
        elif axis == 3:
            self.z_read.setText(f"{user_value:.3f}")
            self.z_position_spinbox.setValue(user_value)

    def _refresh_positions(self):
        for axis in (1, 2, 3):
            hw_value = self.nano.single_read_n(axis, self.nano.handle)
            self._set_axis_widgets(axis, hw_value)

    def _move_axis_absolute_user(self, axis, user_target):
        hw_target = self._clamp_hw(axis, self._user_to_hw(axis, user_target))
        #hw_target = float(user_target)
        actual_hw = self.nano.monitor_n(hw_target, axis, self.nano.handle)
        self._set_axis_widgets(axis, actual_hw)

    def _step_axis(self, axis, delta_um):
        current_hw = self.nano.single_read_n(axis, self.nano.handle)
        target_hw = self._clamp_hw(axis, current_hw + float(delta_um))
        #target_hw = current_hw + float(delta_um)
        actual_hw = self.nano.monitor_n(target_hw, axis, self.nano.handle)
        self._set_axis_widgets(axis, actual_hw)

    def _home_axes(self):
        for axis in (1, 2, 3):
            actual_hw = self.nano.monitor_n(self.axis_centers[axis], axis, self.nano.handle)
            self._set_axis_widgets(axis, actual_hw)

    def _safe_call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, 'Nano-Drive error', str(exc))
            return None
        
    def _set_edited_axes(self):
        for axis in self.edited_axes:
            if axis == 1:
                value = self.x_position_spinbox.value()
            elif axis == 2:
                value = self.y_position_spinbox.value()
            elif axis == 3:
                value = self.z_position_spinbox.value()
            self._move_axis_absolute_user(axis, value)
        self.edited_axes.clear()
        self._refresh_positions()  # Ensure widgets reflect actual position after move

    def closeEvent(self, event):
        try:
            if hasattr(self.nano, 'release_handle') and hasattr(self.nano, 'handle'):
                self.nano.release_handle(self.nano.handle)
                print('Nano-Drive handle released.')
        except Exception as e:
            print(f'Error releasing Nano-Drive handle: {e}')
        super().closeEvent(event)


        