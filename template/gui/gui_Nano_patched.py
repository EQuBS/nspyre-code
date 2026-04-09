"""
Qt GUI for the Nano-3D200FT from MadCity Labs.

Rolando A. Fimbres Grijalva 6/12/2025
Patched for safer motion handling.
"""
from pyqtgraph.Qt import QtWidgets
from pyqtgraph import SpinBox
from MCL_Madlib_Wrapper import MCL_Nanodrive


class NanoWidget(QtWidgets.QWidget):
    """Qt widget for controlling the Nano-3D200FT from MadCity Labs."""

    def __init__(self, nano):
        super().__init__()
        self.nano = nano

        # Query the actual axis ranges from the controller instead of hard-coding 100 um.
        self.axis_min = {1: 0.0, 2: 0.0, 3: 0.0}
        self.axis_max = {
            1: float(self.nano.get_calibration(1, self.nano.handle)),
            2: float(self.nano.get_calibration(2, self.nano.handle)),
            3: float(self.nano.get_calibration(3, self.nano.handle)),
        }
        self.axis_center = {
            axis: 0.5 * (self.axis_min[axis] + self.axis_max[axis])
            for axis in (1, 2, 3)
        }

        layout = QtWidgets.QGridLayout()
        layout_row = 0

        # Create textboxes for X, Y, Z positions.
        self.x_pos_box = QtWidgets.QLineEdit()
        self.y_pos_box = QtWidgets.QLineEdit()
        self.z_pos_box = QtWidgets.QLineEdit()
        self.x_pos_box.setReadOnly(True)
        self.y_pos_box.setReadOnly(True)
        self.z_pos_box.setReadOnly(True)

        read_button = QtWidgets.QPushButton('Read Position')
        read_button.clicked.connect(
            lambda _=False: self._safe_call(self._refresh_positions)
        )

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

        # X position spinbox.
        layout.addWidget(QtWidgets.QLabel('X-Position (um)'), layout_row, 0)
        self.x_position_spinbox = SpinBox(
            value=0,
            siPrefix=False,
            bounds=(-self.axis_center[1], self.axis_center[1]),
            step=0.003,
            dec=3,
            int=False,
        )
        self.x_position_spinbox.setFixedSize(120, 30)
        self.x_position_spinbox.setValue(value=0)
        layout.addWidget(self.x_position_spinbox, layout_row, 1)

        move_xbutton = QtWidgets.QPushButton('Move')
        move_xbutton.clicked.connect(
            lambda _=False: self._safe_call(
                self._move_axis_absolute_user,
                1,
                self.x_position_spinbox.value(),
            )
        )
        layout.addWidget(move_xbutton, layout_row, 2)
        layout_row += 1

        layout.addWidget(QtWidgets.QLabel('X Step Size (um)'), layout_row, 0)
        self.x_step_size_spinbox = SpinBox(
            value=0.05,
            siPrefix=False,
            bounds=(0.000, self.axis_max[1] - self.axis_min[1]),
            step=0.003,
            dec=3,
            int=False,
        )
        self.x_step_size_spinbox.setFixedSize(120, 30)
        self.x_step_size_spinbox.setValue(value=0.05)
        layout.addWidget(self.x_step_size_spinbox, layout_row, 1)

        plus_xbutton = QtWidgets.QPushButton('+')
        plus_xbutton.clicked.connect(
            lambda _=False: self._safe_call(
                self._step_axis,
                1,
                self.x_step_size_spinbox.value(),
            )
        )
        layout.addWidget(plus_xbutton, layout_row, 2)
        plus_xbutton.setFixedSize(60, 30)

        minus_xbutton = QtWidgets.QPushButton('-')
        minus_xbutton.clicked.connect(
            lambda _=False: self._safe_call(
                self._step_axis,
                1,
                -self.x_step_size_spinbox.value(),
            )
        )
        layout.addWidget(minus_xbutton, layout_row, 3)
        minus_xbutton.setFixedSize(60, 30)
        layout_row += 1

        # Y position spinbox.
        layout.addWidget(QtWidgets.QLabel('Y-Position (um)'), layout_row, 0)
        self.y_position_spinbox = SpinBox(
            value=0,
            siPrefix=False,
            bounds=(-self.axis_center[2], self.axis_center[2]),
            step=0.003,
            dec=3,
            int=False,
        )
        self.y_position_spinbox.setFixedSize(120, 30)
        self.y_position_spinbox.setValue(value=0)
        layout.addWidget(self.y_position_spinbox, layout_row, 1)

        move_ybutton = QtWidgets.QPushButton('Move')
        move_ybutton.clicked.connect(
            lambda _=False: self._safe_call(
                self._move_axis_absolute_user,
                2,
                self.y_position_spinbox.value(),
            )
        )
        layout.addWidget(move_ybutton, layout_row, 2)
        layout_row += 1

        layout.addWidget(QtWidgets.QLabel('Y Step Size (um)'), layout_row, 0)
        self.y_step_size_spinbox = SpinBox(
            value=0.05,
            siPrefix=False,
            bounds=(0.000, self.axis_max[2] - self.axis_min[2]),
            step=0.003,
            dec=3,
            int=False,
        )
        self.y_step_size_spinbox.setFixedSize(120, 30)
        self.y_step_size_spinbox.setValue(value=0.05)
        layout.addWidget(self.y_step_size_spinbox, layout_row, 1)

        plus_ybutton = QtWidgets.QPushButton('+')
        plus_ybutton.clicked.connect(
            lambda _=False: self._safe_call(
                self._step_axis,
                2,
                self.y_step_size_spinbox.value(),
            )
        )
        layout.addWidget(plus_ybutton, layout_row, 2)
        plus_ybutton.setFixedSize(60, 30)

        minus_ybutton = QtWidgets.QPushButton('-')
        minus_ybutton.clicked.connect(
            lambda _=False: self._safe_call(
                self._step_axis,
                2,
                -self.y_step_size_spinbox.value(),
            )
        )
        layout.addWidget(minus_ybutton, layout_row, 3)
        minus_ybutton.setFixedSize(60, 30)
        layout_row += 1

        # Z position spinbox.
        layout.addWidget(QtWidgets.QLabel('Z-Position (um)'), layout_row, 0)
        self.z_position_spinbox = SpinBox(
            value=0,
            siPrefix=False,
            bounds=(-self.axis_center[3], self.axis_center[3]),
            step=0.003,
            dec=3,
            int=False,
        )
        self.z_position_spinbox.setFixedSize(120, 30)
        self.z_position_spinbox.setValue(value=0)
        layout.addWidget(self.z_position_spinbox, layout_row, 1)

        move_zbutton = QtWidgets.QPushButton('Move')
        move_zbutton.clicked.connect(
            lambda _=False: self._safe_call(
                self._move_axis_absolute_user,
                3,
                self.z_position_spinbox.value(),
            )
        )
        layout.addWidget(move_zbutton, layout_row, 2)
        layout_row += 1

        layout.addWidget(QtWidgets.QLabel('Z Step Size (um)'), layout_row, 0)
        self.z_step_size_spinbox = SpinBox(
            value=0.05,
            siPrefix=False,
            bounds=(0.000, self.axis_max[3] - self.axis_min[3]),
            step=0.003,
            dec=3,
            int=False,
        )
        self.z_step_size_spinbox.setFixedSize(120, 30)
        self.z_step_size_spinbox.setValue(value=0.05)
        layout.addWidget(self.z_step_size_spinbox, layout_row, 1)

        plus_zbutton = QtWidgets.QPushButton('+')
        plus_zbutton.clicked.connect(
            lambda _=False: self._safe_call(
                self._step_axis,
                3,
                self.z_step_size_spinbox.value(),
            )
        )
        layout.addWidget(plus_zbutton, layout_row, 2)
        plus_zbutton.setFixedSize(60, 30)

        minus_zbutton = QtWidgets.QPushButton('-')
        minus_zbutton.clicked.connect(
            lambda _=False: self._safe_call(
                self._step_axis,
                3,
                -self.z_step_size_spinbox.value(),
            )
        )
        layout.addWidget(minus_zbutton, layout_row, 3)
        minus_zbutton.setFixedSize(60, 30)
        layout_row += 1

        home_button = QtWidgets.QPushButton('Home')
        home_button.clicked.connect(lambda _=False: self._safe_call(self._home_axes))
        layout.addWidget(home_button, layout_row, 0, 1, 2)
        layout_row += 1

        self.setLayout(layout)
        self._safe_call(self._refresh_positions)

    def _hw_to_user(self, axis, hw_value):
        return float(hw_value) - self.axis_center[axis]

    def _user_to_hw(self, axis, user_value):
        return self.axis_center[axis] + float(user_value)

    def _clamp_hw(self, axis, hw_target):
        return max(self.axis_min[axis], min(float(hw_target), self.axis_max[axis]))

    def _set_axis_widgets(self, axis, hw_value):
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

    def _refresh_positions(self):
        for axis in (1, 2, 3):
            hw_value = self.nano.single_read_n(axis, self.nano.handle)
            self._set_axis_widgets(axis, hw_value)

    def _move_axis_absolute_user(self, axis, user_target):
        hw_target = self._clamp_hw(axis, self._user_to_hw(axis, user_target))
        actual_hw = self.nano.monitor_n(hw_target, axis, self.nano.handle)
        self._set_axis_widgets(axis, actual_hw)

    def _step_axis(self, axis, delta_um):
        current_hw = self.nano.single_read_n(axis, self.nano.handle)
        target_hw = self._clamp_hw(axis, current_hw + float(delta_um))
        actual_hw = self.nano.monitor_n(target_hw, axis, self.nano.handle)
        self._set_axis_widgets(axis, actual_hw)

    def _home_axes(self):
        for axis in (1, 2, 3):
            actual_hw = self.nano.monitor_n(self.axis_center[axis], axis, self.nano.handle)
            self._set_axis_widgets(axis, actual_hw)

    def _safe_call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, 'Nano-Drive error', str(exc))
            return None

    def closeEvent(self, event):
        try:
            if hasattr(self.nano, 'release_handle') and hasattr(self.nano, 'handle'):
                self.nano.release_handle(self.nano.handle)
                print('Nano-Drive handle released.')
        except Exception as e:
            print(f'Error releasing Nano-Drive handle: {e}')
        super().closeEvent(event)
