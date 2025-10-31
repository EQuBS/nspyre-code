"""
Rolando A. Fimbres Grijalva 10/29/2025

Scanning procedure based on the Safe-Scan approach (dir. XieLab_Scripts). 

"""

import numpy as np
from nspyre import HeatMapWidget
from nspyre import ExperimentWidget
from nspyre import DataSink
from nspyre import InstrumentGateway
from nspyre.gui.widgets.save import save_json
from pyqtgraph import SpinBox
from pyqtgraph.Qt import QtWidgets
import sys
sys.path.append('../experiments')
from . import spin_measurements as sm

class TwoD_Scan(ExperimentWidget):
    def __init__(self):
        # Parameters for 2D Scan
        params_config = {
            # add three checkboxes
            'Select X': {
                'display_text': 'Enable X',
                'widget': QtWidgets.QCheckBox(),  # unchecked by default
            },
            'Select Y': {
                'display_text': 'Enable Y',
                'widget': QtWidgets.QCheckBox(),
            },
            'Select Z': {
                'display_text': 'Enable Z',
                'widget': QtWidgets.QCheckBox(),
            },
            'Data_Points': {
                'display_text': 'Num. of Data Points',
                'widget': SpinBox(
                    value = 10,
                    int = True,
                    bounds = (2, 9999),
                    dec = True,
                ),
            },
            'Axis_Min_1': {
                'display_text': 'Axis 1: ',
                'widget': QtWidgets.QLineEdit('x'),
                'display_text': 'Min. Value Axis 1 (µm)',
                'widget': SpinBox(
                    value=0, 
                    siPrefix=False,
                    bounds=(-100.000, 100.000),
                    step=0.003, dec=4,
                    int=False
                ),    
            },
            'Axis_Max_1': {
                'display_text': 'Axis 1: ',
                'widget': QtWidgets.QLineEdit('x'),
                'display_text': 'Max. Value Axis 1 (µm)',
                'widget': SpinBox(
                    value=0, 
                    siPrefix=False,
                    bounds=(-100.000, 100.000),
                    step=0.003, dec=4,
                    int=False
                ),  
            },
            'Axis_Min_2': {
                'display_text': 'Axis 2: ',
                'widget': QtWidgets.QLineEdit('y'),
                'display_text': 'Min. Value Axis 2 (µm)',
                'widget': SpinBox(
                    value=0, 
                    siPrefix=False,
                    bounds=(-100.000, 100.000),
                    step=0.003, dec=4,
                    int=False
                ),
            },
            'Axis_Max_2': {
                'display_text': 'Axis 2: ',
                'widget': QtWidgets.QLineEdit('y'),
                'display_text': 'Max. Value Axis 2 (µm)',
                'widget': SpinBox(
                    value=0, 
                    siPrefix=False,
                    bounds=(-100.000, 100.000),
                    step=0.003, dec=4,
                    int=False
                ),
            },
            'Dwell_Time': {
                'display_text': 'Dwell Time (ms): ',
                'widget': SpinBox(
                    value = 5,
                    siPrefix = False,
                    bounds = (0.1, 5),
                    step=0.1, dec=1,
                ),
            },
            'Laser_Power': {
                'display_text': 'Laser Power: ',
                'widget': SpinBox(
                    value = 1.0,
                    int = True,
                    suffix = 'mW',
                    siPrefix = True,
                    bounds = (0, 100),
                    dec = True,
                    ),
            },
        }

        super().__init__(params_config,
                         sm,
                         'SpinMeasurements',
                         'Two_D_Scan_R',
                         title='2D_Scan')
        
def process_2D_Scan_data(sink: DataSink):
    # Retrieve Scan Data
    axis1 = sink.datasets['xSteps']
    axis2 = sink.datasets['ySteps']
    scan_forward = sink.datasets['Scan_Forward']
    scan_backward = sink.datasets['Scan_Backward']
    scan_averaged = sink.datasets['Scan_Averaged']

    # Visualization parameters
    extent = (axis1[0], axis1[-1], axis2[0], axis2[-1])
    vmin = min(np.min(scan_forward), np.min(scan_backward), np.min(scan_averaged))
    vmax = max(np.max(scan_forward), np.max(scan_backward), np.max(scan_averaged))
    # Create Heatmap Widgets

class ScanPlotWidget(HeatMapWidget):
    def __init__(self):
        title = '2D_Scan'
        #super().__init__(title=title, btm_label='X', lft_label='Y', colormap = 0.5)
        super().__init__(title=title, btm_label='X (um)', lft_label='Y (um)', colormap = None)


    def setup(self):
        self.sink = DataSink('2D_Scan')
        self.sink.__enter__()


    def teardown(self):
        self.sink.__exit__()


    def update(self):
        self.sink.pop() #wait for some data to be saved to sink
        self.set_data(self.sink.datasets['xSteps'], self.sink.datasets['ySteps'], self.sink.datasets['Scan_Forward'])