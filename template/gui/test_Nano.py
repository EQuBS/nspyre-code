"""
Qt GUI for the Nano-3D200FT from MadCity Labs.

Rolando A. Fimbres Grijalva 6/17/2025
"""
from pyqtgraph.Qt import QtWidgets
from pyqtgraph import SpinBox
from MCL_Madlib_Wrapper import MCL_Nanodrive 
import time

class N_test(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.nano = MCL_Nanodrive()
        self.handle = self.nano.init_handle()
