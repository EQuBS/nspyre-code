# Modified by Rolando for test.

# from curses import echo
import time
from itertools import count

import numpy as np
from nspyre import DataSource
from nspyre import StreamingList
from nspyre import InstrumentGateway
from nspyre import experiment_widget_process_queue
from tqdm import tqdm

from .gui_dlnsec import DLnsecWidget

from PyQt5.QtCore import pyqtSignal

from rpyc.utils.classic import obtain 

# from drivers.pulses import Pulses

# Added Artif. by Rolando to make it work... xd
DAQ_buffer = 1024*1024 # buffer size for DAQ readout

class SpinMeasurements:
    """Perform spin measurements."""
    def __init__(self, queue_to_exp=None, queue_from_exp=None):
        """
        Args:
            queue_to_exp: A multiprocessing Queue object used to send messages
                to the experiment from the GUI.
            queue_from_exp: A multiprocessing Queue object used to send messages
                to the GUI from the experiment.
        """
        self.queue_to_exp = queue_to_exp
        self.queue_from_exp = queue_from_exp
    
    def read(self, buffer, seq, runs):
        '''
        Function that takes empty buffer as argument, reads samples to buffer and returns it.
        '''
        with InstrumentGateway() as gw:
            #try:
                #gw.daq.start_task()
            #except:
                #print("DAQ TASK ERROR!")
            
            runs = int(np.ceil(runs)) # integer no. of runs
            #gw.ps.laser_on()
            # execute chosen sequence on Pulse Streamer
            gw.ps.stream(seq, runs)
            #print(123) 
            #import pdb; pdb.set_trace()
            # convert data back to numpy array from rpyc.netref data type
            #buffer = obtain(gw.daq.read_samples(buffer, len(buffer), 180))
            #counter = gw.daq.start_counter([3], 100, 100, 1e3) # start counter on channel 0 with binwidth of 1 ps and buffer size of DAQ_buffer
            #buffer = obtain(gw.daq.get_counter_data())
            buffer = np.zeros(runs, dtype=np.uint32)
            # get_counter_data  

            #gw.daq.stop_task()
            gw.ps.ps.reset()

            return buffer

    def sigvstime_run(self, sampling_rate: float):
        '''
        Developed by Tian-Xing in Sept.2023
        '''
        with InstrumentGateway() as gw, DataSource('SigVsTime') as sigvstime_data:
            
            # run laser on continuously here from laser driver
            
            ps_seq = gw.ps.SigvsTime(1/sampling_rate * 1e9) # pulse streamer sequence for Signal vs Time
            
            n_runs = 10 #TXZ: why we do n_runs = 10 here? Maybe due to the fact that we need to run the sequence for a few times to readout the average PL
            # the data buffer needs to be dtype = np.uint32 for digital readout
            signal_array = np.zeros(n_runs, dtype = np.uint32)
            
            ## Normal python list
            #PL_data = []
            #t = []
            ## StreamList
            PL_data_StreamingList = StreamingList([])
            t_StreamingList = StreamingList([])
            PL_t_StreamingList = StreamingList([])
          
            gw.ps.sampling_time = 1/sampling_rate * 1e9 # period defining sig vs time sampling rate
            #gw.ps.clock_time = clock_time #* 1e9 #width of our clock pulse.
            #gw.daq.open_task(n_runs) # one clock per each of the "n_runs" no. of sequences

            time_start = time.time()
            print("TIME 0 = ", time.time() - time_start)
            
            for i in range(10000):
                # Stream the pulse sequence by ps, meausre the signal from APD and read it out by DAQ
                sig_result_raw = self.read(signal_array, ps_seq, n_runs)
                # keeps the laser trigger on ?
                #gw.ps.laser_on()
                #print("TIME 1 = ", time.time() - time_start)
                # print("Raw signal: ", sig_result_raw)
                
                # Now do the math for getting the actual averaged photon counting rate
                delta_signal = sig_result_raw[1:] - sig_result_raw[:-1]
                #sig_result = np.mean(delta_signal)/((n_runs-1)/sampling_rate) # TXZ: I think this is a mistake, we don't need to devide by (n_runs-1) if we are taking the np.mean already
                sig_result = np.mean(delta_signal)*sampling_rate
                # print("signal AFTER avg over the total sampling time: ", sig_result)
                time_pt = time.time() - time_start
                print("TIME 2 = ", time_pt)
                # Update the StreamingList
                PL_data_StreamingList.append(sig_result)
                t_StreamingList.append(time_pt)
                PL_t_StreamingList.append(np.array([[time_pt], [sig_result]]))
                
                #print("TIMES: ", t_StreamingList)
                #print("SIG DATA: ", PL_data_StreamingList)
                #print("PL_t_StreamingList: ", PL_t_StreamingList)

                sigvstime_data.push({'title': 'Signal vs Time',
                                    'xlabel': 't',
                                    'ylabel': 'Counts/s',
                                    'datasets': {'SigVsT_data' : PL_t_StreamingList}
                    })
                print("TIME END LOOP = ", time.time() - time_start)
                
                if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                    #gw.laser.off()
                    print('the GUI has asked us nicely to exit')
                    return

            #gw.daq.close_task()