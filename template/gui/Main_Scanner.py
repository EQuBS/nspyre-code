"""
Rolando A. Fimbres G. 7/29/2025
This script contains the functions required for our instruments to perform a scan.
Initial parameter data are supplied (dictionaries) so these methods can be used. Results will then
be 'pushed-and-sank' in order to be displayed by the GUI through plots.
"""

from pyqtgraph.Qt import QtWidgets
from PyQt5.QtWidgets import QMessageBox
import numpy as np
import matplotlib.pyplot as plt
from rpyc.utils.classic import obtain
from nspyre import DataSink, DataSource
import sys
from nspyre.gui.widgets.save import save_json
from nspyre import HeatMapWidget 
import numpy as np
# import time
from TimeTagger import CHANNEL_UNUSED
from scipy.signal import convolve, deconvolve
#import template.gui.gui_ScanXY as M
from nspyre import InstrumentGateway

class MainScanner:
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
    
    def scan_xz(self, **kwargs):
        with DataSource('XZ Scan') as scanXZ_data:

            x_min = kwargs['x-initial'] + 100
            x_max = kwargs['x-final'] + 100
            x_dpoints = kwargs['x_data-points']
            z_min = kwargs['z-initial'] + 100
            z_max = kwargs['z-final'] + 100
            z_dpoints = kwargs['z_data-points']

            # Position arrays
            x_line_for = np.linspace(x_min, x_max, x_dpoints)
            x_line_bac = x_line_for[::-1]
            z_vals = np.linspace(z_min, z_max, z_dpoints)

            # Empty waveform arrays
            x_wfm = []
            z_wfm = []

            # Waveformn data for scanning procedure
            for i, z_pos in enumerate(z_vals):
                if i % 2 == 0:
                    x_wfm.extend(x_line_for)
                else:
                    x_wfm.extend(x_line_bac)
                z_wfm.extend([z_pos] * x_dpoints)

            # Convert to numpy arrays
            x_wfm = np.array(x_wfm, dtype=np.float64)
            z_wfm = np.array(z_wfm, dtype=np.float64)
            data_points = len(x_wfm) # Number of data points per axis (NOT in TOTAL SCAN)

            # Timing and iteration parameters
            duration = 5 # miliseconds can be set from 0.1 to 5 ms
            iter = 1 # Number of iterations for the scan

            # Time tagger config.
            pix_start_ch = 4 # Channel for pixel start
            spcm_ch = 3      # Channel for SPCM

            npix = x_dpoints * z_dpoints # Total number of pixels in the scan

            # We create a tagger for synchronized measurements
            sync = self.tagger.synchro()

            # We set the trigger levels on the tagger
            self.tagger.set_trigger_level(pix_start_ch, 1.2)
            self.tagger.set_trigger_level(spcm_ch, 1.0)

            # We prepare the NanoDrive to used the created waveform path
            self.nano.wfma_setup(x_wfm, z_wfm, data_points, duration, iter, self.nano.handle)
            # We bind the pixel clock to the NanoDrive's X-Axis
            self.nano.iss_bind_clock_to_axis(1, 2, 1, self.nano.handle)
            
            # We set the counting events
            self.tagger.start_cbm(tagger=sync, click_channel=spcm_ch, begin_channel=pix_start_ch, end_channel=CHANNEL_UNUSED, n_values=npix)
            self.tagger.start_counter(tagger=sync, channels=[spcm_ch, pix_start_ch], binwidth=duration*1e9, n_values=npix, measurement_duration=npix*(duration*1e9))
            self.tagger.start_countrate(tagger=sync, channels=[spcm_ch, pix_start_ch], measurement_duration=npix*(duration*1e9))
            # We set the startFor and Waiting period for the counting events
            self.tagger.sync_sFor(data_points*duration*1e9)
            self.tagger.sync_wait()

            # We trigger the NanoDrive, marking the start of the scan
            self.nano. wfma_trigger(self.nano.handle)

            # We get the CountBetweenMarkers data from our CBM Counting Event
            cbm_remote = self.tagger.count_BM()
            cbm = obtain(cbm_remote)

            # We get the Counter data from the Counter Counting Event
            spcm_n_ttls = self.tagger.get_counter_data()
            spcm_n_ttls = obtain(spcm_n_ttls)
            # We get the Countrate data from the Countrate Counting Event
            c_rate = self.tagger.get_countrate_data()
            c_rate = obtain(c_rate)

            # We prepare the data according to our Triangular-Snake Scan, for it to be properly used in the HeatMap Plotting widget
            def snake(arr):
                for i in range(np.shape(arr)[0]):
                    if i % 2 != 0:
                        arr[i] = arr[i][::-1]
                    else:
                        arr[i] = arr[i]
                return arr
            
            img = np.reshape(cbm, (z_dpoints, x_dpoints))
            img = snake(img)

            # We push the data to the Data Server
            scanXZ_data.push({
                'title': 'XZ Scan',
                'xLabel': 'X [µm]',
                'yLabel': 'Z [µm]',
                'datasets': {
                    'xSteps': x_wfm,
                    'ySteps': z_wfm,
                    'intensity': img,
                }
            })

                        
