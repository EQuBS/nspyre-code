"""
GUI for a Scanning procedure.

Rolando A. Fimbres Grijalva 6/23/2025
"""
from PyQt5.QtWidgets import QSizePolicy
from pyqtgraph.Qt import QtWidgets
from pyqtgraph import SpinBox
#from MCL_Madlib_Wrapper import MCL_Nanodrive
from PyQt5.QtWidgets import QMessageBox
import numpy as np
import matplotlib.pyplot as plt
from rpyc.utils.classic import obtain # converts a remote (proxy) object into a real, local Python object so you can use it as normal in your script
from nspyre import DataSink, DataSource
import sys
from nspyre.gui.widgets.save import save_json
""" 
from nspyre import ExperimentWidget
from nspyre import InstrumentGateway
from nspyre import StreamingList
from nspyre import FlexLinePlotWidget 
"""
from nspyre import HeatMapWidget 
import numpy as np
import time
from TimeTagger import CHANNEL_UNUSED
from scipy.signal import convolve, deconvolve


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
        self.ps = pulse_streamer_driver
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

        # Create a QLineEdit for user input and set the placeholder text to the current date.
        self.file_path = QtWidgets.QLineEdit(self)
        self.file_path.setPlaceholderText('File Name')
        layout.addWidget(self.file_path, layout_row, 0, 1, 4)
        layout_row += 1

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
        self.data_points_z = QtWidgets.QSpinBox()

        # Set size policy for compactness
        for widget in [
            self.x_min_box, self.x_max_box, self.data_points_x,
            self.y_min_box, self.y_max_box, self.data_points_y,
            self.z_min_box, self.z_max_box, self.data_points_z
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
        self.data_points_y.setRange(2, 70) #
        layout.addWidget(self.y_min_box, layout_row, 1)
        layout.addWidget(self.y_max_box, layout_row, 2)
        layout.addWidget(self.data_points_y, layout_row, 3)
        layout_row += 1

        # Row 3: Z position
        layout.addWidget(QtWidgets.QLabel('Z'), layout_row, 0)
        self.z_min_box.setRange(0.000, 200.000)
        self.z_min_box.setDecimals(3)
        self.z_min_box.setSingleStep(0.003)
        self.z_max_box.setRange(2.000, 200.000)
        self.z_max_box.setDecimals(3)
        self.z_max_box.setSingleStep(0.003)
        self.data_points_z.setRange(2, 70)  # Set range for Z data points
        layout.addWidget(self.z_min_box, layout_row, 1)
        layout.addWidget(self.z_max_box, layout_row, 2)
        # If you add a data_points_z, add it here as well
        layout.addWidget(self.data_points_z, layout_row, 3)
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
        total_z_length = self.z_max_box.value() - self.z_min_box.value()
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
                
                # Updated by Rolando 7/7/2025

                # Axis config. from GUI
                """ The parameters define the scan area from its current position.
                Meaning, current position plus the minimum and maximum values set in the spin boxes.  
                """
                
                """ # Current position
                x_pos = self.nano.single_read_n(1, self.nano.handle)  # Read current X position
                y_pos = self.nano.single_read_n(2, self.nano.handle)  # Read current Y position

                # Movement to current position
                self.nano.single_write_n(x_pos, 1, self.nano.handle)  # Set X position
                self.nano.single_write_n(y_pos, 2, self.nano.handle)  # Set Y position """

                x_min = self.nano.single_read_n(1, self.nano.handle) + self.x_min_box.value()  # Read current X position
                x_max = x_min + self.x_max_box.value()
                y_min = self.nano.single_read_n(2, self.nano.handle) + self.y_min_box.value()  # Read current Y position
                y_max = y_min + self.y_max_box.value()
                nx_pix = self.data_points_x.value()
                ny_pix = self.data_points_y.value()

                # Range validation
                if x_max <= x_min:
                    QMessageBox.warning(self, "Invalid X Range", "X max must be greater than X min.")
                    return
            
                # Prevent invalid Y range
                if y_max <= y_min:
                    QMessageBox.warning(self, "Invalid Y Range", "Y max must be greater than Y min.")
                    return
                
                # Position arrays
                x_line_for = np.linspace(x_min, x_max, nx_pix)
                x_line_bac = x_line_for[::-1]  # Reverse the X line for backward sweep
                y_vals = np.linspace(y_min, y_max, ny_pix)

                x_wfm = [] # X waveform, original input
                y_wfm = [] # Y waveform, original input

                for i, y_pos in enumerate(y_vals):
                    if i % 2 == 0:
                        x_wfm.extend(x_line_for)
                    else:
                        x_wfm.extend(x_line_bac)
                    y_wfm.extend([y_pos] * nx_pix)  # Repeat Y

                x_wfm = np.array(x_wfm, dtype=np.float64)
                y_wfm = np.array(y_wfm, dtype=np.float64)
                data_points = len(x_wfm) # Number of data points in the x-waveform

                # Timing and iteration
                duration = 5  # Time in milliseconds between data points (from 0.1ms to 5ms)
                iter = 1  # Number of iterations for the waveform. We can add a SpinBox to change this value in the future.

                # Time Tagger config.
                #self.tagger.start_counter([4], 1e8, data_points, data_points * 1e8)  # Start counter on channel 4
                pix_start_ch = 4
                #pix_end_ch = -4
                spcm_ch = 3 # eroaern

                npix = nx_pix * ny_pix
                print("Number of pixels:", npix)

                # Create tagger for synchronized measurements
                sync = self.tagger.synchro() #"""change"""

                # Trigger levels on TT
                self.tagger.set_trigger_level(spcm_ch, 1.0) # Sets the SPCM trigger level at 1.1 V.
                self.tagger.set_trigger_level(pix_start_ch, 1.2) # Sets the MCL's controller trigger level at 2.5 V.

                # Send waveform to the MCL Nanodrive
                """ The wfma_setup() and wfma_trigger&read are used once in order to gather the necessary data to 
                adjust the original input waveform, through deconvolution, and use the result for the REAL scan.
                """
                self.nano.wfma_setup(x_wfm, y_wfm, None, data_points, duration, iter, self.nano.handle)
                read_wfm1 = self.nano.wfma_trigger_and_read(self.nano.handle)  # Read the waveform back from the MCL Nanodrive
                original_output = np.ctypeslib.as_array(read_wfm1)  # Convert the read waveform to a numpy array
                x_out = original_output[0] # Original X output
                y_out = original_output[1] # Original Y output

                # I make use of the adjust input function to adjust the input waveform. 
                x_corrected = self.adj_wfm("x", x_out, x_wfm)
                y_corrected = self.adj_wfm("y", y_out, y_wfm)

                """ I make use of the NEW corrected waveforms to run the REAL Scan. In summary 
                I'll use wfma_setup(), and wfma_trigger_and_read() again. I need to read the 
                waveform for a performance verification test at the end of the scan.
                """
                self.nano.wfma_setup(x_corrected, y_corrected, None, data_points, duration, iter, self.nano.handle)
                self.nano.iss_bind_clock_to_axis(1, 2, 1, self.nano.handle)  # Bind clock to X-Axis, Changed 7/18/2025 
                self.nano.wfma_trigger(self.nano.handle)

                # Read output waveform after adjustment
                #final_read = self.nano.wfma_read(self.nano.handle)

                # Counting events
                self.tagger.start_cbm(tagger=sync, click_channel=spcm_ch, begin_channel=pix_start_ch, end_channel=CHANNEL_UNUSED, n_values= npix)
                self.tagger.start_counter(tagger=sync, channels=[spcm_ch, pix_start_ch], binwidth=duration*1e9, n_values=npix, measurement_duration=npix*(duration*1e9))
                self.tagger.start_countrate(tagger=sync, channels=[spcm_ch, pix_start_ch], measurement_duration=npix*(duration*1e9))  # 100 values, 10ns resolution
                
                #print("Triggered scan with", data_points, "points.")

                # StartFor and WaitUntilFinished synchronized measurements
                self.tagger.sync_sFor(data_points*duration*1e9) #"""change # duration in ps """
                self.tagger.sync_wait() # """change # Start synchronized measurement for the specified duration in seconds"""

                cbm_remote = self.tagger.count_BM() # getData() for CountBetweenMarkers
                # Wait for a moment to allow TTL pulses to start
                #time.sleep(0.5)

                """ # Start countrate on channels 3 (SPCM) and 4 (Pixel Clock)"""
                #self.tagger.start_countrate([3, 4], (nx_pix*ny_pix)*(duration*1e9))  # or use your constants if defined
                #time.sleep(1)  # Let it collect for a second
                #counts = self.tagger.get_countrate_data()
                #print("Tagger Count Rates (Hz):", counts) 
                
                
                #time.sleep(npix*(duration*1e-3) + 0.2)
                cbm = obtain(cbm_remote)
                
                # Troubleshooting
                print("CBM shape:", cbm.shape)
                print("CBM max:", np.max(cbm))
                print("CBM min:", np.min(cbm))
                print("CBM data:", cbm, "Sum of counts:", np.sum(cbm))

                # Debug step ###########################
                #time.sleep(0.1)
                spcm_counts = self.tagger.get_counter_data() # getData() for SPCM Counter and TTLs
                spcm_rate = self.tagger.get_countrate_data() # getData() for SPCM Count Rate
                print("Raw SPCM counter:", spcm_counts)
                print("SPCM count rate:", spcm_rate)
                
                spcm_c = obtain(spcm_counts)  # Convert remote data to local numpy array
                # Push data to data server
                scan_data.push({
                    'title': 'XY Scan',    
                    'xLabel': 'X (um)',
                    'yLabel': 'Y (um)',
                    'zLabel': 'Counts',
                    'datasets': {
                        'xSteps': x_wfm,
                        'ySteps': y_wfm,
                        'ScanCounts': cbm
                    }
                }) 

                # Display scan result
                img = np.reshape(cbm, (ny_pix, nx_pix))
                plt.figure()
                plt.imshow(
                    img, 
                    cmap='hot', 
                    origin='lower',
                    aspect='auto',
                    extent=[x_min, x_max, y_min, y_max]
                )
                plt.xlabel('X (µm)')
                plt.ylabel('Y (µm)')
                plt.title('Scan Counts')
                plt.colorbar(label='Counts')
                plt.show()

                # Check for accuracy of the NanoDrive's positioning
                #QMessageBox.information(self, f"Scan completed successfully.\n{self.print_avg_percentage_error(final_read[0], x_wfm, 'X-axis')}\n{self.print_avg_percentage_error(final_read[1], y_wfm, 'Y-axis')}.")

                """
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
                
                duration = 5 # Time in milliseconds between data points (from 0.1ms to 5ms)
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
                """
            
        start_xy.clicked.connect(scan_xy)
        layout.addWidget(start_xy, layout_row, 0)

        layout_row += 1

        # Start Scan Button
        start_xz = QtWidgets.QPushButton('Start XZ-Scan')
        """
        Start a scan in the XZ plane with the specified parameters.
        This function generates a waveform for the X and Z positions based on the
        minimum and maximum values and the number of data points specified in the
        spin boxes. It creates a zigzag pattern for the X positions while keeping
        the Z position constant for each line, alternating between forward and
        backward sweeps across the Z range. The generated waveforms are then sent
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

        
        """
        # Add an export button.
        self.export_button = QtWidgets.QPushButton('Export', self)
        layout.addWidget(self.export_button)
        self.export_button.clicked.connect(self.handle_export) """

        def scan_xz():

            with DataSource('XZ Scan') as scan_data:
                
                # Updated by Rolando 7/7/2025

                # Axis config. from GUI
                """ The parameters define the scan area from its current position.
                Meaning, current position plus the minimum and maximum values set in the spin boxes.  
                """
                
                """ # Current position
                x_pos = self.nano.single_read_n(1, self.nano.handle)  # Read current X position
                y_pos = self.nano.single_read_n(2, self.nano.handle)  # Read current Y position

                # Movement to current position
                self.nano.single_write_n(x_pos, 1, self.nano.handle)  # Set X position
                self.nano.single_write_n(y_pos, 2, self.nano.handle)  # Set Y position """

                x_min = self.nano.single_read_n(1, self.nano.handle) + self.x_min_box.value()  # Read current X position
                x_max = x_min + self.x_max_box.value()
                z_min = self.nano.single_read_n(3, self.nano.handle) + self.z_min_box.value()  # Read current Z position
                z_max = z_min + self.z_max_box.value()
                nx_pix = self.data_points_x.value()
                nz_pix = self.data_points_z.value()

                # Range validation
                if x_max <= x_min:
                    QMessageBox.warning(self, "Invalid X Range", "X max must be greater than X min.")
                    return

                # Prevent invalid Z range
                if z_max <= z_min:
                    QMessageBox.warning(self, "Invalid Z Range", "Z max must be greater than Z min.")
                    return
                
                # Position arrays
                x_line_for = np.linspace(x_min, x_max, nx_pix)
                x_line_bac = x_line_for[::-1]  # Reverse the X line for backward sweep
                z_vals = np.linspace(z_min, z_max, nz_pix)

                x_wfm = [] # X waveform
                z_wfm = [] # Z waveform

                for i, z_pos in enumerate(z_vals):
                    if i % 2 == 0:
                        x_wfm.extend(x_line_for)
                    else:
                        x_wfm.extend(x_line_bac)
                    z_wfm.extend([z_pos] * nx_pix)  # Repeat Z

                x_wfm = np.array(x_wfm, dtype=np.float64)
                z_wfm = np.array(z_wfm, dtype=np.float64)
                data_points = len(x_wfm) # Number of data points in the x-waveform

                # Timing and iteration
                duration = 5  # Time in milliseconds between data points (from 0.1ms to 5ms)
                iter = 1  # Number of iterations for the waveform. We can add a SpinBox to change this value in the future.

                # Time Tagger config.
                #self.tagger.start_counter([4], 1e8, data_points, data_points * 1e8)  # Start counter on channel 4
                pix_start_ch = 4
                #pix_end_ch = -4
                spcm_ch = 3 # eroaern

                npix = nx_pix * nz_pix
                print("Number of pixels:", npix)

                # Create tagger for synchronized measurements
                sync = self.tagger.synchro() #"""change"""

                # Trigger levels on TT
                self.tagger.set_trigger_level(spcm_ch, 1.0) # Sets the SPCM trigger level at 1.1 V.
                self.tagger.set_trigger_level(pix_start_ch, 1.2) # Sets the MCL's controller trigger level at 2.5 V.

                # Waveform setup for calibration
                self.nano.wfma_setup(x_wfm, None, z_wfm, data_points, duration, iter, self.nano.handle)
                read_wfm1 = self.nano.wfma_trigger_and_read(self.nano.handle)
                original_output = np.ctypeslib.as_array(read_wfm1)  # Convert the read waveform to a numpy array
                x_out = original_output[0] # Original X output
                z_out = original_output[1] # Original Z output

                # Adjusted waveforms
                x_corrected = self.adj_wfm("x", x_out, x_wfm)
                z_corrected = self.adj_wfm("z", z_out, z_wfm)

                # Send waveform to the MCL Nanodrive
                self.nano.wfma_setup(x_corrected, None, z_corrected, data_points, duration, iter, self.nano.handle)
                self.nano.iss_bind_clock_to_axis(1, 2, 1, self.nano.handle)  # Bind clock to WRITE, Changed 7/24/2025
                #self.nano.wfma_trigger(self.nano.handle)
                
                # Counting events
                self.tagger.start_cbm(tagger=sync, click_channel=spcm_ch, begin_channel=pix_start_ch, end_channel=CHANNEL_UNUSED, n_values= npix)
                self.tagger.start_counter(tagger=sync, channels=[spcm_ch, pix_start_ch], binwidth=duration*1e9, n_values=npix, measurement_duration=npix*(duration*1e9))
                self.tagger.start_countrate(tagger=sync, channels=[spcm_ch, pix_start_ch], measurement_duration=npix*(duration*1e9))  # 100 values, 10ns resolution
                
                #print("Triggered scan with", data_points, "points.")
                self.nano.wfma_trigger(self.nano.handle)

                # StartFor and WaitUntilFinished synchronized measurements
                self.tagger.sync_sFor(data_points*duration*1e9) #"""change # duration in ps """
                self.tagger.sync_wait() # """change # Start synchronized measurement for the specified duration in seconds"""

                cbm_remote = self.tagger.count_BM() # getData() for CountBetweenMarkers
                # Wait for a moment to allow TTL pulses to start
                #time.sleep(0.5)

                """ # Start countrate on channels 3 (SPCM) and 4 (Pixel Clock)"""
                #self.tagger.start_countrate([3, 4], (nx_pix*ny_pix)*(duration*1e9))  # or use your constants if defined
                #time.sleep(1)  # Let it collect for a second
                #counts = self.tagger.get_countrate_data()
                #print("Tagger Count Rates (Hz):", counts) 
                
                
                #time.sleep(npix*(duration*1e-3) + 0.2)
                cbm = obtain(cbm_remote)
                
                # Troubleshooting
                print("CBM shape:", cbm.shape)
                print("CBM max:", np.max(cbm))
                print("CBM min:", np.min(cbm))
                print("CBM data:", cbm, "Sum of counts:", np.sum(cbm))

                # Debug step ###########################
                #time.sleep(0.1)
                spcm_counts = self.tagger.get_counter_data() # getData() for SPCM Counter and TTLs
                spcm_rate = self.tagger.get_countrate_data() # getData() for SPCM Count Rate
                print("Raw SPCM counter:", spcm_counts)
                print("SPCM count rate:", spcm_rate)

                print("X-array length:", len(x_wfm))
                print("Y-array length:", len(z_wfm))

                spcm_c = obtain(spcm_counts)  # Convert remote data to local numpy array
                # Push data to data server

                img = np.reshape(cbm, (nz_pix, nx_pix))  # Reshape counts to image format

                # 7/25/2025  
                # I didnt used the adjusted values, just x_wfm and z_wfm. The reason is arrays not matching. I'll fix that later.
                scan_data.push({
                    'title': 'XZ Scan',    
                    'xLabel': 'X (µm)',
                    'yLabel': 'Z (µm)',
                    'zLabel': 'Counts',
                    'datasets': {
                        'xSteps': x_wfm,
                        'ySteps': z_wfm,
                        'ScanCounts': img
                    }
                }) 
                

                # Display scan result
                #img = np.reshape(spcm_c[0], (nz_pix, nx_pix))

                """ # Fix zigzag visualization
                for i in range(1, nz_pix, 2):
                    img[i] = img[i][::-1] """

                """ plt.figure()
                plt.imshow(
                    img, 
                    cmap='hot', 
                    origin='lower',
                    aspect='auto',
                    extent=[x_min, x_max, z_min, z_max]
                )
                plt.xlabel('X (µm)')
                plt.ylabel('Z (µm)')
                plt.title('Scan Counts')
                plt.colorbar(label='Counts')
                plt.show()
 """

        start_xz.clicked.connect(scan_xz)
        layout.addWidget(start_xz, layout_row, 0)

        # Add stretch to keep widgets at the top
        
        # Gate (SPCM) on button
        gate_on_button = QtWidgets.QPushButton('Gate/Laser On ')
        gate_on_button.clicked.connect(lambda: self.ps.gate_on())
        layout.addWidget(gate_on_button, layout_row, 1)
        # Gate (SPCM) off button
        gate_off_button = QtWidgets.QPushButton('Gate/Laser Off')
        gate_off_button.clicked.connect(lambda: self.ps.gate_off())
        layout.addWidget(gate_off_button, layout_row, 2)
        """  # Laser trigger button
        gate_off_button = QtWidgets.QPushButton('Laser Trigger')
        gate_off_button.clicked.connect(lambda: self.ps.laser_on())
        layout.addWidget(gate_off_button, layout_row, 3) """

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

    # Function to adjust input waveform. Rolando 7/24/2025
    def adj_wfm(self, axis, output_wfm, input_wfm):
        """ This function assumes the target/ideal waveform has been defined.   
            is equal to the input waveform set into the NanoDrive. 
            A time-domain deconvolution is performed.
            ------------------------------------------
            Args:
                axis [str]: The axis of the waveform being adjusted ("x", "y", or "z").
                output_wfm [np.ndarray]: The waveform obtained from wfma_setup() after a trigger_and_read().
                input_wfm [np.ndarray]: The waveform set into the NanoDrive, through wfma_setup().
        """
        # STEP 1: The system's impulse response (h[n]) is estimated:
        try:
            h_est, _ = deconvolve(output_wfm, input_wfm)
        except Exception as e:
            raise RuntimeError(f"Impulse response estimation failed: {e}")
        
        # STEP 2: We deconvolve the target (input) with the system's response to compute the corrected waveform.
        try:
            corrected_input, _ = deconvolve(input_wfm, h_est)
        except Exception as e:
            raise RuntimeError(f"Corrected input computation failed: {e}") 
        
        # STEP 3: We clip the corrected waveform according to the axis limits.
        axis_bounds = {
            'x': (self.x_min_box.value(), self.x_max_box.value()),
            'y': (self.y_min_box.value(), self.y_max_box.value()),
            'z': (self.z_min_box.value(), self.z_max_box.value())
        }
        if axis not in axis_bounds:
            raise ValueError(f"Invalid axis '{axis}' specified. Valid axes are 'x', 'y', or 'z'.")
        min_val, max_val = axis_bounds[axis]
        corrected_input = np.clip(corrected_input, min_val, max_val)
        
        # STEP 4: Return the corrected waveform.
        return corrected_input

    # Function to print the average percentual error between the input_wfm and corrected_input.
    def print_avg_percentage_error(self, corrected_input: np.ndarray, input_wfm: np.ndarray, label: str = ""):
        """
        Calculates and prints the average percentage error between a corrected waveform
        and the desired target waveform.

        Args:
            corrected_input (np.ndarray): The waveform computed to compensate system distortion.
            input_wfm (np.ndarray): The desired or theoretical waveform.
            label (str): Optional string to label the output (e.g., "X-axis").
        """
        if len(corrected_input) != len(input_wfm):
            raise ValueError("Waveforms must be the same length.")

        abs_diff = np.abs(corrected_input - input_wfm)
        with np.errstate(divide='ignore', invalid='ignore'):
            percentage_error = np.where(input_wfm != 0, ((abs_diff / np.abs(input_wfm)) * 100), 0)

        avg_error = np.mean(percentage_error)
        max_error = np.max(percentage_error)

        label_str = f"{label}: " if label else ""
        print(f"{label_str}Average % Error: {avg_error:.5f}%  |  Max % Error: {max_error:.5f}%")

    """ def visualize_scan_data(self):
        """
        #Visualize scan data using DataSink and FlexLinePlotWidget.
        #This function pulls the latest scan data from the data server and displays it.
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

        layout_row += 1 """        
    
    def export_data(self):
        sink = DataSink('XZ Scan')
        sink.start()
        sink.pop()
        data = sink.data.get('datasets')
        # Retrieve the text from the QLineEdit.
        file_path_str = "C:\\Users\\XieLab\\Documents\\Confocal_System\\Exp_Nspyre" + self.file_path.text()
        # Use the obtained file path to save data.
        save_json(file_path_str, data)
        print("✅ Data Exported to ", file_path_str)

    def closeEvent(self, event):
        try:
            if hasattr(self.nano, 'dll') and hasattr(self.nano, 'handle'):
                self.nano.dll.MCL_ReleaseHandle(self.nano.handle)
                print("Nano-Drive handle released.")
        except Exception as e:
            print(f"Error releasing Nano-Drive handle: {e}")
        super().closeEvent(event)

class ScanPlotWidget(HeatMapWidget):
    def __init__(self):
        title = 'XZ Scan'
        super().__init__(title=title, btm_label="X (µm)", lft_label="Y (µm)", colormap=None)

    def setup(self):
        self.sink = DataSink('XZ Scan')
        self.sink.__enter__()


    def teardown(self):
        self.sink.__exit__()


    def update(self):
        self.sink.pop() #wait for some data to be saved to sink
        self.set_data(self.sink.datasets['xSteps'], self.sink.datasets['ySteps'], self.sink.datasets['ScanCounts'])

"""
7/25/2025
Rolando A. Fimbres Grijalva

Implementation of the HeatmapWidget for the XZ Scan. I needed to make the weird reshape,
the plotting widget required:
1) 1D array for X steps
2) 1D array for Y steps
3) 2D array for scan counts (the reason I reshaped from the 1D we get from the Time Tagger).

This is TEMPORARY and will be changed.

"""