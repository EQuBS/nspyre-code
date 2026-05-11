"""
Qt GUI for the MCL Nano-3D200FT through Micro-Manager/Pycro-Manager.

This version does not use MCL_Madlib_Wrapper.py. Micro-Manager owns the MCL
stage through the MCL_NanoDrive device adapter, while this GUI talks to the
Micro-Manager Core through pycromanager.
"""
from __future__ import annotations

from pyqtgraph.Qt import QtWidgets

# Use the same Qt binding selected by pyqtgraph/nspyre. Do not import PyQt6
# directly here; mixing PyQt5 and PyQt6 in the same app can produce thread and
# ownership warnings around Qt widgets.
QApplication = QtWidgets.QApplication
QDoubleSpinBox = QtWidgets.QDoubleSpinBox
QGridLayout = QtWidgets.QGridLayout
QGroupBox = QtWidgets.QGroupBox
QHBoxLayout = QtWidgets.QHBoxLayout
QLabel = QtWidgets.QLabel
QLineEdit = QtWidgets.QLineEdit
QMessageBox = QtWidgets.QMessageBox
QPushButton = QtWidgets.QPushButton

try:
    from template.drivers.MCL_MicroManager_Wrapper_mm import MCLStageConfig, MicroManagerMCLStage
except Exception:
    from template.drivers.MCL_MicroManager_Wrapper_mm import MCLStageConfig, MicroManagerMCLStage


