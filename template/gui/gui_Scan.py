"""
GUI for a Scanning procedure.

Rolando A. Fimbres Grijalva 6/23/2025
"""
from PyQt5.QtWidgets import QSizePolicy
from pyqtgraph.Qt import QtWidgets
from pyqtgraph import SpinBox
from MCL_Madlib_Wrapper import MCL_Nanodrive
from PyQt5.QtWidgets import QMessageBox
import numpy as np
import matplotlib.pyplot as plt
from rpyc.utils.classic import obtain # converts a remote (proxy) object into a real, local Python object so you can use it as normal in your script
from nspyre import DataSink
from nspyre import FlexLinePlotWidget
import sys
from nspyre import ExperimentWidget
from nspyre import InstrumentGateway
from nspyre import DataSource
from nspyre import StreamingList
from nspyre import DataSink, FlexLinePlotWidget
import numpy as np


sys.path.append('../experiments')

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

    def __init__(self, nano, laser_driver, pulse_streamer_driver, tagger):
        """
        Args:
            nano: The MCL Nanodrive driver.
                - handle: The handle for the MCL Nanodrive. Handle is obtained during initialization. See MCL_Madlib_Wrapper.py code line 49 for more details.
            laser: The DLnsec laser driver.
            streamer: The Swabian Pulse Streamer driver.
            tagger: The Swabian Time Tagger driver.

        """
        super().__init__(parent=None)
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
        self.pulse_streamer_driver = pulse_streamer_driver
        self.tagger = tagger

        # Following block removed for the intro of more than one instrument in the ScanWidget.
        # Rolando A. Fimbres Grijalva 6/25/2025
        """
        super().__init__()
        if nano is None or handle is None:
            self.nano = MCL_Nanodrive()
            self.handle = self.nano.init_handle()
        else:
            self.nano = nano
            self.handle = handle
        """
        # top level layout
        layout = QtWidgets.QGridLayout()
        layout_row = 0
        layout.setSpacing(2)
        layout.setContentsMargins(4, 4, 4, 4)

        #layout_row += 1

        # Create Labels for the Start/Stop and Num. of datapoints in the Scan for X, Y, Z positions.

        """
            N: Number of datapoints from the minimum to the maximum position.
            X_min: Minimum X position
            X_max: Maximum X position
            Y_min: Minimum Y position
            Y_max: Maximum Y position
            Z_min: Minimum Z position
            Z_max: Maximum Z position
        """

        # Row 0: Header Labels
        layout.addWidget(QtWidgets.QLabel(''), layout_row, 0)  # Empty label for the axis column
        layout.addWidget(QtWidgets.QLabel('Min.'), layout_row, 1)
        layout.addWidget(QtWidgets.QLabel('Max.'), layout_row, 2)
        layout.addWidget(QtWidgets.QLabel('Data Points per Axis'), layout_row, 3)
        layout_row += 1

        # Create spin boxes for all axes
        self.x_min_box = QtWidgets.QDoubleSpinBox()
        self.x_max_box = QtWidgets.QDoubleSpinBox()
        self.data_points_x = QtWidgets.QSpinBox()
        self.y_min_box = QtWidgets.QDoubleSpinBox()
        self.y_max_box = QtWidgets.QDoubleSpinBox()
        self.data_points_y = QtWidgets.QSpinBox()
        self.z_min_box = QtWidgets.QDoubleSpinBox()
        self.z_max_box = QtWidgets.QDoubleSpinBox()

        # Set size policy for compactness
        for widget in [
            self.x_min_box, self.x_max_box, self.data_points_x,
            self.y_min_box, self.y_max_box, self.data_points_y,
            self.z_min_box, self.z_max_box
        ]:
            widget.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed))

        # Row 1: X position
        layout.addWidget(QtWidgets.QLabel('X'), layout_row, 0)
        self.x_min_box.setRange(0.000, 200.000)
        self.x_min_box.setDecimals(3)
        self.x_min_box.setSingleStep(0.003)
        self.x_max_box.setRange(2.000, 200.000)
        self.x_max_box.setDecimals(3)
        self.x_max_box.setSingleStep(0.003)
        self.data_points_x.setRange(2, 70)
        layout.addWidget(self.x_min_box, layout_row, 1)
        layout.addWidget(self.x_max_box, layout_row, 2)
        layout.addWidget(self.data_points_x, layout_row, 3)
        layout_row += 1

        # Row 2: Y position
        layout.addWidget(QtWidgets.QLabel('Y'), layout_row, 0)
        self.y_min_box.setRange(0.000, 200.000)
        self.y_min_box.setDecimals(3)
        self.y_min_box.setSingleStep(0.003)
        self.y_max_box.setRange(2.000, 200.000)
        self.y_max_box.setDecimals(3)
        self.y_max_box.setSingleStep(0.003)
        self.data_points_y.setRange(2, 70)
        layout.addWidget(self.y_min_box, layout_row, 1)
        layout.addWidget(self.y_max_box, layout_row, 2)
        layout.addWidget(self.data_points_y, layout_row, 3)
        layout_row += 1

        # Row 3: Z position
        layout.addWidget(QtWidgets.QLabel('Z'), layout_row, 0)
        self.z_min_box.setRange(0.000, 200.000)
        self.z_min_box.setDecimals(3)
        self.z_min_box.setSingleStep(0.003)
        self.z_max_box.setRange(0.000, 200.000)
        self.z_max_box.setDecimals(3)
        self.z_max_box.setSingleStep(0.003)
        layout.addWidget(self.z_min_box, layout_row, 1)
        layout.addWidget(self.z_max_box, layout_row, 2)
        # If you add a data_points_z, add it here as well
        # layout.addWidget(self.data_points_z, layout_row, 3)
        layout_row += 1

        # Total Data Points 
        data_points = 2*self.data_points_x.value()*self.data_points_y.value()

        """
        I've been thinking it might be a good idea to introduce a dropdown menu to select the type of scan
        to be performed. This way, we can easily switch between different scanning modes, such as
        1) XY-Scan
        2) XYZ-Scan
        3) Custom Scan
        4) etc.
        This would allow for more flexibility and ease of use when setting up scans.

        --To be implemented in the future.--
        
        06/26/2025
        Rolando A. Fimbres Grijalva
        """
        total_x_length = self.x_max_box.value() - self.x_min_box.value()
        total_y_length = self.y_max_box.value() - self.y_min_box.value()
        scan_area = total_x_length * total_y_length

        #Step size needs to be rounded to the nearest 3nm (current units in microns)
        #round(number / 3) * 3
        # rounded_value = np.ceil(value / 0.003) * 0.003

        """
        Rolando A. Fimbres Grijalva        07/01/2025
        I introduce other ways of defining the step size.
        """
        step_x = (total_x_length / (self.data_points_x.value()-1))
        step_y = (total_y_length / (self.data_points_y.value()-1))


        step_size = np.sqrt(scan_area/data_points)
        
        # Waveform data

        x_line_for = np.arange(self.x_min_box.value(), self.x_max_box.value(), step_size)
        x_line_bac = x_line_for[::-1] # X line backward      
        

        # Start Scan Button
        start_xy = QtWidgets.QPushButton('Start XY-Scan')
        """
        Start a scan in the XY plane with the specified parameters.
        This function generates a waveform for the X and Y positions based on the
        minimum and maximum values and the number of data points specified in the
        spin boxes. It creates a zigzag pattern for the X positions while keeping
        the Y position constant for each line, alternating between forward and 
        backward sweeps across the Y range. The generated waveforms are then sent 
        to the MCL Nanodrive for execution.
        
        A clock signal needs to be set and sent to the Time Tagger to synchronize 
        the data acquisition.
        
        Data gathering functionalities from the Time Tagger needs to be added.
        
        Note: A review of the Time Tagger's API documentation is required to
        implement the data gathering functionalities. So far, we have used basic functions.
        Look at the scanning intensity tutorial as a reference on how to better implement this.
        
        06/25/2025
        Rolando A. Fimbres Grijalva
        """
        def scan_xy():

            with DataSource('Scan_data') as scan_data:

                x_wfm = [] # X waveform
                y_wfm = [] # Y waveform
                #z_wfm = [] # Z waveform

                # Prevent invalid X range
                if self.x_max_box.value() <= self.x_min_box.value():
                    QMessageBox.warning(self, "Invalid X Range", "X max must be greater than X min.")
                    return
            
                # Prevent invalid Y range
                if self.y_max_box.value() <= self.y_min_box.value():
                    QMessageBox.warning(self, "Invalid Y Range", "Y max must be greater than Y min.")
                    return

        
                y_lines = int(total_y_length/step_size)
                
                for i in range(y_lines):
                    y_pos = self.y_min_box.value() + i * step_size
                    if i % 2 == 0:
                        x_wfm.extend(x_line_for)
                    else:
                        x_wfm.extend(x_line_bac)
                    y_wfm.extend([y_pos] * len(x_line_for)) 
                
                x_wfm = np.array(x_wfm, dtype=np.float64)
                y_wfm = np.array(y_wfm, dtype=np.float64)
                #data_points = len(x_wfm) + len(y_wfm)
                
                duration = 0.1 # Time in milliseconds between data points (from 0.1ms to 5ms)
                iter = 1 # Number of iterations for the waveform. We can add a SpinBox to change this value in the future.
                self.nano.wfma_setup(x_wfm, y_wfm, None, data_points, duration, iter, self.nano.handle)
                print(x_wfm)
                self.nano.iss_bind_clock_to_axis(1 , 2, 6, self.nano.handle)  # Bind clock to Waveform Write 
                self.nano.wfma_trigger(self.nano.handle)

                #self.tagger.start_countrate([4], duration * 1000)  # Start countrate measurement on channel 4  
                self.tagger.start_counter([4], 1e8, data_points, data_points*1e8)
                
                # We create a measurment object for intensity scanning.
                pix_start_ch = 4 # Rising edge on input channel 4
                pix_end_ch = -4 # Falling edge on input channel 4
                spcm_ch = 3 # Channel for the SPCM
                self.tagger.set_trigger_level(spcm_ch, 1.1)  # Set trigger level for SPCM channel
                self.tagger.set_trigger_level(pix_start_ch, 2.5)  # Set trigger level for pixel start channel
                nx_pix = self.data_points_x.value()  # Number of pixels in X direction
                ny_pix = self.data_points_y.value()  # Number of pixels in Y direction
                npix = nx_pix * ny_pix
                cbm = self.tagger.count_BM(spcm_ch, pix_start_ch, pix_end_ch, npix)
                #counts_remote = cbm.getData()  # Get the counts data
                counts = obtain(cbm) # Convert remote data to local numpy array
                # Push scan data to the data server
                scan_data.push({
                    'title': 'XY Scan',    
                    'xLabel': 'X (um)',
                    'yLabel': 'Y (um)',
                    'zLabel': 'Counts',
                    'datasets': {
                        'xSteps': x_wfm,
                        'ySteps': y_wfm,
                        'ScanCounts': counts
                    }
                })

                # For immediate visualization with matplotlib (as before):
                img = np.reshape(counts, (nx_pix, ny_pix))  # Reshape counts to image format
                plt.figure()
                plt.imshow(img, cmap='hot', origin='lower', aspect='auto')
                plt.xlabel('X pixel')
                plt.ylabel('Y pixel')
                plt.title('Scan Counts')
                plt.colorbar(label='Counts')
                plt.show()
            
        start_xy.clicked.connect(scan_xy)
        layout.addWidget(start_xy, layout_row, 0)
        
        # Add stretch to keep widgets at the top
        
        self.setLayout(layout)
        #layout.setRowStretch(layout_row, 1)
        

        """
        A mechanism that would resemble the 'sigvstime_run' function's process of pushing data to the
        data server must be implemented here.
        This would allow the data to be sent to the server for further processing or storage.

        --To be implemented in the future.--

        06/26/2025
        Rolando A. Fimbres Grijalva
        """
    def visualize_scan_data(self):
        """
        Visualize scan data using DataSink and FlexLinePlotWidget.
        This function pulls the latest scan data from the data server and displays it.
        """
        with DataSink('Scan_data') as sink:
            data = sink.pull()
            if not data or 'datasets' not in data:
                QMessageBox.warning(self, "No Data", "No scan data available to visualize.")
                return
            x = np.array(data['datasets']['xSteps'])
            y = np.array(data['datasets']['ySteps'])
            counts = np.array(data['datasets']['ScanCounts'])
            nx_pix = self.data_points_x.value()
            ny_pix = self.data_points_y.value()
            if counts.size != nx_pix * ny_pix:
                QMessageBox.warning(self, "Data Error", "Scan data shape does not match scan parameters.")
                return
            img = np.reshape(counts, (nx_pix, ny_pix))
            # Display using FlexLinePlotWidget as an image
            plot_widget = FlexLinePlotWidget()
            plot_widget.setWindowTitle('Scan Counts Visualization')
            plot_widget.imshow(
                img,
                x=np.linspace(self.x_min_box.value(), self.x_max_box.value(), nx_pix),
                y=np.linspace(self.y_min_box.value(), self.y_max_box.value(), ny_pix),
                xlabel='X (um)', ylabel='Y (um)', title='Scan Counts'
            )
            plot_widget.show()

        layout_row += 1

        

    def closeEvent(self, event):
        try:
            if hasattr(self.nano, 'dll') and hasattr(self.nano, 'handle'):
                self.nano.dll.MCL_ReleaseHandle(self.nano.handle)
                print("Nano-Drive handle released.")
        except Exception as e:
            print(f"Error releasing Nano-Drive handle: {e}")
        super().closeEvent(event)