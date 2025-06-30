"""
GUI for a Scanning procedure.

Rolando A. Fimbres Grijalva 6/23/2025
"""
from pyqtgraph.Qt import QtWidgets
from pyqtgraph import SpinBox
from MCL_Madlib_Wrapper import MCL_Nanodrive
from PyQt5.QtWidgets import QMessageBox
import numpy as np
import matplotlib.pyplot as plt
from rpyc.utils.classic import obtain # converts a remote (proxy) object into a real, local Python object so you can use it as normal in your script

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

    def __init__(self, nano, handle, laser_driver, pulse_streamer_driver, tagger):
        """
        Args:
            nano: The MCL Nanodrive driver.
            handle: The handle for the MCL Nanodrive.
            laser: The DLnsec laser driver.
            streamer: The Swabian Pulse Streamer driver.
            tagger: The Swabian Time Tagger driver.

        """
        super().__init__(parent=None)
        self.nano = nano
        self.handle = handle
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

        # Waveform data

        x_line_for = np.linspace(self.x_min_box.value(), self.x_max_box.value(), self.x_n_box.value())
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

            x_wfm = [] # X waveform
            y_wfm = [] # Y waveform
            #z_wfm = [] # Z waveform
            step_x = (self.x_max_box.value() - self.x_min_box.value()) / (self.x_n_box.value() - 1)
            if self.y_n_box.value() <= 1:
                QMessageBox.warning(self, "Invalid Y N", "Number of Y points (N) must be greater than 1.")
                return
            step_y = (self.y_max_box.value() - self.y_min_box.value()) / (self.y_n_box.value() - 1)
            if step_y == 0:
                QMessageBox.warning(self, "Invalid Y Range", "Y max and Y min must be different.")
                return
            y_lines = int((self.y_max_box.value() - self.y_min_box.value()) / step_y) + 1
            
            for i in range(y_lines):
                y_pos = self.y_min_box.value() + i*(self.y_max_box.value() - self.y_min_box.value())/(y_lines - 1)
                if i % 2 == 0:
                    x_wfm.extend(x_line_for)
                else:
                    x_wfm.extend(x_line_bac)
                y_wfm.extend([y_pos] * (self.x_n_box.value()-1))
            
            x_wfm = np.array(x_wfm, dtype=np.float64)
            y_wfm = np.array(y_wfm, dtype=np.float64)
            data_points = len(x_wfm) + len(y_wfm)
            
            if data_points >= 10000:
                QMessageBox.warning(self, "Warning", "Too many data points. Please reduce the number of points.")
                return
            
            duration = 2 # Time in milliseconds between data points (from 0.1ms to 5ms)
            iter = 1 # Number of iterations for the waveform. We can add a SpinBox to change this value in the future.
            self.nano.wfma_setup(x_wfm, y_wfm, None, data_points, duration, iter, self.handle)
            print(x_wfm)
            self.nano.iss_bind_clock_to_axis(1 , 4, 6, self.handle)  # Bind clock to Waveform Write 
            self.nano.wfma_trigger(self.handle)
            
            # We create a measurment object for intensity scanning.
            pix_start_ch = 4 # Rising edge on input channel 4
            pix_end_ch = -4 # Falling edge on input channel 4
            spcm_ch = 3 # Channel for the SPCM
            self.tagger.set_trigger_level(spcm_ch, 1.1)  # Set trigger level for SPCM channel
            self.tagger.set_trigger_level(pix_start_ch, 2.5)  # Set trigger level for pixel start channel
            nx_pix = self.x_n_box.value()
            ny_pix = self.y_n_box.value()
            npix = nx_pix * ny_pix
            cbm = self.tagger.count_BM(spcm_ch, pix_start_ch, pix_end_ch, npix)
            counts_remote = cbm.getData()  # Get the counts data
            counts = obtain(counts_remote) # Convert remote data to local numpy array
            img = np.reshape(counts, nx_pix, ny_pix)  # Reshape counts to image format
            plt.figure()
            plt.imshow(img, cmap='hot', origin='lower', aspect='auto')
            plt.xlabel('X pixel')
            plt.ylabel('Y pixel')
            plt.title('Scan Counts')
            plt.colorbar(label='Counts')
            plt.show()
            #self.tagger.start_countrate([4], duration * 1000)  # Start countrate measurement on channel 4  
            self.tagger.start_counter([4], duration, data_points, data_points*duration)

        start_xy.clicked.connect(scan_xy)
        layout.addWidget(start_xy, layout_row, 0)

        """
        A mechanism that would resemble the 'sigvstime_run' function's process of pushing data to the
        data server must be implemented here.
        This would allow the data to be sent to the server for further processing or storage.

        --To be implemented in the future.--

        06/26/2025
        Rolando A. Fimbres Grijalva
        """

        layout_row += 1

        # Add stretch to keep widgets at the top
        layout.setRowStretch(layout_row, 1)

        self.setLayout(layout)

    def closeEvent(self, event):
        try:
            if hasattr(self.nano, 'dll') and hasattr(self, 'handle'):
                self.nano.dll.MCL_ReleaseHandle(self.handle)
                print("Nano-Drive handle released.")
        except Exception as e:
            print(f"Error releasing Nano-Drive handle: {e}")
        super().closeEvent(event)