class NanoWidget(QtWidgets.QWidget):
    """Qt widget for controlling the Nano-3D200FT through Micro-Manager."""

    def __init__(self, stage=None, stage_range_um=200.0, user_origin_mode="center"):
        super().__init__()
        if stage is None:
            config = MCLStageConfig(
                axis_max_um=(float(stage_range_um), float(stage_range_um), float(stage_range_um)),
                user_origin_mode=user_origin_mode,
            )
            stage = MicroManagerMCLStage(config=config)
        self.stage = stage
        self.edited_axes = set()

        master_layout = QHBoxLayout()
        nanostage_group = QGroupBox("Nanostage Controls - Micro-Manager MCL")
        grid = QGridLayout()
        grid.setVerticalSpacing(2)
        grid.setContentsMargins(5, 5, 5, 5)

        grid.addWidget(QLabel("X (um)"), 0, 0)
        self.x_read = QLineEdit()
        self.x_read.setReadOnly(True)
        grid.addWidget(self.x_read, 0, 1)

        grid.addWidget(QLabel("Y (um)"), 1, 0)
        self.y_read = QLineEdit()
        self.y_read.setReadOnly(True)
        grid.addWidget(self.y_read, 1, 1)

        grid.addWidget(QLabel("Z (um)"), 2, 0)
        self.z_read = QLineEdit()
        self.z_read.setReadOnly(True)
        grid.addWidget(self.z_read, 2, 1)

        read_btn = QPushButton("Read")
        grid.addWidget(read_btn, 0, 2, 3, 1)

        grid.addWidget(QLabel("<b>Step Size</b>"), 3, 0)
        self.step_val = QDoubleSpinBox()
        self.step_val.setValue(0.025)
        self.step_val.setRange(0.001, 25.000)
        self.step_val.setSingleStep(0.003)
        self.step_val.setDecimals(3)
        grid.addWidget(self.step_val, 3, 1, 1, 2)

        grid.addWidget(QLabel("X"), 4, 0)
        x_plus = QPushButton("+")
        x_minus = QPushButton("-")
        grid.addWidget(x_plus, 4, 1)
        grid.addWidget(x_minus, 4, 2)

        grid.addWidget(QLabel("Y"), 5, 0)
        y_plus = QPushButton("+")
        y_minus = QPushButton("-")
        grid.addWidget(y_plus, 5, 1)
        grid.addWidget(y_minus, 5, 2)

        grid.addWidget(QLabel("Z"), 6, 0)
        z_plus = QPushButton("+")
        z_minus = QPushButton("-")
        grid.addWidget(z_plus, 6, 1)
        grid.addWidget(z_minus, 6, 2)

        grid.addWidget(QLabel("<b>Set Position</b>"), 7, 0, 1, 3)

        grid.addWidget(QLabel("X"), 8, 0)
        self.x_position_spinbox = self._make_position_spinbox(1)
        grid.addWidget(self.x_position_spinbox, 8, 1)

        grid.addWidget(QLabel("Y"), 9, 0)
        self.y_position_spinbox = self._make_position_spinbox(2)
        grid.addWidget(self.y_position_spinbox, 9, 1)

        grid.addWidget(QLabel("Z"), 10, 0)
        self.z_position_spinbox = self._make_position_spinbox(3)
        grid.addWidget(self.z_position_spinbox, 10, 1)

        set_button = QPushButton("Set")
        grid.addWidget(set_button, 8, 2, 2, 1)
        home_button = QPushButton("Home")
        grid.addWidget(home_button, 10, 2)

        status_label = QLabel(
            "Step buttons: relative single-axis requests | Core XY: MCL NanoDrive XY Stage"
        )
        grid.addWidget(status_label, 11, 0, 1, 3)
        grid.setRowStretch(12, 1)

        nanostage_group.setLayout(grid)
        master_layout.addWidget(nanostage_group)
        self.setLayout(master_layout)

        self.x_position_spinbox.editingFinished.connect(lambda: self.edited_axes.add(1))
        self.y_position_spinbox.editingFinished.connect(lambda: self.edited_axes.add(2))
        self.z_position_spinbox.editingFinished.connect(lambda: self.edited_axes.add(3))

        home_button.clicked.connect(lambda _=False: self._safe_call(self._home_axes))
        set_button.clicked.connect(lambda _=False: self._safe_call(self._set_edited_axes))
        read_btn.clicked.connect(lambda _=False: self._safe_call(self._refresh_positions, True))

        x_plus.clicked.connect(lambda _=False: self._safe_call(self._step_axis, 1, self.step_val.value()))
        x_minus.clicked.connect(lambda _=False: self._safe_call(self._step_axis, 1, -self.step_val.value()))
        y_plus.clicked.connect(lambda _=False: self._safe_call(self._step_axis, 2, self.step_val.value()))
        y_minus.clicked.connect(lambda _=False: self._safe_call(self._step_axis, 2, -self.step_val.value()))
        z_plus.clicked.connect(lambda _=False: self._safe_call(self._step_axis, 3, self.step_val.value()))
        z_minus.clicked.connect(lambda _=False: self._safe_call(self._step_axis, 3, -self.step_val.value()))

        self._safe_call(self._refresh_positions, True)

    def _make_position_spinbox(self, axis):
        low, high = self.stage.user_limits(axis)
        box = QDoubleSpinBox()
        box.setValue(0.0)
        box.setRange(float(low), float(high))
        box.setSingleStep(0.003)
        box.setDecimals(3)
        return box

    def _set_axis_widgets(self, axis, user_value):
        user_value = float(user_value)
        if axis == 1:
            self.x_read.setText(f"{user_value:.3f}")
            self.x_position_spinbox.setValue(user_value)
        elif axis == 2:
            self.y_read.setText(f"{user_value:.3f}")
            self.y_position_spinbox.setValue(user_value)
        elif axis == 3:
            self.z_read.setText(f"{user_value:.3f}")
            self.z_position_spinbox.setValue(user_value)

    def _refresh_positions(self, sync_commanded_cache=False):
        # For normal automatic refreshes after a move, do not sync the stage
        # command cache to readback.  Otherwise readback noise can become the
        # next preserved companion-axis command.  The manual Read button passes
        # sync_commanded_cache=True to recover after external/manual motion.
        if sync_commanded_cache and hasattr(self.stage, "sync_commanded_to_readback"):
            pos = self.stage.sync_commanded_to_readback()
        else:
            pos = self.stage.read_user()
        for axis in (1, 2, 3):
            self._set_axis_widgets(axis, pos[axis])

    def _move_axis_absolute_user(self, axis, user_target):
        self.stage.move_axis(axis, float(user_target), wait=True)
        self._refresh_positions(False)

    def _step_axis(self, axis, delta_um):
        self.stage.step_axis(axis, float(delta_um), wait=True)
        self._refresh_positions(False)

    def _home_axes(self):
        self.stage.home(wait=True)
        self._refresh_positions(False)

    def _set_edited_axes(self):
        targets = {}
        for axis in self.edited_axes:
            if axis == 1:
                targets[1] = self.x_position_spinbox.value()
            elif axis == 2:
                targets[2] = self.y_position_spinbox.value()
            elif axis == 3:
                targets[3] = self.z_position_spinbox.value()
        if targets:
            self.stage.move_axes(targets, wait=True)
        self.edited_axes.clear()
        self._refresh_positions(False)

    def _safe_call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            QMessageBox.critical(self, "Nano-Drive Micro-Manager error", str(exc))
            return None

    def closeEvent(self, event):
        try:
            if hasattr(self.stage, "close"):
                self.stage.close()
        except Exception as exc:
            print(f"Error closing Micro-Manager stage backend: {exc}")
        super().closeEvent(event)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    widget = NanoWidget()
    widget.show()
    if hasattr(app, "exec"):
        sys.exit(app.exec())
    sys.exit(app.exec_())
