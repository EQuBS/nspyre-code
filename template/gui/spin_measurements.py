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

from TimeTagger import CHANNEL_UNUSED

from pulsestreamer import PulseStreamer, OutputState 

# from drivers.pulses import Pulses

# Added Artif. by Rolando to make it work... xd
DAQ_buffer = 1024 * 1024  # buffer size for DAQ readout

class SpinMeasurements:
    """Perform spin measurements."""
    
    ## nspyre v1.0.0 (older than v0.6.0) __init__ function
    # def __init__(self):
    #     # self.ps = Pulses()
    #     pass

    ## nspyre v0.6.0 __init__ function
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

    def read(self, buffer, sampling_time, runs, gw):
        '''
        Function that takes empty buffer as argument, reads samples to buffer and returns it.
        '''
        # with InstrumentGateway() as gw:
        try:
            #print("check entered read function")
                #sampling_time = 50000 #gw.ps.sampling_time # in [ns] , Introd. sampl. time as an argument to the read function
            gw.daq.start_counter([3], sampling_time, runs) # took , sampling_time*runs 
            gw.daq.sFor_Counter(sampling_time*runs)
        except:
            print("DAQ TASK ERROR!")
            
        runs = int(np.ceil(runs)) # integer no. of runs
        #gw.ps.laser_on()
        # execute chosen sequence on Pulse Streamer
        #gw.ps.stream(seq, runs) # 5/28/2025 commented by Rolando, 8/25/2025 commented off by Rolando
        #print("successfully streaming")
        tt_data = gw.daq.get_counter_data()[0] # get the counter data from DAQ
        print("tt_data: ", tt_data)
        #import pdb; pdb.set_trace()
        # convert data back to numpy array from rpyc.netref data type
        buffer = obtain(tt_data)
        #print("buffer: ", buffer)

            # gw.daq.stop_task()
            #gw.ps.ps.reset() # from Pulser to ps

        return buffer
    
    def read_R(self, buffer, seq, sampling_time, runs, gw):
        try:
            gw.daq.start_counter([1,3], sampling_time, runs, sampling_time*runs) # channel 1 is the clock, channel 3 is the data
        except:
            print("DAQ TASK ERROR!")
        runs = int(np.ceil(runs)) # integer no. of runs
        gw.ps.stream(seq, runs)
        event_data = gw.daq.get_counter_data() # get the counter data from TimeTagger
        buffer = obtain(event_data)
        return buffer

    def read_TX(self, buffer, seq, runs):
        '''
        Function that takes empty buffer as argument, reads samples to buffer and returns it.
        '''
        with InstrumentGateway() as gw:
            try:
                gw.daq.start_task()
            except:
                print("DAQ TASK ERROR!")
            
            runs = int(np.ceil(runs)) # integer no. of runs
            #gw.ps.laser_on()
            # execute chosen sequence on Pulse Streamer
            gw.ps.stream(seq, runs) 
            #import pdb; pdb.set_trace()
            # convert data back to numpy array from rpyc.netref data type
            buffer = obtain(gw.daq.read_samples(buffer, len(buffer), 180))  

            gw.daq.stop_task()
            gw.ps.Pulser.reset()

            return buffer

    def digital_math(self, array, exp_type, pts = 0):
        # Reshape and calculate the count from the Raw data buffer from the digital readout counter
        diff_array = array[1:]-array[:-1]
        if exp_type == 'ODMR':
            sig = diff_array[::2] # single integrated data point for each MW on/off window
            bg = diff_array[1::2]
            sum1 = np.sum(sig) # MW ON - summed up signal data for plotting
            sum2 = np.sum(bg) # MW OFF - summed up background data for plotting
            return sum1, sum2
        elif exp_type =='Pulsed ODMR':
            sig_all = diff_array[::4] # single integrated data point for each MW on/off window
            bg_all = diff_array[2::4]
            sum1 = np.sum(sig_all) # MW ON - summed up signal data for plotting
            sum2 = np.sum(bg_all)
            return sum1, sum2

        elif exp_type == 'ContinousRead':
            sig_all = diff_array
            #for i in range(pts):# we might need to through away the last point because that's the data of the dark time
            sig_array = np.ones(pts)
            for i in range(pts):
                sig_array[i] = np.sum(sig_all[i::pts])
            return sig_array

        elif  exp_type == 'Optical T1' or exp_type == 'Calibrate_LaserLag':
            sig_all = diff_array[::2]
            sig_array = np.ones(pts) # bright data array
            for i in range(pts):
                sig_array[i] = np.sum(sig_all[i::pts])
                # Doing np.sum here will make the Y axis in the data plotting actually means "the total number of photons collected for all runs"
            return sig_array
        # elif exp_type == 'Optical T1':
        #     # Here, we use the same data for sig and bg for fixing the 'data not showing up' bug while pushing data
        #     sig_all = diff_array[::2]
        #     bg_all = diff_array[::2]
        #     sig_array = np.ones(pts) # bright data array
        #     bg_array = np.ones(pts)
        #     for i in range(pts):
        #         sig_array[i] = np.sum(sig_all[i::pts])
        #         bg_array[i] = np.sum(bg_all[i::pts])
                # Doing np.sum here will make the Y axis in the data plotting actually means "the total number of photons collected for all runs"
            #return sig_array, bg_array
            #return sig_array
        elif exp_type == 'Rabi' or exp_type == 'T2' or exp_type == 'MW_T1' or exp_type == 'Correlation Spectroscopy':
            sig_all = diff_array[::2] # single integrated data point for each MW on/off window
            bg_all = diff_array[1::2]
            sig_array = np.ones(pts) # bright data array
            bg_array = np.ones(pts) # dark data array
            for i in range(pts):
                sig_array[i] = np.sum(sig_all[i::pts])
                bg_array[i] = np.sum(bg_all[i::pts])
                # Doing np.sum here will make the Y axis in the Rabi data plotting actually means "the total number of photons collected for all runs"
            return sig_array, bg_array
        elif exp_type == 'DEER' or exp_type == 'DEER_CPMG':
            dark_ms1_all = diff_array[::8]
            dark_ms0_all = diff_array[2::8]
            echo_ms1_all = diff_array[4::8]
            echo_ms0_all = diff_array[6::8]

            dark_ms1 = np.sum(dark_ms1_all) # dark data
            dark_ms0 = np.sum(dark_ms0_all) # dark ref data
            echo_ms1 = np.sum(echo_ms1_all) # echo data
            echo_ms0 = np.sum(echo_ms0_all) # echo ref data
            return dark_ms1, dark_ms0, echo_ms1, echo_ms0
        elif exp_type == 'DEER_Rabi' or exp_type == 'DEER_FID' or exp_type == 'reporterT1' or exp_type == 'Correlation_Rabi' or exp_type == 'ReporterT2' or exp_type == 'instantaneous_diff':
            # for Rabi type sequence, Dimensions[array] = [readout clk = 2, darkVSEchoMs01 = 4, \tau = pts, repetition = runs]
            dark_ms1_all = diff_array[::8]
            dark_ms0_all = diff_array[2::8]
            echo_ms1_all = diff_array[4::8]
            echo_ms0_all = diff_array[6::8]
            dark_ms1_array = np.ones(pts)
            dark_ms0_array = np.ones(pts)
            echo_ms1_array = np.ones(pts)
            echo_ms0_array = np.ones(pts)
            for i in range(pts):
                dark_ms1_array[i] = np.sum(dark_ms1_all[i::pts])
                dark_ms0_array[i] = np.sum(dark_ms0_all[i::pts])
                echo_ms1_array[i] = np.sum(echo_ms1_all[i::pts])
                echo_ms0_array[i] = np.sum(echo_ms0_all[i::pts])
                # Doing np.sum here will make the Y axis in the Rabi data plotting actually means "the total number of photons collected for all runs"
            return dark_ms1_array, dark_ms0_array, echo_ms1_array, echo_ms0_array
        else:
            raise ValueError("No corresponding math for this sequence in digital math func yet! PLS Check the name.")
            pass

    def analog_math(self, array, exp_type, pts = 0):
        # split up buffers array into signal data (MW ON) and background data (MW OFF)
        # if exp_type == "T2" or exp_type == "Rabi":
        #     ana_sig1 = array[::8] # single integrated data point for each MW on/off window
        #     sig_ref1 = array[1::8]
        #     ana_sig2 = array[6::8] # alternate between MW on - off - off - on for one sequence to cancel integrator offset issue
        #     sig_ref2 = array[7::8]
        #     ana_bg1 = array[2::8]
        #     bg_ref1 = array[3::8]
        #     ana_bg2 = array[4::8]
        #     bg_ref2 = array[5::8]

        #     ana_sig = ana_sig1/sig_ref1 + ana_sig2/sig_ref2
        #     ana_bg = ana_bg1/bg_ref1 + ana_bg2/bg_ref2
        # else:
        ana_sig = array[::2] # single integrated data point for each MW on/off window
        ana_bg = array[1::2]

        if exp_type == 'ODMR':
            sum1 = np.sum(ana_sig) # MW ON - summed up dark data for plotting
            sum2 = np.sum(ana_bg) # MW OFF - summed up bright data for plotting
            
            return [sum1, sum2]
        
        elif exp_type == 'Cal' or exp_type == 'Optical_T1':
            sig_array = np.ones(pts)
            ana_sig = ana_sig + ana_bg
            
            for i in range(pts):
                sig_array[i] = np.sum(ana_sig[i::pts])

            return sig_array

        elif exp_type == 'DEER':
            # ana_dark_sig = array[::4]
            # ana_dark_bg = array[1::4]
            # ana_echo_sig = array[2::4]
            # ana_echo_bg = array[3::4]

            # ana_echo_sig = array[::2]
            # ana_echo_bg = array[1::2]

            # print("DEER ECHO SIGNAL: ", ana_echo_sig)
            # print("DEER ECHO BACK: ", ana_echo_bg)

            # sum1 = np.mean(ana_echo_sig)
            # sum2 = np.mean(ana_echo_bg)

            sum1 = np.mean(array)
            # sum1 = np.mean(ana_dark_sig)
            # sum2 = np.mean(ana_dark_bg)
            # sum3 = np.mean(ana_echo_sig)
            # sum4 = np.mean(ana_echo_bg)
            
            # print("MATH SIG DEER RESULT = ", sum3)
            # print("MATH BG DEEER RESULT = ", sum4)
            
            return [sum1]
        
        elif exp_type == 'DEER_2':
            ana_dark_sig = array[::4]
            ana_dark_bg = array[1::4]
            ana_echo_sig = array[2::4]
            ana_echo_bg = array[3::4]
            
            dark_ms1_array = np.ones(pts) # bright data array
            dark_ms0_array = np.ones(pts) # dark data array
            echo_ms1_array = np.ones(pts) # bright data array
            echo_ms0_array = np.ones(pts) # dark data array

            for i in range(pts):
                dark_ms1_array[i] = np.mean(ana_dark_sig[i::pts]) # pts = no. of runs
                dark_ms0_array[i] = np.mean(ana_dark_bg[i::pts])
                echo_ms1_array[i] = np.mean(ana_echo_sig[i::pts])
                echo_ms0_array[i] = np.mean(ana_echo_bg[i::pts])
            
            return [dark_ms1_array, dark_ms0_array, echo_ms1_array, echo_ms0_array]

        else:
            ms1_array = np.ones(pts) # bright data array
            ms0_array = np.ones(pts) # dark data array

            for i in range(pts):
                ms1_array[i] = np.mean(ana_sig[i::pts])
                ms0_array[i] = np.mean(ana_bg[i::pts])
            
            return [ms1_array, ms0_array]

    def sort_taus_for_balance(self, array):
        # This function rearrange the array = [0,1,2,3,4,5,6] to array' = [0,6,1,5,2,4,3]
        # This is for balancing the heatup from MW and Laser to the NV. 
        # This works for linear taus, not for exponential taus
        sorted_array = np.zeros(len(array)) # initialize sorted array
        array_copy = np.copy(array) # create copy of array to pop values from
        idx_iter = 0 # iteration index to determine whether an element is popped from beginning or end of array (alternating)

        for i in range(len(array)):
            if idx_iter%2 == 0: 
                popped, array_copy = array_copy[0], array_copy[1:] # even no. for idx_iter --> pop from beginning of array 
            else:
                popped, array_copy = array_copy[-1], array_copy[:-1] # odd no. for idx_iter --> pop from end of array 
            
            sorted_array[i] = popped # create sorted array
            idx_iter += 1

        return sorted_array

    def sig_analysis_run(self, acquisition_time: float, sampling_rate: float, clock_time: int):
        
        with InstrumentGateway() as gw, DataSource('SigAnalysis') as siganalysis_data:
            
            time_start = time.time()

            n_runs = int(acquisition_time * sampling_rate)
            print("No. runs = ", n_runs)

            ni_sample_buffer = np.ascontiguousarray(np.zeros(n_runs), dtype=np.float64)
            sig_buffer = [ni_sample_buffer]
            
            print("TIME 1 = ", time.time() - time_start)

            ps_seq = gw.ps.SigAnalysis(n_runs, 1/sampling_rate*1e9) # pulse streamer sequence for CW ODMR

            print("TIME 2 = ", time.time() - time_start)

            dataset = {'times': np.linspace(1/sampling_rate, acquisition_time, n_runs), # in [s]
                       'PL_data': np.zeros(n_runs)}
            
            print("PS sampling time = ", 1/sampling_rate * 1e9)

            gw.ps.clock_time = clock_time #* 1e9 #width of our clock pulse.
            #gw.daq.open_task(len(sig_buffer[0])) # one clock per each of the "n_runs" no. of sequences
            gw.daq.set_trigger_level(3, 1.1)

            print("TIME 3 = ", time.time() - time_start)

            sig_result = self.read(sig_buffer[0], ps_seq, 1)

            print("TIME 4 = ", time.time() - time_start)

            dataset['PL_data'] = sig_result

            siganalysis_data.push({'dataset': dataset})
            # print("TIMES: ", t)
            # print("SIG DATA: ", PL_data)

            gw.daq.free_time_tagger()
    
    
    def sigvstime_no_clock(self, sampling_rate: float):
        # This function is for testing the Signal vs Time measurement without using PS clock pulse but using PC-CPU clock 

        with InstrumentGateway() as gw, DataSource('SigVsTime') as sigvstime_data:
            # Define a duration for the measurement, e.g. dur = 0.1s (this is defined by CPU, not by PS)
            # Define data structure, e.g. x = [times], y = [counts]
            # For i in range(10000)
            # Time = dur * i
            # Count.startFor(dur)
            # Count.waitUntilFinished()
            # Push ([Time], [Count])
            gw.daq.free_time_tagger()
            
    
    def sigvstime_run(self, sampling_rate: float):
        '''
        Developed by Tian-Xing in Sept.2023
        '''
        with InstrumentGateway() as gw, DataSource('SigVsTime') as sigvstime_data:
            
            # run laser on continuously here from laser driver
            
            #ps_seq = gw.ps.SigvsTime(1/sampling_rate * 1e9) # pulse streamer sequence for Signal vs Time
            
            n_runs = 1 #TXZ: why we do n_runs = 10 here? Maybe due to the fact that we need to run the sequence for a few times to readout the average PL
            # the data buffer needs to be dtype = np.uint32 for digital readout
            signal_array = np.zeros(n_runs, dtype = np.uint32)
            
            ## Normal python list
            #PL_data = []
            #t = []
            ## StreamList
            PL_data_StreamingList = StreamingList([])
            t_StreamingList = StreamingList([])
            PL_t_StreamingList = StreamingList([])
          
            sampling_time = 1/sampling_rate * 1e12 # period defining sig vs time sampling rate
            # gw.ps.sampling_time = 1/sampling_rate * 1e9 # period defining sig vs time sampling rate
            #gw.ps.clock_time = clock_time #* 1e9 #width of our clock pulse.
            
            """"
            Mod. with function from TT driver (A.K.)
            """
            #gw.daq.open_task(n_runs) # one clock per each of the "n_runs" no. of sequences
            gw.daq.set_trigger_level(3, 1.1)

            time_start = time.time()
            print("TIME 0 = ", time.time() - time_start)
            

            for i in range(10000):
                #print(i)
                #gw.daq.start_counter
                # Stream the pulse sequence by ps, meausre the signal from APD and read it out by DAQ
                #print(time.time() - time_start) 
                sig_result_raw = self.read(signal_array, sampling_time, n_runs, gw) # 5/28/2025 commented by Rolando 
                #print(time.time() -time_start)
                #print("sig_result_raw: ", sig_result_raw)
                # keeps the laser trigger on ?
                #gw.ps.laser_on()
                #print("TIME 1 = ", time.time() - time_start)
                # print("Raw signal: ", sig_result_raw)
                
                # Now do the math for getting the actual averaged photon counting rate
                #delta_signal = sig_result_raw[1:] - sig_result_raw[:-1]
                #sig_result = np.mean(delta_signal)/((n_runs-1)/sampling_rate) # TXZ: I think this is a mistake, we don't need to devide by (n_runs-1) if we are taking the np.mean already
                sig_result = sig_result_raw[0]  #np.mean(delta_signal)*sampling_rate
                # print("signal AFTER avg over the total sampling time: ", sig_result)
                time_pt = time.time() - time_start
                #print("TIME 2 = ", time_pt)
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
                #print("TIME END LOOP = ", time.time() - time_start)
                
                if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                    gw.laser.off()
                    print('the GUI has asked us nicely to exit')
                    return

            gw.daq.free_time_tagger()

    def cal_lag_run(self, **kwargs):

        with InstrumentGateway() as gw, DataSource('Calibration') as cal_data:
             # read window timings that will be swept over in the calibration
            read_start_times = np.linspace(kwargs['Read_Start_Time'], kwargs['Read_Stop_Time'], kwargs['num_pts']) * 1e9
            #num_read_wind = len(read_windows)

            # define buffer size here
            buffer_size = 2*kwargs['runs']*kwargs['num_pts']
            if buffer_size < 2:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(buffer_size), dtype = np.uint32)
            calibrate_buffer = [ni_sample_buffer]

            np.set_printoptions(precision = 6)

            signal_sweeps = StreamingList()
            #background_sweeps = StreamingList()

            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()

            #gw.daq.open_task(len(calibrate_buffer[0]))

            ps_seq = gw.ps.Calibrate_LaserLag(read_start_times, kwargs['laser_start']*1e9, kwargs['read_window']*1e9, kwargs['laser_window']*1e9) # pulse streamer sequence for CW ODMR

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):
                    
                    Cal_result = self.read(calibrate_buffer[0], ps_seq, kwargs['runs'])

                    # partition buffer into signal and background datasets
                    sig_array = self.digital_math(Cal_result, 'Calibrate_LaserLag', kwargs['num_pts'])
                    
                    #print('mw_times_ordered is: \n',mw_times_ordered)
                    signal_sweeps.append(np.stack([read_start_times, sig_array]))
                    # notify the streaminglist that this entry has updated so it will be pushed to the data server
                    signal_sweeps.updated_item(-1)

                    cal_data.push({'params': {'mw_num': kwargs['num_pts'], 'iter_num': kwargs['iters'],'runs_num': kwargs['runs']},
                                    'title': 'Calibrate LaserLag',
                                    'xlabel': 'Read Start Time (ns)',
                                    'ylabel': 'Counts',
                                    'datasets': {'signal' : signal_sweeps}
                    })
                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        gw.daq.free_time_tagger()
                        gw.ps.Pulser.reset()
                        gw.laser.off()
                        print('the GUI has asked us nicely to exit')
                        return

                    pbar.update(1)

            gw.daq.free_time_tagger()
            gw.ps.Pulser.reset()
            gw.laser.off()

    def cal_initialize_run(self, **kwargs):

        with InstrumentGateway() as gw, DataSource('Calibration') as cal_data:
             # read window timings that will be swept over in the calibration
            read_windows = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
            num_read_wind = len(read_windows)

            # define buffer size here
            init_buffer_size = kwargs['runs']*num_read_wind
            if init_buffer_size < 4:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(init_buffer_size), dtype=np.float64)
            init_buffer = [ni_sample_buffer]

            np.set_printoptions(precision = 6)

            dataset = {'cal': []}

            # set initial parameters for instrument server devices
            gw.ps.clock_time = 11 # [ns] width of our clock pulse.
            gw.ps.runs = kwargs['runs'] #number of runs per point
            gw.daq.set_trigger_level(3, 1.1)

            ps_seq = gw.ps.Calibrate_Initialize(read_windows, kwargs['init_pulse']) # pulse streamer sequence for CW ODMR
                
            cal_result = self.read(init_buffer[0], ps_seq, kwargs['runs']/4) # read samples to buffer
            print("RESULT: ", cal_result)
            # partition buffer into signal and background datasets
            cal = self.analog_math(cal_result, 'Cal', num_read_wind)

            dataset['cal'].append(np.stack([read_windows/1e3, cal]))

            # send data to data server for plotting
            cal_data.push({'params': {'runs_num': kwargs['runs'],
                            'r': gw.zaber.update_positions_callback(),
                            'theta': gw.thor_polar.update_positions_callback(),
                            'phi': gw.thor_azi.update_positions_callback()}, 
                            'dataset': dataset})

            # kwargs['queue'].put(100)

            # close DAQ task + reset SG396 and PS parameters
            # print("TASK ID: ", gw.daq.read_task)
            gw.daq.free_time_tagger()
            gw.ps.Pulser.reset()

    def cal_singlet_run(self, **kwargs):
        with InstrumentGateway() as gw, DataSource('Calibration') as cal_data:
             # read window timings that will be swept over in the calibration
            decay_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
            num_decays = len(decay_times)

            # define buffer size here
            decay_buffer_size = kwargs['runs']*num_decays
            if decay_buffer_size < 4:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(decay_buffer_size), dtype=np.float64)
            init_buffer = [ni_sample_buffer]

            np.set_printoptions(precision = 6)

            dataset = {'cal': []}

            # set initial parameters for instrument server devices
            gw.ps.laser_time = kwargs['init'] * 1e9
            gw.ps.clock_time = 11 # [ns] width of our clock pulse.
            gw.ps.runs = kwargs['runs'] #number of runs per point
            gw.daq.set_trigger_level(3, 1.1) 

            ps_seq = gw.ps.Calibrate_SingletDecay(decay_times) # pulse streamer sequence for CW ODMR

            for iter in range(kwargs['iters']):

                cal_result = self.read(init_buffer[0], ps_seq, kwargs['runs']/4) # read samples to buffer
                # print("RESULT: ", cal_result)
                # partition buffer into signal and background datasets
                cal = self.analog_math(cal_result, 'Cal', num_decays)

                dataset['cal'].append(np.stack([decay_times/1e3, cal]))

                # send data to data server for plotting
                cal_data.push({'params': {'runs_num': kwargs['runs'], 'iters_num': kwargs['iters'],
                                'r': gw.zaber.update_positions_callback(),
                                'theta': gw.thor_polar.update_positions_callback(),
                                'phi': gw.thor_azi.update_positions_callback()}, 
                                'dataset': dataset})

                # percent_complete = int((iter+1)/kwargs['iters']*100)
                # kwargs['queue'].put(percent_complete)

            # close DAQ task + reset SG396 and PS parameters
            # print("TASK ID: ", gw.daq.read_task)
            gw.daq.free_time_tagger()
            gw.ps.Pulser.reset()

    def cal_switch(self, **kwargs):
        
        with InstrumentGateway() as gw:
            gw.sg.set_frequency(kwargs['freq'])
            gw.sg.set_rf_amplitude(kwargs['rf_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')

            for i in range(2):
                kwargs['pihalf'][i] = kwargs['pihalf'][i]*1e9
                kwargs['pi'][i] = kwargs['pi'][i]*1e9

            ps_seq = gw.ps.Calibrate_Switch_Echo(kwargs['tau']*1e9, kwargs['pihalf'][0], kwargs['pihalf'][1], 
                                         kwargs['pi'][0], kwargs['pi'][1])

            gw.ps.stream(ps_seq, kwargs['runs'])

    def cal_DEER_offset(self, **kwargs):
        with InstrumentGateway() as gw:
            gw.sg.set_frequency(kwargs['freq'])
            gw.sg.set_rf_amplitude(kwargs['rf_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')

            ps_seq = gw.ps.Calibrate_DEER_offset()
            time.sleep(20)
            gw.ps.stream(ps_seq, 1)

            time.sleep(30)
            
            print("Finished sequence.")
            gw.sg.set_rf_toggle(0)
            gw.sg.set_mod_toggle(0)
            gw.ps.Pulser.reset()

    def odmr_run(self, **kwargs):
        '''
        Developed by Tian-Xing in Sept.2023
        '''
        with InstrumentGateway() as gw, DataSource(kwargs['dataset']) as odmr_data:

            # define buffer size here
            odmr_buffer_size = 2*kwargs['runs']+1
            if odmr_buffer_size < 2:
                raise ValueError("Buffer size too small.")

            odmr_buffer_size_test = 1 #kwargs['runs'] # This is the test buffer size 8/13/2025

            ni_sample_buffer = np.zeros(odmr_buffer_size_test, dtype = np.uint32) # Uses test buffer size;removed np.ascontiguousarray() that formats to more efficient C array when taking multiple points per frequency,bin
            odmr_buffer = [ni_sample_buffer]

            np.set_printoptions(precision = 6)

            # frequencies that will be swept over in the ODMR measurement
            frequencies = np.linspace(kwargs['start_freq'], kwargs['stop_freq'], kwargs['num_points'])

            signal_sweeps = StreamingList()
            background_sweeps = StreamingList()

            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.cw_mode()
            gw.laser.on()

            gw.daq.set_trigger_level(3, 1.1) # set trigger level for Time Tagger

            # Set the correct Signal Generator
            if kwargs['odmr_sg'] == 'SRS':
                # Pulse Stramer Sequence
                if kwargs['odmr_type'] == 'CW':
                    #gw.ps.probe_time = kwargs['probe_time'] * 1e9 # change unit to ns
                    gw.ps.CW_ODMR(kwargs['runs'], kwargs['probe_time'] * 1e9) # pulse streamer sequence for CW ODMR, 8/13/2025 was defined as ps_seq
                    samp_time = 5*1e7 #int(kwargs['runs']*kwargs['probe_time']*1e9)
                    gw.ps.gate_on_cw_odmr() # Opening the SPCM's gate, 8/12/2025 Very possible to be changed
                    print('\nCW ODMR sequence generated!\n')
                elif kwargs['odmr_type']=='Pulsed':
                    #pi_xy, pi_time = kwargs['pi_xy'], kwargs['pi_time']*1e9 # these two parameters come from gui
                    gw.ps.Pulsed_ODMR(kwargs['xy'], kwargs['pi_time']*1e9, kwargs['runs'], kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9, kwargs['seq_gap']*1e9) # 8/13/2025 was defined as ps_seq
                    samp_time = int(2 * (1000 + kwargs['init_time'] + kwargs['wait_time'] + kwargs['init_time'] + kwargs['pi_time'] + kwargs['read_wait'] + kwargs['seq_gap']))
                    print('\nPulsed ODMR sequence generated!\n')
                else:
                    raise ValueError("\nOnly CW or Pulsed ODMR!\n")
                # else:
                #     ps_seq = gw.ps.Pulsed_ODMR(kwargs['xy'], kwargs['pi']) # pulse streamer sequence for Pulsed ODMR
                gw.sg.set_rf_amplitude(kwargs['mw_power'])
                time.sleep(0.1)
                #gw.sg.set_mod_type('IQ') # Commented for testing purposes 8/14/2025
                #time.sleep(0.1)
                gw.sg.set_rf_toggle(1)
                time.sleep(0.1)
                #gw.sg.set_mod_toggle(1) # Commented for testing purposes 8/14/2025
                #time.sleep(0.1)
                #gw.sg.set_mod_function('ramp') #set modulation function from external to ramp; Commented for testing purposes 8/14/2025

            elif kwargs['odmr_sg'] == 'WindFreak':
                # Pulse Stramer Sequence
                if kwargs['odmr_type'] == 'CW':
                    #gw.ps.probe_time = kwargs['probe_time'] * 1e9 # change unit to ns
                    ps_seq = gw.ps.CW_ODMR_Switch(kwargs['runs'], kwargs['probe_time'] * 1e9) # pulse streamer sequence for CW ODMR
                else:
                    raise ValueError("\nWe can only do CW ODMR with WindFreak for now!\n")
                # else:
                #     ps_seq = gw.ps.Pulsed_ODMR(kwargs['xy'], kwargs['pi']) # pulse streamer sequence for Pulsed ODMR
            
                #gw.windfreak.set_power_ch0(kwargs['mw_power'])
                #gw.windfreak.set_freq_ch0(kwargs['freq'])
                #gw.windfreak.ch0_on()
            else:
                raise ValueError("\nWe only have Signal Generators: SRS or WindFreak!\n")
            ## TXZ & Evan: Found that the class variable cannot be updated by doing this "gw.ps.[class variable] = XXX", maybe this is nspyre's protection
            ## TXZ & Evan: If you really want to change the class variable, you need to write a funtion inside the class for changing the class variable
            #gw.ps.clock_time = 10 # [ns] width of our clock pulse.
            #gw.ps.runs = kwargs['runs'] #number of runs per point
            #print("\n gw.ps.runs:", gw.ps.runs) 

            with tqdm(total = kwargs['iterations']) as pbar:

                for iter in range(kwargs['iterations']):
                    # photon counts corresponding to each frequency
                    # initialize to NaN
                    sig_counts = np.empty(kwargs['num_points'])
                    sig_counts[:] = np.nan
                    signal_sweeps.append(np.stack([frequencies/1e9, sig_counts]))
                    bg_counts = np.empty(kwargs['num_points'])
                    bg_counts[:] = np.nan
                    background_sweeps.append(np.stack([frequencies/1e9, bg_counts]))
                    
                    for f, freq in enumerate(frequencies):
                        if kwargs['odmr_sg'] == 'SRS':
                            gw.sg.set_frequency(freq) # set particular SG396 frequency
                        #elif kwargs['odmr_sg'] == 'WindFreak':
                            #gw.windfreak.set_freq_ch0(freq)
                        else:
                            raise ValueError("\nWe only have Signal Generators: SRS or WindFreak!\n")
                        
                        
                        # partition buffer into signal and background datasets
                        if kwargs['odmr_type']=='CW':
                            #TXZ: Here we set the # of runs to be 1, because we put the actual runs into the sequence directly
                            ### This self.read the the most "important" function, which let the pulse streamer starting streaming the seq and let the DAQ read data ####
                            #odmr_result = self.read(odmr_buffer[0], ps_seq, 1, gw) # read samples to buffer
                            odmr_result = self.read(odmr_buffer[0], samp_time, 1, gw)
                            sig, bg = self.digital_math(odmr_result, 'ODMR')
                        elif kwargs['odmr_type']=='Pulsed':
                            # Here since the Pulses_ODMR function inside pulses.py only generate the sequence for 1 run
                            odmr_result = self.read(odmr_buffer[0], samp_time, kwargs['runs'], gw)
                            sig, bg = self.digital_math(odmr_result, 'Pulsed ODMR', 1)

                        # record the photon counts
                        signal_sweeps[-1][1][f] = sig
                        background_sweeps[-1][1][f] = bg
                        # notify the streaminglist that this entry has updated so it will be pushed to the data server
                        signal_sweeps.updated_item(-1)
                        background_sweeps.updated_item(-1)

                        odmr_data.push({'params': {'start': kwargs['start_freq'], 'stop': kwargs['stop_freq'], 'num_points': kwargs['num_points'], 'iterations': kwargs['iterations']},
                                    'title': 'Optically Detected Magnetic Resonance',
                                    'xlabel': 'Frequency (GHz)',
                                    'ylabel': 'Counts',
                                    'datasets': {'signal' : signal_sweeps,
                                                'background': background_sweeps}
                        })

                        # potential position to add the XY sweeping or point defect PL tracking
                        if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                            gw.daq.free_time_tagger()
                            gw.sg.set_rf_toggle(0)
                            time.sleep(0.1)
                            #gw.sg.set_mod_toggle(0) # Commented for testing purposes 8/14/2025
                            gw.ps.ps_reset()
                            gw.laser.off()
                            print('the GUI has asked us nicely to exit')
                            return

                    pbar.update(1)

                # close DAQ task + reset SG396 and PS parameters
                #gw.daq.free_time_tagger()
                gw.sg.set_rf_toggle(0)
                #gw.sg.set_mod_toggle(0) # Commented for testing purposes 8/14/2025
                gw.ps.ps_reset()
                gw.laser.off()
                gw.ps.gate_off() # Closing the SPCM's gate


    def odmr_run_R(self, **kwargs): # by Rolando 8/27/2025
        with InstrumentGateway() as gw, DataSource(kwargs['dataset']) as odmr_data:

            # Sig. Gen. cannot allow more than 6 digits after the decimal point.
            np.set_printoptions(precision = 6)
           
            frequencies = np.linspace(kwargs['start_freq'], kwargs['stop_freq'], kwargs['num_points'])
            
            signal_sweeps = StreamingList()
            background_sweeps = StreamingList()

            # We define parameters 
            dwell_time = kwargs['dwell_time'] # in seconds
            n_bins = 10
            bin_width = dwell_time/n_bins # in ms

            # Set laser
            gw.laser.cw_mode()
            gw.laser.get_power()
            gw.laser.set_power(5) # Set laser power to 5%
            gw.laser.on()

            # We set the appropriate Sig. Generator
            if kwargs['odmr_sg'] == 'SRS':
                # We create the Pulse Streamer seq.
                if kwargs['odmr_type'] == 'CW':
                    cw_odmr_seq = gw.ps.CW_ODMR_R(dwell_time*1e9, kwargs['runs'])
                elif kwargs['odmr_type']=='Pulsed':
                    pul_odmr_seq = gw.ps.Pulsed_ODMR_R(kwargs['iterations'], kwargs['probe_time']*1e9, kwargs['read_time']*1e9)
                else:
                    raise ValueError("Invalid ODMR type")

                # We set parameters for our signal generator
                gw.sg.set_rf_amplitude(kwargs['mw_power'])
                

            # We assign Trigger Levels, and counting event in the Time Tagger
            tt_gate_ch = 1
            tt_sync_ch = 2
            tt_spcm_ch = 3

            #gw.daq.set_trigger_level(spcm, 1.3)
            gw.daq.set_trigger_level(tt_gate_ch, 1.3)
            gw.daq.set_trigger_level(tt_sync_ch, 1.3)
            gw.daq.set_trigger_level(tt_spcm_ch, 1.1)

            
            # Set the sig. gen parameters.
            gw.sg.set_rf_amplitude(kwargs['mw_power'])
            gw.sg.set_mod_type(6) # 'IQ' modulation : 6
            gw.sg.set_qmod_function(5) # 'IQ modulation function': External
            gw.sg.set_mod_toggle(1)
            gw.sg.set_rf_toggle(1)            

            sig_a = np.zeros(kwargs['num_points'])
            bg_a = np.zeros(kwargs['num_points'])

            for iter in range(kwargs['iterations']):
                print(f"Iteration {iter + 1} of {kwargs['iterations']}")
                sig = []
                bg = []
                for f, freq in enumerate(frequencies):
                    gw.sg.set_frequency(freq)

                    if kwargs['odmr_type'] == 'CW':
                        gw.daq.start_counter([tt_spcm_ch], int(bin_width*1E3), n_bins)
                        n_runs = 1
                        gw.ps.stream(obtain(cw_odmr_seq), n_runs)
                        gw.daq.sFor_Counter(int(dwell_time*1E12))
                        gw.daq.wait_until_counter()  
                        
                        counter_data = gw.daq.get_counter_data()
                        
                        # Record of photon counts
                        sig.append(counter_data[0][3])
                        bg.append(counter_data[0][6])

                    elif kwargs['odmr_type'] == 'Pulsed':
                        runs = 3000
                        gw.daq.start_cbm(tt_spcm_ch, tt_gate_ch, -tt_gate_ch, runs*2)
                        gw.daq.CBM_start()
                        gw.daq.sync()
                        gw.ps.stream(pul_odmr_seq, runs)
                        ready = False
                        while ready is False:
                            ready = gw.daq.cbm_ready()
                            counts = gw.daq.count_BM()
                        # Record of photon counts
                        sig.append(sum(counts[0::2]))
                        bg.append(sum(counts[1::2]))
                
                # avg_data = (avg_data*iter + np.array(signal_sweeps))/(iter+1)
                sig_a = (sig_a*iter + np.array([float(x) for x in sig]))/(iter+1)
                bg_a = (bg_a*iter + np.array([float(x) for x in bg]))/(iter+1)

                signal_sweeps.append(sig_a)
                background_sweeps.append(bg_a)

                # Notify the streamlist, and update it
                signal_sweeps.updated_item(-1)
                background_sweeps.updated_item(-1)

                if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                    #gw.daq.free_time_tagger()
                    gw.sg.set_rf_toggle(0)
                    print(6)
                    gw.sg.set_mod_toggle(0)
                    print(7)
                    gw.ps.ps_reset()
                    gw.laser.get_power()
                    gw.laser.set_power(0)
                    gw.ps.just_gate_off() # We close the SPCM gate
                    gw.laser.off()
                    print('the GUI has asked us nicely to exit')
                    return


                # Data push 
                odmr_data.push({'params': {'start': kwargs['start_freq'], 'stop': kwargs['stop_freq'], 'num_points': kwargs['num_points'], 'iterations': kwargs['iterations']},
                                    'title': 'Optically Detected Magnetic Resonance',
                                    'xlabel': 'Frequency (GHz)',
                                    'ylabel': 'Counts',
                                    'datasets': {'signal' : sig_a,
                                                'background': bg_a}
                        })

        # We turn OFF the mw signal (modulation and amplitude)
        gw.sg.set_mod_toggle(0)
        print(9)
        gw.sg.set_rf_toggle(0)
        print(8)
        gw.laser.off()
        #gw.ps.constant(OutputState([], 0.0, 0.0))
        gw.ps.gate_off()
        gw.ps.ps_reset()
        gw.daq.free_time_tagger()


    #ODMR_2Dsweeping
    def odmr_run_with_2d_scan(self, **kwargs):
        '''
        By Guanming Lao, Sept.2024
        Modified ODMR
        Taking the ODMR spectrum while sanning an area in XY plane, which will average the signal spatially
        '''
        with InstrumentGateway() as gw, DataSource(kwargs['dataset']) as odmr_2d_data:
            gw.fsm.initialize()
            # Define buffer size
            odmr_2d_buffer_size = 2 * kwargs['runs'] + 1
            if odmr_2d_buffer_size < 2:
                raise ValueError("Buffer size too small.")
            ni_sample_buffer = np.ascontiguousarray(np.zeros(odmr_2d_buffer_size), dtype=np.uint32)
            odmr_2d_buffer = [ni_sample_buffer]
            np.set_printoptions(precision=6)

            # Frequencies to sweep
            frequencies = np.linspace(kwargs['start_freq'], kwargs['stop_freq'], kwargs['num_points'])
            signal_sweeps = StreamingList()
            background_sweeps = StreamingList()

            # Set initial parameters for instruments
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            

            # Retrieve scan parameters from kwargs
            x_start = kwargs.get('x_start', -5)
            x_end = kwargs.get('x_end', 5)
            y_start = kwargs.get('y_start', -5)
            y_end = kwargs.get('y_end', 5)
            step_size = kwargs.get('step_size', 1)
            delay = kwargs.get('delay', 0.01)
            if kwargs['odmr_sg'] == 'SRS':
                # Pulse Stramer Sequence
                if kwargs['odmr_type'] == 'CW':
                    #gw.ps.probe_time = kwargs['probe_time'] * 1e9 # change unit to ns
                    ps_seq = gw.ps.CW_ODMR(kwargs['runs'], kwargs['probe_time'] * 1e9) # pulse streamer sequence for CW ODMR
                else:
                    raise ValueError("\nWe can only do CW ODMR for now!\n")
            # else:
            #     ps_seq = gw.ps.Pulsed_ODMR(kwargs['xy'], kwargs['pi']) # pulse streamer sequence for Pulsed ODMR
                gw.sg.set_rf_amplitude(kwargs['mw_power'])
                gw.sg.set_mod_type('QAM')
                gw.sg.set_rf_toggle(1)
                gw.sg.set_mod_toggle(1)
                gw.sg.set_mod_function('external')
            elif kwargs['odmr_sg'] == 'WindFreak':
                if kwargs['odmr_type'] == 'CW':
                    ps_seq = gw.ps.CW_ODMR_Switch(kwargs['runs'], kwargs['probe_time'] * 1e9)  # Pulse streamer sequence for CW ODMR
                else:
                    raise ValueError("\nWe can only do CW ODMR for now!\n")
                gw.windfreak.set_power_ch0(kwargs['mw_power'])
                gw.windfreak.ch0_on()
            else:
                raise ValueError("\nWe only have Signal Generators: SRS or WindFreak!\n")
            #gw.daq.open_task(len(odmr_2d_buffer[0]))
            # Check if DAQ reader is initialized
            #if gw.daq.read_task is None or gw.daq.reader is None:
                # Ensure that the task is opened if it has not been done yet
                #gw.daq.open_task(odmr_2d_buffer_size)
            with tqdm(total=kwargs['iterations']) as pbar:
                 # Initialize the FSM with necessary channels
                #gw.fsm.initialize()
                #gw.daq.open_task(len(odmr_2d_buffer[0]))
                #sig_counts_total = np.zeros(kwargs['num_points'])
                #bg_counts_total = np.zeros(kwargs['num_points'])
                for iter in range(kwargs['iterations']):
                    sig_counts = np.empty(kwargs['num_points']) #single experiment
                    sig_counts[:] = np.nan
                    signal_sweeps.append(np.stack([frequencies/1e9, sig_counts]))
                    bg_counts = np.empty(kwargs['num_points'])
                    bg_counts[:] = np.nan
                    background_sweeps.append(np.stack([frequencies/1e9, bg_counts]))

                    for f, freq in enumerate(frequencies):
                        if kwargs['odmr_sg'] == 'SRS':
                            gw.sg.set_frequency(freq) # set particular SG396 frequency
                        elif kwargs['odmr_sg'] == 'WindFreak':
                            gw.windfreak.set_freq_ch0(freq)
                        else:
                            raise ValueError("\nWe only have Signal Generators: SRS or WindFreak!\n")
                        #gw.sg.set_frequency(freq)
                        signal_sweeps[-1][1][f]=0
                        background_sweeps[-1][1][f]=0
                        # 2D scan loop with user-specified range, step size, and delay
                        for x_pos in np.arange(x_start, x_end + step_size, step_size):
                            gw.fsm.set_x(x_pos)
                            for y_pos in np.arange(y_start, y_end + step_size, step_size):
                                #print("current position:", x_pos, y_pos)
                                gw.fsm.set_y(y_pos)
                                time.sleep(delay)  # Wait for the FSM to settle

                                # Read ODMR result
                                #print("Ps_seq:", ps_seq)
                                odmr_2d_result = self.read(odmr_2d_buffer[0], ps_seq, 1)
                                sig, bg = self.digital_math(odmr_2d_result, 'ODMR')

                                # record the photon counts
                                signal_sweeps[-1][1][f] += sig
                                background_sweeps[-1][1][f] += bg
                                # notify the streaminglist that this entry has updated so it will be pushed to the data server
                                signal_sweeps.updated_item(-1)
                                background_sweeps.updated_item(-1)

                                # Accumulate counts
                                #sig_counts_total[f] += sig
                                #bg_counts_total[f] += bg
                                # debug
                                #print("X, Y\n", x_pos, y_pos)
                                #print("This XY Signal check:\n", sig_counts_total,bg_counts_total)
                                # Check if the GUI requested stop
                                if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                                    gw.daq.close_task()
                                    gw.sg.set_rf_toggle(0)
                                    gw.sg.set_mod_toggle(0)
                                    gw.ps.Pulser.reset()
                                    gw.laser.off()
                                    gw.fsm.finalize()
                                    print('Stopped by GUI request')
                                    return
                        #print("X, Y :", x_pos, y_pos)
                        #print("This XY Signal check:\n", f, signal_sweeps[-1][1][f])
                        # Store summed signal and background counts
                        #signal_sweeps_total.append(np.stack([frequencies / 1e9, sig_counts_total]))
                        #background_sweeps_total.append(np.stack([frequencies / 1e9, bg_counts_total]))
                        #print("Signal check:", signal_sweeps,background_sweeps)

                        # Push data to the server
                        odmr_2d_data.push({'params': {'start': kwargs['start_freq'], 'stop': kwargs['stop_freq'], 'num_points': kwargs['num_points'], 'iterations': kwargs['iterations']},
                                        'title': 'Optically Detected Magnetic Resonance',
                                        'xlabel': 'Frequency (GHz)',
                                        'ylabel': 'Counts',
                                        'datasets': {'signal': signal_sweeps, 'background': background_sweeps}})
                    
                        if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                            gw.daq.close_task()
                            gw.sg.set_rf_toggle(0)
                            gw.sg.set_mod_toggle(0)
                            gw.ps.Pulser.reset()
                            gw.laser.off()
                            gw.fsm.finalize()
                            print('Stopped by GUI request')
                            return
                        
                    pbar.update(1)

            # Close tasks and reset devices
                gw.daq.close_task()
                gw.sg.set_rf_toggle(0)
                gw.sg.set_mod_toggle(0)
                gw.ps.Pulser.reset()
                gw.laser.off()
                gw.fsm.finalize()

    def xy_scan_odmr(self, **kwargs):
        '''
        Hanyan Cai and Tian-Xing Zheng, Feb2025. Written from Guanming's odmr_run_with_2d_scan code and the xyscan code from scan.py
        XY Scan heat map with color based on ODMR contrast for a MW fixed frequency.
        '''
        with InstrumentGateway() as gw, DataSource('XY ODMR') as xy_scan_odmr_data:
            print("✅ Experiment DataSource connected to DataSink!")
            gw.fsm.initialize()

            # Define buffer size
            # This buffer will hold each self.read data values
            xy_scan_odmr_buffer_size = 2 * kwargs['runs_per_step'] + 1
            if xy_scan_odmr_buffer_size < 2:
                raise ValueError("Buffer size too small.")
            ni_sample_buffer = np.ascontiguousarray(np.zeros(xy_scan_odmr_buffer_size), dtype=np.uint32)
            xy_scan_odmr_buffer = [ni_sample_buffer]
            np.set_printoptions(precision=6)

            # We have one set frequency that ODMR scan uses
            frequency = kwargs['frequency']
            # There is no sweep of signal/background in a heat map
            '''signal_sweeps = StreamingList()
            background_sweeps = StreamingList()'''

            # Set initial parameters for instruments
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            
            # starting point for scan
            start_scan_pt = np.array([kwargs['x_center']-kwargs['scan_range']/2, kwargs['y_center']-kwargs['scan_range']/2])
            # number of pixels to scan in one line
            line_scan_steps = kwargs['line_scan_steps'] + 1
            # number of ODMR runs for each pixel
            runs_per_step = kwargs['runs_per_step']
            # vector in the X direction, direction of the line scan
            scan_vector = np.array([1,0])*kwargs['scan_range']
            # vector in the Y direction of stepping (normal to the line scan)
            extent_vector = np.array([0,1])*kwargs['scan_range']
            # Do snake scan or not
            snake_scan = kwargs['snake_scan']
            # Another delay between movement in the FSG
            delay = kwargs.get('delay', 0.01)
            # Laser probe time of ODMR
            probe_time = kwargs['probe_time']
            # Power of the microwave
            mw_power = kwargs['mw_power']
    
            if kwargs['odmr_sg'] == 'SRS':
                # Set the frequency of sg
                gw.sg.set_frequency(frequency)
                # Pulse Stramer Sequence
                if kwargs['odmr_type'] == 'CW':
                    #gw.ps.probe_time = kwargs['probe_time'] * 1e9 # change unit to ns
                    ps_seq = gw.ps.CW_ODMR(runs_per_step, probe_time * 1e9) # pulse streamer sequence for CW ODMR                
                elif kwargs['odmr_type']=='Pulsed':
                    #pi_xy, pi_time = kwargs['pi_xy'], kwargs['pi_time']*1e9 # these two parameters come from gui
                    ps_seq = gw.ps.Pulsed_ODMR(kwargs['xy'], kwargs['pi_time']*1e9, kwargs['runs'], kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9, kwargs['seq_gap']*1e9)
                    print('\nPulsed ODMR sequence generated!\n')
                else:
                    raise ValueError("\nWe can only do CW or pulsed ODMR for now!\n")
            # else:
            #     ps_seq = gw.ps.Pulsed_ODMR(kwargs['xy'], kwargs['pi']) # pulse streamer sequence for Pulsed ODMR
                gw.sg.set_rf_amplitude(mw_power)
                gw.sg.set_mod_type('QAM')
                gw.sg.set_rf_toggle(1)
                gw.sg.set_mod_toggle(1)
                gw.sg.set_mod_function('external')
            elif kwargs['odmr_sg'] == 'WindFreak':
                 # Set the frequency of sg
                gw.windfreak.set_freq_ch0(frequency)
                if kwargs['odmr_type'] == 'CW':
                    ps_seq = gw.ps.CW_ODMR_Switch(runs_per_step, probe_time * 1e9)  # Pulse streamer sequence for CW ODMR
                else:
                    raise ValueError("\nWe can only do CW ODMR for now!\n")
                gw.windfreak.set_power_ch0(mw_power)
                gw.windfreak.ch0_on()
            else:
                raise ValueError("\nWe only have Signal Generators: SRS or WindFreak!\n")

            gw.daq.open_task(len(xy_scan_odmr_buffer[0]))
            # Check if DAQ reader is initialized
            #if gw.daq.read_task is None or gw.daq.reader is None:
                # Ensure that the task is opened if it has not been done yet
                #gw.daq.open_task(odmr_2d_buffer_size)


            # Initialize a streamingList 
            # contrast_list = StreamingList()

            # For the progress bar, we will use the number of points completed as a metric
            # for completion. So we need to calculate the total number of points/spots
            total_points = kwargs['line_scan_steps'] * kwargs['extent_steps']

            # Data structure to store all of the x,y data
            xyscan_DataList = np.zeros((0,line_scan_steps))
            
            # To express the data structure in the format of the nspyre heatmap widget
            # We will need to scan line by line 
            xSteps = np.linspace(start_scan_pt[0], (start_scan_pt + scan_vector)[0], line_scan_steps, endpoint=True)
            ySteps = np.array([])

            with tqdm(total=total_points) as pbar:
                # Iterating over the y steps
                for s in range(kwargs['extent_steps'] + 1):
                    line_scan_start_pt = start_scan_pt + s/(kwargs['extent_steps']) * extent_vector
                    line_scan_stop_pt = line_scan_start_pt + scan_vector
                    ySteps = np.append(ySteps, np.array(line_scan_start_pt[1]))
                    # For every y change, we need to redefine the scan_vector
                    # for the correct orientation, since snake scan will change
                    # its direction
                    scan_vector = np.array([1,0])*kwargs['scan_range']
                    # First run goes from left to right (x row), even runs go from right to left
                    if snake_scan == 1 and (s+1)%2 == 0:
                        #print('s:', s)
                        # Switching the starting point and the ending point since we are going the backwards direction
                        tempory_point = line_scan_start_pt
                        line_scan_start_pt = line_scan_stop_pt
                        #print('line_scan_start_pt : ', line_scan_start_pt)
                        line_scan_stop_pt = tempory_point
                        # Snake scan goes backwards, so we set the scan vector to be negative
                        scan_vector = -scan_vector
                    
                    # Python list to temporarily store the x row contrast data
                    line_data = []
                    # For every y step, we iterate over the x row 
                    for x in range(line_scan_steps):
                        # This determines how much to go for each step
                        scan_point = line_scan_start_pt + x / kwargs['line_scan_steps'] * scan_vector
                        
                        # Moving the fsm to the step
                        x_pos = scan_point[0]
                        y_pos = scan_point[1]
                        print("Current position:", x_pos, y_pos)
                        gw.fsm.set_x(x_pos)  
                        gw.fsm.set_y(y_pos)
                        # Wait for the FSM to settle
                        time.sleep(delay)  

                        # The odmr result from the defined ODMR pulse sequence, one run
                        if kwargs['odmr_type']=='CW':
                            #TXZ: Here we set the # of runs to be 1, because we put the actual runs into the sequence directly
                            ### This self.read the the most "important" function, which let the pulse streamer starting streaming the seq and let the DAQ read data ####
                            odmr_result = self.read(xy_scan_odmr_buffer[0], ps_seq, 1) # read samples to buffer
                            sig, bg = self.digital_math(odmr_result, 'ODMR')
                        elif kwargs['odmr_type']=='Pulsed':
                            # Here since the Pulses_ODMR function inside pulses.py only generate the sequence for 1 run
                            odmr_result = self.read(xy_scan_odmr_buffer[0], ps_seq, kwargs['runs'])
                            sig, bg = self.digital_math(odmr_result, 'Pulsed ODMR', 1)
                        
                        # odmr_result = self.read(xy_scan_odmr_buffer[0], ps_seq, 1)
                        # Using digital math to extract the signal and background photon counts
                        # sig, bg = self.digital_math(odmr_result, 'ODMR')
                        
                        # Getting the difference value instead of the contrast value because we want to avoid the "0/0" problem when laser is on the very dim spots
                        diff = np.int32(bg) - np.int32(sig)
                        #contrast = (1 - (sig / bg)) * 100
                        # Adding the contrast value to the line_data list
                        #line_data.append(contrast)
                        line_data.append(diff)
                        print(f'Signal count = {sig}, Background count = {bg}, Difference = {diff}')
                        # Update progress bar by one, finishing one point
                        pbar.update(1)

                    if snake_scan == 1 and (s+1)%2 == 0:
                    # reversing the order of the line_data for snake_scan
                        line_data = line_data[::-1]    

                    # Convert line_data to numpy array, needs to be numpy for the np.append function below
                    line_data = np.array(line_data)
                    #print("line_data is:\n", line_data)
                    xyscan_DataList = np.append(xyscan_DataList, line_data.reshape((1,line_scan_steps)), axis=0)
                    #print("xyscan_DataList is:\n", xyscan_DataList)
                    # contrast_list.append(np.stack([line_data]))

                    print("📡 Preparing data for DataSource push...")
                    #print(f"📊 xSteps: {xSteps.shape}, ySteps: {ySteps.shape}, xyscan_DataList: {xyscan_DataList.shape}")

                    # contrast_list.updated_item(-1)

                    # Push data to the server
                    xy_scan_odmr_data.push({'title': 'XY Scan',    
                                'xLabel': 'X (um)',
                                'yLabel': 'Y (um)',
                                'zLabel': 'Counts',
                                'datasets': {'xSteps':xSteps, 'ySteps':ySteps, 'ScanCounts': xyscan_DataList}})
                    
                    print("✅ Data pushed successfully to DataSource!")
                    

                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        #gw.daq.close_task()
                        gw.sg.set_rf_toggle(0)
                        gw.sg.set_mod_toggle(0)
                        gw.ps.Pulser.reset()
                        gw.laser.off()
                        gw.fsm.finalize()
                        print('Stopped by GUI request')
                        return

                # Close tasks and reset devices
                #gw.daq.close_task()
                gw.sg.set_rf_toggle(0)
                gw.sg.set_mod_toggle(0)
                gw.ps.Pulser.reset()
                gw.laser.off()
                gw.fsm.finalize()

    def odmr_double_resonance(self, **kwargs):
        '''
        Developed by Tian-Xing in 2025 March
        '''
        with InstrumentGateway() as gw, DataSource('ODMR_doubleresonance') as odmr_doubleresonance_data:

            # define buffer size here
            odmr_buffer_size = 2*kwargs['runs']+1
            if odmr_buffer_size < 2:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(odmr_buffer_size), dtype = np.uint32)
            odmr_buffer = [ni_sample_buffer]

            np.set_printoptions(precision = 6)

            # frequencies that will be swept over in the ODMR measurement
            frequencies = np.linspace(kwargs['start_freq'], kwargs['stop_freq'], kwargs['num_points'])

            signal_sweeps = StreamingList()
            background_sweeps = StreamingList()

            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()

            # Set the correct Signal Generator
            
            ps_seq = gw.ps.ODMR_DoubleResonance(kwargs['xy'], kwargs['pi_time_fix']*1e9,kwargs['pi_time_sweep']*1e9, kwargs['switch_delay']*1e9, kwargs['runs'], kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9, kwargs['seq_gap']*1e9)
            gw.sg.set_rf_amplitude(kwargs['mw_fix_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')
            gw.sg.set_frequency(kwargs['mw_fix_freq']) # set particular SG396 frequency

            gw.windfreak.set_power_ch0(kwargs['mw_sweep_power'])
            gw.windfreak.ch0_on()

            gw.daq.open_task(len(odmr_buffer[0]))

            with tqdm(total = kwargs['iterations']) as pbar:

                for iter in range(kwargs['iterations']):
                    # photon counts corresponding to each frequency
                    # initialize to NaN
                    sig_counts = np.empty(kwargs['num_points'])
                    sig_counts[:] = np.nan
                    signal_sweeps.append(np.stack([frequencies/1e9, sig_counts]))
                    bg_counts = np.empty(kwargs['num_points'])
                    bg_counts[:] = np.nan
                    background_sweeps.append(np.stack([frequencies/1e9, bg_counts]))
                    
                    for f, freq in enumerate(frequencies):
                        gw.windfreak.set_freq_ch0(freq)
                        
                        # partition buffer into signal and background datasets
                        odmr_result = self.read(odmr_buffer[0], ps_seq, kwargs['runs'])
                        sig, bg = self.digital_math(odmr_result, 'Pulsed ODMR', 1)

                        # record the photon counts
                        signal_sweeps[-1][1][f] = sig
                        background_sweeps[-1][1][f] = bg
                        # notify the streaminglist that this entry has updated so it will be pushed to the data server
                        signal_sweeps.updated_item(-1)
                        background_sweeps.updated_item(-1)

                        odmr_doubleresonance_data.push({'params': {'start': kwargs['start_freq'], 'stop': kwargs['stop_freq'], 'num_points': kwargs['num_points'], 'iterations': kwargs['iterations']},
                                    'title': 'ODMR double resonance',
                                    'xlabel': 'Frequency (GHz)',
                                    'ylabel': 'Counts',
                                    'datasets': {'signal' : signal_sweeps,
                                                'background': background_sweeps}
                        })

                        # potential position to add the XY sweeping or point defect PL tracking
                        if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                            gw.daq.close_task()
                            gw.sg.set_rf_toggle(0)
                            gw.sg.set_mod_toggle(0)
                            gw.ps.Pulser.reset()
                            gw.laser.off()
                            gw.windfreak.ch0_off()
                            print('the GUI has asked us nicely to exit')
                            return

                    pbar.update(1)

                # close DAQ task + reset SG396 and PS parameters
                gw.daq.close_task()
                gw.sg.set_rf_toggle(0)
                gw.sg.set_mod_toggle(0)
                gw.ps.Pulser.reset()
                gw.laser.off()
                gw.windfreak.ch0_off()

    def mw_saturation_run(self, **kwargs):
        
        with InstrumentGateway() as gw, DataSource('ODMR') as odmr_data:
            # define buffer size here
            odmr_buffer_size = 2*kwargs['runs']
            if odmr_buffer_size < 2:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(odmr_buffer_size, dtype=np.float64))
            odmr_buffer = [ni_sample_buffer]

            # frequencies and powers that will be swept over in the ODMR measurement
            frequencies = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_freq_pts'])

            if kwargs['mw_start_unit'] == 'mW':
                rf_start_pow = np.log10(rf_start_pow*1e-3)
            elif kwargs['mw_start_unit'] == 'uW':
                rf_start_pow = np.log10(rf_start_pow*1e-6)
            elif kwargs['mw_start_unit'] == 'nW':
                rf_start_pow = np.log10(rf_start_pow*1e-9)

            if kwargs['mw_stop_unit'] == 'mW':
                rf_stop_pow = np.log10(rf_stop_pow*1e-3)
            elif kwargs['mw_stop_unit'] == 'uW':
                rf_stop_pow = np.log10(rf_stop_pow*1e-6)
            elif kwargs['mw_stop_unit'] == 'nW':
                rf_stop_pow = np.log10(rf_stop_pow*1e-9)

            powers = np.logspace(kwargs['start_pow'], kwargs['stop_pow'], kwargs['num_pow_pts'])
            
            contrast_data = np.ones(kwargs['num_pow_pts'])

            dataset = {'contrast': []}

            # set initial parameters for instrument server devices
            gw.laser.set_modulation_state('cw')
            gw.laser.set_analog_control_mode('current')
            gw.laser.set_diode_current_realtime(110)
            gw.laser.laser_on()
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')

            # set initial parameters for instrument server devices
            gw.ps.probe_time = kwargs['probe'] * 1e9
            gw.ps.clock_time = 11 # [ns] width of our clock pulse.
            gw.ps.runs = kwargs['runs'] #number of runs per point

            ps_seq = gw.ps.CW_ODMR() # pulse streamer sequence for CW ODMR

            with tqdm(total = kwargs['num_pow_pts']) as pbar:

                for iter, rfpow in enumerate(powers):
                    
                    dataset['contrast'].append(np.stack([frequencies/1e9, contrast_data]))

                    for f, freq in enumerate(frequencies):
                        
                        gw.sg.set_rf_amplitude(rfpow)
                        gw.sg.set_frequency(freq)

                        odmr_result = self.read(odmr_buffer[0], ps_seq, kwargs['runs']) # read samples to buffer

                        sig = self.analog_math(odmr_result, 'ODMR')[0]
                        bck = self.analog_math(odmr_result, 'ODMR')[1]

                        contrast_data[f] = sig/bck

                        dataset['contrast'][-1][1][f] = sig/bck

                        odmr_data.push({'params': {'iteration': iter, 'freq_idx': f, 'freq_num': kwargs['num_freq_pts'], 'pow_num': kwargs['num_pow_pts']}, 
                                        'dataset': dataset})

                    pbar.update(1)

            # close DAQ task + reset SG396 and PS parameters
            # print("TASK ID: ", gw.daq.read_task)
            gw.daq.close_task()
            gw.sg.set_rf_toggle(0)
            gw.sg.set_mod_toggle(0)
            gw.ps.Pulser.reset()

    def rabi_run(self, **kwargs):
        '''
        Developed by Tian-Xing in Sept.2023
        '''
        with InstrumentGateway() as gw, DataSource("Rabi") as rabi_data:
            
            # pi pulse durations that will be swept over in the Rabi measurement (converted to ns)
            mw_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
            #num_mw = len(mw_times)

            # define buffer size here
            rabi_buffer_size = 4*kwargs['runs']*kwargs['num_pts']
            if rabi_buffer_size < 4:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(rabi_buffer_size, dtype=np.uint32))
            rabi_buffer = [ni_sample_buffer]

            signal_sweeps = StreamingList()
            background_sweeps = StreamingList()

            np.random.shuffle(mw_times) # random shuffel the mw_times for balancing the heating and charge of the sample
            print("MW times after random shuffle:", mw_times)

            # pulse streamer sequence
            if kwargs['rabi_type'] == "SRS":
                print("USING SRS FOR RABI MEASUREMENT.")
                ps_seq = gw.ps.Rabi(mw_times, kwargs['xy'], kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9, kwargs['seq_gap']*1e9)
                # Setup the MW
                gw.sg.set_frequency(kwargs['freq'])
                gw.sg.set_rf_amplitude(kwargs['rf_power'])
                gw.sg.set_mod_type('QAM')
                gw.sg.set_rf_toggle(1)
                gw.sg.set_mod_toggle(1)
                gw.sg.set_mod_function('external')
            elif kwargs['rabi_type'] == "WindFreak":
                print("USING WINDFREAK FOR RABI MEASUREMENT.")
                ps_seq = gw.ps.Rabi_WindFreak(mw_times, kwargs['xy'], kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9, kwargs['switch_delay']*1e9, kwargs['seq_gap']*1e9)
                # Setup the MW
                gw.windfreak.set_power_ch0(kwargs['rf_power'])
                gw.windfreak.set_freq_ch0(kwargs['freq'])
                gw.windfreak.ch0_on()
            else:
                raise ValueError("Rabi Type must be SRS or WindFreak!")
            
            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            # Open a readout task on DAQ
            gw.daq.open_task(rabi_buffer_size)
            

            # index order of sorted mw_times 
            # used to match x and y axis order for plotting
            index_order = np.argsort(mw_times) 
            mw_times_ordered = np.sort(mw_times) # record the ordered mw_times for Rabi plotting
            #print('mw_times after np.sort is: \n',mw_times)
            #dataset['mw_times'] = np.sort(mw_times) # order mw_times for Rabi plotting

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):
                    
                    rabi_result = self.read(rabi_buffer[0], ps_seq, kwargs['runs'])

                    # partition buffer into signal and background datasets
                    sig_array, bg_array = self.digital_math(rabi_result, 'Rabi', kwargs['num_pts'])
                    
                    
                    # correct the y-axis data ordering for plots
                    sig_array = np.array([sig_array[i] for i in index_order])
                    bg_array = np.array([bg_array[i] for i in index_order])
                    #print('mw_times_ordered is: \n',mw_times_ordered)
                    signal_sweeps.append(np.stack([mw_times_ordered, sig_array]))
                    background_sweeps.append(np.stack([mw_times_ordered, bg_array]))
                    # notify the streaminglist that this entry has updated so it will be pushed to the data server
                    signal_sweeps.updated_item(-1)
                    background_sweeps.updated_item(-1)

                    
                    rabi_data.push({'params': {'mw_num': kwargs['num_pts'], 'iter_num': kwargs['iters'],'runs_num': kwargs['runs']},
                                    'title': 'Rabi',
                                    'xlabel': 'MW Time (ns)',
                                    'ylabel': 'Counts',
                                    'datasets': {'signal' : signal_sweeps,
                                                'background': background_sweeps}
                    })
                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        gw.daq.close_task()
                        gw.ps.Pulser.reset()
                        gw.laser.off()
                        if kwargs['rabi_type'] == "SRS":
                            gw.sg.set_rf_toggle(0)
                            gw.sg.set_mod_toggle(0)
                        else:
                            gw.windfreak.ch0_off()
                        print('the GUI has asked us nicely to exit')
                        return

                    pbar.update(1)

            gw.daq.close_task()
            gw.ps.Pulser.reset()
            gw.laser.off()
            if kwargs['rabi_type'] == "SRS":
                gw.sg.set_rf_toggle(0)
                gw.sg.set_mod_toggle(0)
            else:
                gw.windfreak.ch0_off()

    def rabi_run_R(self, **kwargs):  # Rolando version
        '''
        Developed by Tian-Xing in Sept.2023
        '''
        with InstrumentGateway() as gw, DataSource("Rabi") as rabi_data:
            
            np.set_printoptions(precision=6)

            # pi pulse durations that will be swept over in the Rabi measurement (converted to ns)
            mw_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
            #num_mw = len(mw_times)

            signal_sweeps = StreamingList()
            background_sweeps = StreamingList()

                        
            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.laser.cw_mode()
            gw.laser.get_power()
            gw.laser.set_power(10) # set laser power to 10% 
            gw.laser.on()

            # pulse streamer sequence
            if kwargs['rabi_type'] == "SRS":
                print("USING SRS FOR RABI MEASUREMENT.")
                ps_seq = gw.ps.Rabi_R(mw_times, kwargs['xy'], kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9, kwargs['seq_gap']*1e9)
                # Setup the MW
                gw.sg.set_frequency(kwargs['freq'])
                gw.sg.set_rf_amplitude(kwargs['rf_power'])
                gw.sg.set_mod_type(6)
                gw.sg.set_qmod_function(5)
                gw.sg.set_mod_toggle(1)
                gw.sg.set_rf_toggle(1)
            else:
                raise ValueError("Rabi Type must be SRS!")

            """ Time Tagger Channel, Trigger Level and Counting Event Setup """
            tt_gate_ch = 1
            tt_sync_ch = 2
            tt_spcm_ch = 3

            gw.daq.set_trigger_level(tt_gate_ch, 1.3)   # Gate channel trigger level
            gw.daq.set_trigger_level(tt_sync_ch, 1.3)   # Sync channel trigger level
            gw.daq.set_trigger_level(tt_spcm_ch, 1.1)   # SPCM channel trigger level

            runs = 20000

            gw.daq.start_cbm(tt_spcm_ch, tt_gate_ch, -tt_gate_ch, 2*len(mw_times)*runs)
            gw.daq.CBM_start()
            gw.daq.sync()

            gw.ps.stream(obtain(ps_seq), runs)
            ready = False

            while ready is False:
                ready = gw.daq.cbm_ready()
                counts = gw.daq.count_BM()
                
            i = 0
            sig = np.zeros(len(mw_times))
            bg = np.zeros(len(mw_times))
            length_unit = len(mw_times)*2 # Length of data values in one full sequence (signal + background)
            while i < len(counts):
                unit_data = counts[i:i+length_unit] # Used to separate data for a single full sequence
                sig += unit_data[1::2]
                bg += unit_data[::2]
                i += length_unit

            sig = sig/runs
            bg = bg/runs

            signal_sweeps.append(sig)
            background_sweeps.append(bg)
            # notify the streaminglist that this entry has updated so it will be pushed to the data server
            signal_sweeps.updated_item(-1)
            background_sweeps.updated_item(-1)

                
            rabi_data.push({'params': {'mw_num': kwargs['num_pts'], 'iter_num': kwargs['iters'],'runs_num': kwargs['runs']},
                            'title': 'Rabi',
                            'xlabel': 'MW Time (ns)',
                            'ylabel': 'Counts',
                            'datasets': {'signal' : signal_sweeps,
                                        'background': background_sweeps}
            })
            if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                # gw.daq.free_time_tagger()
                gw.sg.set_rf_toggle(0)
                gw.sg.set_mod_toggle(0)
                gw.ps.ps_reset()
                gw.laser.get_power()
                gw.laser.off()
                gw.laser.set_power(0)
                # if kwargs['rabi_type'] == "SRS":
                #else:
                # gw.windfreak.ch0_off()
                print('the GUI has asked us nicely to exit')
                return

                

        # We turn OFF the mw signal (modulation and amplitude)        
        gw.sg.set_rf_toggle(0)
        gw.sg.set_mod_toggle(0)
        gw.laser.off()
        gw.laser.get_power()
        gw.laser.set_power(0)
        gw.ps.ps_reset()
        gw.daq.free_time_tagger()
        # if kwargs['rabi_type'] == "SRS":
            
            
    
    def DEER_FID_run_Evan(self, **kwargs):
        '''
        Developed by Evan
        '''
        with InstrumentGateway() as gw, DataSource('DEER_FID') as deer_data:
            print("Running DEER FID...")
            # frequencies that will be swept over in the ODMR measurement
            tau_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
            tau_times = np.insert(tau_times, 0, 1) # insert 1 ns as first data point that will be skipped in plotting           
            num_tau = len(tau_times)

            # define buffer size here
            deer_fid_buffer_size = 4*kwargs['runs']*num_tau

            if deer_fid_buffer_size < 4:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(deer_fid_buffer_size, dtype=np.float64))
            deer_fid_buffer = [ni_sample_buffer]
            
            x_axis_data = np.delete(tau_times, 0)/1e9

            dataset = {'taus': x_axis_data,
                       'dark_ms1': np.zeros((kwargs['iters'], kwargs['num_pts'])), 
                       'dark_ms0': np.zeros((kwargs['iters'], kwargs['num_pts'])),
                       'echo_ms1': np.zeros((kwargs['iters'], kwargs['num_pts'])),
                       'echo_ms0': np.zeros((kwargs['iters'], kwargs['num_pts'])),
                       'sum_dark_ms1': np.zeros(kwargs['num_pts']),
                       'sum_dark_ms0': np.zeros(kwargs['num_pts']),
                       'sum_echo_ms1': np.zeros(kwargs['num_pts']),
                       'sum_echo_ms0': np.zeros(kwargs['num_pts'])}

            # set initial parameters for instrument server devices
            gw.laser.set_modulation_state('pulsed')
            gw.laser.set_analog_control_mode('current')
            gw.laser.set_diode_current_realtime(110)
            gw.laser.laser_on()
            gw.sg.set_frequency(kwargs['freq'])
            gw.sg.set_rf_amplitude(kwargs['rf_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')

            gw.ps.laser_time = kwargs['init'] * 1e9 # initialization pulse duration
            gw.ps.readout_time = kwargs['read'] * 1e9 # readout window duration
            gw.ps.clock_time = 11 # [ns] width of our clock pulse.
            gw.ps.runs = kwargs['runs'] # number of runs per point

            for i in range(2):
                kwargs['pihalf'][i] = kwargs['pihalf'][i]*1e9
                kwargs['pi'][i] = kwargs['pi'][i]*1e9

            ps_seq = gw.ps.DEER_FID_2(tau_times, kwargs['pihalf'][0], kwargs['pihalf'][1], 
                                kwargs['pi'][0], kwargs['pi'][1], kwargs['n'])

            gw.daq.open_task(len(deer_fid_buffer[0]))

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):
                    
                    deer_fid_result = self.read(deer_fid_buffer[0], ps_seq, kwargs['runs']) # read samples to buffer
                    # average runs from deer_result data for each of the 4 datasets (dark_ms1, dark_ms0, echo_ms1, echo_ms0) 
                    # individually and then assign averaged data value to corresponding data array
                    dark_ms1 = self.analog_math(deer_fid_result, 'DEER_2', num_tau)[0]
                    dark_ms0 = self.analog_math(deer_fid_result, 'DEER_2', num_tau)[1]
                    echo_ms1 = self.analog_math(deer_fid_result, 'DEER_2', num_tau)[2]
                    echo_ms0 = self.analog_math(deer_fid_result, 'DEER_2', num_tau)[3]

                    # delete the "1 ns" data point from the set and use the rest for plotting
                    dark_ms1 = np.delete(dark_ms1, 0)
                    dark_ms0 = np.delete(dark_ms0, 0)
                    echo_ms1 = np.delete(echo_ms1, 0)
                    echo_ms0 = np.delete(echo_ms0, 0)
                    # FID_contrast = ((dark_ms0 - dark_ms1)/(dark_ms0 + dark_ms1)) / ((echo_ms0 - echo_ms1)/(echo_ms0 + echo_ms1))

                    dataset['dark_ms1'][iter] = dark_ms1
                    dataset['dark_ms0'][iter] = dark_ms0
                    dataset['echo_ms1'][iter] = echo_ms1
                    dataset['echo_ms0'][iter] = echo_ms0

                    dataset['sum_dark_ms1'] = dataset['sum_dark_ms1'] + dark_ms1
                    dataset['sum_dark_ms0'] = dataset['sum_dark_ms0'] + dark_ms0
                    dataset['sum_echo_ms1'] = dataset['sum_echo_ms1'] + echo_ms1
                    dataset['sum_echo_ms0'] = dataset['sum_echo_ms0'] + echo_ms0

                    # dataset['dark_ms1'].append(np.stack([tau_times/1e3, dark_ms1]))
                    # dataset['dark_ms0'].append(np.stack([tau_times/1e3, dark_ms0]))
                    # dataset['echo_ms1'].append(np.stack([tau_times/1e3, echo_ms1]))
                    # dataset['echo_ms0'].append(np.stack([tau_times/1e3, echo_ms0]))

                    deer_data.push({'params': {'iter_num': kwargs['iters'], 'tau_num': num_tau, 
                                                'iter_idx': iter,
                                                'runs_num': kwargs['runs'],
                                                'rf_power': kwargs['rf_power'], 'freq': kwargs['freq']}, 
                                   'dataset': dataset})
                    
                    pbar.update(1)
                    
            gw.daq.close_task()
            gw.sg.set_rf_toggle(0) 
            gw.sg.set_mod_toggle(0) 
            gw.ps.Pulser.reset()

    def DEER_FID_run(self, **kwargs):
        '''
        Developed by Hanyan April2.2024. Based on DEER_rabi_run logic.
        '''
        with InstrumentGateway() as gw, DataSource('DEER_FID') as DEER_FID_data:
            if kwargs['tau_type']=='linear':
                tau_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
                print("Using linear sampling.")
            #These code is copied from T2 run. The commented codes are ones not needed.
            #x_axis_data = np.copy(tau_times)
            #tau_times = self.sort_taus_for_balance(tau_times) 
            #index_order = np.argsort(tau_times) 
            #tau_balance = True
            elif kwargs['tau_type']=='exp':
                tau_times = np.geomspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
                print("Using exponential sampling.")
            #x_axis_data = np.copy(tau_times)
            #np.random.shuffle(tau_times)
            # index order of sorted mw_times used to match x and y axis order for plotting
            #index_order = np.argsort(tau_times) 
            #tau_balance = False
            #The interaction times between the rf-pulses.
            #num_tau = len(tau_times)

            # define buffer size here
            deer_FID_buffer_size = 8*kwargs['runs']*kwargs['num_pts']
            if deer_FID_buffer_size < 8:
                raise ValueError("Buffer size too small.")
            
            ni_sample_buffer = np.ascontiguousarray(np.zeros(deer_FID_buffer_size, dtype=np.uint32))
            deer_FID_buffer = [ni_sample_buffer]

            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            # Setup the SRS
            gw.sg.set_frequency(kwargs['nv_mw_freq'])
            gw.sg.set_rf_amplitude(kwargs['nv_mw_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')
            # Setup the WindFreak power and frequency
            gw.windfreak.set_power_ch0(kwargs['el_mw_power'])
            gw.windfreak.set_freq_ch0(kwargs['el_mw_freq'])
            gw.windfreak.ch0_on()

            print("Tau times before random shuffle:", tau_times)
            np.random.shuffle(tau_times) # random shuffle the mw_times for balancing the heating and charge of the sample
            print("Tau times after random shuffle:", tau_times)

            #tau_times = np.insert(tau_times, 0, 1) # insert 1 ns as first data point that will be skipped in plotting           
            # TXZ: The reason we have this first 1ns data point (but throw it away when plotting) is to warm up the experimentl setup
            num_tau = len(tau_times)

            ps_seq = gw.ps.DEER_FID(tau_times, kwargs['pihalf_x']*1e9, kwargs['pihalf_y']*1e9, kwargs['pi_x']*1e9, kwargs['pi_y']*1e9, kwargs['pi_electron']*1e9, 
                                kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9, kwargs['seq_gap']*1e9)

            # index order of sorted mw_times 
            # used to match x and y axis order for plotting
            index_order = np.argsort(tau_times) 
            tau_times_ordered = np.sort(tau_times) # record the ordered mw_times for Rabi plotting
            # order mw_times for Rabi plotting

            gw.daq.open_task(len(deer_FID_buffer[0]))
            dark_ms1_sweeps = StreamingList()
            dark_ms0_sweeps = StreamingList()
            echo_ms1_sweeps = StreamingList()
            echo_ms0_sweeps = StreamingList()

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):
                    
                    deer_FID_result = self.read(deer_FID_buffer[0], ps_seq, kwargs['runs'])

                    # partition buffer into signal and background datasets
                    dark_ms1_array, dark_ms0_array, echo_ms1_array, echo_ms0_array = self.digital_math(deer_FID_result, 'DEER_FID', kwargs['num_pts'])
                    
                    # correct the y-axis data ordering for plots
                    dark_ms1_array = np.array([dark_ms1_array[i] for i in index_order])
                    dark_ms0_array = np.array([dark_ms0_array[i] for i in index_order])
                    echo_ms1_array = np.array([echo_ms1_array[i] for i in index_order])
                    echo_ms0_array = np.array([echo_ms0_array[i] for i in index_order])
                    #print('tau_times is: \n',tau_times)
                    #Multipying tau_times by two because the x-axis will be 2tau
                    dark_ms1_sweeps.append(np.stack([2 * tau_times_ordered, dark_ms1_array]))
                    dark_ms0_sweeps.append(np.stack([2 * tau_times_ordered, dark_ms0_array]))
                    echo_ms1_sweeps.append(np.stack([2 * tau_times_ordered, echo_ms1_array]))
                    echo_ms0_sweeps.append(np.stack([2 * tau_times_ordered, echo_ms0_array]))
                    # notify the streaminglist that this entry has updated so it will be pushed to the data server
                    dark_ms1_sweeps.updated_item(-1)
                    dark_ms0_sweeps.updated_item(-1)
                    echo_ms1_sweeps.updated_item(-1)
                    echo_ms0_sweeps.updated_item(-1)
                    #print('\nfreq now:',freq)
                    #print('\ndark_ms1_sweeps[-1] = ',dark_ms1_sweeps[-1])
                    DEER_FID_data.push({'params': {'start': kwargs['start'], 'stop': kwargs['stop'], 'num_pts': kwargs['num_pts'], 'iterations': kwargs['iters']},
                                'title': 'DEER FID',
                                'xlabel': '2 tau (ns)',
                                'ylabel': 'Counts',
                                'datasets': {'dark_ms1' : dark_ms1_sweeps,
                                            'dark_ms0': dark_ms0_sweeps,
                                            'echo_ms1' : echo_ms1_sweeps,
                                            'echo_ms0': echo_ms0_sweeps}
                    })
                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        gw.daq.close_task()
                        gw.sg.set_rf_toggle(0)
                        gw.sg.set_mod_toggle(0)
                        gw.ps.Pulser.reset()
                        gw.laser.off()
                        gw.windfreak.ch0_off()
                        print('the GUI has asked us nicely to exit')
                        return
                    pbar.update(1)

        gw.daq.close_task()
        gw.sg.set_rf_toggle(0) 
        gw.sg.set_mod_toggle(0) 
        gw.ps.Pulser.reset()
        gw.laser.off()
        gw.windfreak.ch0_off()                 

    def DEER_run(self, **kwargs):
        '''
        Developed by Tian-Xing at Sept.2023
        '''
        with InstrumentGateway() as gw, DataSource('DEER') as deer_data:
            frequencies = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts'])      
            #num_freqs = len(frequencies)

            # define buffer size here
            # We need 8*kwargs['runs'] here because we have 4 sequence for DEER (with&without pi-pulse on reporter spin, and +- pi/2 for reference), the DAQ also needs two sets of data for the NV readout
            deer_buffer_size = 8*kwargs['runs']
            if deer_buffer_size < 8:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(deer_buffer_size, dtype=np.uint32))
            deer_buffer = [ni_sample_buffer]
            
            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            # Setup the SRS
            gw.sg.set_frequency(kwargs['nv_mw_freq'])
            gw.sg.set_rf_amplitude(kwargs['nv_mw_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')
            # Setup the WindFreak power
            gw.windfreak.set_power_ch0(kwargs['el_mw_power'])
            #init_time, read_time, wait_time, read_wait, seq_gap = kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9, kwargs['seq_gap']*1e9

            ps_seq = gw.ps.DEER(kwargs['pihalf_x']*1e9, kwargs['pihalf_y']*1e9, 
                                kwargs['pi_x']*1e9, kwargs['pi_y']*1e9, 
                                kwargs['tau']*1e9, kwargs['pi_electron']*1e9, kwargs['switch_delay']*1e9, 
                                kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9, kwargs['seq_gap']*1e9)
                        
            gw.daq.open_task(len(deer_buffer[0]))
            dark_ms1_sweeps = StreamingList()
            dark_ms0_sweeps = StreamingList()
            echo_ms1_sweeps = StreamingList()
            echo_ms0_sweeps = StreamingList()

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):
                    # photon counts corresponding to each frequency
                    # initialize to NaN
                    dark_ms1 = np.empty(kwargs['num_pts'])
                    dark_ms1[:] = np.nan
                    dark_ms1_sweeps.append(np.stack([frequencies/1e9, dark_ms1]))
                    dark_ms0 = np.empty(kwargs['num_pts'])
                    dark_ms0[:] = np.nan
                    dark_ms0_sweeps.append(np.stack([frequencies/1e9, dark_ms0]))
                    echo_ms1 = np.empty(kwargs['num_pts'])
                    echo_ms1[:] = np.nan
                    echo_ms1_sweeps.append(np.stack([frequencies/1e9, echo_ms1]))
                    echo_ms0 = np.empty(kwargs['num_pts'])
                    echo_ms0[:] = np.nan
                    echo_ms0_sweeps.append(np.stack([frequencies/1e9, echo_ms0]))
                    for f, freq in enumerate(frequencies):
                        gw.windfreak.set_freq_ch0(freq)
                        gw.windfreak.ch0_on()
                        #gw.windfreak.ch0_off()#For debug
                        #print('\nset WindFreak Freq to be:',freq)
                        #print('\nWindFreak Freq now is:', gw.windfreak.get_freq_ch0())
                        deer_result = self.read(deer_buffer[0], ps_seq, kwargs['runs'])
                        dark_ms1, dark_ms0, echo_ms1, echo_ms0 = self.digital_math(deer_result, 'DEER')
                        # record the photon counts
                        dark_ms1_sweeps[-1][1][f] = dark_ms1
                        dark_ms0_sweeps[-1][1][f] = dark_ms0
                        echo_ms1_sweeps[-1][1][f] = echo_ms1
                        echo_ms0_sweeps[-1][1][f] = echo_ms0
                        # notify the streaminglist that this entry has updated so it will be pushed to the data server
                        dark_ms1_sweeps.updated_item(-1)
                        dark_ms0_sweeps.updated_item(-1)
                        echo_ms1_sweeps.updated_item(-1)
                        echo_ms0_sweeps.updated_item(-1)
                        #print('\nfreq now:',freq)
                        #print('\ndark_ms1_sweeps[-1] = ',dark_ms1_sweeps[-1])
                        deer_data.push({'params': {'start': kwargs['start'], 'stop': kwargs['stop'], 'num_pts': kwargs['num_pts'], 'iterations': kwargs['iters']},
                                    'title': 'DEER',
                                    'xlabel': 'Frequency (GHz)',
                                    'ylabel': 'Counts',
                                    'datasets': {'dark_ms1' : dark_ms1_sweeps,
                                                'dark_ms0': dark_ms0_sweeps,
                                                'echo_ms1' : echo_ms1_sweeps,
                                                'echo_ms0': echo_ms0_sweeps}
                        })
                        if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                            gw.daq.close_task()
                            gw.sg.set_rf_toggle(0)
                            gw.sg.set_mod_toggle(0)
                            gw.ps.Pulser.reset()
                            gw.laser.off()
                            gw.windfreak.ch0_off()
                            print('the GUI has asked us nicely to exit')
                            return
                    pbar.update(1)

            gw.daq.close_task()
            gw.sg.set_rf_toggle(0) 
            gw.sg.set_mod_toggle(0) 
            gw.ps.Pulser.reset()
            gw.laser.off()
            gw.windfreak.ch0_off()

    def DEER_Padding_run(self, **kwargs):
            '''
            Developed by Tian-Xing at Sept.2023
            '''
            with InstrumentGateway() as gw, DataSource('DEER_Padding') as DEER_Padding_data:
                frequencies = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts'])      
                #num_freqs = len(frequencies)

                # define buffer size here
                # We need 8*kwargs['runs'] here because we have 4 sequence for DEER (with&without pi-pulse on reporter spin, and +- pi/2 for reference), the DAQ also needs two sets of data for the NV readout
                deerPadding_buffer_size = 8*kwargs['runs']
                if deerPadding_buffer_size < 8:
                    raise ValueError("Buffer size too small.")

                ni_sample_buffer = np.ascontiguousarray(np.zeros(deerPadding_buffer_size, dtype=np.uint32))
                deerPadding_buffer = [ni_sample_buffer]
                
                # set initial parameters for instrument server devices
                # Turn on the laser
                gw.ps.laser_on()
                gw.laser.las_mode()
                gw.laser.on()
                # Setup the SRS
                gw.sg.set_frequency(kwargs['nv_mw_freq'])
                gw.sg.set_rf_amplitude(kwargs['nv_mw_power'])
                gw.sg.set_mod_type('QAM')
                gw.sg.set_rf_toggle(1)
                gw.sg.set_mod_toggle(1)
                gw.sg.set_mod_function('external')
                # Setup the WindFreak power
                gw.windfreak.set_power_ch0(kwargs['el_mw_power'])

                ps_seq = gw.ps.DEER_Padding(kwargs['pihalf_x']*1e9, kwargs['pihalf_y']*1e9, 
                                    kwargs['pi_x']*1e9, kwargs['pi_y']*1e9, 
                                    kwargs['tau']*1e9, kwargs['pi_electron']*1e9, kwargs['scan_time']*1e9)
                            
                gw.daq.open_task(len(deerPadding_buffer[0]))
                dark_ms1_sweeps = StreamingList()
                dark_ms0_sweeps = StreamingList()
                echo_ms1_sweeps = StreamingList()
                echo_ms0_sweeps = StreamingList()

                with tqdm(total = kwargs['iters']) as pbar:

                    for iter in range(kwargs['iters']):
                        # photon counts corresponding to each frequency
                        # initialize to NaN
                        dark_ms1 = np.empty(kwargs['num_pts'])
                        dark_ms1[:] = np.nan
                        dark_ms1_sweeps.append(np.stack([frequencies/1e9, dark_ms1]))
                        dark_ms0 = np.empty(kwargs['num_pts'])
                        dark_ms0[:] = np.nan
                        dark_ms0_sweeps.append(np.stack([frequencies/1e9, dark_ms0]))
                        echo_ms1 = np.empty(kwargs['num_pts'])
                        echo_ms1[:] = np.nan
                        echo_ms1_sweeps.append(np.stack([frequencies/1e9, echo_ms1]))
                        echo_ms0 = np.empty(kwargs['num_pts'])
                        echo_ms0[:] = np.nan
                        echo_ms0_sweeps.append(np.stack([frequencies/1e9, echo_ms0]))
                        for f, freq in enumerate(frequencies):
                            gw.windfreak.set_freq_ch0(freq)
                            gw.windfreak.ch0_on()
                            #gw.windfreak.ch0_off()#For debug
                            #print('\nset WindFreak Freq to be:',freq)
                            #print('\nWindFreak Freq now is:', gw.windfreak.get_freq_ch0())
                            deerPadding_result = self.read(deerPadding_buffer[0], ps_seq, kwargs['runs'])
                            dark_ms1, dark_ms0, echo_ms1, echo_ms0 = self.digital_math(deerPadding_result, 'DEER')
                            # record the photon counts
                            dark_ms1_sweeps[-1][1][f] = dark_ms1
                            dark_ms0_sweeps[-1][1][f] = dark_ms0
                            echo_ms1_sweeps[-1][1][f] = echo_ms1
                            echo_ms0_sweeps[-1][1][f] = echo_ms0
                            # notify the streaminglist that this entry has updated so it will be pushed to the data server
                            dark_ms1_sweeps.updated_item(-1)
                            dark_ms0_sweeps.updated_item(-1)
                            echo_ms1_sweeps.updated_item(-1)
                            echo_ms0_sweeps.updated_item(-1)
                            #print('\nfreq now:',freq)
                            #print('\ndark_ms1_sweeps[-1] = ',dark_ms1_sweeps[-1])
                            DEER_Padding_data.push({'params': {'start': kwargs['start'], 'stop': kwargs['stop'], 'num_pts': kwargs['num_pts'], 'iterations': kwargs['iters']},
                                        'title': 'DEER Padding',
                                        'xlabel': 'Frequency (GHz)',
                                        'ylabel': 'Counts',
                                        'datasets': {'dark_ms1' : dark_ms1_sweeps,
                                                    'dark_ms0': dark_ms0_sweeps,
                                                    'echo_ms1' : echo_ms1_sweeps,
                                                    'echo_ms0': echo_ms0_sweeps}
                            })
                            if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                                gw.daq.close_task()
                                gw.sg.set_rf_toggle(0)
                                gw.sg.set_mod_toggle(0)
                                gw.ps.Pulser.reset()
                                gw.laser.off()
                                gw.windfreak.ch0_off()
                                print('the GUI has asked us nicely to exit')
                                return
                        pbar.update(1)

                gw.daq.close_task()
                gw.sg.set_rf_toggle(0) 
                gw.sg.set_mod_toggle(0) 
                gw.ps.Pulser.reset()
                gw.laser.off()
                gw.windfreak.ch0_off()

    def DEER_rabi_run(self, **kwargs):
        '''
        Developed by Tian-Xing and Hanyan at April.2024
        '''
        with InstrumentGateway() as gw, DataSource('DEER_Rabi') as deer_rabi_data:
            # pi pulse durations on electron spin that will be swept over in the Rabi measurement (converted to ns)
            mw_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
            #num_mw = len(mw_times)

            # define buffer size here
            deer_rabi_buffer_size = 8*kwargs['runs']*kwargs['num_pts']
            if deer_rabi_buffer_size < 8:
                raise ValueError("Buffer size too small.")
            
            ni_sample_buffer = np.ascontiguousarray(np.zeros(deer_rabi_buffer_size, dtype=np.uint32))
            deer_rabi_buffer = [ni_sample_buffer]
            
            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            # Setup the SRS
            gw.sg.set_frequency(kwargs['nv_mw_freq'])
            gw.sg.set_rf_amplitude(kwargs['nv_mw_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')
            # Setup the WindFreak power and frequency
            gw.windfreak.set_power_ch0(kwargs['el_mw_power'])
            gw.windfreak.set_freq_ch0(kwargs['el_mw_freq'])
            gw.windfreak.ch0_on()

            np.random.shuffle(mw_times) # random shuffel the mw_times for balancing the heating and charge of the sample
            print("MW times after random shuffle:", mw_times)
            # pulse streamer sequence
            ps_seq = gw.ps.DEER_Rabi(mw_times, kwargs['pihalf_x']*1e9, kwargs['pihalf_y']*1e9, 
                                kwargs['pi_x']*1e9, kwargs['pi_y']*1e9, 
                                kwargs['tau']*1e9, 
                                kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9, kwargs['seq_gap']*1e9)
            # index order of sorted mw_times 
            # used to match x and y axis order for plotting
            index_order = np.argsort(mw_times) 
            mw_times_ordered = np.sort(mw_times) # record the ordered mw_times for Rabi plotting
            # order mw_times for Rabi plotting

            gw.daq.open_task(len(deer_rabi_buffer[0]))
            dark_ms1_sweeps = StreamingList()
            dark_ms0_sweeps = StreamingList()
            echo_ms1_sweeps = StreamingList()
            echo_ms0_sweeps = StreamingList()

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):
                    
                    deer_rabi_result = self.read(deer_rabi_buffer[0], ps_seq, kwargs['runs'])

                    # partition buffer into signal and background datasets
                    dark_ms1_array, dark_ms0_array, echo_ms1_array, echo_ms0_array = self.digital_math(deer_rabi_result, 'DEER_Rabi', kwargs['num_pts'])
                    
                    # correct the y-axis data ordering for plots
                    dark_ms1_array = np.array([dark_ms1_array[i] for i in index_order])
                    dark_ms0_array = np.array([dark_ms0_array[i] for i in index_order])
                    echo_ms1_array = np.array([echo_ms1_array[i] for i in index_order])
                    echo_ms0_array = np.array([echo_ms0_array[i] for i in index_order])
                    #print('mw_times_ordered is: \n',mw_times_ordered)
                    dark_ms1_sweeps.append(np.stack([mw_times_ordered, dark_ms1_array]))
                    dark_ms0_sweeps.append(np.stack([mw_times_ordered, dark_ms0_array]))
                    echo_ms1_sweeps.append(np.stack([mw_times_ordered, echo_ms1_array]))
                    echo_ms0_sweeps.append(np.stack([mw_times_ordered, echo_ms0_array]))
                    # notify the streaminglist that this entry has updated so it will be pushed to the data server
                    dark_ms1_sweeps.updated_item(-1)
                    dark_ms0_sweeps.updated_item(-1)
                    echo_ms1_sweeps.updated_item(-1)
                    echo_ms0_sweeps.updated_item(-1)
                    #print('\nfreq now:',freq)
                    #print('\ndark_ms1_sweeps[-1] = ',dark_ms1_sweeps[-1])
                    deer_rabi_data.push({'params': {'start': kwargs['start'], 'stop': kwargs['stop'], 'num_pts': kwargs['num_pts'], 'iterations': kwargs['iters']},
                                'title': 'DEER Rabi',
                                'xlabel': 'electron spin MW time (ns)',
                                'ylabel': 'Counts',
                                'datasets': {'dark_ms1' : dark_ms1_sweeps,
                                            'dark_ms0': dark_ms0_sweeps,
                                            'echo_ms1' : echo_ms1_sweeps,
                                            'echo_ms0': echo_ms0_sweeps}
                    })
                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        gw.daq.close_task()
                        gw.sg.set_rf_toggle(0)
                        gw.sg.set_mod_toggle(0)
                        gw.ps.Pulser.reset()
                        gw.laser.off()
                        gw.windfreak.ch0_off()
                        print('the GUI has asked us nicely to exit')
                        return
                    pbar.update(1)

        gw.daq.close_task()
        gw.sg.set_rf_toggle(0) 
        gw.sg.set_mod_toggle(0) 
        gw.ps.Pulser.reset()
        gw.laser.off()
        gw.windfreak.ch0_off()

    def DEER_rabi_run_Evan(self, **kwargs):
        '''
        Developed by Evan
        '''
        with InstrumentGateway() as gw, DataSource('DRabi') as deer_data:
            # tau_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
            dark_taus = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9            
            # dark_taus = np.insert(dark_taus, 0, 1) # insert 1 ns as first data point that will be skipped in plotting           
            num_tau = len(dark_taus)
            
            # define buffer size here
            deer_buffer_size = 4*kwargs['runs']*num_tau
            if deer_buffer_size < 4:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(deer_buffer_size, dtype=np.float64))
            deer_buffer = [ni_sample_buffer]

            # x_axis_data = np.delete(dark_taus, 0)/1e9
                       
            dataset = {'taus': dark_taus/1e9,
                       'dark_ms1': np.zeros((kwargs['iters'], kwargs['num_pts'])), 
                       'dark_ms0': np.zeros((kwargs['iters'], kwargs['num_pts'])),
                       'echo_ms1': np.zeros((kwargs['iters'], kwargs['num_pts'])),
                       'echo_ms0': np.zeros((kwargs['iters'], kwargs['num_pts'])),
                       'sum_dark_ms1': np.zeros(kwargs['num_pts']),
                       'sum_dark_ms0': np.zeros(kwargs['num_pts']),
                       'sum_echo_ms1': np.zeros(kwargs['num_pts']),
                       'sum_echo_ms0': np.zeros(kwargs['num_pts'])}

            # set initial parameters for instrument server devices
            gw.laser.set_modulation_state('pulsed')
            gw.laser.set_analog_control_mode('current')
            gw.laser.set_diode_current_realtime(110)
            gw.laser.laser_on()
            gw.sg.set_frequency(kwargs['freq'])
            gw.sg.set_rf_amplitude(kwargs['rf_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')

            gw.ps.laser_time = kwargs['laser_time'] * 1e9 # initialization pulse duration
            # gw.ps.readout_time = kwargs['read'] * 1e9 # readout window duration
            gw.ps.clock_time = 11 # [ns] width of our clock pulse.
            gw.ps.runs = kwargs['runs'] # number of runs per point

            for i in range(2):
                kwargs['pihalf'][i] = kwargs['pihalf'][i]*1e9
                kwargs['pi'][i] = kwargs['pi'][i]*1e9

            ps_seq = gw.ps.DEER_Rabi(kwargs['pihalf'][0], kwargs['pihalf'][1], 
                                kwargs['pi'][0], kwargs['pi'][1], 
                                kwargs['tau']*1e9, num_tau)
                        
            gw.daq.open_task(len(deer_buffer[0]))

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):

                    deer_result = self.read(deer_buffer[0], ps_seq, kwargs['runs'])

                    dark_ms1 = self.analog_math(deer_result, 'DEER_2', num_tau)[0]
                    dark_ms0 = self.analog_math(deer_result, 'DEER_2', num_tau)[1]
                    echo_ms1 = self.analog_math(deer_result, 'DEER_2', num_tau)[2]
                    echo_ms0 = self.analog_math(deer_result, 'DEER_2', num_tau)[3]

                    # delete the "1 ns" data point from the set and use the rest for plotting
                    # dark_ms1 = np.delete(dark_ms1, 0)
                    # dark_ms0 = np.delete(dark_ms0, 0)
                    # echo_ms1 = np.delete(echo_ms1, 0)
                    # echo_ms0 = np.delete(echo_ms0, 0)
                    # FID_contrast = ((dark_ms0 - dark_ms1)/(dark_ms0 + dark_ms1)) / ((echo_ms0 - echo_ms1)/(echo_ms0 + echo_ms1))

                    dataset['dark_ms1'][iter] = dark_ms1
                    dataset['dark_ms0'][iter] = dark_ms0
                    dataset['echo_ms1'][iter] = echo_ms1
                    dataset['echo_ms0'][iter] = echo_ms0

                    dataset['sum_dark_ms1'] = dataset['sum_dark_ms1'] + dark_ms1
                    dataset['sum_dark_ms0'] = dataset['sum_dark_ms0'] + dark_ms0
                    dataset['sum_echo_ms1'] = dataset['sum_echo_ms1'] + echo_ms1
                    dataset['sum_echo_ms0'] = dataset['sum_echo_ms0'] + echo_ms0
                    

                    deer_data.push({'params': {'iter_num': kwargs['iters'], 'tau_num': kwargs['num_pts'], 
                                                'iter_idx': iter,
                                                'runs_num': kwargs['runs'],
                                                'rf_power': kwargs['rf_power'], 'freq': kwargs['freq']}, 
                                    'dataset': dataset})
                    
                    pbar.update(1)

            gw.daq.close_task()
            gw.sg.set_rf_toggle(0) 
            gw.sg.set_mod_toggle(0) 
            gw.ps.Pulser.reset()

    def DEER_corr_rabi_run(self, **kwargs):
        '''
        Developed by Evan
        '''
        with InstrumentGateway() as gw, DataSource('DCorrRabi') as drabi_data:
            # tau_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
            mw_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9            
            num_mw = len(mw_times)

            # define buffer size here
            deer_buffer_size = 2*kwargs['runs']*num_mw
            if deer_buffer_size < 2:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(deer_buffer_size, dtype=np.float64))
            deer_buffer = [ni_sample_buffer]

            dataset = {'ms1': [], 'ms0': [], 'contrast': []}

            # set initial parameters for instrument server devices
            gw.laser.set_modulation_state('pulsed')
            gw.laser.set_analog_control_mode('current')
            gw.laser.set_diode_current_realtime(110)
            gw.laser.laser_on()
            gw.sg.set_frequency(kwargs['freq'])
            gw.sg.set_rf_amplitude(kwargs['rf_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')

            gw.ps.laser_time = kwargs['laser_time'] * 1e9 # initialization pulse duration
            # gw.ps.readout_time = kwargs['read'] * 1e9 # readout window duration
            gw.ps.clock_time = 11 # [ns] width of our clock pulse.
            gw.ps.runs = kwargs['runs'] # number of runs per point

            # convert pi pulse times to ns for pulse streamer
            for i in range(2):
                kwargs['pihalf'][i] = kwargs['pihalf'][i]*1e9
                kwargs['pi'][i] = kwargs['pi'][i]*1e9

            ps_seq = gw.ps.DEER_Corr_Rabi(kwargs['pihalf'][0], kwargs['pihalf'][1], 
                                kwargs['pi'][0], kwargs['pi'][1], 
                                kwargs['tau']*1e9, kwargs['echo_rest_time']*1e9, 
                                kwargs['awg_trig_delay_time']*1e9, num_mw)
                        
            gw.daq.open_task(len(deer_buffer[0]))

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):

                    deer_result = self.read(deer_buffer[0], ps_seq, kwargs['runs'])
                    
                    ms1 = self.analog_math(deer_result, 'DEER_Corr', num_mw)[0]
                    ms0 = self.analog_math(deer_result, 'DEER_Corr', num_mw)[1]
                   
                    ctrst = (ms0 - ms1)/(ms0 + ms1)

                    dataset['ms1'].append(np.stack([mw_times, ms1]))
                    dataset['ms0'].append(np.stack([mw_times, ms0]))
                    dataset['contrast'].append(np.stack([mw_times, ctrst]))

                    drabi_data.push({'params': {'iter_num': kwargs['iters'], 'mw_num': num_mw, 
                                                'iter_idx': iter,
                                                'runs_num': kwargs['runs'],
                                                'rf_power': kwargs['rf_power'], 'freq': kwargs['freq']}, 
                                    'dataset': dataset})
                    
                    pbar.update(1)

            gw.daq.close_task()
            gw.sg.set_rf_toggle(0) 
            gw.sg.set_mod_toggle(0) 
            gw.ps.Pulser.reset()

    def T1_run(self, **kwargs):
        '''
        Developed by Tian-Xing in Sept.2023
        tau_balance is turned off, we don't need the extra waiting time since we've already balance the tau for linear case and random shuffle the tau for exp case
        '''
        with InstrumentGateway() as gw, DataSource('T1') as t1_data:

            if kwargs['tau_type']=='linear':
                tau_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
                x_axis_data = np.copy(tau_times)
                tau_times = self.sort_taus_for_balance(tau_times)
                index_order = np.argsort(tau_times)
                tau_balance = False
            elif kwargs['tau_type']=='exp':
                tau_times = np.geomspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
                x_axis_data = np.copy(tau_times)
                np.random.shuffle(tau_times)
                # index order of sorted mw_times used to match x and y axis order for plotting
                index_order = np.argsort(tau_times) 
                tau_balance = False
            else:
                raise ValueError("tau_type can only be linear or exp!")
            tau_times = np.insert(tau_times, 0, 1) # insert 1 ns as first data point that will be skipped in plotting           
            # TXZ: The reason we have this first 1ns data point (but throw it away when plotting) is to warm up the experimentl setup and qubit
            num_tau = len(tau_times)


            init_time, read_time = kwargs['init_time']*1e9, kwargs['read_time']*1e9
            # seq_gap for avoding the nidaqmx.errors. And reinitialize the system
            # DaqReadError: Acquisition has been stopped to prevent an input buffer overwrite. Your application was unable to read samples from the buffer fast enough to prevent new samples from overwriting unread data.
            seq_gap = kwargs['seq_gap']*1e9

            if kwargs['seq'] == 'MW T1':
                # define MW T1 buffer size here
                T1_buffer_size = 4*kwargs['runs']*num_tau
                if T1_buffer_size < 4:
                    raise ValueError("Buffer size too small.")

                ni_sample_buffer = np.ascontiguousarray(np.zeros(T1_buffer_size, dtype=np.uint32))
                t1_buffer = [ni_sample_buffer]

                if kwargs['xy'] == 'x':
                    pi_pulse = kwargs['pi_x']*1e9 # [ns] units for pulse streamer
                elif kwargs['xy'] == 'y':
                    pi_pulse = kwargs['pi_y']*1e9
                else:
                    raise ValueError("MW pulse must be x or y!")
                
                print("PI PULSE T1 TIME: ", pi_pulse)
                # set initial parameters for instrument server devices
                if kwargs['T1_sg'] == 'SRS':
                    print("USING SRS FOR T1 MEASUREMENT.")
                    ps_seq = gw.ps.Diff_T1(tau_times, tau_balance, kwargs['xy'], pi_pulse, init_time, read_time, seq_gap)
                    # Setup the MW
                    gw.sg.set_frequency(kwargs['freq'])
                    gw.sg.set_rf_amplitude(kwargs['rf_power'])
                    gw.sg.set_mod_type('QAM')
                    gw.sg.set_rf_toggle(1)
                    gw.sg.set_mod_toggle(1)
                    gw.sg.set_mod_function('external')
                elif kwargs['T1_sg'] == 'WindFreak':
                    print("USING WindFreak FOR T1 MEASUREMENT.")
                    ps_seq = gw.ps.Diff_T1_Switch(tau_times, tau_balance, kwargs['xy'], pi_pulse, init_time, read_time, seq_gap)
                    # Setup the MW
                    gw.windfreak.set_power_ch0(kwargs['rf_power'])
                    gw.windfreak.set_freq_ch0(kwargs['freq'])
                    gw.windfreak.ch0_on()
                else:
                    raise ValueError("\nWe only have Signal Generators: SRS or WindFreak!\n")

            elif kwargs['seq'] == 'Optical T1 NV':
                # define optical T1 buffer size here
                T1_buffer_size = 2*kwargs['runs']*num_tau 
                if T1_buffer_size < 2:
                    raise ValueError("Buffer size too small.")

                ni_sample_buffer = np.ascontiguousarray(np.zeros(T1_buffer_size, dtype=np.uint32))
                t1_buffer = [ni_sample_buffer]

                ps_seq = gw.ps.Optical_T1(tau_times, tau_balance, init_time, read_time, DAQ_buffer, seq_gap, forNV=True)

            elif kwargs['seq'] == 'Optical T1 General':
                # define optical T1 buffer size here
                T1_buffer_size = 2*kwargs['runs']*num_tau 
                if T1_buffer_size < 2:
                    raise ValueError("Buffer size too small.")

                ni_sample_buffer = np.ascontiguousarray(np.zeros(T1_buffer_size, dtype=np.uint32))
                t1_buffer = [ni_sample_buffer]
                
                ps_seq = gw.ps.Optical_T1(tau_times, tau_balance, init_time, read_time, DAQ_buffer, seq_gap, forNV=False)
            
            elif kwargs['seq'] == 'T1rho':
                # define MW T1 buffer size here
                T1_buffer_size = 4*kwargs['runs']*num_tau
                if T1_buffer_size < 4:
                    raise ValueError("Buffer size too small.")

                ni_sample_buffer = np.ascontiguousarray(np.zeros(T1_buffer_size, dtype=np.uint32))
                t1_buffer = [ni_sample_buffer]

                print("USING SRS FOR T1_rho (Dressed State T1) MEASUREMENT.")
                ps_seq = gw.ps.Diff_T1rho(tau_times, tau_balance, kwargs['pihalf_y']*1e9, init_time, read_time, seq_gap)
                # Setup the MW
                gw.sg.set_frequency(kwargs['freq'])
                gw.sg.set_rf_amplitude(kwargs['rf_power'])
                gw.sg.set_mod_type('QAM')
                gw.sg.set_rf_toggle(1)
                gw.sg.set_mod_toggle(1)
                gw.sg.set_mod_function('external')
            else:
                raise ValueError("sequence must be MW T1 or Optical T1!")

            print("pulse seuqnce is:\n",ps_seq)
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            # Open a DAQ task for readout
            gw.daq.open_task(len(t1_buffer[0]))

            ms1_sweeps = StreamingList()
            ms0_sweeps = StreamingList()

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):
                    
                    if kwargs['seq'] == 'MW T1' or kwargs['seq'] == 'T1rho':
                        t1_result = self.read(t1_buffer[0], ps_seq, round(kwargs['runs']))

                        # partition buffer into signal and background datasets
                        ms1, ms0 = self.digital_math(t1_result, 'MW_T1', num_tau)
                        
                        #print('\nms0 here is:\n',ms0)
                        # delete the "1 ns" data point from the set and use the rest for plotting
                        ms1 = np.delete(ms1, 0)
                        ms0 = np.delete(ms0, 0)
                        
                        # sort back the data to the correct order
                        ms1 = np.array([ms1[i] for i in index_order])
                        ms0 = np.array([ms0[i] for i in index_order])
                        #print("\n shape ms1:\n", np.shape(ms1))
                        #print("\n type ms1[0]:\n", type(ms1[0]))
                        ms1_sweeps.append(np.stack([x_axis_data, ms1]))
                        ms0_sweeps.append(np.stack([x_axis_data, ms0]))
                        # notify the streaminglist that this entry has updated so it will be pushed to the data server
                        ms1_sweeps.updated_item(-1)
                        ms0_sweeps.updated_item(-1)
                        #print('\nMW ms1_sweeps here is:\n',ms1_sweeps)
                        t1_data.push({'params': {'tau_num': kwargs['num_pts'], 'iter_num': kwargs['iters'],'runs_num': kwargs['runs']},
                                    'title': 'MW T1',
                                    'xlabel': 'Total Time (ns)',
                                    'ylabel': 'Counts',
                                    'datasets': {'ms1' : ms1_sweeps,
                                                'ms0': ms0_sweeps}
                                    })
                        
                    elif kwargs['seq'] == 'Optical T1 NV' or kwargs['seq'] == 'Optical T1 General':
                        t1_result = self.read(t1_buffer[0], ps_seq, kwargs['runs'])
                        #print('\n t1_result:\n',t1_result)
                        ms1 = self.digital_math(t1_result, 'Optical T1', num_tau)
                        ms1 = np.delete(ms1, 0)
                        #ms0 = np.delete(ms0, 0)
                        # sort back the data to the correct order
                        ms1 = np.array([ms1[i] for i in index_order])
                        #ms0 = np.array([ms0[i] for i in index_order])
                        #print("\n shape ms1:\n", np.shape(ms1))
                        #print("\n type ms1[0]:\n", type(ms1[0]))
                        #print("\n ms1:\n",ms1)
                        ms0 = ms1
                        ms1_sweeps.append(np.stack([x_axis_data, ms1]))
                        ms0_sweeps.append(np.stack([x_axis_data, ms0]))
                        #print(ms1_sweeps)
                        #ms0_sweeps = ms1_sweeps
                        # notify the streaminglist that this entry has updated so it will be pushed to the data server
                        ms1_sweeps.updated_item(-1)
                        ms0_sweeps.updated_item(-1)
                        #
                        #print('\nOptical ms1_sweeps here is:\n',ms1_sweeps)
                        t1_data.push({'params': {'tau_num': kwargs['num_pts'], 'iter_num': kwargs['iters'],'runs_num': kwargs['runs']},
                                    'title': 'MW T1',
                                    'xlabel': 'Total Time (ns)',
                                    'ylabel': 'Counts',
                                    'datasets': {'ms1' : ms1_sweeps,
                                                'ms0': ms0_sweeps}
                                    })
                    else:
                        raise ValueError("sequence must be MW T1 or Opitcal T1 NV or Optical T1 General or T1rho!")
                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        gw.daq.close_task()
                        gw.sg.set_rf_toggle(0)
                        gw.sg.set_mod_toggle(0)
                        gw.ps.Pulser.reset()
                        gw.laser.off()
                        print('the GUI has asked us nicely to exit')
                        return
                    pbar.update(1)
                gw.daq.close_task()
                gw.sg.set_rf_toggle(0)
                gw.sg.set_mod_toggle(0)
                gw.ps.Pulser.reset()
                gw.laser.off()
    
    def T2_run(self, **kwargs):
        '''
        Developed by Tian-Xing in Sept.2023
        tau_balance is turned off, we don't need the extra waiting time since we've already balance the tau for linear case and random shuffle the tau for exp case
        '''
        with InstrumentGateway() as gw, DataSource('T2') as t2_data:  
            if kwargs['tau_type']=='linear':
                tau_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
                x_axis_data = np.copy(tau_times)
                tau_times = self.sort_taus_for_balance(tau_times)
                index_order = np.argsort(tau_times) 
                tau_balance = False
            elif kwargs['tau_type']=='exp':
                tau_times = np.geomspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
                x_axis_data = np.copy(tau_times)
                np.random.shuffle(tau_times)
                # index order of sorted mw_times used to match x and y axis order for plotting
                index_order = np.argsort(tau_times) 
                tau_balance = False
            tau_times = np.insert(tau_times, 0, 1) # insert 1 ns as first data point that will be skipped in plotting           
            # TXZ: The reason we have this first 1ns data point (but throw it away when plotting) is to warm up the experimentl setup
            num_tau = len(tau_times)
            
            # define buffer size here
            T2_buffer_size = 4*kwargs['runs']*num_tau
            if T2_buffer_size < 4:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(T2_buffer_size, dtype=np.uint32))
            t2_buffer = [ni_sample_buffer]

            ms1_sweeps = StreamingList()
            ms0_sweeps = StreamingList()
            
            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            # Open a readout task on DAQ
            gw.daq.open_task(T2_buffer_size)
            # Setup the MW
            gw.sg.set_frequency(kwargs['freq'])
            gw.sg.set_rf_amplitude(kwargs['rf_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')

            #gw.ps.laser_time = kwargs['init'] * 1e9 # initialization pulse duration
            #gw.ps.clock_time = 11 # [ns] width of our clock pulse.
            #gw.ps.runs = kwargs['runs'] # number of runs per point
            # change the pi and pi/2 pulse length unit into ns
            #for i in range(2):
            kwargs['pihalf_x'] = kwargs['pihalf_x']*1e9
            kwargs['pihalf_y'] = kwargs['pihalf_y']*1e9
            kwargs['pi_x'] = kwargs['pi_x']*1e9
            kwargs['pi_y'] = kwargs['pi_y']*1e9
            init_time, read_time, wait_time, read_wait, seq_gap = kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9, kwargs['seq_gap']*1e9

            if kwargs['seq'] == 'Ramsey':
                ps_seq = gw.ps.Ramsey(tau_times, tau_balance, kwargs['pihalf_x'], kwargs['pihalf_y'], init_time, read_time, wait_time, read_wait)
                x_axis_data = 2*kwargs['pihalf_x'] + x_axis_data
            elif kwargs['seq'] == 'Spin Echo':
                ps_seq = gw.ps.Echo(tau_times, tau_balance, kwargs['pihalf_x'], kwargs['pihalf_y'], 
                                         kwargs['pi_x'], kwargs['pi_y'], init_time, read_time, wait_time, read_wait, seq_gap)
                # make the x_axis to be the total sequence time, instead of the tau time.
                x_axis_data = 2*x_axis_data + 2*kwargs['pihalf_x'] + kwargs['pi_y']
                # x_times = 2*kwargs['pihalf'][0] + tau_times + kwargs['pi'][1]
            # elif kwargs['seq'] == 'XY4':
            #     ps_seq = gw.ps.XY4_N(tau_times, 'xy', 
            #                          kwargs['pihalf'][0], kwargs['pihalf'][1], 
            #                          kwargs['pi'][0], kwargs['pi'][1], kwargs['n'])
            #     # x_times = 2*kwargs['pihalf'][0] + (2*(tau_times/2)/(4*kwargs['n']) + 2*kwargs['pi'][0] + \
            #             #   2*kwargs['pi'][1] + 3*tau_times/(4*kwargs['n']))*kwargs['n']
            # elif kwargs['seq'] == 'YY4':
            #     ps_seq = gw.ps.XY4_N(tau_times, 'yy', 
            #                          kwargs['pihalf'][0], kwargs['pihalf'][1], 
            #                          kwargs['pi'][0], kwargs['pi'][1], kwargs['n'])
            #     # x_times = 2*kwargs['pihalf'][0] + (2*(tau_times/2)/(4*kwargs['n']) + 4*kwargs['pi'][1] + 3*tau_times/(4*kwargs['n']))*kwargs['n']
            elif kwargs['seq'] == 'XY8':
                ps_seq = gw.ps.XY8_N(tau_times, tau_balance, 'xy',
                                     kwargs['pihalf_x'], kwargs['pihalf_y'], 
                                     kwargs['pi_x'], kwargs['pi_y'], kwargs['n'], init_time, read_time, wait_time, read_wait)
                x_axis_data = 16*kwargs['n']*x_axis_data + 2*kwargs['pihalf_y'] + 4*kwargs['n']*kwargs['pi_x'] + 4*kwargs['n']*kwargs['pi_y']
            elif kwargs['seq'] == 'XY8 NQR':
                ps_seq = gw.ps.XY8_N_NQR(tau_times, tau_balance, 'xy',
                                     kwargs['pihalf_x'], kwargs['pihalf_y'], 
                                     kwargs['pi_x'], kwargs['pi_y'], kwargs['n'], init_time, read_time, wait_time, read_wait)
                x_axis_data =  (8*kwargs['n'] + 4)*x_axis_data + 2*kwargs['pihalf_x'] + 4*kwargs['n']*kwargs['pi_x'] + 4*kwargs['n']*kwargs['pi_y'] + 2*kwargs['pi_x'] + kwargs['pi_y']
            elif kwargs['seq'] == 'YY8':
                ps_seq = gw.ps.XY8_N(tau_times, tau_balance, 'yy',
                                     kwargs['pihalf_x'], kwargs['pihalf_y'], 
                                     kwargs['pi_x'], kwargs['pi_y'], kwargs['n'], init_time, read_time, wait_time, read_wait)
                x_axis_data = 16*kwargs['n']*x_axis_data + 2*kwargs['pihalf_y'] + 8*kwargs['n']*kwargs['pi_y']
            elif kwargs['seq'] == 'CPMG':
                ps_seq = gw.ps.CPMG_N(tau_times, tau_balance, kwargs['pulse_axis'], 
                                     kwargs['pihalf_x'], kwargs['pihalf_y'], 
                                     kwargs['pi_x'], kwargs['pi_y'], kwargs['n'], init_time, read_time, wait_time, read_wait)
                
                # make the x_axis to be the total sequence time, instead of the tau time.
                if kwargs['pulse_axis'] == 'X':
                    x_axis_data = 2*kwargs['n']*x_axis_data + 2*kwargs['pihalf_x'] + kwargs['n']*kwargs['pi_x']
                elif kwargs['pulse_axis'] == 'Y':
                    x_axis_data = 2*kwargs['n']*x_axis_data + 2*kwargs['pihalf_x'] + kwargs['n']*kwargs['pi_y']
                else:
                    raise ValueError("pulse_axis must be 'X' or 'Y'!")
            #     # x_times = 2*kwargs['pihalf'][0] + tau_times/kwargs['n'] + (kwargs['pi'][0] + tau_times/kwargs['n'])*(kwargs['n']-1) + kwargs['pi'][0]
            elif kwargs['seq'] == 'WAHUHA':
                ps_seq = gw.ps.WAHUHA_N(tau_times, tau_balance,
                                     kwargs['pihalf_x'], kwargs['pihalf_y'], 
                                     kwargs['pi_x'], kwargs['pi_y'], kwargs['n'], init_time, read_time, wait_time, read_wait)
                x_axis_data = 6 *kwargs['n']*x_axis_data + 2*kwargs['n']*kwargs['pihalf_x'] + 2*kwargs['n']*kwargs['pihalf_y']
            elif kwargs['seq'] == 'DROID':
                ps_seq = gw.ps.DROID_N(tau_times, tau_balance,
                                     kwargs['pihalf_x'], kwargs['pihalf_y'], 
                                     kwargs['pi_x'], kwargs['pi_y'], kwargs['n'], init_time, read_time, wait_time, read_wait)
                x_axis_data = 47 *kwargs['n']*x_axis_data + 12*kwargs['n']*kwargs['pihalf_x'] + 12*kwargs['n']*kwargs['pihalf_y'] + 18*kwargs['n']*kwargs['pi_x'] + 18*kwargs['n']*kwargs['pi_y']
            else:
                raise ValueError("seq must be: Ramsey, Spin Echo, XY4, YY4, XY8, YY8, CPMG, WAHUHA, or DROID")
            gw.daq.open_task(len(t2_buffer[0]))


            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):

                    t2_result = self.read(t2_buffer[0], ps_seq, kwargs['runs'])

                    # partition buffer into signal and background datasets
                    ms1, ms0 = self.digital_math(t2_result, 'T2', num_tau)
                    
                    ms1 = np.delete(ms1, 0)
                    ms0 = np.delete(ms0, 0)
                    
                    # sort back the data to the correct order
                    ms1 = np.array([ms1[i] for i in index_order])
                    ms0 = np.array([ms0[i] for i in index_order])
                    
                    ms1_sweeps.append(np.stack([x_axis_data, ms1]))
                    ms0_sweeps.append(np.stack([x_axis_data, ms0]))
                    # notify the streaminglist that this entry has updated so it will be pushed to the data server
                    ms1_sweeps.updated_item(-1)
                    ms0_sweeps.updated_item(-1)

                    
                    t2_data.push({'params': {'mw_num': kwargs['num_pts'], 'iter_num': kwargs['iters'],'runs_num': kwargs['runs']},
                                    'title': 'T2',
                                    'xlabel': 'Total Time (ns)',
                                    'ylabel': 'Counts',
                                    'datasets': {'ms1' : ms1_sweeps,
                                                'ms0': ms0_sweeps}
                    })
                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        gw.daq.close_task()
                        gw.sg.set_rf_toggle(0)
                        gw.sg.set_mod_toggle(0)
                        gw.ps.Pulser.reset()
                        gw.laser.off()
                        print('the GUI has asked us nicely to exit')
                        return
                    
                    
                    pbar.update(1)

            gw.daq.close_task()
            gw.sg.set_rf_toggle(0) 
            gw.sg.set_mod_toggle(0) 
            gw.ps.Pulser.reset()
            gw.laser.off()

    def Correlation_Spectroscopy_run(self, **kwargs):
        '''
        Developed by Tian-Xing and Hanyan in Feb.2025
        tau_balance is turned off, we don't need the extra waiting time since we've already balance the tau for linear case and random shuffle the tau for exp case
        '''
        with InstrumentGateway() as gw, DataSource('Correlation_Spectroscopy') as Correlation_Spectroscopy_data:  
            if kwargs['t_corr_type']=='linear':
                t_corr_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
                x_axis_data = np.copy(t_corr_times)
                t_corr_times = self.sort_taus_for_balance(t_corr_times)
                index_order = np.argsort(t_corr_times) 
                tau_balance = True
            elif kwargs['t_corr_type']=='exp':
                t_corr_times = np.geomspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
                x_axis_data = np.copy(t_corr_times)
                np.random.shuffle(t_corr_times)
                # index order of sorted mw_times used to match x and y axis order for plotting
                index_order = np.argsort(t_corr_times) 
                tau_balance = False
            t_corr_times = np.insert(t_corr_times, 0, 1) # insert 1 ns as first data point that will be skipped in plotting           
            # TXZ: The reason we have this first 1ns data point (but throw it away when plotting) is to warm up the experimentl setup
            num_t_corr = len(t_corr_times)
            
            # define buffer size here
            Correlation_Spectroscopy_buffer_size = 4*kwargs['runs']*num_t_corr
            if Correlation_Spectroscopy_buffer_size < 4:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(Correlation_Spectroscopy_buffer_size, dtype=np.uint32))
            Correlation_Spectroscopy_buffer = [ni_sample_buffer]

            ms1_sweeps = StreamingList()
            ms0_sweeps = StreamingList()
            
            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            # Open a readout task on DAQ
            gw.daq.open_task(Correlation_Spectroscopy_buffer_size)
            # Setup the MW
            gw.sg.set_frequency(kwargs['freq'])
            gw.sg.set_rf_amplitude(kwargs['rf_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')

            #gw.ps.laser_time = kwargs['init'] * 1e9 # initialization pulse duration
            #gw.ps.clock_time = 11 # [ns] width of our clock pulse.
            #gw.ps.runs = kwargs['runs'] # number of runs per point
            # change the pi and pi/2 pulse length unit into ns
            #for i in range(2):
            kwargs['pihalf_x'] = kwargs['pihalf_x']*1e9
            kwargs['pihalf_y'] = kwargs['pihalf_y']*1e9
            kwargs['pi_x'] = kwargs['pi_x']*1e9
            kwargs['pi_y'] = kwargs['pi_y']*1e9
            kwargs['tau'] = kwargs['tau']*1e9
            init_time, read_time, wait_time, read_wait = kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9
            seq_type = kwargs['seq']

            ps_seq = gw.ps.Corr_Spectroscopy(t_corr_times, kwargs['tau'], tau_balance, seq_type, kwargs['pihalf_x'], kwargs['pihalf_y'], 
                                     kwargs['pi_x'], kwargs['pi_y'], kwargs['n'], init_time, read_time, wait_time, read_wait)
            
            # For correlation sequece, our x-axis data is just t_corr_times
            # if seq_type == 'XY8 NQR':
            #     x_axis_data = 8*kwargs['n']*(kwargs['pi_x'] + kwargs['pi_y'] + 2*kwargs['tau']) + 2*kwargs['pihalf_x'] + 2*kwargs['pihalf_y'] + 6*kwargs['tau'] + 4*kwargs['pi_x'] + 2*kwargs['pi_y'] + x_axis_data  
            # elif seq_type == 'YY8':
            #     x_axis_data = 4*kwargs['pihalf_y'] + x_axis_data + 2*kwargs['n']*(16*kwargs['tau'] + 8*kwargs['pi_y'])
            # else:
            #     raise ValueError("seq must be: XY8 NQR or YY8")
            gw.daq.open_task(len(Correlation_Spectroscopy_buffer[0]))


            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):

                    Correlation_Spectroscopy_result = self.read(Correlation_Spectroscopy_buffer[0], ps_seq, kwargs['runs'])

                    # partition buffer into signal and background datasets
                    ms1, ms0 = self.digital_math(Correlation_Spectroscopy_result, 'Correlation Spectroscopy', num_t_corr)
                    
                    ms1 = np.delete(ms1, 0)
                    ms0 = np.delete(ms0, 0)
                    
                    # sort back the data to the correct order
                    ms1 = np.array([ms1[i] for i in index_order])
                    ms0 = np.array([ms0[i] for i in index_order])
                    
                    ms1_sweeps.append(np.stack([x_axis_data, ms1]))
                    ms0_sweeps.append(np.stack([x_axis_data, ms0]))
                    # notify the streaminglist that this entry has updated so it will be pushed to the data server
                    ms1_sweeps.updated_item(-1)
                    ms0_sweeps.updated_item(-1)

                    
                    Correlation_Spectroscopy_data.push({'params': {'mw_num': kwargs['num_pts'], 'iter_num': kwargs['iters'],'runs_num': kwargs['runs']},
                                    'title': 'Correlation Spectroscopy',
                                    'xlabel': 'Total Time (ns)',
                                    'ylabel': 'Counts',
                                    'datasets': {'ms1' : ms1_sweeps,
                                                'ms0': ms0_sweeps}
                    })
                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        gw.daq.close_task()
                        gw.sg.set_rf_toggle(0)
                        gw.sg.set_mod_toggle(0)
                        gw.ps.Pulser.reset()
                        gw.laser.off()
                        print('the GUI has asked us nicely to exit')
                        return
                    
                    
                    pbar.update(1)

            gw.daq.close_task()
            gw.sg.set_rf_toggle(0) 
            gw.sg.set_mod_toggle(0) 
            gw.ps.Pulser.reset()
            gw.laser.off()

    def NMR_run(self, **kwargs):
        '''
        Developed by Evan
        '''
        with InstrumentGateway() as gw, DataSource('NMR') as nmr_data:
            # correlation times that will be swept over in the Corr Spec measurement
            # tau_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
            t_corr_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9            
            num_t_corr = len(t_corr_times)

            # define buffer size here
            NMR_buffer_size = 2*kwargs['runs']*num_t_corr
            if NMR_buffer_size < 2:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(NMR_buffer_size, dtype=np.float64))
            nmr_buffer = [ni_sample_buffer]

            dataset = {'ms1': [], 'ms0': [], 'contrast': []}

            # set initial parameters for instrument server devices
            gw.laser.set_modulation_state('pulsed')
            gw.laser.set_analog_control_mode('current')
            gw.laser.set_diode_current_realtime(110)
            gw.laser.laser_on()
            gw.sg.set_frequency(kwargs['freq'])
            gw.sg.set_rf_amplitude(kwargs['rf_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')

            gw.ps.laser_time = kwargs['init'] * 1e9 # initialization pulse duration
            gw.ps.readout_time = kwargs['read'] * 1e9 # readout window duration
            gw.ps.clock_time = 11 # [ns] width of our clock pulse.
            gw.ps.runs = kwargs['runs'] # number of runs per point

            for i in range(2):
                kwargs['pihalf'][i] = kwargs['pihalf'][i]*1e9
                kwargs['pi'][i] = kwargs['pi'][i]*1e9

            if kwargs['seq'] == 'Correlation Spectroscopy':
                ps_seq = gw.ps.Corr_Spectroscopy(t_corr_times, kwargs['tau']*1e9, 
                                     kwargs['pihalf'][0], kwargs['pihalf'][1], 
                                     kwargs['pi'][0], kwargs['pi'][1], kwargs['n'])

            gw.daq.open_task(len(nmr_buffer[0]))

            print("BUFFER LENGTH: ", len(nmr_buffer[0]))

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):

                    nmr_result = self.read(nmr_buffer[0], ps_seq, kwargs['runs']/2)

                    # partition buffer into signal and background datasets
                    ms1 = self.analog_math(nmr_result, 'NMR', num_t_corr)[0]
                    ms0 = self.analog_math(nmr_result, 'NMR', num_t_corr)[1]

                    dataset['ms1'].append(np.stack([t_corr_times/1e3, ms1]))
                    dataset['ms0'].append(np.stack([t_corr_times/1e3, ms0]))
                    dataset['contrast'].append(np.stack([t_corr_times/1e3, (ms0-ms1)/(ms0+ms1)]))

                    nmr_data.push({'params': {'iter_num': kwargs['iters'], 'T_ns': kwargs['stop']*1e9, 't_corr_num': num_t_corr, 'runs_num': kwargs['runs'],
                                            'freq': kwargs['freq'], 'rf_power': kwargs['rf_power'],
                                            'pi_xy': kwargs['pi'], 'pihalf_xy': kwargs['pihalf'],
                                            'tau': kwargs['tau'],
                                            'seq': kwargs['seq'], 'n': kwargs['n'],
                                            'r': gw.zaber.update_positions_callback(),
                                            'theta': gw.thor_polar.update_positions_callback(),
                                            'phi': gw.thor_azi.update_positions_callback()}, 
                                            'dataset': dataset})
                    pbar.update(1)
                
            gw.daq.close_task()
            gw.sg.set_rf_toggle(0) 
            gw.sg.set_mod_toggle(0) 
            gw.ps.Pulser.reset()

    def DEER_CPMG_run(self, **kwargs):
        '''
        Developed by Hanyan May.2024. Based on DEER_rabi_run logic.
        '''
        with InstrumentGateway() as gw, DataSource('DEER_CPMG') as deer_CPMG_data:
            frequencies = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts'])      
            #num_freqs = len(frequencies)

            # define buffer size here
            # We need 8*kwargs['runs'] here because we have 4 sequence for DEER (with&without pi-pulse on reporter spin, and +- pi/2 for reference), the DAQ also needs two sets of data for the NV readout
            deer_CPMG_buffer_size = 8*kwargs['runs']
            if deer_CPMG_buffer_size < 8:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(deer_CPMG_buffer_size, dtype=np.uint32))
            deer_CPMG_buffer = [ni_sample_buffer]
            
            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            # Setup the SRS
            gw.sg.set_frequency(kwargs['nv_mw_freq'])
            gw.sg.set_rf_amplitude(kwargs['nv_mw_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')
            # Setup the WindFreak power
            gw.windfreak.set_power_ch0(kwargs['el_mw_power'])

            ps_seq = gw.ps.DEER_CPMG(kwargs['pihalf_x']*1e9, kwargs['pihalf_y']*1e9, 
                                kwargs['pi_x']*1e9, kwargs['pi_y']*1e9, 
                                kwargs['tau']*1e9, kwargs['pi_electron']*1e9, kwargs['n'])
                        
            gw.daq.open_task(len(deer_CPMG_buffer[0]))
            dark_ms1_sweeps = StreamingList()
            dark_ms0_sweeps = StreamingList()
            echo_ms1_sweeps = StreamingList()
            echo_ms0_sweeps = StreamingList()

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):
                    # photon counts corresponding to each frequency
                    # initialize to NaN
                    dark_ms1 = np.empty(kwargs['num_pts'])
                    dark_ms1[:] = np.nan
                    dark_ms1_sweeps.append(np.stack([frequencies/1e9, dark_ms1]))
                    dark_ms0 = np.empty(kwargs['num_pts'])
                    dark_ms0[:] = np.nan
                    dark_ms0_sweeps.append(np.stack([frequencies/1e9, dark_ms0]))
                    echo_ms1 = np.empty(kwargs['num_pts'])
                    echo_ms1[:] = np.nan
                    echo_ms1_sweeps.append(np.stack([frequencies/1e9, echo_ms1]))
                    echo_ms0 = np.empty(kwargs['num_pts'])
                    echo_ms0[:] = np.nan
                    echo_ms0_sweeps.append(np.stack([frequencies/1e9, echo_ms0]))
                    for f, freq in enumerate(frequencies):
                        gw.windfreak.set_freq_ch0(freq)
                        gw.windfreak.ch0_on()
                        #gw.windfreak.ch0_off()#For debug
                        #print('\nset WindFreak Freq to be:',freq)
                        #print('\nWindFreak Freq now is:', gw.windfreak.get_freq_ch0())
                        deer_CPMG_result = self.read(deer_CPMG_buffer[0], ps_seq, kwargs['runs'])
                        dark_ms1, dark_ms0, echo_ms1, echo_ms0 = self.digital_math(deer_CPMG_result, 'DEER_CPMG')
                        # record the photon counts
                        dark_ms1_sweeps[-1][1][f] = dark_ms1
                        dark_ms0_sweeps[-1][1][f] = dark_ms0
                        echo_ms1_sweeps[-1][1][f] = echo_ms1
                        echo_ms0_sweeps[-1][1][f] = echo_ms0
                        # notify the streaminglist that this entry has updated so it will be pushed to the data server
                        dark_ms1_sweeps.updated_item(-1)
                        dark_ms0_sweeps.updated_item(-1)
                        echo_ms1_sweeps.updated_item(-1)
                        echo_ms0_sweeps.updated_item(-1)
                        #print('\nfreq now:',freq)
                        #print('\ndark_ms1_sweeps[-1] = ',dark_ms1_sweeps[-1])
                        deer_CPMG_data.push({'params': {'start': kwargs['start'], 'stop': kwargs['stop'], 'num_pts': kwargs['num_pts'], 'iterations': kwargs['iters']},
                                    'title': 'DEER CPMG',
                                    'xlabel': 'Frequency (GHz)',
                                    'ylabel': 'Counts',
                                    'datasets': {'dark_ms1' : dark_ms1_sweeps,
                                                'dark_ms0': dark_ms0_sweeps,
                                                'echo_ms1' : echo_ms1_sweeps,
                                                'echo_ms0': echo_ms0_sweeps}
                        })
                        if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                            gw.daq.close_task()
                            gw.sg.set_rf_toggle(0)
                            gw.sg.set_mod_toggle(0)
                            gw.ps.Pulser.reset()
                            gw.laser.off()
                            gw.windfreak.ch0_off()
                            print('the GUI has asked us nicely to exit')
                            return
                    pbar.update(1)

            gw.daq.close_task()
            gw.sg.set_rf_toggle(0) 
            gw.sg.set_mod_toggle(0) 
            gw.ps.Pulser.reset()
            gw.laser.off()
            gw.windfreak.ch0_off()

    def ReporterT1_run(self, **kwargs):
        '''
        Developed by Tengyang July20.2024. Based on DEER_rabi_run logic.
        '''
        with InstrumentGateway() as gw, DataSource('reporterT1') as reporterT1_data:
            if kwargs['tau_type']=='linear':
                tau_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
                print("Using linear sampling.")
            #These code is copied from T2 run. The commented codes are ones not needed.
            #x_axis_data = np.copy(tau_times)
            #tau_times = self.sort_taus_for_balance(tau_times) 
            #index_order = np.argsort(tau_times) 
            #tau_balance = True
            elif kwargs['tau_type']=='exp':
                tau_times = np.geomspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
                print("Using exponential sampling.")
            #x_axis_data = np.copy(tau_times)
            #np.random.shuffle(tau_times)
            # index order of sorted mw_times used to match x and y axis order for plotting
            #index_order = np.argsort(tau_times) 
            #tau_balance = False
            #The interaction times between the rf-pulses.
            #num_tau = len(tau_times)

            # define buffer size here
            reporterT1_buffer_size = 8*kwargs['runs']*kwargs['num_pts']
            if reporterT1_buffer_size < 8:
                raise ValueError("Buffer size too small.")
            
            ni_sample_buffer = np.ascontiguousarray(np.zeros(reporterT1_buffer_size, dtype=np.uint32))
            reporterT1_buffer = [ni_sample_buffer]

            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            # Setup the SRS
            gw.sg.set_frequency(kwargs['nv_mw_freq'])
            gw.sg.set_rf_amplitude(kwargs['nv_mw_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')
            # Setup the WindFreak power and frequency
            gw.windfreak.set_power_ch0(kwargs['el_mw_power'])
            gw.windfreak.set_freq_ch0(kwargs['el_mw_freq'])
            gw.windfreak.ch0_on()

            print("Tau times before random shuffle:", tau_times)
            np.random.shuffle(tau_times) # random shuffle the mw_times for balancing the heating and charge of the sample
            print("Tau times after random shuffle:", tau_times)

            #tau_times = np.insert(tau_times, 0, 1) # insert 1 ns as first data point that will be skipped in plotting           
            # TXZ: The reason we have this first 1ns data point (but throw it away when plotting) is to warm up the experimentl setup
            num_tau = len(tau_times)

            ps_seq = gw.ps.ReporterSpin_T1(tau_times, kwargs['pihalf_x']*1e9, kwargs['pihalf_y']*1e9, 
                                kwargs['pi_x']*1e9, kwargs['pi_y']*1e9, kwargs['tau0']*1e9, kwargs['extra_pipulse']*1e9,
                                kwargs['pi_electron']*1e9)

            # index order of sorted mw_times 
            # used to match x and y axis order for plotting
            index_order = np.argsort(tau_times) 
            tau_times_ordered = np.sort(tau_times) # record the ordered mw_times for Rabi plotting
            # order mw_times for Rabi plotting

            gw.daq.open_task(len(reporterT1_buffer[0]))
            dark_ms1_sweeps = StreamingList()
            dark_ms0_sweeps = StreamingList()
            echo_ms1_sweeps = StreamingList()
            echo_ms0_sweeps = StreamingList()

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):
                    
                    reporterT1_result = self.read(reporterT1_buffer[0], ps_seq, kwargs['runs'])

                    # partition buffer into signal and background datasets
                    dark_ms1_array, dark_ms0_array, echo_ms1_array, echo_ms0_array = self.digital_math(reporterT1_result, 'reporterT1', kwargs['num_pts'])
                    
                    # correct the y-axis data ordering for plots
                    dark_ms1_array = np.array([dark_ms1_array[i] for i in index_order])
                    dark_ms0_array = np.array([dark_ms0_array[i] for i in index_order])
                    echo_ms1_array = np.array([echo_ms1_array[i] for i in index_order])
                    echo_ms0_array = np.array([echo_ms0_array[i] for i in index_order])
                    #print('tau_times is: \n',tau_times)
                    #Multipying tau_times by two because the x-axis will be 2tau
                    dark_ms1_sweeps.append(np.stack([tau_times_ordered, dark_ms1_array]))
                    dark_ms0_sweeps.append(np.stack([tau_times_ordered, dark_ms0_array]))
                    echo_ms1_sweeps.append(np.stack([tau_times_ordered, echo_ms1_array]))
                    echo_ms0_sweeps.append(np.stack([tau_times_ordered, echo_ms0_array]))
                    # notify the streaminglist that this entry has updated so it will be pushed to the data server
                    dark_ms1_sweeps.updated_item(-1)
                    dark_ms0_sweeps.updated_item(-1)
                    echo_ms1_sweeps.updated_item(-1)
                    echo_ms0_sweeps.updated_item(-1)
                    #print('\nfreq now:',freq)
                    #print('\ndark_ms1_sweeps[-1] = ',dark_ms1_sweeps[-1])
                    reporterT1_data.push({'params': {'start': kwargs['start'], 'stop': kwargs['stop'], 'num_pts': kwargs['num_pts'], 'iterations': kwargs['iters']},
                                'title': 'Reporter Spin T1',
                                'xlabel': 'tau (ns)',
                                'ylabel': 'Counts',
                                'datasets': {'dark_ms1' : dark_ms1_sweeps,
                                            'dark_ms0': dark_ms0_sweeps,
                                            'echo_ms1' : echo_ms1_sweeps,
                                            'echo_ms0': echo_ms0_sweeps}
                    })
                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        gw.daq.close_task()
                        gw.sg.set_rf_toggle(0)
                        gw.sg.set_mod_toggle(0)
                        gw.ps.Pulser.reset()
                        gw.laser.off()
                        gw.windfreak.ch0_off()
                        print('the GUI has asked us nicely to exit')
                        return
                    pbar.update(1)

        gw.daq.close_task()
        gw.sg.set_rf_toggle(0) 
        gw.sg.set_mod_toggle(0) 
        gw.ps.Pulser.reset()
        gw.laser.off()
        gw.windfreak.ch0_off()   

    def Correlation_Rabi_Run(self, **kwargs):
            '''
            Developed by Hanyan and Tengyang April.2.2024. Based on DEER_rabi_run logic.
            '''
            with InstrumentGateway() as gw, DataSource('DEER_Correlation_Rabi') as Correlation_Rabi_data:
                
                e_pulse_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9

                # define buffer size here
                Correlation_Rabi_buffer_size = 8*kwargs['runs']*kwargs['num_pts']
                if Correlation_Rabi_buffer_size < 8:
                    raise ValueError("Buffer size too small.")
                
                ni_sample_buffer = np.ascontiguousarray(np.zeros(Correlation_Rabi_buffer_size, dtype=np.uint32))
                Correlation_Rabi_buffer = [ni_sample_buffer]

                # set initial parameters for instrument server devices
                # Turn on the laser
                gw.ps.laser_on()
                gw.laser.las_mode()
                gw.laser.on()
                # Setup the SRS
                gw.sg.set_frequency(kwargs['nv_mw_freq'])
                gw.sg.set_rf_amplitude(kwargs['nv_mw_power'])
                gw.sg.set_mod_type('QAM')
                gw.sg.set_rf_toggle(1)
                gw.sg.set_mod_toggle(1)
                gw.sg.set_mod_function('external')
                # Setup the WindFreak power and frequency
                gw.windfreak.set_power_ch0(kwargs['el_mw_power'])
                gw.windfreak.set_freq_ch0(kwargs['el_mw_freq'])
                gw.windfreak.ch0_on()

                print("e pulse times before random shuffle:", e_pulse_times)
                np.random.shuffle(e_pulse_times) # random shuffle the mw_times for balancing the heating and charge of the sample
                print("e pulse times after random shuffle:", e_pulse_times)

                #tau_times = np.insert(tau_times, 0, 1) # insert 1 ns as first data point that will be skipped in plotting           
                # TXZ: The reason we have this first 1ns data point (but throw it away when plotting) is to warm up the experimentl setup
                num_tau = len(e_pulse_times)

                ps_seq = gw.ps.DEER_Correlation_Rabi(e_pulse_times, kwargs['pihalf_x']*1e9, kwargs['pihalf_y']*1e9, kwargs['pi_x']*1e9, kwargs['pi_y']*1e9,
                                                    kwargs['tau0']*1e9, kwargs['middle_pulse_start_time']*1e9, kwargs['tau']*1e9, kwargs['pi_electron']*1e9,
                                                    kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9)

                # index order of sorted mw_times 
                # used to match x and y axis order for plotting
                index_order = np.argsort(e_pulse_times) 
                e_pulse_times_ordered = np.sort(e_pulse_times) # record the ordered mw_times for Rabi plotting
                # order mw_times for Rabi plotting

                gw.daq.open_task(len(Correlation_Rabi_buffer[0]))
                dark_ms1_sweeps = StreamingList()
                dark_ms0_sweeps = StreamingList()
                echo_ms1_sweeps = StreamingList()
                echo_ms0_sweeps = StreamingList()

                with tqdm(total = kwargs['iters']) as pbar:

                    for iter in range(kwargs['iters']):
                        
                        Correlation_Rabi_result = self.read(Correlation_Rabi_buffer[0], ps_seq, kwargs['runs'])

                        # partition buffer into signal and background datasets
                        dark_ms1_array, dark_ms0_array, echo_ms1_array, echo_ms0_array = self.digital_math(Correlation_Rabi_result, 'Correlation_Rabi', kwargs['num_pts'])
                        
                        # correct the y-axis data ordering for plots
                        dark_ms1_array = np.array([dark_ms1_array[i] for i in index_order])
                        dark_ms0_array = np.array([dark_ms0_array[i] for i in index_order])
                        echo_ms1_array = np.array([echo_ms1_array[i] for i in index_order])
                        echo_ms0_array = np.array([echo_ms0_array[i] for i in index_order])
                        #print('tau_times is: \n',tau_times)
                        #Multipying tau_times by two because the x-axis will be 2tau
                        dark_ms1_sweeps.append(np.stack([e_pulse_times_ordered, dark_ms1_array]))
                        dark_ms0_sweeps.append(np.stack([e_pulse_times_ordered, dark_ms0_array]))
                        echo_ms1_sweeps.append(np.stack([e_pulse_times_ordered, echo_ms1_array]))
                        echo_ms0_sweeps.append(np.stack([e_pulse_times_ordered, echo_ms0_array]))
                        # notify the streaminglist that this entry has updated so it will be pushed to the data server
                        dark_ms1_sweeps.updated_item(-1)
                        dark_ms0_sweeps.updated_item(-1)
                        echo_ms1_sweeps.updated_item(-1)
                        echo_ms0_sweeps.updated_item(-1)
                        #print('\nfreq now:',freq)
                        #print('\ndark_ms1_sweeps[-1] = ',dark_ms1_sweeps[-1])
                        Correlation_Rabi_data.push({'params': {'start': kwargs['start'], 'stop': kwargs['stop'], 'num_pts': kwargs['num_pts'], 'iterations': kwargs['iters']},
                                    'title': 'DEER Correlation Rabi',
                                    'xlabel': 'Reporter Spin Middle Pulse Time (ns)',
                                    'ylabel': 'Counts',
                                    'datasets': {'dark_ms1' : dark_ms1_sweeps,
                                                'dark_ms0': dark_ms0_sweeps,
                                                'echo_ms1' : echo_ms1_sweeps,
                                                'echo_ms0': echo_ms0_sweeps}
                        })
                        if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                            gw.daq.close_task()
                            gw.sg.set_rf_toggle(0)
                            gw.sg.set_mod_toggle(0)
                            gw.ps.Pulser.reset()
                            gw.laser.off()
                            gw.windfreak.ch0_off()
                            print('the GUI has asked us nicely to exit')
                            return
                        pbar.update(1)

            gw.daq.close_task()
            gw.sg.set_rf_toggle(0) 
            gw.sg.set_mod_toggle(0) 
            gw.ps.Pulser.reset()
            gw.laser.off()
            gw.windfreak.ch0_off()   
    
    def ReporterT2_run(self, **kwargs):
            '''
            Developed by Hanyan April 2024. Based on Correlation_Rabi_Run.
            '''
            with InstrumentGateway() as gw, DataSource('ReporterT2') as ReporterT2_data:
                
                e_spin_echo_interaction_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9

                # define buffer size here
                ReporterT2_buffer_size = 8*kwargs['runs']*kwargs['num_pts']
                if ReporterT2_buffer_size < 8:
                    raise ValueError("Buffer size too small.")
                
                ni_sample_buffer = np.ascontiguousarray(np.zeros(ReporterT2_buffer_size, dtype=np.uint32))
                ReporterT2_buffer = [ni_sample_buffer]

                # set initial parameters for instrument server devices
                # Turn on the laser
                gw.ps.laser_on()
                gw.laser.las_mode()
                gw.laser.on()
                # Setup the SRS
                gw.sg.set_frequency(kwargs['nv_mw_freq'])
                gw.sg.set_rf_amplitude(kwargs['nv_mw_power'])
                gw.sg.set_mod_type('QAM')
                gw.sg.set_rf_toggle(1)
                gw.sg.set_mod_toggle(1)
                gw.sg.set_mod_function('external')
                # Setup the WindFreak power and frequency
                gw.windfreak.set_power_ch0(kwargs['el_mw_power'])
                gw.windfreak.set_freq_ch0(kwargs['el_mw_freq'])
                gw.windfreak.ch0_on()

                print("Reporter spin echo interaction times before random shuffle:", e_spin_echo_interaction_times)
                np.random.shuffle(e_spin_echo_interaction_times) # random shuffle the mw_times for balancing the heating and charge of the sample
                print("Reporter spin echo interaction times after random shuffle:", e_spin_echo_interaction_times)

                #tau_times = np.insert(tau_times, 0, 1) # insert 1 ns as first data point that will be skipped in plotting           
                # TXZ: The reason we have this first 1ns data point (but throw it away when plotting) is to warm up the experimentl setup
                num_tau = len(e_spin_echo_interaction_times)

                ps_seq = gw.ps.ReporterSpin_T2(e_spin_echo_interaction_times, kwargs['pihalf_x']*1e9, kwargs['pihalf_y']*1e9, 
                                    kwargs['pi_x']*1e9, kwargs['pi_y']*1e9, kwargs['tau0']*1e9, kwargs['spin_echo_first_DEER_gap_time']*1e9, kwargs['tau']*1e9,
                                    kwargs['pi_electron']*1e9, kwargs['pi_half_electron']*1e9, kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9)

                # index order of sorted mw_times 
                # used to match x and y axis order for plotting
                index_order = np.argsort(e_spin_echo_interaction_times) 
                e_spin_echo_interaction_times_ordered = np.sort(e_spin_echo_interaction_times) # record the ordered mw_times for Rabi plotting
                # order mw_times for Rabi plotting

                gw.daq.open_task(len(ReporterT2_buffer[0]))
                dark_ms1_sweeps = StreamingList()
                dark_ms0_sweeps = StreamingList()
                echo_ms1_sweeps = StreamingList()
                echo_ms0_sweeps = StreamingList()

                with tqdm(total = kwargs['iters']) as pbar:

                    for iter in range(kwargs['iters']):
                        
                        ReporterT2_result = self.read(ReporterT2_buffer[0], ps_seq, kwargs['runs'])

                        # partition buffer into signal and background datasets
                        dark_ms1_array, dark_ms0_array, echo_ms1_array, echo_ms0_array = self.digital_math(ReporterT2_result, 'ReporterT2', kwargs['num_pts'])
                        
                        # correct the y-axis data ordering for plots
                        dark_ms1_array = np.array([dark_ms1_array[i] for i in index_order])
                        dark_ms0_array = np.array([dark_ms0_array[i] for i in index_order])
                        echo_ms1_array = np.array([echo_ms1_array[i] for i in index_order])
                        echo_ms0_array = np.array([echo_ms0_array[i] for i in index_order])
                        #print('tau_times is: \n',tau_times)
                        #Multipying tau_times by two because the x-axis will be 2tau
                        dark_ms1_sweeps.append(np.stack([e_spin_echo_interaction_times_ordered, dark_ms1_array]))
                        dark_ms0_sweeps.append(np.stack([e_spin_echo_interaction_times_ordered, dark_ms0_array]))
                        echo_ms1_sweeps.append(np.stack([e_spin_echo_interaction_times_ordered, echo_ms1_array]))
                        echo_ms0_sweeps.append(np.stack([e_spin_echo_interaction_times_ordered, echo_ms0_array]))
                        # notify the streaminglist that this entry has updated so it will be pushed to the data server
                        dark_ms1_sweeps.updated_item(-1)
                        dark_ms0_sweeps.updated_item(-1)
                        echo_ms1_sweeps.updated_item(-1)
                        echo_ms0_sweeps.updated_item(-1)
                        #print('\nfreq now:',freq)
                        #print('\ndark_ms1_sweeps[-1] = ',dark_ms1_sweeps[-1])
                        ReporterT2_data.push({'params': {'start': kwargs['start'], 'stop': kwargs['stop'], 'num_pts': kwargs['num_pts'], 'iterations': kwargs['iters']},
                                    'title': 'DEER Reporter T2',
                                    'xlabel': 'Reporter Spin Echo Interaction Time Between Pi/2 and Pi Pulse (ns)',
                                    'ylabel': 'Counts',
                                    'datasets': {'dark_ms1' : dark_ms1_sweeps,
                                                'dark_ms0': dark_ms0_sweeps,
                                                'echo_ms1' : echo_ms1_sweeps,
                                                'echo_ms0': echo_ms0_sweeps}
                        })
                        if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                            gw.daq.close_task()
                            gw.sg.set_rf_toggle(0)
                            gw.sg.set_mod_toggle(0)
                            gw.ps.Pulser.reset()
                            gw.laser.off()
                            gw.windfreak.ch0_off()
                            print('the GUI has asked us nicely to exit')
                            return
                        pbar.update(1)

            gw.daq.close_task()
            gw.sg.set_rf_toggle(0) 
            gw.sg.set_mod_toggle(0) 
            gw.ps.Pulser.reset()
            gw.laser.off()
            gw.windfreak.ch0_off()   

    def instantaneuous_diff_run(self, **kwargs):
        '''
        '''
        with InstrumentGateway() as gw, DataSource('instantaneuous_diff') as instantaneous_diff_data:
            if kwargs['tau_type']=='linear':
                tau_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
                print("Using linear sampling.")
                tau_balance = False
            #These code is copied from T2 run. We don't use them here since we are doing the random shuffle later
            #x_axis_data = np.copy(tau_times)
            #tau_times = self.sort_taus_for_balance(tau_times) 
            #index_order = np.argsort(tau_times) 
            #tau_balance = True
            elif kwargs['tau_type']=='exp':
                tau_times = np.geomspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
                print("Using exponential sampling.")
                tau_balance = False
            #x_axis_data = np.copy(tau_times)
            #np.random.shuffle(tau_times)
            # index order of sorted mw_times used to match x and y axis order for plotting
            #index_order = np.argsort(tau_times) 
            #tau_balance = False
            #The interaction times between the rf-pulses.
            #num_tau = len(tau_times)

            # define buffer size here
            instantaneuous_diff_size = 8*kwargs['runs']*kwargs['num_pts']
            if instantaneuous_diff_size < 8:
                raise ValueError("Buffer size too small.")
            
            ni_sample_buffer = np.ascontiguousarray(np.zeros(instantaneuous_diff_size, dtype=np.uint32))
            instantaneous_diff_buffer = [ni_sample_buffer]

            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            # Setup the SRS
            gw.sg.set_frequency(kwargs['nv_mw_freq'])
            gw.sg.set_rf_amplitude(kwargs['nv_mw_power'])
            gw.sg.set_mod_type('QAM')
            gw.sg.set_rf_toggle(1)
            gw.sg.set_mod_toggle(1)
            gw.sg.set_mod_function('external')
            # Setup the WindFreak power and frequency
            gw.windfreak.ch0_on()

            print("Tau times before random shuffle:", tau_times)
            np.random.shuffle(tau_times) # random shuffle the mw_times for balancing the heating and charge of the sample
            print("Tau times after random shuffle:", tau_times)

            #tau_times = np.insert(tau_times, 0, 1) # insert 1 ns as first data point that will be skipped in plotting           
            # TXZ: The reason we have this first 1ns data point (but throw it away when plotting) is to warm up the experimentl setup
            num_tau = len(tau_times)

            init_time, read_time, wait_time, read_wait, seq_gap = kwargs['init_time']*1e9, kwargs['read_time']*1e9, kwargs['wait_time']*1e9, kwargs['read_wait']*1e9, kwargs['seq_gap']*1e9

            
            ps_seq = gw.ps.Instantaneous_diff_phase_cycling(tau_times, tau_balance, kwargs['pihalf_x']*1e9, kwargs['pihalf_y']*1e9, 
                                kwargs['pi_x']*1e9, kwargs['pi_y']*1e9, init_time, read_time, wait_time, read_wait, seq_gap)

            # index order of sorted mw_times 
            # used to match x and y axis order for plotting
            index_order = np.argsort(tau_times) 
            tau_times_ordered = np.sort(tau_times) # record the ordered mw_times for Rabi plotting
            # order mw_times for Rabi plotting

            gw.daq.open_task(len(instantaneous_diff_buffer[0]))
            dark_ms1_sweeps = StreamingList()
            dark_ms0_sweeps = StreamingList()
            echo_ms1_sweeps = StreamingList()
            echo_ms0_sweeps = StreamingList()

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):
                    
                    instantaneous_diff_result = self.read(instantaneous_diff_buffer[0], ps_seq, kwargs['runs'])

                    # partition buffer into signal and background datasets
                    dark_ms1_array, dark_ms0_array, echo_ms1_array, echo_ms0_array = self.digital_math(instantaneous_diff_result, 'instantaneous_diff', kwargs['num_pts'])
                    
                    # correct the y-axis data ordering for plots
                    dark_ms1_array = np.array([dark_ms1_array[i] for i in index_order])
                    dark_ms0_array = np.array([dark_ms0_array[i] for i in index_order])
                    echo_ms1_array = np.array([echo_ms1_array[i] for i in index_order])
                    echo_ms0_array = np.array([echo_ms0_array[i] for i in index_order])
                    #print('tau_times is: \n',tau_times)
                    #Multipying tau_times by two because the x-axis will be 2tau
                    dark_ms1_sweeps.append(np.stack([2 * tau_times_ordered, dark_ms1_array]))
                    dark_ms0_sweeps.append(np.stack([2 * tau_times_ordered, dark_ms0_array]))
                    echo_ms1_sweeps.append(np.stack([2 * tau_times_ordered, echo_ms1_array]))
                    echo_ms0_sweeps.append(np.stack([2 * tau_times_ordered, echo_ms0_array]))
                    # notify the streaminglist that this entry has updated so it will be pushed to the data server
                    dark_ms1_sweeps.updated_item(-1)
                    dark_ms0_sweeps.updated_item(-1)
                    echo_ms1_sweeps.updated_item(-1)
                    echo_ms0_sweeps.updated_item(-1)
                    #print('\nfreq now:',freq)
                    #print('\ndark_ms1_sweeps[-1] = ',dark_ms1_sweeps[-1])
                    instantaneous_diff_data.push({'params': {'start': kwargs['start'], 'stop': kwargs['stop'], 'num_pts': kwargs['num_pts'], 'iterations': kwargs['iters']},
                                'title': 'Instantaneuous Diffusion Phase Cycling',
                                'xlabel': '2 tau (ns)',
                                'ylabel': 'Counts',
                                'datasets': {'dark_ms1' : dark_ms1_sweeps,
                                            'dark_ms0': dark_ms0_sweeps,
                                            'echo_ms1' : echo_ms1_sweeps,
                                            'echo_ms0': echo_ms0_sweeps}
                    })
                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        gw.daq.close_task()
                        gw.sg.set_rf_toggle(0)
                        gw.sg.set_mod_toggle(0)
                        gw.ps.Pulser.reset()
                        gw.laser.off()
                        gw.windfreak.ch0_off()
                        print('the GUI has asked us nicely to exit')
                        return
                    pbar.update(1)

        gw.daq.close_task()
        gw.sg.set_rf_toggle(0) 
        gw.sg.set_mod_toggle(0) 
        gw.ps.Pulser.reset()
        gw.laser.off()
        gw.windfreak.ch0_off()         

    def rabi_no_readwait_run(self, **kwargs):
        '''
        Developed by Tian-Xing in Sept.2023
        '''
        with InstrumentGateway() as gw, DataSource("rabi_no_readwait_run") as rabi_data:
            
            # pi pulse durations that will be swept over in the Rabi measurement (converted to ns)
            mw_times = np.linspace(kwargs['start'], kwargs['stop'], kwargs['num_pts']) * 1e9
            #num_mw = len(mw_times)

            # define buffer size here
            rabi_buffer_size = 4*kwargs['runs']*kwargs['num_pts']
            if rabi_buffer_size < 4:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(rabi_buffer_size, dtype=np.uint32))
            rabi_buffer = [ni_sample_buffer]

            signal_sweeps = StreamingList()
            background_sweeps = StreamingList()

            np.random.shuffle(mw_times) # random shuffel the mw_times for balancing the heating and charge of the sample
            print("MW times after random shuffle:", mw_times)

            # pulse streamer sequence
            if kwargs['rabi_type'] == "SRS":
                print("USING SRS FOR RABI MEASUREMENT.")
                ps_seq = gw.ps.RabiNoReadWait(mw_times, kwargs['xy'], kwargs['init_time']*1e9, kwargs['read_time']*1e9)
                # Setup the MW
                gw.sg.set_frequency(kwargs['freq'])
                gw.sg.set_rf_amplitude(kwargs['rf_power'])
                gw.sg.set_mod_type('QAM')
                gw.sg.set_rf_toggle(1)
                gw.sg.set_mod_toggle(1)
                gw.sg.set_mod_function('external')
            elif kwargs['rabi_type'] == "WindFreak":
                print("USING WINDFREAK FOR RABI MEASUREMENT.")
                ps_seq = gw.ps.Rabi_WindFreak(mw_times, kwargs['xy'], kwargs['init_time']*1e9, kwargs['read_time']*1e9)
                # Setup the MW
                gw.windfreak.set_power_ch0(kwargs['rf_power'])
                gw.windfreak.set_freq_ch0(kwargs['freq'])
                gw.windfreak.ch0_on()
            else:
                raise ValueError("Rabi Type must be SRS or WindFreak!")
            
            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            # Open a readout task on DAQ
            gw.daq.open_task(rabi_buffer_size)
            

            # index order of sorted mw_times 
            # used to match x and y axis order for plotting
            index_order = np.argsort(mw_times) 
            mw_times_ordered = np.sort(mw_times) # record the ordered mw_times for Rabi plotting
            #print('mw_times after np.sort is: \n',mw_times)
            #dataset['mw_times'] = np.sort(mw_times) # order mw_times for Rabi plotting

            with tqdm(total = kwargs['iters']) as pbar:

                for iter in range(kwargs['iters']):
                    
                    rabi_result = self.read(rabi_buffer[0], ps_seq, kwargs['runs'])

                    # partition buffer into signal and background datasets
                    sig_array, bg_array = self.digital_math(rabi_result, 'Rabi', kwargs['num_pts'])
                    
                    
                    # correct the y-axis data ordering for plots
                    sig_array = np.array([sig_array[i] for i in index_order])
                    bg_array = np.array([bg_array[i] for i in index_order])
                    #print('mw_times_ordered is: \n',mw_times_ordered)
                    signal_sweeps.append(np.stack([mw_times_ordered, sig_array]))
                    background_sweeps.append(np.stack([mw_times_ordered, bg_array]))
                    # notify the streaminglist that this entry has updated so it will be pushed to the data server
                    signal_sweeps.updated_item(-1)
                    background_sweeps.updated_item(-1)

                    
                    rabi_data.push({'params': {'mw_num': kwargs['num_pts'], 'iter_num': kwargs['iters'],'runs_num': kwargs['runs']},
                                    'title': 'Rabi',
                                    'xlabel': 'MW Time (ns)',
                                    'ylabel': 'Counts',
                                    'datasets': {'signal' : signal_sweeps,
                                                'background': background_sweeps}
                    })
                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        gw.daq.close_task()
                        gw.ps.Pulser.reset()
                        gw.laser.off()
                        if kwargs['rabi_type'] == "SRS":
                            gw.sg.set_rf_toggle(0)
                            gw.sg.set_mod_toggle(0)
                        else:
                            gw.windfreak.ch0_off()
                        print('the GUI has asked us nicely to exit')
                        return

                    pbar.update(1)

            gw.daq.close_task()
            gw.ps.Pulser.reset()
            gw.laser.off()
            if kwargs['rabi_type'] == "SRS":
                gw.sg.set_rf_toggle(0)
                gw.sg.set_mod_toggle(0)
            else:
                gw.windfreak.ch0_off()
    
    def ContinousRead_run(self, **kwargs):
        '''
        '''
        with InstrumentGateway() as gw, DataSource('ContinousRead_run') as ContinousRead_data:
            ContinousRead_buffer_size =  kwargs['runs']*kwargs['read_window_num']
            if ContinousRead_buffer_size < 2:
                raise ValueError("Buffer size too small.")

            ni_sample_buffer = np.ascontiguousarray(np.zeros(ContinousRead_buffer_size, dtype=np.uint32))
            ContinousRead_buffer = [ni_sample_buffer]
            
            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()

            Time = np.linspace(kwargs['readout_time']*1e9, kwargs['read_window_num']*kwargs['readout_time']*1e9, kwargs['read_window_num'])
            #frequencies = np.linspace(kwargs['start_freq'], kwargs['stop_freq'], kwargs['num_points'])            
            gw.daq.open_task(len(ContinousRead_buffer[0]))
            signal_sweeps = StreamingList()
            #background_sweeps = StreamingList()
            ps_seq = gw.ps.ContinousRead(kwargs['readout_time']*1e9, kwargs['relaxation_time']*1e9, 
                                kwargs['read_window_num'])
            # set initial parameters for instrument server devices
            # Turn on the laser
            gw.ps.laser_on()
            gw.laser.las_mode()
            gw.laser.on()
            #print('sequence is:\n',ps_seq)
            with tqdm(total = kwargs['iterations']) as pbar:

                for iter in range(kwargs['iterations']):
                    # photon counts corresponding to each frequency
                    # initialize to NaN
                    #print('buffer',ContinousRead_buffer[0])
                    #print("runs", kwargs['runs'])
                    ContinousRead_result = self.read(ContinousRead_buffer[0], ps_seq, kwargs['runs']) # read samples to buffer
                    #print("After self.read!!!!!")
                    sig = self.digital_math(ContinousRead_result, 'ContinousRead', kwargs['read_window_num'])
                    #print('sig is:\n',sig)
                    #print('Time is:\n',Time)
                    
                    signal_sweeps.append(np.stack([Time[:-1], sig[:-1]]))

                    #print('signal_sweeps:\n',signal_sweeps)
                    # notify the streaminglist that this entry has updated so it will be pushed to the data server
                    signal_sweeps.updated_item(-1)
                    
                    
                    ContinousRead_data.push({'params': {'read_window_num': kwargs['read_window_num'], 'iter_num': kwargs['iterations'],'runs_num': kwargs['runs'], 'relaxation_time': kwargs['relaxation_time']},
                                    'title': 'ContinousRead',
                                    'xlabel': 'ContinousRead Time (ns)',
                                    'ylabel': 'Counts',
                                    'datasets': {'signal' : signal_sweeps
                                                }
                    })
                    if experiment_widget_process_queue(self.queue_to_exp) == 'stop':
                        gw.daq.close_task()
                        gw.ps.Pulser.reset()
                        gw.laser.off()
                        print('the GUI has asked us nicely to exit')
                        return

                    pbar.update(1)

                gw.daq.close_task()
                gw.laser.off()
