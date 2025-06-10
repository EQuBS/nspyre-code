'''
Pulse sequence class with all sequences used for Nanoscale NMR experiments for new nspyre
All the time are in ns unit

Edited & rewritten by Evan Villafranca - September 10, 2022

Edited & rewritten by Tian-Xing Zheng & Evan Villafranca - starting at July 28, 2023 for dil-fridge setup
'''

import time
import numpy as np
import pandas as pd
from math import sin, cos, radians
import typing as t

from rpyc.utils.classic import obtain

from drivers.swabian.pulsestreamer.grpc.pulse_streamer_grpc import PulseStreamer
from drivers.swabian.pulsestreamer.sequence import Sequence, OutputState

class Pulses():

    '''
    ALL UNITS: [ns]
    '''
    def __init__(self):
        '''
        :param channel_dict: Dictionary of which channels correspond to which instr controls
        :param readout_time: Laser readout time in ns, 400ns is for NV center, use user-defined value when measuring other kind of qubits
        :param laser_time: Laser time to reinit post readout. 2000ns is for NV center, use user-defined value when measuring other kind of qubits
        :param initial_delay: Delay in laser turning on, about 130ns for dil-fridge setup 
        :param MW_buffer_time: Buffer after MW turns off and before the laser NV readout
        :param IQ: IQ modulation/analog channels
        :param switch_delay: the delay time between the trigger of the switch and the switch really turns the MW from the second signal generator on
        :param wait_SG12 = 10ns A necessary time gap between the SG1 and SG2 (20240809 currently occurs when using the MW switch, 10ns is the value, not sure is totally accurate)
        '''
        self.channel_dict = {"clock": 0, "laser": 1, "switch": 2, "":3, "": 4, "": 5, "": 6, "": 7, "": None}
        self.laser_time = 2e3
        self.laser_lag = 130
        self.singlet_decay = 600
        self.readout_time = 400 
        self.MW_buffer_time = 200
        self.clock_time = 10
        self.switch_delay = 5
        self.sampling_time = 50000
        self.trig_spot = 50
        self.awg_trig_time = 10
        self.awg_pulse_delay = 0
        self.rest_time_btw_seqs = 1e3
        ip="169.254.8.2"
        self.Pulser = PulseStreamer(ip)
        print('creating sequence')
        self.sequence = Sequence()
        print('done creating sequence')
        self.latest_streamed = pd.DataFrame({})
        self.total_time = 0 #update when a pulse sequence is streamed

        self.wait_SG12 = 10 # A necessary time gap between the SG1 and SG2 (20240809 currently occurs when using the MW switch, 10ns is the value, not sure is totally accurate)

        #202306 Jason and Tianxing very very rough try, but much better than [-0.0012,-0.0012]
        # self.IQ0 = [0.013,0.013]
        # self.IQ = self.IQ0

        # self.IQpx = [0.4461,-0.0012]
        # self.IQnx = [-0.4922,-0.0082]

        # self.IQpy = [-0.0231,0.4772]
        # self.IQny = [-2.31E-02, -0.4838]

        # IQ ideal values
        # self.IQ0 = [0.0, 0.0]
        # self.IQ = self.IQ0

        # self.IQpx = [0.5, 0.0]
        # self.IQnx = [-0.5, 0.0]

        # self.IQpy = [0.0, 0.5]
        # self.IQny = [0.0, -0.5]

        # 20231207 calibrated by multimeter and PulseStreamer controller, by Tian-Xing
        # self.IQ0 = [0.001, 0.001]
        # self.IQ = self.IQ0

        # self.IQpx = [0.498, 0.001]
        # self.IQnx = [-0.479, 0.001]

        # self.IQpy = [0.001, 0.482]
        # self.IQny = [0.001, -0.48]

        # 20250423 calibrated by multimeter and PulseStreamer controller, by Tian-Xing
        self.IQ0 = [0.0098, 0.0010]
        self.IQ = self.IQ0

        self.IQpx = [0.497, 0.001]
        self.IQnx = [-0.479, 0.001]

        self.IQpy = [0.0098, 0.482]
        self.IQny = [0.0098, -0.481]
        
        #self.IQboth = [0.4355, 0.4667]
        #self.IQtest = [.95, 0]

    def has_sequence(self):
        """
        Has Sequence
        """
        return self.Pulser.hasSequence()
    
    def has_finished(self):
        """
        Has Finished
        """
        return self.Pulser.hasFinished()
    
    # Set the channel on ps for triggering the laser to be 1 
    def laser_on(self):
        return self.Pulser.constant(OutputState([self.channel_dict["laser"]], 0.0, 0.0))
    
    # Set the channel on ps for all digital/analog channel to be 0V 
    def all_zero(self):
        return self.Pulser.constant(OutputState([], 0.0, 0.0))

    # Most important function, it use the obtain() function to transform the rpyc object to original object type.
    # The self.Pulser.stream(seq,n_runs) let the pulse streamer run the sequence by n_runs number of times
    def stream(self,seq,n_runs):
        seq = obtain(seq)
        # print('type(seq) is:', type(seq))
        # print('seq is:', seq)
        self.Pulser.stream(seq,n_runs)

    # TX: what does this function do?
    def clocksource(self,clk_src):
        self.Pulser.selectClock(clk_src)

    # TX: what does this function do?
    def _normalize_IQ(self, IQ):
        self.IQ = IQ/(2.5*np.linalg.norm(IQ))

    # Here, we force the type of time parameters to be an int type in python
    # All times variables here are in unit of ns
    _T = t.TypeVar('_T')

    def convert_type(self, arg: t.Any, converter: _T) -> _T:
        return converter(arg)

    def PiHalf(self, axis, pi_half_time):
        iq_on = pi_half_time
        
        if axis in ["X","x"]:
            mw_I_on = (iq_on, self.IQpx[0])
            mw_Q_on = (iq_on, self.IQpx[1])
        elif axis in ["-X","-x"]:
            mw_I_on = (iq_on, self.IQnx[0])
            mw_Q_on = (iq_on, self.IQnx[1])
        elif axis in ["Y","y"]:
            mw_I_on = (iq_on, self.IQpy[0])
            mw_Q_on = (iq_on, self.IQpy[1])
        elif axis in ["-Y","-y"]:
            mw_I_on = (iq_on, self.IQny[0])
            mw_Q_on = (iq_on, self.IQny[1])
        
        return mw_I_on, mw_Q_on
        
    def Pi(self, axis, pi_time):
        iq_on = pi_time
        if axis in ["X","x"]:
            mw_I_on = (iq_on, self.IQpx[0])
            mw_Q_on = (iq_on, self.IQpx[1])
        elif axis in ["-X","-x"]:
            mw_I_on = (iq_on, self.IQnx[0])
            mw_Q_on = (iq_on, self.IQnx[1])
        elif axis in ["Y","y"]:
            mw_I_on = (iq_on, self.IQpy[0])
            mw_Q_on = (iq_on, self.IQpy[1])
        elif axis in ["-Y","-y"]:
            mw_I_on = (iq_on, self.IQny[0])
            mw_Q_on = (iq_on, self.IQny[1])
        
        return mw_I_on, mw_Q_on

    
    '''
    PULSE SEQUENCES FOR EXPERIMENTS
    '''
    def SigAnalysis(self, runs, sampling_interval):
        
        runs = self.convert_type(round(runs), int)
            
        seq = self.Pulser.createSequence()

        trig_off = sampling_interval - self.clock_time
        daq_clock_seq = [(trig_off, 0), (self.clock_time, 1)]

        daq_clock_seq = daq_clock_seq*runs

        seq.setDigital(0, daq_clock_seq) # integrator trigger

        return seq
        
    def SigvsTime(self, sampling_interval):
        seq = self.Pulser.createSequence()
        
        trig_off = sampling_interval - self.clock_time
        daq_clock_seq = [(trig_off, 0), (self.clock_time, 1)]
        print(daq_clock_seq)

        #seq.setDigital(0, daq_clock_seq) # integrator trigger
        seq.setDigital(self.channel_dict["clock"], daq_clock_seq)

        # Makre sure the laser trigger is on while ps is streaming the sequence, this is only for fixing the bug of DLnsec laser
        laser_on_seq = [(sampling_interval, 1)]
        seq.setDigital(self.channel_dict["laser"], laser_on_seq)

        return seq
    
    def CW_ODMR(self, runs, probe_time):
        '''
        CW ODMR Sequence
        Laser on for entire sequence. 
        MW on for probe_time.
        MW off for probe_time.
        Tian-Xing  Zheng, Sept.21.2023
        '''
        #print('\n runs in CW_ODMR() = ', runs)
        # create sequence object
        seq = self.Pulser.createSequence()
        
        # set DAQ trigger off time based on optimal readout window during MW on/off window
        clock_on = self.clock_time
        clock_off = probe_time - self.clock_time

        iq_on = probe_time 
        iq_off = probe_time

        # define sequence structure for clock and MW I/Q channels
        #daq_clock_seq = [(clock_off1, 0), (clock_on, 1), (clock_off2, 0), (clock_on, 1), (clock_off3, 0)]
        daq_clock_seq = [(clock_on, 1), (clock_off, 0), (clock_on, 1), (clock_off, 0)]*runs
        mw_I_seq = [(iq_on, self.IQpx[0]), (iq_off, self.IQ0[0])]*runs
        mw_Q_seq = [(iq_on, self.IQpx[1]), (iq_off, self.IQ0[1])]*runs

        # Last clock to collect for the last point in the run        
        daq_clock_seq += [(self.clock_time, 1)]
        mw_I_seq += [(self.clock_time, self.IQ0[0])]
        mw_Q_seq += [(self.clock_time, self.IQ0[1])]

        # Makre sure the laser trigger is on while ps is streaming the sequence, this is only for fixing the bug of DLnsec laser
        laser_on_seq = [(probe_time*runs + self.clock_time, 1)]
        seq.setDigital(self.channel_dict["laser"], laser_on_seq)

        # assign sequences to respective channels
        seq.setDigital(self.channel_dict['clock'], daq_clock_seq) # DAQ clock -- record data
        # seq.setDigital(1, switch_seq) # RF switch
        seq.setAnalog(0, mw_I_seq) # mw_I
        seq.setAnalog(1, mw_Q_seq) # mw_Q

        return seq
    
    def CW_ODMR_Switch(self, runs, probe_time):
        '''
        CW ODMR Sequence that using MW switch to turn MW on/off
        Can be used to the SG that don't have internal IQ modulation, such as: WindFreak
        Laser on for entire sequence. 
        MW on for probe_time.
        MW off for probe_time.
        Tian-Xing  Zheng, Feb.12.2024
        '''
        #print('\n runs in CW_ODMR() = ', runs)
        # create sequence object
        seq = self.Pulser.createSequence()
        
        # set DAQ trigger off time based on optimal readout window during MW on/off window
        clock_on = self.clock_time
        clock_off = probe_time - self.clock_time

        mw_on = probe_time 
        mw_off = probe_time

        # define sequence structure for clock and MW I/Q channels
        #daq_clock_seq = [(clock_off1, 0), (clock_on, 1), (clock_off2, 0), (clock_on, 1), (clock_off3, 0)]
        daq_clock_seq = [(clock_on, 1), (clock_off, 0), (clock_on, 1), (clock_off, 0)]*runs
        # define the control of the MW switch
        switch_seq = [(mw_on - self.switch_delay, 1),(mw_off + self.switch_delay, 0)]*runs

        # Last clock to collect for the last point in the run        
        daq_clock_seq += [(self.clock_time, 1)]
        switch_seq += [(self.clock_time, 0)]

        # Makre sure the laser trigger is on while ps is streaming the sequence, this is only for fixing the bug of DLnsec laser
        laser_on_seq = [(probe_time*runs + self.clock_time, 1)]
        seq.setDigital(self.channel_dict["laser"], laser_on_seq)

        # assign sequences to respective channels
        seq.setDigital(self.channel_dict['clock'], daq_clock_seq) # DAQ clock -- record data
        seq.setDigital(self.channel_dict["switch"], switch_seq) # RF control switch
        
        return seq

    def Pulsed_ODMR(self, pi_xy, pi_time, runs, init_time, read_time, wait_time, read_wait, seq_gap):
        '''
        Pulsed ODMR sequence by Tengyang and Hanyan, Nov.2024
        Need to test it on an known sample
        '''
        ## Run a pi pulse, then measure the signal
        ## and reference counts from NV.
        pi_time = self.convert_type(round(pi_time), float)
        self.laser_time = init_time
        self.readout_time = read_time
        ## we can measure the pi time on x and on y.
        ## they should be the same, but they technically
        ## have different offsets on our pulse streamer.
        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        elif pi_xy == 'y':
            self.IQ_ON = self.IQpy
        else:
            raise ValueError("pi_xy must be 'x' or 'y'!")
        #def Pi(axis):
            #iq_on = pi_time 
            
            #if axis == 'x':
                #mw_I_on = (iq_on, self.IQpx[0])
                #mw_Q_on = (iq_on, self.IQpx[1])
            #else:
                #mw_I_on = (iq_on, self.IQpy[0])
                #mw_Q_on = (iq_on, self.IQpy[1])
            
            #return mw_I_on, mw_Q_on

        def SinglePulsed_ODMR():
            '''
            CREATE SINGLE RABI SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT

            pad_time: padding time to equalize duration of every run (for different vsg_on durations)
            '''
            #pad_time = 50000 - self.laser_lag - self.laser_time - self.singlet_decay - pi_time - self.MW_buffer_time - self.readout_time 
            #pad_time = 50000 - self.laser_lag - self.laser_time - wait_time - pi_time - self.MW_buffer_time - read_wait - self.readout_time
            pad_time= 200

            init_laser_time = self.laser_time
            laser_off1 = wait_time + pi_time + self.MW_buffer_time + read_wait
            laser_off2 = 200 + pad_time + seq_gap
            self.total_time = init_laser_time + laser_off1 + self.readout_time + laser_off2

            # mw I & Q off windows
            
            iq_off1 = self.laser_lag + self.laser_time + wait_time
            iq_off2 = self.MW_buffer_time + read_wait + self.readout_time + laser_off2 - self.laser_lag

            # DAQ trigger windows
            clock_off1 = self.laser_lag + self.laser_time + laser_off1
            clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag
            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq_on = self.Pulser.createSequence()
            seq_off = self.Pulser.createSequence()

            # define sequence structure for laser

            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]

  
            # define sequence structure for DAQ
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]

            mw_I_on_seq = [(iq_off1, self.IQ0[0]), (pi_time, self.IQ_ON[0]), (iq_off2, self.IQ0[0])]
            mw_Q_on_seq = [(iq_off1, self.IQ0[1]), (pi_time, self.IQ_ON[1]), (iq_off2, self.IQ0[1])]

            # when MW = OFF
            mw_I_off_seq = [(iq_off1, self.IQ0[0]), (pi_time, self.IQ0[0]), (iq_off2, self.IQ0[0])]
            mw_Q_off_seq = [(iq_off1, self.IQ0[1]), (pi_time, self.IQ0[1]), (iq_off2, self.IQ0[1])]

            # assign sequences to respective channels for seq_on
            seq_on.setDigital(self.channel_dict["laser"], laser_seq) # laser 
            seq_on.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            # seq_on.setDigital(1, switch_on_seq) # RF control switch
            seq_on.setAnalog(0, mw_I_on_seq) # mw_I
            seq_on.setAnalog(1, mw_Q_on_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            seq_off.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_off.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            # seq_off.setDigital(1, switch_off_seq) # RF control switch
            seq_off.setAnalog(0, mw_I_off_seq) # mw_I
            seq_off.setAnalog(1, mw_Q_off_seq) # mw_Q
            return seq_on + seq_off

        seqs = self.Pulser.createSequence()
        seqs = SinglePulsed_ODMR()
        # for i in range(runs):
        #     seqs += SinglePulsed_ODMR()

        return seqs
    
    def ODMR_DoubleResonance(self, pi_xy, pi_time_fix, pi_time_sweep, switch_delay, runs, init_time, read_time, wait_time, read_wait, seq_gap):
        '''
        Pulsed ODMR with one fixed frequency pi-pulse (SRS) and another sweeping frequency pi-pulse (WindFreak)
        Tian-Xing Zheng March.2025
        '''
        ## Run a pi pulse, then measure the signal
        ## and reference counts from NV.
        pi_time_fix = self.convert_type(round(pi_time_fix), float)
        pi_time_sweep = self.convert_type(round(pi_time_sweep), float)
        self.laser_time = init_time
        self.readout_time = read_time
        ## we can measure the pi time on x and on y.
        ## they should be the same, but they technically
        ## have different offsets on our pulse streamer.
        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        elif pi_xy == 'y':
            self.IQ_ON = self.IQpy
        else:
            raise ValueError("pi_xy must be 'x' or 'y'!")

        def Single_ODMR_DoubleResonance():
            '''
            CREATE SINGLE RABI SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT

            pad_time: padding time to equalize duration of every run (for different vsg_on durations)
            '''
            #pad_time = 50000 - self.laser_lag - self.laser_time - self.singlet_decay - pi_time - self.MW_buffer_time - self.readout_time 
            #pad_time = 50000 - self.laser_lag - self.laser_time - wait_time - pi_time - self.MW_buffer_time - read_wait - self.readout_time
            pad_time= 200

            init_laser_time = self.laser_time
            laser_off1 = wait_time + pi_time_fix + pi_time_sweep + self.MW_buffer_time + read_wait
            laser_off2 = pad_time + seq_gap
            self.total_time = init_laser_time + laser_off1 + self.readout_time + laser_off2

            # mw I & Q off windows
            iq_off1 = self.laser_lag + self.laser_time + wait_time
            iq_off2 = pi_time_sweep + self.MW_buffer_time + read_wait + self.readout_time + laser_off2 - self.laser_lag
            # mw by WindFreak control by the microwave switch
            switch_off1 = iq_off1 + pi_time_fix + self.wait_SG12
            switch_on1 = pi_time_sweep + switch_delay
            switch_off2 = -self.wait_SG12 - switch_delay - pi_time_sweep + iq_off2
            # DAQ trigger windows
            clock_off1 = self.laser_lag + self.laser_time + laser_off1
            clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag
            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq_on = self.Pulser.createSequence()
            seq_off = self.Pulser.createSequence()

            # define sequence structure for laser

            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]

  
            # define sequence structure for DAQ
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
            # when MW for the sweep freq pi-pulse is ON
            mw_I_on_seq = [(iq_off1, self.IQ0[0]), (pi_time_fix, self.IQ_ON[0]), (iq_off2, self.IQ0[0])]
            mw_Q_on_seq = [(iq_off1, self.IQ0[1]), (pi_time_fix, self.IQ_ON[1]), (iq_off2, self.IQ0[1])]

            # sequence for driving the electron spin by using the 2nd signal generator and MW switch
            switch_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0)]
            switch_ref_seq = [(switch_off1, 0), (switch_on1, 0), (switch_off2, 0)]

            # assign sequences to respective channels for seq_on
            seq_on.setDigital(self.channel_dict["laser"], laser_seq) # laser 
            seq_on.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq_on.setDigital(self.channel_dict["switch"], switch_seq)
            
            seq_on.setAnalog(0, mw_I_on_seq) # mw_I
            seq_on.setAnalog(1, mw_Q_on_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            seq_off.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_off.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq_off.setDigital(self.channel_dict["switch"], switch_ref_seq)
            
            seq_off.setAnalog(0, mw_I_on_seq) # mw_I
            seq_off.setAnalog(1, mw_Q_on_seq) # mw_Q
            return seq_on + seq_off

        seqs = self.Pulser.createSequence()
        seqs = Single_ODMR_DoubleResonance()
        # for i in range(runs):
        #     seqs += SinglePulsed_ODMR()

        return seqs

    def Rabi(self, params, pi_xy, init_time, read_time, wait_time, read_wait, seq_gap):
        '''
        Rabi sequence
        init_time: laser duration for initialize the qubit
        read_time: laser duration for readout the qubit
        wait_time: waiting duration after the initialization laser
        read_wait: waiting duration before the readout laser
        seq_gap: waiting time after each sequence is done, for reinitialization. If needed
        '''
        ## Run a MW pulse of varying duration, then measure the signal
        ## and reference counts from NV.
        # self.total_time = 0
        longest_time = self.convert_type(round(max(params)), float)
        self.laser_time = init_time
        self.readout_time = read_time
        ## we can measure the pi time on x and on y.
        ## they should be the same, but they technically
        ## have different offsets on our pulse streamer.
        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        elif pi_xy == 'y':
            self.IQ_ON = self.IQpy
        else:
            raise ValueError("pi_xy must be 'x' or 'y'!")

        def SingleRabi(iq_on):
            '''
            CREATE SINGLE RABI SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            iq_on = float(round(iq_on)) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run (for different vsg_on durations)

            pad_time = longest_time - iq_on

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            init_laser_time = self.laser_time
            #laser_off1 = self.singlet_decay + iq_on + self.MW_buffer_time
            #laser_off1 = wait_time + iq_on + self.MW_buffer_time
            laser_off1 = wait_time + iq_on + self.MW_buffer_time + read_wait
            laser_off2 = 200 + pad_time + seq_gap
            self.total_time = init_laser_time + laser_off1 + self.readout_time + laser_off2

            # mw I & Q off windows
            #iq_off1 = self.laser_lag + self.laser_time + self.singlet_decay
            iq_off1 = self.laser_lag + self.laser_time + wait_time
            #iq_off2 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag
            iq_off2 = self.MW_buffer_time + read_wait + self.readout_time + laser_off2 - self.laser_lag

            # DAQ trigger windows
            clock_off1 = self.laser_lag + self.laser_time + laser_off1
            clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag
                   
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq_on = self.Pulser.createSequence()
            seq_off = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]
            
            # define sequence structure for DAQ trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # define sequence structure for MW I and Q when MW = ON
            mw_I_on_seq = [(iq_off1, self.IQ0[0]), (iq_on, self.IQ_ON[0]), (iq_off2, self.IQ0[0])]
            mw_Q_on_seq = [(iq_off1, self.IQ0[1]), (iq_on, self.IQ_ON[1]), (iq_off2, self.IQ0[1])]

            # when MW = OFF
            mw_I_off_seq = [(iq_off1, self.IQ0[0]), (iq_on, self.IQ0[0]), (iq_off2, self.IQ0[0])]
            mw_Q_off_seq = [(iq_off1, self.IQ0[1]), (iq_on, self.IQ0[1]), (iq_off2, self.IQ0[1])]
            #print('\ndaq_clock_seq is:\n',daq_clock_seq)
            # assign sequences to respective channels for seq_on
            seq_on.setDigital(self.channel_dict["laser"], laser_seq) # laser 
            seq_on.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            # seq_on.setDigital(1, switch_on_seq) # RF control switch
            seq_on.setAnalog(0, mw_I_on_seq) # mw_I
            seq_on.setAnalog(1, mw_Q_on_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            seq_off.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_off.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            # seq_off.setDigital(1, switch_off_seq) # RF control switch
            seq_off.setAnalog(0, mw_I_off_seq) # mw_I
            seq_off.setAnalog(1, mw_Q_off_seq) # mw_Q

            return seq_on + seq_off

        seqs = self.Pulser.createSequence()
        seqs_total_time = 0
        for mw_time in params:
            seqs += SingleRabi(mw_time)
            seqs_total_time += 2*self.total_time
        print('Rabi sequence created!')
        print('sequence time for 1 run is (ns):',seqs_total_time)
        return seqs

    def Rabi_WindFreak(self, params, pi_xy, init_time, read_time, wait_time, read_wait, switch_delay, seq_gap):
        '''
        Rabi sequence by using the WindFreak signal generator pulse a ZFSWA2-63DR+ MW switch
        init_time: laser duration for initialize the qubit
        read_time: laser duration for readout the qubit
        wait_time: waiting duration after the initialization laser
        read_wait: waiting duration before the readout laser
        '''
        ## Run a MW pulse of varying duration, then measure the signal
        ## and reference counts from NV.
        # self.total_time = 0
        longest_time = self.convert_type(round(max(params)), float)
        self.laser_time = init_time
        self.readout_time = read_time
        ## we can measure the pi time on x and on y.
        ## they should be the same, but they technically
        ## have different offsets on our pulse streamer.
        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        elif pi_xy == 'y':
            self.IQ_ON = self.IQpy
        else:
            raise ValueError("pi_xy must be 'x' or 'y'!")

        def SingleRabi(iq_on):
            '''
            CREATE SINGLE RABI SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            iq_on = float(round(iq_on)) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run (for different vsg_on durations)
            # pad_time = 50000 - self.laser_lag - self.laser_time - self.singlet_decay - iq_on - self.MW_buffer_time - self.readout_time 
            pad_time = longest_time - iq_on

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            init_laser_time = self.laser_time
            #laser_off1 = self.singlet_decay + iq_on + self.MW_buffer_time
            #laser_off1 = wait_time + iq_on + self.MW_buffer_time
            laser_off1 = wait_time + iq_on + self.MW_buffer_time + read_wait
            laser_off2 = 200 + pad_time + seq_gap
            self.total_time = init_laser_time + laser_off1 + self.readout_time + laser_off2

            # mw I & Q off windows
            #iq_off1 = self.laser_lag + self.laser_time + self.singlet_decay
            iq_off1 = self.laser_lag + self.laser_time + wait_time
            #q_off2 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag
            iq_off2 = self.MW_buffer_time + read_wait + self.readout_time + laser_off2 - self.laser_lag

            # DAQ trigger windows
            clock_off1 = self.laser_lag + self.laser_time + laser_off1
            clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag
                   
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq_on = self.Pulser.createSequence()
            seq_off = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]
            
            # define sequence structure for DAQ trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # define the control of the MW switch
            # switch_delay = 5
            #switch_on_seq = [(iq_off1 - self.switch_delay, 0), (iq_on + self.switch_delay, 1), (iq_off2 , 0)]
            #switch_off_seq = [(iq_off1 - self.switch_delay, 0), (iq_on + self.switch_delay, 0), (iq_off2, 0)]
            #switch_delay is changeable
            switch_on_seq = [(iq_off1 - switch_delay, 0), (iq_on + switch_delay, 1), (iq_off2 , 0)]
            switch_off_seq = [(iq_off1 - switch_delay, 0), (iq_on + switch_delay, 0), (iq_off2, 0)]
            # define sequence structure for MW I and Q when MW = ON
            #mw_I_on_seq = [(iq_off1, self.IQ0[0]), (iq_on, self.IQ_ON[0]), (iq_off2, self.IQ0[0])]
            #mw_Q_on_seq = [(iq_off1, self.IQ0[1]), (iq_on, self.IQ_ON[1]), (iq_off2, self.IQ0[1])]

            # when MW = OFF
            #mw_I_off_seq = [(iq_off1, self.IQ0[0]), (iq_on, self.IQ0[0]), (iq_off2, self.IQ0[0])]
            #mw_Q_off_seq = [(iq_off1, self.IQ0[1]), (iq_on, self.IQ0[1]), (iq_off2, self.IQ0[1])]
            #print('\ndaq_clock_seq is:\n',daq_clock_seq)
            # assign sequences to respective channels for seq_on
            seq_on.setDigital(self.channel_dict["laser"], laser_seq) # laser 
            seq_on.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq_on.setDigital(self.channel_dict["switch"], switch_on_seq) # RF control switch
            #seq_on.setAnalog(0, mw_I_on_seq) # mw_I
            #seq_on.setAnalog(1, mw_Q_on_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            seq_off.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_off.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq_off.setDigital(self.channel_dict["switch"], switch_off_seq) # RF control switch
            #seq_off.setAnalog(0, mw_I_off_seq) # mw_I
            #seq_off.setAnalog(1, mw_Q_off_seq) # mw_Q

            return seq_on + seq_off

        seqs = self.Pulser.createSequence()
        seqs_total_time = 0
        for mw_time in params:
            seqs += SingleRabi(mw_time)
            seqs_total_time += 2*self.total_time
        print('Rabi sequence created!')
        print('sequence time for 1 run is (ns):',seqs_total_time)
        return seqs

    def Rabi_AWG(self, params, pi_xy, wait_time):
        '''
        Rabi sequence
        init_time: laser duration for initialize the qubit
        read_time: laser duration for readout the qubit
        wait_time: waiting duration after the initialization laser
        read_wait: waiting duration before the readout laser
        '''
        ## Run a MW pulse of varying duration, then measure the signal
        ## and reference counts from NV.
        # self.total_time = 0
        longest_time = self.convert_type(round(max(params)), float)
        ## we can measure the pi time on x and on y.
        ## they should be the same, but they technically
        ## have different offsets on our pulse streamer.
        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        else:
            self.IQ_ON = self.IQpy

        def SingleRabi(iq_on):
            '''
            CREATE SINGLE RABI SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            iq_on = float(round(iq_on)) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run (for different vsg_on durations)
            # pad_time = 50000 - self.laser_lag - self.laser_time - self.singlet_decay - iq_on - self.MW_buffer_time - self.readout_time 
            pad_time = longest_time - iq_on

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''

            laser_off1 = self.laser_lag 
            #laser_off2 = self.singlet_decay + iq_on + self.MW_buffer_time
            laser_off2 = wait_time + iq_on + self.MW_buffer_time
            laser_off3 = 100 + pad_time 
            # laser_off3 = pad_time + self.rest_time_btw_seqs
            # laser_off4 = laser_off2
            # laser_off5 = self.rest_time_btw_seqs

            # mw I & Q off windows
            #iq_off1 = laser_off1 + self.laser_time + self.singlet_decay
            iq_off1 = laser_off1 + self.laser_time + wait_time
            iq_off2 = self.MW_buffer_time + 1*self.readout_time + laser_off3 # + self.laser_time # + laser_off4 + laser_off5

            # DAQ trigger windows
            clock_off1 = laser_off1 + self.laser_time + laser_off2 + self.readout_time - self.trig_spot - self.clock_time
            clock_off2 = self.trig_spot + laser_off3
            
            print("SEQ TOTAL TIME = ", iq_off1 + iq_on + iq_off2)
            print("TIME AFTER MW PULSE = ", laser_off3)
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq_on = self.Pulser.createSequence()
            seq_off = self.Pulser.createSequence()

            # define sequence structure for laser            
            laser_seq = [(laser_off1, 0), (self.laser_time, 1), (laser_off2, 0), (self.readout_time, 1), (laser_off3, 0)]
                        #  (laser_off3, 0), (self.laser_time, 1), (laser_off4, 0), (self.readout_time, 1), (laser_off5, 0)]
        
            # define sequence structure for DAQ trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off2, 0)]

            # define sequence structure for MW I and Q when MW = ON
            mw_I_on_seq = [(iq_off1, self.IQ0[0]), (iq_on, self.IQ_ON[0]), (iq_off2, self.IQ0[0])]
            mw_Q_on_seq = [(iq_off1, self.IQ0[1]), (iq_on, self.IQ_ON[1]), (iq_off2, self.IQ0[1])]
            
            # when MW = OFF
            mw_I_off_seq = [(iq_off1, self.IQ0[0]), (iq_on, self.IQ0[0]), (iq_off2, self.IQ0[0])]
            mw_Q_off_seq = [(iq_off1, self.IQ0[1]), (iq_on, self.IQ0[1]), (iq_off2, self.IQ0[1])]

            awg_seq = [(iq_off1, 0), (self.awg_trig_time, 1), (iq_off2 + iq_on - self.awg_trig_time, 0)]
            awg_ref_seq = [(iq_off1, 0), (self.awg_trig_time, 0), (iq_off2 + iq_on - self.awg_trig_time, 0)]
            # switch_on_seq = [(iq_off1 - 20, 0), (iq_on + 40, 1), (iq_off2 - 20, 0)]
            # switch_off_seq = [(iq_off1 - 20, 0), (iq_on + 40, 0), (iq_off2 - 20, 0)]

            # assign sequences to respective channels for seq_on
            seq_on.setDigital(3, laser_seq) # laser 
            seq_on.setDigital(0, daq_clock_seq) # integrator trigger
            seq_on.setDigital(4, awg_seq)
            # seq_on.setDigital(1, switch_on_seq) # RF control switch
            seq_on.setAnalog(0, mw_I_on_seq) # mw_I
            seq_on.setAnalog(1, mw_Q_on_seq) # mw_Q
            # seq_on.plot()
            print("LASER SEQ = ", laser_seq)
            print("DAQ SEQ = ", daq_clock_seq)
            print("AWG SEQ = ", awg_seq)

            # assign sequences to respective channels for seq_off
            seq_off.setDigital(3, laser_seq) # laser
            seq_off.setDigital(0, daq_clock_seq) # integrator trigger
            seq_off.setDigital(4, awg_ref_seq)
            # seq_off.setDigital(1, switch_off_seq) # RF control switch
            seq_off.setAnalog(0, mw_I_off_seq) # mw_I
            seq_off.setAnalog(1, mw_Q_off_seq) # mw_Q
            return seq_on + seq_off

        seqs = self.Pulser.createSequence()

        for mw_time in params:
            seqs += SingleRabi(mw_time)

        return seqs
    
    def Calibrate_LaserLag(self, params, buffer_time, read_window, laser_window):
        
        buffer_time = self.convert_type(round(buffer_time), float)
        read_window = self.convert_type(round(read_window), float)
        laser_window = self.convert_type(round(laser_window), float)
        longest_time = self.convert_type(round(max(params)), float) + laser_window + self.rest_time_btw_seqs

        def SingleLag(read_time):
            '''
            CREATE SINGLE T1 SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            read_time = int(round(read_time)) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run
            pad_time = longest_time - read_time

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            #laser_off1 = self.laser_lag + buffer_time + self.trig_delay
            #laser_off2 = buffer_time + self.rest_time_btw_seqs
            laser_off1 = buffer_time
            laser_off2 = longest_time - buffer_time - laser_window

            # integrator trigger windows     
            clock_off1 = read_time
            clock_off2 = read_window - 2*self.clock_time
            clock_off3 = longest_time - read_time - read_window
            #int_trig_off3 = (self.trig_delay - self.clock_time) + pad_time + self.rest_time_btw_seqs       

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(laser_off1, 0), (laser_window, 1), (laser_off2, 0)]

            # define sequence structure for integrator trigger
            #int_trig_seq = [(int_trig_off1, 0), (self.clock_time, 1), (int_trig_off2, 0)]
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off2, 0), (self.clock_time, 1), (clock_off3, 0)]
            

            seq.setDigital(self.channel_dict["laser"], laser_seq) # laser 
            seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger

            return seq

        seqs = self.Pulser.createSequence()

        for read in params:
            seqs += SingleLag(read)

        return seqs

    def Calibrate_Initialize(self, params, init_pulse_length):
        
        longest_time = self.convert_type(round(max(params)), float)
        init_pulse_length = self.convert_type(round(init_pulse_length), float)
        self.initialize = init_pulse_length

        def SingleInitialize(read_time):
            '''
            CREATE SINGLE T1 SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            read_time = int(round(read_time)) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run
            pad_time = longest_time - read_time 

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            laser_off1 = self.laser_lag
            laser_off2 = pad_time + self.rest_time_btw_seqs

            # integrator trigger windows     
            int_trig_off1 = laser_off1 + (read_time - self.trig_delay)
            
            int_trig_off2 = (self.trig_delay - self.clock_time) + self.initialize + laser_off2            

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq1 = self.Pulser.createSequence()
            seq2 = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(laser_off1, 0), (self.initialize, 1), (laser_off2, 0)]

            # define sequence structure for integrator trigger
            int_trig_seq = [(int_trig_off1, 0), (self.clock_time, 1), (int_trig_off2, 0)]

            print("LASER SEQ: ", laser_seq)
            print("TRIG SEQ: ", int_trig_seq)

            # assign sequences to respective channels for seq_on
            seq1.setDigital(7, laser_seq) # laser
            seq1.setDigital(4, int_trig_seq) # integrator trigger
            seq2.setDigital(7, laser_seq) # laser
            seq2.setDigital(4, int_trig_seq) # integrator trigger

            return seq1 + seq2 + seq2 + seq1

        seqs = self.Pulser.createSequence()

        for read in params:
            seqs += SingleInitialize(read)

        return seqs

    def Calibrate_SingletDecay(self, params):
        longest_time = self.convert_type(round(max(params)), float)

        def SingleDecay(decay_time):
            '''
            CREATE SINGLE T1 SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            decay_time = int(round(decay_time)) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run
            pad_time = longest_time - decay_time 

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            laser_off1 = self.laser_lag
            laser_off2 = decay_time
            laser_off3 = pad_time + self.rest_time_btw_seqs

            # integrator trigger windows     
            int_trig_off1 = laser_off1 + self.laser_time + (laser_off2 - self.trig_delay)
            
            int_trig_off2 = (self.trig_delay - self.clock_time) + self.readout_time + laser_off3            

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq1 = self.Pulser.createSequence()
            seq2 = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(laser_off1, 0), (self.laser_time, 1), (laser_off2, 0), (self.readout_time, 1), (laser_off3, 0)]
            
            # define sequence structure for integrator trigger
            int_trig_seq = [(int_trig_off1, 0), (self.clock_time, 1), (int_trig_off2, 0)]

            # assign sequences to respective channels for seq_on
            seq1.setDigital(7, laser_seq) # laser
            seq1.setDigital(4, int_trig_seq) # integrator trigger
            seq2.setDigital(7, laser_seq) # laser
            seq2.setDigital(4, int_trig_seq) # integrator trigger

            return seq1 + seq2 + seq2 + seq1

        seqs = self.Pulser.createSequence()

        for decay in params:
            seqs += SingleDecay(decay)

        return seqs

    def Calibrate_IntSNR(self, pi, pi_xy):
        '''
        Calibrate integration window duration for experiments w/ integrator.
        Assess SNR for these integration windows.
        
        Run a pi pulse, then measure the signal and reference counts from NV.
        '''

        pi_ns = pi.to("ns").magnitude
        iq_buffer = 15
        iq_on = 2*iq_buffer + pi_ns

        def Pi(axis):
            vsg_on = (pi_ns, 1)

            if axis == 'x':
                mw_I_on = (iq_on, self.IQpx[0])
                mw_Q_on = (iq_on, self.IQpx[1])
            elif axis == '-x':
                mw_I_on = (iq_on, self.IQnx[0])
                mw_Q_on = (iq_on, self.IQnx[1])
            elif axis == 'y':
                mw_I_on = (iq_on, self.IQpy[0])
                mw_Q_on = (iq_on, self.IQpy[1])
            elif axis == '-y':
                mw_I_on = (iq_on, self.IQny[0])
                mw_Q_on = (iq_on, self.IQny[1])
            
            return vsg_on, mw_I_on, mw_Q_on

        def SingleSNR():
            '''
            CREATE SINGLE SNR (RABI-LIKE) SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run (for different vsg_on durations)
            pad_time = 50000 - self.laser_time - self.MW_buffer_time - 2*iq_buffer - pi_ns

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off1 = self.laser_time + self.singlet_decay
            iq_off2 = self.MW_buffer_time + self.laser_time + pad_time

            # VSG disable windows
            vsg_off1 = self.laser_time + self.singlet_decay + iq_buffer
            vsg_off2 = iq_buffer + iq_off2

            laser_off1 = self.singlet_decay + iq_on + self.MW_buffer_time
            laser_off2 = pad_time

            # integrator trigger windows
            int_trig_off1 = self.laser_time + (laser_off1 - self.trig_delay)
            int_trig_off2 = (self.trig_delay - self.clock_time) + self.laser_time + pad_time            


            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq_on = self.Pulser.createSequence()
            seq_off = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(self.laser_time, 1), (laser_off1, 0), (self.laser_time, 1), (laser_off2, 0)]
            
            # define sequence structure for integrator trigger
            int_trig_seq = [(int_trig_off1, 0), (self.clock_time, 1), (int_trig_off2, 0)]
            
            # define sequence structure for MW I and Q when MW = ON
            mw_I_on_seq = [(vsg_off1, self.IQ0[0]), (pi_ns, self.IQpx[0]), (vsg_off2, self.IQ0[0])]
            mw_Q_on_seq = [(vsg_off1, self.IQ0[1]), (pi_ns, self.IQpx[1]), (vsg_off2, self.IQ0[1])]
            
            # when MW = OFF
            mw_I_off_seq = [(vsg_off1, self.IQ0[0]), (pi_ns, self.IQ0[0]), (vsg_off2, self.IQ0[0])]
            mw_Q_off_seq = [(vsg_off1, self.IQ0[1]), (pi_ns, self.IQ0[1]), (vsg_off2, self.IQ0[1])]

            # assign sequences to respective channels for seq_on
            seq_on.setDigital(7, laser_seq) # laser
            seq_on.setDigital(4, int_trig_seq) # integrator trigger
            seq_on.setAnalog(0, mw_I_on_seq) # mw_I
            seq_on.setAnalog(1, mw_Q_on_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            seq_off.setDigital(7, laser_seq) # laser
            seq_off.setDigital(4, int_trig_seq) # integrator trigger
            seq_off.setAnalog(0, mw_I_off_seq) # mw_I
            seq_off.setAnalog(1, mw_Q_off_seq) # mw_Q

            return seq_on + seq_off + seq_off + seq_on # sequence order to deal with int. offset

        seqs = SingleSNR()

        return seqs

    def Calibrate_Switch_Echo(self, tau_set, pihalf_x, pihalf_y, pi_x, pi_y):
        '''
        Spin Echo pulse sequence for calibrating RF switch.
        MW sequence: pi/2(x) - tau - pi(y) - tau - pi/2(x)

        '''
        tau_time = self.convert_type(round(tau_set), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)

        def SingleCalEcho():
            '''
            CREATE SINGLE HAHN-ECHO SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''            

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off1 = 200
            iq_off2 = tau_time # /2
            iq_off3 = tau_time # /2
            iq_off4 = 200

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()
            
            # sequence structure for I & Q MW channels 
            mw_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            mw_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            mw_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # for testing switch, keep MW I and Q constantly on
            mw_I_TEST_seq = [(iq_off1, self.IQpx[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQpx[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQpx[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQpx[0])]
            mw_Q_TEST_seq = [(iq_off1, self.IQpx[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQpx[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQpx[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQpx[1])]

            switch_on_seq = [(iq_off1, 0), (pihalf_x, 1), (iq_off2, 0), (pi_y, 1), (iq_off3, 0), (pihalf_x, 1), (iq_off4, 0)]
            switch_off_seq = [(iq_off1, 0), (pihalf_x, 0), (iq_off2, 0), (pi_y, 0), (iq_off3, 0), (pihalf_x, 0), (iq_off4, 0)]

            # switch_on_seq = [(iq_off1 - 20, 0), (pihalf_x + 40, 1), (iq_off2 - 40, 0), (pi_y + 40, 1), (iq_off3 - 40, 0), (pihalf_x + 40, 1), (iq_off4 - 20, 0)]
            # switch_off_seq = [(iq_off1 - 20, 0), (pihalf_x + 40, 0), (iq_off2 - 40, 0), (pi_y + 40, 0), (iq_off3 - 40, 0), (pihalf_x + 40, 0), (iq_off4 - 20, 0)]

            # assign sequences to respective channels for seq_on
            # seq.setDigital(3, laser_seq) # laser
            # seq.setDigital(0, daq_clock_seq) # integrator trigger
            seq.setDigital(5, switch_on_seq) # RF switch 
            seq.setDigital(2, switch_on_seq) # RF switch to oscilloscope
            # seq.setAnalog(0, mw_I_seq) # mw_I
            # seq.setAnalog(1, mw_Q_seq) # mw_Q
            seq.setAnalog(0, mw_I_TEST_seq) # mw_I
            seq.setAnalog(1, mw_Q_TEST_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            # seq_ref.setDigital(3, laser_seq) # laser
            # seq_ref.setDigital(0, daq_clock_seq) # integrator trigger
            seq_ref.setDigital(5, switch_off_seq) # RF switch 
            seq_ref.setDigital(2, switch_off_seq) # RF switch to oscilloscope
            # seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            # seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q
            seq_ref.setAnalog(0, mw_I_TEST_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_TEST_seq) # mw_Q

            return seq # + seq_ref 

        seqs = SingleCalEcho()

        return seqs
    
    def Calibrate_DEER_offset(self):

        def SingleCalDEER():
            '''
            CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''
            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off1 = 0
            iq_on = 200
            
            awg_off = 1000
            awg_trig = 10
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            
            # sequence structure for I & Q MW channels on SRS SG396
            # srs_I_seq = [(iq_off1, self.IQpx[0]), (iq_on, self.IQpx[0]), (1000, self.IQpx[0])]
            # srs_Q_seq = [(iq_off1, self.IQpx[1]), (iq_on, self.IQpx[1]), (1000, self.IQpx[1])]

            srs_I_seq = [(iq_off1, self.IQ0[0]), (iq_on, 1), (10, self.IQ0[0])]
            srs_Q_seq = [(iq_off1, self.IQ0[1]), (iq_on, 0), (10, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            awg_seq = [(0, 0), (awg_trig, 1), (10, 0)]

            # print("SRS I: ", srs_I_seq)
            print("AWG: ", awg_seq)
            # assign sequences to respective channels for seq_on
            seq.setDigital(4, awg_seq)
            seq.setAnalog(0, srs_I_seq) # mw_I
            seq.setAnalog(1, srs_Q_seq) # mw_Q

            return seq
        
        # concatenate single ODMR sequence "runs" number of times

        seqs = SingleCalDEER()

        return seqs
 
    def Optical_T1(self, params, tau_balance, init_time, read_time, seq_gap ,forNV=True):
        '''
        Optical T1 sequence with integrator
        By Tian-Xing Zheng and Tengyang Ruan Sept.2024. Modified from Evan's code
        "seq_gap": for sample to relax and reinitialize. Its also helpful for the DAQ speed issue
        '''
        self.laser_time = init_time
        self.readout_time = read_time
        longest_time = self.convert_type(round(max(params)), float)
        print("LONGEST T1 time to plot: ", longest_time)
        ## we can measure the pi time on x and on y.
        ## they should be the same, but they technically
        ## have different offsets on our pulse streamer.

        def SingleOptical_T1(tau_time, tau_balance, seq_gap, forNV=True):
            '''
            CREATE SINGLE T1 SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            tau_time = self.convert_type(round(tau_time), float) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run
            pad_time = longest_time - tau_time 

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            init_laser_time = self.laser_time
            if forNV is True:
                # The optical T1 sequence is for measuring NV and we need to add the singlet_decay time
                laser_off1 = self.singlet_decay + tau_time
                
            else:
                # Optical T1 sequence for all fluorescence molecules/spin defects, only wait for \tau
                laser_off1 = tau_time

            if tau_balance:
                laser_off2 = 200 + pad_time + seq_gap
            else:
                laser_off2 = 200 + seq_gap
            self.total_time = init_laser_time + laser_off1 + self.readout_time + laser_off2

            # DAQ trigger clock times
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects
            seq = self.Pulser.createSequence()


            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]

            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout,0), (self.clock_time, 1), (clock_off2, 0)]

            # print("LASER SEQ: ", laser_seq)

            # assign sequences to respective channels for seq_on
            seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger            

            return seq 

        seqs = self.Pulser.createSequence()
        seqs_total_time = 0
        for tau in params:
            seqs += SingleOptical_T1(tau, tau_balance, seq_gap, forNV)
            seqs_total_time += 1*self.total_time

        print('Optical T1 sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)

        return seqs

    def Diff_T1(self, params, tau_balance, pi_xy, pi_time, init_time, read_time, seq_gap):#the wait time here is used to replace the self.singlet_decay
        '''
        MW (differential) T1 sequence with integrator
        '''
        ## Run a pi pulse, then measure the signal
        ## and reference counts from NV.
        self.laser_time = init_time
        self.readout_time = read_time
        longest_time = self.convert_type(round(max(params)), float)
        pi_time = self.convert_type(round(pi_time), float)

        ## we can measure the pi time on x and on y.
        ## they should be the same, but they technically
        ## have different offsets on our pulse streamer.

        def SingleDiff_T1(tau_time, tau_balance):
            '''
            CREATE SINGLE T1 SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            tau_time = self.convert_type(round(tau_time), float) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run
            pad_time = longest_time - tau_time 

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            init_laser_time = self.laser_time
            laser_off1 = self.singlet_decay + pi_time + tau_time
            #laser_off1 = wait_time + pi_time + tau_time
            if tau_balance:
                laser_off2 = 200 + seq_gap
            else:
                laser_off2 = 200 + pad_time + seq_gap
            self.total_time = init_laser_time + laser_off1 + self.readout_time + laser_off2


            # DAQ trigger windows
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows
            iq_off1 = init_laser_time + self.singlet_decay + self.laser_lag
            #iq_off1 = init_laser_time + wait_time + self.laser_lag
            iq_off2 = tau_time + self.readout_time + laser_off2 - self.laser_lag

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq_on = self.Pulser.createSequence()
            seq_off = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]

            # define sequence structure for DAQ trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout,0), (self.clock_time, 1), (clock_off2, 0)]

            # define sequence structure for MW I and Q when MW = ON
            mw_I_on_seq = [(iq_off1, self.IQ0[0]), self.Pi(pi_xy, pi_time)[0], (iq_off2, self.IQ0[0])]
            mw_Q_on_seq = [(iq_off1, self.IQ0[1]), self.Pi(pi_xy, pi_time)[1], (iq_off2, self.IQ0[1])]
            # when MW = OFF
            mw_I_off_seq = [(iq_off1, self.IQ0[0]), (pi_time, self.IQ0[0]), (iq_off2, self.IQ0[0])]
            mw_Q_off_seq = [(iq_off1, self.IQ0[1]), (pi_time, self.IQ0[1]), (iq_off2, self.IQ0[1])]

            # assign sequences to respective channels for seq_on
            seq_on.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_on.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq_on.setAnalog(0, mw_I_on_seq) # mw_I
            seq_on.setAnalog(1, mw_Q_on_seq) # mw_Q

            # assign sequences to respective channels for seq_off
            seq_off.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_off.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq_off.setAnalog(0, mw_I_off_seq) # mw_I
            seq_off.setAnalog(1, mw_Q_off_seq) # mw_Q

            return seq_on + seq_off

        seqs = self.Pulser.createSequence()
        
        seqs_total_time = 0
        for tau in params:
            seqs += SingleDiff_T1(tau, tau_balance)
            seqs_total_time += 2*self.total_time
        print('Diff T1 sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)

        return seqs

    def Diff_T1rho(self, params, tau_balance, pihalf_y, init_time, read_time, seq_gap):
        '''
        Developed by Tian-Xing Zheng, Aug.2024
        MW (differential) T1_rho sequence 
        pi/2(y)- MW(x-axis for tau) - pi/2(y, -y)
        '''
        ## Run a pi pulse, then measure the signal
        ## and reference counts from NV.
        self.laser_time = init_time
        self.readout_time = read_time
        longest_time = self.convert_type(round(max(params)), float)
        #pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        #pi_x = self.convert_type(round(pi_x), float)
        #pi_y = self.convert_type(round(pi_y), float)

        ## we can measure the pi time on x and on y.
        ## they should be the same, but they technically
        ## have different offsets on our pulse streamer.

        def SingleDiff_T1rho(tau_time, tau_balance):
            '''
            CREATE SINGLE T1 SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            tau_time = self.convert_type(round(tau_time), float) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run
            pad_time = longest_time - tau_time 

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            init_laser_time = self.laser_time
            laser_off1 = self.singlet_decay + pihalf_y + tau_time + pihalf_y + self.MW_buffer_time
            if tau_balance:
                laser_off2 = 200 + seq_gap
            else:
                laser_off2 = 200 + pad_time + seq_gap
            self.total_time = init_laser_time + laser_off1 + self.readout_time + laser_off2


            # DAQ trigger windows
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows
            iq_off1 = self.laser_lag + init_laser_time + self.singlet_decay
            iq_off2 = self.MW_buffer_time + self.readout_time + laser_off2 - self.singlet_decay

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]

            # define sequence structure for DAQ trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout,0), (self.clock_time, 1), (clock_off2, 0)]

            # define sequence structure for MW I and Q 
            mw_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('y', pihalf_y)[0], self.PiHalf('x', tau_time)[0], self.PiHalf('y', pihalf_y)[0], (iq_off2, self.IQ0[0])]
            mw_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('y', pihalf_y)[1], self.PiHalf('x', tau_time)[1], self.PiHalf('y', pihalf_y)[1], (iq_off2, self.IQ0[1])]
            
            mw_I_seq_ref = [(iq_off1, self.IQ0[0]), self.PiHalf('y', pihalf_y)[0], self.PiHalf('x', tau_time)[0], self.PiHalf('-y', pihalf_y)[0], (iq_off2, self.IQ0[0])]
            mw_Q_seq_ref = [(iq_off1, self.IQ0[1]), self.PiHalf('y', pihalf_y)[1], self.PiHalf('x', tau_time)[1], self.PiHalf('-y', pihalf_y)[1], (iq_off2, self.IQ0[1])]

            # assign sequences to respective channels for seq_on
            seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q

            # assign sequences to respective channels for seq_off
            seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq_ref.setAnalog(0, mw_I_seq_ref) # mw_I
            seq_ref.setAnalog(1, mw_Q_seq_ref) # mw_Q

            return seq + seq_ref

        seqs = self.Pulser.createSequence()
        
        seqs_total_time = 0
        for tau in params:
            seqs += SingleDiff_T1rho(tau, tau_balance)
            seqs_total_time += 2*self.total_time
        print('Diff T1_rho sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)

        return seqs

    def Diff_T1_Switch(self, params, tau_balance, pi_xy, pi_time, init_time, read_time, seq_gap):
        '''
        MW (differential) T1 sequence with WindFreak SG and MW Switch
        '''
        ## Run a pi pulse, then measure the signal
        ## and reference counts from NV.
        self.laser_time = init_time
        self.readout_time = read_time
        longest_time = self.convert_type(round(max(params)), float)
        pi_time = self.convert_type(round(pi_time), float)

        ## we can measure the pi time on x and on y.
        ## they should be the same, but they technically
        ## have different offsets on our pulse streamer.

        def SingleDiff_T1_Switch(tau_time, tau_balance):
            '''
            CREATE SINGLE T1 SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            tau_time = self.convert_type(round(tau_time), float) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run
            pad_time = longest_time - tau_time 

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            init_laser_time = self.laser_time
            laser_off1 = self.singlet_decay + pi_time + tau_time
            if tau_balance:
                laser_off2 = 200 + seq_gap
            else:
                laser_off2 = 200 + pad_time + seq_gap
            self.total_time = init_laser_time + laser_off1 + self.readout_time + laser_off2


            # DAQ trigger windows
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows
            iq_off1 = init_laser_time + self.singlet_decay
            iq_off2 = tau_time + self.readout_time + laser_off2

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq_on = self.Pulser.createSequence()
            seq_off = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]

            # define sequence structure for DAQ trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout,0), (self.clock_time, 1), (clock_off2, 0)]

            # define the control of the MW switch
            # switch_delay = 5
            switch_on_seq = [(iq_off1 - self.switch_delay, 0), (pi_time + self.switch_delay, 1), (iq_off2 , 0)]
            switch_off_seq = [(iq_off1 - self.switch_delay, 0), (pi_time + self.switch_delay, 0), (iq_off2, 0)]
            
            # define sequence structure for MW I and Q when MW = ON
            # mw_I_on_seq = [(iq_off1, self.IQ0[0]), self.Pi(pi_xy, pi_time)[0], (iq_off2, self.IQ0[0])]
            # mw_Q_on_seq = [(iq_off1, self.IQ0[1]), self.Pi(pi_xy, pi_time)[1], (iq_off2, self.IQ0[1])]
            # when MW = OFF
            # mw_I_off_seq = [(iq_off1, self.IQ0[0]), (pi_time, self.IQ0[0]), (iq_off2, self.IQ0[0])]
            # mw_Q_off_seq = [(iq_off1, self.IQ0[1]), (pi_time, self.IQ0[1]), (iq_off2, self.IQ0[1])]

            # assign sequences to respective channels for seq_on
            seq_on.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_on.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq_on.setDigital(self.channel_dict["switch"], switch_on_seq) # RF control switch
            # seq_on.setAnalog(0, mw_I_on_seq) # mw_I
            # seq_on.setAnalog(1, mw_Q_on_seq) # mw_Q

            # assign sequences to respective channels for seq_off
            seq_off.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_off.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq_off.setDigital(self.channel_dict["switch"], switch_off_seq) # RF control switch
            # seq_off.setAnalog(0, mw_I_off_seq) # mw_I
            # seq_off.setAnalog(1, mw_Q_off_seq) # mw_Q

            return seq_on + seq_off

        seqs = self.Pulser.createSequence()
        
        seqs_total_time = 0
        for tau in params:
            seqs += SingleDiff_T1_Switch(tau, tau_balance)
            seqs_total_time += 2*self.total_time
        print('Diff T1 with Switch sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)

        return seqs
    
    def Ramsey(self, params, tau_balance, pihalf_x, pihalf_y, init_time, read_time, wait_time, read_wait):
        
        '''
        init_time: for laser initialization
        read_time: for laser read out
        wait_time: the time after laser initialization (singlet decay)
        read_wait: the time before read out laser

        Ramsey pulse sequence.
        MW sequence: pi/2(x) - tau - pi/2(x)

        '''
        longest_time = self.convert_type(round(max(params)), float)
        #longest_time = self.convert_type(round(params[-1]), int)
        pihalf_x = self.convert_type(round(pihalf_x), int)
        pihalf_y = self.convert_type(round(pihalf_y), int)

        def SingleRamsey(tau_time, tau_balance):
            '''
            CREATE SINGLE RAMSEY SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            tau_time = self.convert_type(round(tau_time), int) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run (for different tau durations)
            pad_time = longest_time - tau_time 

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''

            init_laser_time = init_time
            readout_laser_time = read_time
            #laser_off1 = self.singlet_decay + pihalf_x + tau_time + pihalf_x + self.MW_buffer_time
            laser_off1 = wait_time + pihalf_x + tau_time + pihalf_x + self.MW_buffer_time + read_wait
            if tau_balance:
                laser_off2 = 200
            else:
                laser_off2 = 200 + pad_time
            #self.total_time = init_laser_time + laser_off1 + self.readout_time + laser_off2
            self.total_time = init_laser_time + laser_off1 + readout_laser_time + laser_off2

            # DAQ trigger windows
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            #clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off_readout = readout_laser_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag      

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            #iq_off1 = self.laser_lag + init_laser_time + self.singlet_decay
            iq_off1 = self.laser_lag + init_laser_time + wait_time
            iq_off2 = tau_time
            #iq_off3 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag
            iq_off3 = self.MW_buffer_time + read_wait + readout_laser_time + laser_off2 - self.laser_lag
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()

            # define sequence structure for laser
            #laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (readout_laser_time, 1), (laser_off2, 0)]
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels 
            mw_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off3, self.IQ0[0])]
            mw_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off3, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            mw_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off3, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off3, self.IQ0[1])]

            # assign sequences to respective channels for seq_on
            seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q

            # assign sequences to respective channels for seq_off
            seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # DAQ trigger
            seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q

            return seq + seq_ref

        # concatenate single ODMR sequence "runs" number of times
        seqs = self.Pulser.createSequence()
        
        for tau in params:
            seqs += SingleRamsey(tau, tau_balance)
        
        return seqs

    def Echo(self, params, tau_balance, pihalf_x, pihalf_y, pi_x, pi_y, init_time, read_time, wait_time, read_wait, seq_gap):
        '''
        Spin Echo pulse sequence.
        MW sequence: pi/2(x) - tau - pi(y) - tau - pi/2(x)
        init_time: laser duration for initialize the qubit
        read_time: laser duration for readout the qubit
        wait_time: waiting duration after the initialization laser
        read_wait: waiting duration before the readout laser
        seq_gap: waiting between each sequence for spins to relax. Not needed for NV but for other fluorescent spin qubits (pentacene)
        '''
        print("Generating Spin Echo Seq")
        #self.laser_time = init_time
        #self.readout_time = read_time
        longest_time = self.convert_type(round(max(params)), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)

        def SingleEcho(tau_time, tau_balance):
            '''
            CREATE SINGLE HAHN-ECHO SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            tau_time = self.convert_type(round(tau_time), float) # convert to proper data type to avoid undesired rpyc netref data type
            
            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run (for different tau durations)
            pad_time = longest_time - tau_time

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''            
            init_laser_time = init_time
            #laser_off1 = self.singlet_decay + pihalf_x + tau_time + pi_y + tau_time + pihalf_x + self.MW_buffer_time
            #laser_off1 = wait_time + pihalf_x + tau_time + pi_y + tau_time + pihalf_x + self.MW_buffer_time
            laser_off1 = wait_time + pihalf_x + tau_time + pi_y + tau_time + pihalf_x + self.MW_buffer_time + read_wait
            if tau_balance:
                laser_off2 = 200 + seq_gap
            else:
                laser_off2 = 200 + pad_time + seq_gap
            self.total_time = init_laser_time + laser_off1 + read_time + laser_off2

            # DAQ trigger windows
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            clock_off_readout = read_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            #iq_off1 = self.laser_lag + init_laser_time + self.singlet_decay
            iq_off1 = self.laser_lag + init_laser_time + wait_time
            iq_off2 = tau_time # /2
            iq_off3 = tau_time # /2
            #iq_off4 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag
            iq_off4 = self.MW_buffer_time + read_wait + read_time + laser_off2 - self.laser_lag
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (read_time, 1), (laser_off2, 0)]
            
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout,0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels 
            mw_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            mw_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            mw_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # for testing switch, keep MW I and Q constantly on
            # mw_I_TEST_seq = [(iq_off1, self.IQpx[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQpx[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQpx[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQpx[0])]
            # mw_Q_TEST_seq = [(iq_off1, self.IQpx[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQpx[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQpx[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQpx[1])]

            # switch_on_seq = [(iq_off1, 0), (pihalf_x, 1), (iq_off2, 0), (pi_y, 1), (iq_off3, 0), (pihalf_x, 1), (iq_off4, 0)]
            # switch_off_seq = [(iq_off1, 0), (pihalf_x, 0), (iq_off2, 0), (pi_y, 0), (iq_off3, 0), (pihalf_x, 0), (iq_off4, 0)]

            # switch_on_seq = [(iq_off1 - 20, 0), (pihalf_x + 40, 1), (iq_off2 - 40, 0), (pi_y + 40, 1), (iq_off3 - 40, 0), (pihalf_x + 40, 1), (iq_off4 - 20, 0)]
            # switch_off_seq = [(iq_off1 - 20, 0), (pihalf_x + 40, 0), (iq_off2 - 40, 0), (pi_y + 40, 0), (iq_off3 - 40, 0), (pihalf_x + 40, 0), (iq_off4 - 20, 0)]

            # assign sequences to respective channels for seq_on
            seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q

            # assign sequences to respective channels for seq_off
            seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # DAQ trigger
            seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q
            

            return seq + seq_ref 
        
        # concatenate single ODMR sequence "runs" number of times
        seqs = self.Pulser.createSequence()
        
        seqs_total_time = 0
        for tau in params:
            seqs += SingleEcho(tau, tau_balance)
            seqs_total_time += 2*self.total_time
        print('Spin Echo sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)
        return seqs

    def WAHUHA(self, params, pihalf_x, pihalf_y, pi_x, pi_y):
        '''
        WAHUHA pulse sequence applied to NV centers.
        MW sequence: pi/2(x) - tau/2 - (pi/2(x) - tau - pi/2(-y) - tau - pi/2(y) - tau - pi/2(-x))^N - tau/2 - pi/2(x)

        '''
        longest_time = self.convert_type(round(params[-1]), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        
        def PiPulsesN(axes, tau, N):  
            wahuha_I_seq = [self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.PiHalf('-y', pihalf_y)[0], (iq_off3, self.IQ0[0]), 
                        self.PiHalf('y', pihalf_y)[0], (iq_off4, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0]]
            wahuha_Q_seq = [self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.PiHalf('-y', pihalf_y)[1], (iq_off3, self.IQ0[1]), 
                        self.PiHalf('y', pihalf_y)[1], (iq_off4, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1]]
            
            tau_half_I_seq = [((tau/2), self.IQ0[0])]
            tau_half_Q_seq = [((tau/2), self.IQ0[1])]
            tau_I_seq = [(tau, self.IQ0[0])]
            tau_Q_seq = [(tau, self.IQ0[1])]

            xy4_I_seq = [self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0]]
            xy4_Q_seq = [self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1]]
            mw_I = (tau_half_I_seq + xy4_I_seq + tau_I_seq + list(reversed(xy4_I_seq)) + tau_half_I_seq)*N
            mw_Q = (tau_half_Q_seq + xy4_Q_seq + tau_Q_seq + list(reversed(xy4_Q_seq)) + tau_half_Q_seq)*N

            return mw_I, mw_Q
        
        def SingleWAHUHA(tau_time):
            '''
            CREATE SINGLE WAHUHA SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            tau_time = self.convert_type(round(tau_time), float) # convert to proper data type to avoid undesired rpyc netref data type
            
            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run (for different tau durations)
            pad_time = longest_time - tau_time

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''            
            laser_off1 = self.laser_lag
            # laser_off2 = self.singlet_decay + pihalf_x + tau_time/2 + pi_y + tau_time/2 + pihalf_x + self.MW_buffer_time
            laser_off2 = self.singlet_decay + pihalf_x + tau_time + pihalf_y + tau_time + pihalf_y + tau_time + pihalf_x + self.MW_buffer_time
            laser_off3 = 100 + pad_time
            
            # DAQ trigger windows
            clock_off1 = laser_off1 + self.laser_time + laser_off2 + self.readout_time - self.trig_spot - self.clock_time
            clock_off2 = self.trig_spot + laser_off3

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off1 = laser_off1 + self.laser_time + self.singlet_decay
            iq_off2 = tau_time # /2
            iq_off3 = 2*tau_time # /2
            iq_off4 = tau_time # /2
            iq_off5 = self.MW_buffer_time + self.readout_time + laser_off3

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(laser_off1, 0), (self.laser_time, 1), (laser_off2, 0), (self.readout_time, 1), (laser_off3, 0)]
            
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels 
            mw_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], self.PiHalf('x', pihalf_x)[0], (iq_off5, self.IQ0[0])]
            mw_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.PiHalf('-y', pihalf_y)[1], (iq_off3, self.IQ0[1]), 
                        self.PiHalf('y', pihalf_y)[1], (iq_off4, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off5, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            mw_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # switch_on_seq = [(iq_off1, 0), (pihalf_x, 1), (iq_off2, 0), (pi_y, 1), (iq_off3, 0), (pihalf_x, 1), (iq_off4, 0)]
            # switch_off_seq = [(iq_off1, 0), (pihalf_x, 0), (iq_off2, 0), (pi_y, 0), (iq_off3, 0), (pihalf_x, 0), (iq_off4, 0)]

            # switch_on_seq = [(iq_off1 - 20, 0), (pihalf_x + 40, 1), (iq_off2 - 40, 0), (pi_y + 40, 1), (iq_off3 - 40, 0), (pihalf_x + 40, 1), (iq_off4 - 20, 0)]
            # switch_off_seq = [(iq_off1 - 20, 0), (pihalf_x + 40, 0), (iq_off2 - 40, 0), (pi_y + 40, 0), (iq_off3 - 40, 0), (pihalf_x + 40, 0), (iq_off4 - 20, 0)]

            # assign sequences to respective channels for seq_on
            seq.setDigital(3, laser_seq) # laser
            seq.setDigital(0, daq_clock_seq) # integrator trigger
            # seq1.setDigital(1, switch_on_seq) # RF switch 
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            seq_ref.setDigital(3, laser_seq) # laser
            seq_ref.setDigital(0, daq_clock_seq) # integrator trigger
            # seq2.setDigital(1, switch_off_seq) # RF switch 
            seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q

            return seq + seq_ref

        # concatenate single ODMR sequence "runs" number of times
        seqs = self.Pulser.createSequence()
        
        for tau in params:
            seqs += SingleWAHUHA(tau)

        return seqs 
        
    def Echo_WAHUHA():
        pass

    def XY4_N(self, params, pulse_axes, pihalf_x, pihalf_y, pi_x, pi_y, n):
        '''
        XY4-N pulse sequence.
        MW sequence: pi/2(x) - tau/2 - (pi(x) - tau - pi(y) - tau - pi(x) - tau - pi(y))^N - tau/2 - pi/2(x, -x)
        '''
        longest_time = self.convert_type(round(max(params)), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        n = self.convert_type(round(n), int)

        def PiPulsesN(axes, tau, N):            
            if axes == 'xy':
                xy4_I_seq = [((tau), self.IQ0[0]), self.Pi('x', pi_x)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], ((tau), self.IQ0[0])]
                xy4_Q_seq = [((tau), self.IQ0[1]), self.Pi('x', pi_x)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], ((tau), self.IQ0[1])]
                mw_I = (xy4_I_seq)*N
                mw_Q = (xy4_Q_seq)*N
                
            elif axes == 'yy':
                yy4_I_seq = [((tau), self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], ((tau), self.IQ0[0])]
                yy4_Q_seq = [((tau), self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], ((tau), self.IQ0[1])]
                mw_I = (yy4_I_seq)*N
                mw_Q = (yy4_Q_seq)*N

            return mw_I, mw_Q

        def SingleXY4(tau):
            '''
            CREATE SINGLE HAHN-ECHO SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            tau = self.convert_type(round(tau), float) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT

            pad_time = padding time to equalize duration of every run (for different tau durations)
            '''
            pad_time = longest_time - tau 
            # NOTICE: change if using PiHalf['y'] to pihalf_y
            # xy4_time = 2*pihalf_x + (2*(tau/2)/(4*n) + 2*pi_x + 2*pi_y + 3*tau/(4*n))*n
            xy4_time = 2*pihalf_x + (2*tau + 2*pi_x + 2*pi_y + 3*(2*tau))*n
            yy4_time = 2*pihalf_x + (2*tau + 4*pi_y + 3*(2*tau))*n

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''            
            laser_off1 = self.laser_lag

            if pulse_axes == 'xy':
                laser_off2 = self.singlet_decay + xy4_time + self.MW_buffer_time
            else:
                laser_off2 = self.singlet_decay + yy4_time + self.MW_buffer_time

            laser_off3 = 100 + pad_time 
            
            # DAQ trigger windows
            clock_off1 = laser_off1 + self.laser_time + laser_off2 + self.readout_time - self.trig_spot - self.clock_time
            clock_off2 = self.trig_spot + laser_off3          

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off_start = laser_off1 + self.laser_time + self.singlet_decay
            iq_off_end = self.MW_buffer_time + self.readout_time + laser_off3
            
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(laser_off1, 0), (self.laser_time, 1), (laser_off2, 0), (self.readout_time, 1), (laser_off3, 0)]
            
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels 
            mw_I_seq = [(iq_off_start, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0]] + PiPulsesN(pulse_axes, tau, n)[0] + [self.PiHalf('x', pihalf_x)[0], (iq_off_end, self.IQ0[0])]
            mw_Q_seq = [(iq_off_start, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1]] + PiPulsesN(pulse_axes, tau, n)[1] + [self.PiHalf('x', pihalf_x)[1], (iq_off_end, self.IQ0[1])]
            
            # sequence structure for I & Q MW channels (MW off)
            mw_I_ref_seq = [(iq_off_start, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0]] + PiPulsesN(pulse_axes, tau, n)[0] + [self.PiHalf('-x', pihalf_x)[0], (iq_off_end, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off_start, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1]] + PiPulsesN(pulse_axes, tau, n)[1] + [self.PiHalf('-x', pihalf_x)[1], (iq_off_end, self.IQ0[1])]

            # assign sequences to respective channels for seq_on
            seq.setDigital(3, laser_seq) # laser
            seq.setDigital(0, daq_clock_seq) # integrator trigger
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            seq_ref.setDigital(3, laser_seq) # laser
            seq_ref.setDigital(0, daq_clock_seq) # integrator trigger
            seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q

            return seq + seq_ref

        # concatenate single ODMR sequence "runs" number of times
        seqs = self.Pulser.createSequence()
        
        for tau in params:
            seqs += SingleXY4(tau)
        
        return seqs

    def XY8_N(self, params, tau_balance, pulse_axes, pihalf_x, pihalf_y, pi_x, pi_y, n, init_time, read_time, wait_time, read_wait):
        '''
        XY8-N and YY8-N pulse sequence.

        init_time: the time for laser to initialize the system
        read_time: the time for laser to read out the system
        wait_time: the time that we wait after we initialize the system (in NV system is self.singlet_decay)
        read_wait: the time that we wait before we read out

        MW sequence: pi/2(y) - (tau - pi(x) - 2tau - pi(y) - 2tau - pi(x) - 2tau - pi(y) - 2tau - pi(y) - 2tau - pi(x) - 2tau - pi(y)- 2tau - pi(x) - tau/)^N - pi/2(y, -y)
        By Tian-Xing Zheng, Aug.2024
        '''
        longest_time = self.convert_type(round(max(params)), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        n = self.convert_type(round(n), int)
        
        def PiPulsesN(axes, tau, N):
            tau_half_I_seq = [(tau, self.IQ0[0])]
            tau_half_Q_seq = [(tau, self.IQ0[1])]
            tau_I_seq = [(2*tau, self.IQ0[0])]
            tau_Q_seq = [(2*tau, self.IQ0[1])]

            if axes == 'xy':
                xy4_I_seq = [self.Pi('x', pi_x)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0]]
                xy4_Q_seq = [self.Pi('x', pi_x)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1]]
                mw_I = (tau_half_I_seq + xy4_I_seq + tau_I_seq + list(reversed(xy4_I_seq)) + tau_half_I_seq)*N
                mw_Q = (tau_half_Q_seq + xy4_Q_seq + tau_Q_seq + list(reversed(xy4_Q_seq)) + tau_half_Q_seq)*N
                
            elif axes == 'yy':
                yy4_I_seq_1 = [self.Pi('-y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('-y', pi_y)[0]]
                yy4_Q_seq_1 = [self.Pi('-y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('-y', pi_y)[1]]
                yy4_I_seq_2 = [self.Pi('-y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('-y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0]]
                yy4_Q_seq_2 = [self.Pi('-y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('-y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1]]
                mw_I = (tau_half_I_seq + yy4_I_seq_1 + tau_I_seq + yy4_I_seq_2 + tau_half_I_seq)*N
                mw_Q = (tau_half_Q_seq + yy4_Q_seq_1 + tau_Q_seq + yy4_Q_seq_2 + tau_half_Q_seq)*N
            
            return mw_I, mw_Q

        def SingleXY8(tau):
            '''
            CREATE SINGLE HAHN-ECHO SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            tau = self.convert_type(round(tau), float) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT

            pad_time = padding time to equalize duration of every run (for different tau durations)
            '''
            #pad_time = (longest_time - tau)*16*n
            pad_time = 0 #set pad_time to be 0 for speed up the measurement, we can add it back until we really see temperature/charge effect

            # NOTICE: change if using PiHalf['y'] to pihalf_y
            # xy8_time = 2*pihalf_x + ((tau/2)/(8*n) + 4*pi_x + 4*pi_y + 7*tau/(8*n) + (tau/2)/(8*n))*n
            # yy8_time = 2*pihalf_x + ((tau/2)/(8*n) + 8*pi_y + 7*tau/(8*n) + (tau/2)/(8*n))*n
            xy8_time = 2*pihalf_y + (tau + 4*pi_x + 4*pi_y + 7*(2*tau) + tau)*n
            yy8_time = 2*pihalf_y + (tau + 8*pi_y + 7*(2*tau) + tau)*n

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''            
            #laser_off1 = self.laser_lag

            #init_laser_time = self.laser_time
            init_laser_time = init_time         #the time for laser to initialize the system
            readout_laser_time = read_time      #the time for laser to read out the system

            if pulse_axes == 'xy':
                #laser_off1 = self.singlet_decay + xy8_time + self.MW_buffer_time
                laser_off1 = wait_time + xy8_time + self.MW_buffer_time + read_wait
            else:
                #laser_off1 = self.singlet_decay + yy8_time + self.MW_buffer_time
                laser_off1 = wait_time + yy8_time + self.MW_buffer_time + read_wait

            if tau_balance:
                laser_off2 = 200 
            else:
                laser_off2 = 200 + pad_time

            #self.total_time = init_laser_time + laser_off1 + self.readout_time + laser_off2
            self.total_time = init_laser_time + laser_off1 + readout_laser_time + laser_off2

            # DAQ trigger windows
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            #clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off_readout = readout_laser_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag          

            # mw I & Q off windows
            #iq_off1 = self.laser_lag + init_laser_time + self.singlet_decay
            #iq_off2 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag
            iq_off1 = self.laser_lag + init_laser_time + wait_time
            iq_off2 = self.MW_buffer_time + read_wait + readout_laser_time + laser_off2 - self.laser_lag
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()

            # define sequence structure for laser
            #laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (readout_laser_time, 1), (laser_off2, 0)]
            
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1),(clock_off2, 0)]
            
            # sequence structure for I & Q MW channels 
            mw_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('y', pihalf_y)[0]] + PiPulsesN(pulse_axes, tau, n)[0] + [self.PiHalf('y', pihalf_y)[0], (iq_off2, self.IQ0[0])]
            mw_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('y', pihalf_y)[1]] + PiPulsesN(pulse_axes, tau, n)[1] + [self.PiHalf('y', pihalf_y)[1], (iq_off2, self.IQ0[1])]
            
            # sequence structure for I & Q MW channels (MW off)
            mw_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('y', pihalf_y)[0]] + PiPulsesN(pulse_axes, tau, n)[0] + [self.PiHalf('-y', pihalf_y)[0], (iq_off2, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('y', pihalf_y)[1]] + PiPulsesN(pulse_axes, tau, n)[1] + [self.PiHalf('-y', pihalf_y)[1], (iq_off2, self.IQ0[1])]

            # assign sequences to respective channels for seq
            seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q

            # assign sequences to respective channels for seq_ref
            seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # DAQ trigger
            seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q

            return seq + seq_ref

        # concatenate single XY8 sequence "runs" number of times
        seqs = self.Pulser.createSequence()
        
        seqs_total_time = 0
        for tau in params:
            seqs += SingleXY8(tau)
            seqs_total_time += 2*self.total_time
        print('XY8 sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)

        return seqs

    def XY8_N_NQR(self, params, tau_balance, pulse_axes, pihalf_x, pihalf_y, pi_x, pi_y, n, init_time, read_time, wait_time, read_wait):
        '''
        Modified XY8 sequence for nuclear quadrupole resonance. 
        Reference: I.Lovechinsky,..., M.D.Lukin, Magnetic resonance spectroscopy of hBN by NV, Science 2017

        init_time: the time for laser to initialize the system
        read_time: the time for laser to read out the system
        wait_time: the time that we wait after we initialize the system (in NV system is self.singlet_decay)
        read_wait: the time that we wait before we read out

        MW sequence: pi/2(x) - (tau - pi(x) - tau - pi(y) - tau - pi(x) - tau - pi(y) - tau - pi(y) - tau - pi(x) - tau - pi(y)- tau - pi(x))^N - tau - pi(x) - tau - pi(y)- tau - pi(x) - tau - pi/2(x, -x)
        By Tian-Xing Zheng and Hanyan Cai, Feb.2025
        '''
        longest_time = self.convert_type(round(max(params)), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        n = self.convert_type(round(n), int)
        
        def PiPulsesN_NQR(axes, tau, N):
            tau_I_seq = [(tau, self.IQ0[0])]
            tau_Q_seq = [(tau, self.IQ0[1])]

            if axes == 'xy':
                xy4_I_seq = [self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0]]
                xy4_Q_seq = [self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1]]
                tail_I_seq = [(tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (tau, self.IQ0[0])]
                tail_Q_seq = [(tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (tau, self.IQ0[1])]
                
                mw_I = (tau_I_seq + xy4_I_seq + tau_I_seq + list(reversed(xy4_I_seq)))*N + tail_I_seq
                mw_Q = (tau_Q_seq + xy4_Q_seq + tau_Q_seq + list(reversed(xy4_Q_seq)))*N + tail_Q_seq
                
            # elif axes == 'yy':
            #     yy4_I_seq_1 = [self.Pi('-y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('-y', pi_y)[0]]
            #     yy4_Q_seq_1 = [self.Pi('-y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('-y', pi_y)[1]]
            #     yy4_I_seq_2 = [self.Pi('-y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('-y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0]]
            #     yy4_Q_seq_2 = [self.Pi('-y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('-y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1]]
            #     mw_I = (tau_half_I_seq + yy4_I_seq_1 + tau_I_seq + yy4_I_seq_2 + tau_half_I_seq)*N
            #     mw_Q = (tau_half_Q_seq + yy4_Q_seq_1 + tau_Q_seq + yy4_Q_seq_2 + tau_half_Q_seq)*N
            else:
                raise ValueError("XY8 NQR haven't implement for YY8")
            
            return mw_I, mw_Q

        def SingleXY8_NQR(tau):
            '''
            CREATE SINGLE HAHN-ECHO SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            tau = self.convert_type(round(tau), float) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT

            pad_time = padding time to equalize duration of every run (for different tau durations)
            '''
            #pad_time = (longest_time - tau)*16*n
            pad_time = 0 #set pad_time to be 0 for speed up the measurement, we can add it back until we really see temperature/charge effect

            # NOTICE: change if using PiHalf['y'] to pihalf_y
            # xy8_time = 2*pihalf_x + ((tau/2)/(8*n) + 4*pi_x + 4*pi_y + 7*tau/(8*n) + (tau/2)/(8*n))*n
            # yy8_time = 2*pihalf_x + ((tau/2)/(8*n) + 8*pi_y + 7*tau/(8*n) + (tau/2)/(8*n))*n
            #xy8_time = 2*pihalf_x + (tau + 4*pi_x + 4*pi_y + 7*(tau))*n + tau + 2*pi_x + pi_y Note: This time might be wrong
            xy8_time = pihalf_x + tau + (4*pi_x + 4*pi_y + 8*tau)*n + pi_x + tau + pi_y + tau + pi_x + tau + pihalf_x
            #yy8_time = 2*pihalf_y + (tau + 8*pi_y + 7*(2*tau) + tau)*n

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''            
            #laser_off1 = self.laser_lag

            #init_laser_time = self.laser_time
            init_laser_time = init_time         #the time for laser to initialize the system
            readout_laser_time = read_time      #the time for laser to read out the system

            if pulse_axes == 'xy':
                #laser_off1 = self.singlet_decay + xy8_time + self.MW_buffer_time
                laser_off1 = wait_time + xy8_time + self.MW_buffer_time + read_wait
            else:
                #laser_off1 = self.singlet_decay + yy8_time + self.MW_buffer_time
                #laser_off1 = wait_time + yy8_time + self.MW_buffer_time + read_wait
                raise ValueError("XY8 NQR haven't implement for YY8")

            if tau_balance:
                laser_off2 = 200 
            else:
                laser_off2 = 200 + pad_time

            #self.total_time = init_laser_time + laser_off1 + self.readout_time + laser_off2
            self.total_time = init_laser_time + laser_off1 + readout_laser_time + laser_off2

            # DAQ trigger windows
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            #clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off_readout = readout_laser_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag          

            # mw I & Q off windows
            #iq_off1 = self.laser_lag + init_laser_time + self.singlet_decay
            #iq_off2 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag
            iq_off1 = self.laser_lag + init_laser_time + wait_time
            iq_off2 = self.MW_buffer_time + read_wait + readout_laser_time + laser_off2 - self.laser_lag
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()

            # define sequence structure for laser
            #laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (readout_laser_time, 1), (laser_off2, 0)]
            
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1),(clock_off2, 0)]
            
            # sequence structure for I & Q MW channels 
            mw_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0]] + PiPulsesN_NQR(pulse_axes, tau, n)[0] + [self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0])]
            mw_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1]] + PiPulsesN_NQR(pulse_axes, tau, n)[1] + [self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1])]
            
            # sequence structure for I & Q MW channels (MW off)
            mw_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0]] + PiPulsesN_NQR(pulse_axes, tau, n)[0] + [self.PiHalf('-x', pihalf_x)[0], (iq_off2, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1]] + PiPulsesN_NQR(pulse_axes, tau, n)[1] + [self.PiHalf('-x', pihalf_x)[1], (iq_off2, self.IQ0[1])]

            # assign sequences to respective channels for seq
            seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q

            # assign sequences to respective channels for seq_ref
            seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # DAQ trigger
            seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q

            return seq + seq_ref

        # concatenate single XY8 sequence "runs" number of times
        seqs = self.Pulser.createSequence()
        
        seqs_total_time = 0
        for tau in params:
            seqs += SingleXY8_NQR(tau)
            seqs_total_time += 2*self.total_time
        print('Modified XY8 NQR sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)

        return seqs

    def CPMG_N(self, params, tau_balance, pulse_axis, pihalf_x, pihalf_y, pi_x, pi_y, n, init_time, read_time, wait_time, read_wait):
        '''
        CPMG-N pulse sequence.
        MW sequence: pi/2(x) - tau - (pi(y) - 2*tau - ...)^N - tau - pi/2(x, -x)

        '''
        print("Generating CPMG Seq")
        #self.laser_time = init_time
        #self.readout_time = read_time
        longest_time = self.convert_type(round(max(params)), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        n = self.convert_type(round(n), int)
        
        print("long time = ", longest_time)
        print("pi/2 x = ", pihalf_x)
        print("n = ", n)

        def PiPulsesN(axis, tau, N):
            if axis == 'X':
                CPMG_I_seq = [self.Pi('x', pi_x)[0], (2*tau, self.IQ0[0])]
                CPMG_Q_seq = [self.Pi('x', pi_x)[1], (2*tau, self.IQ0[1])]
                mw_I = CPMG_I_seq*(N-1) + [self.Pi('x', pi_x)[0]]
                mw_Q = CPMG_Q_seq*(N-1) + [self.Pi('x', pi_x)[1]]

            elif axis == 'Y':
                CPMG_I_seq = [self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0])]
                CPMG_Q_seq = [self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1])]
                mw_I = CPMG_I_seq*(N-1) + [self.Pi('y', pi_y)[0]]
                mw_Q = CPMG_Q_seq*(N-1) + [self.Pi('y', pi_y)[1]]
            else:
                raise ValueError("pulse_axis must be 'X' or 'Y'!")

            return mw_I, mw_Q

        def SingleCPMG(tau, tau_balance):
            '''
            CREATE SINGLE HAHN-ECHO SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''
            print("Orig Tau = ", tau)
            tau = self.convert_type(round(tau), float) # convert to proper data type to avoid undesired rpyc netref data type
            print("Converted Tau = ", tau)
            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT

            pad_time = padding time to equalize duration of every run (for different tau durations)
            '''
            #pad_time = (longest_time - tau)*2*n
            pad_time = 0 #set pad_time to be 0 for speed up the measurement, we can add it back until we really see temperature/charge effect
            
            if pulse_axis == 'X':
                cpmg_time = pihalf_x + (tau + pi_x + tau)*n + pihalf_x
                # cpmg_time = pihalf_x + tau + (pi_x + 2 * tau)*(n-1) + pi_x + tau + pihalf_x
            elif pulse_axis == 'Y':
                cpmg_time = pihalf_x + (tau + pi_y + tau)*n + pihalf_x
            else:
                raise ValueError("pulse_axis must be 'X' or 'Y'!")
            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            init_laser_time = init_time   #note that self.laser_time = init_time (line2056), so init_laser_time = init_time

            #laser_off1 = self.singlet_decay + cpmg_time + self.MW_buffer_time
            laser_off1 = wait_time + cpmg_time + self.MW_buffer_time+ read_wait
            if tau_balance:
                laser_off2 = 200
            else:
                laser_off2 = 200 + pad_time
            self.total_time = init_laser_time + laser_off1 + read_time + laser_off2
            
            # DAQ trigger windows
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            clock_off_readout = read_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows
            #iq_off1 = self.laser_lag + init_laser_time + self.singlet_decay
            #iq_off2 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag
            iq_off1 = self.laser_lag + init_laser_time + wait_time
            iq_off2 = self.MW_buffer_time + read_wait + read_time + laser_off2 - self.laser_lag
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()
            
            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (read_time, 1), (laser_off2, 0)]
            
            # define sequence structure for readout clock
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout,0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels
            mw_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (tau, self.IQ0[0])] + PiPulsesN(pulse_axis, tau, n)[0] + [(tau, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0])]
            mw_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (tau, self.IQ0[1])] + PiPulsesN(pulse_axis, tau, n)[1] + [(tau, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1])]
            
            # sequence structure for I & Q MW channels (last pi/2 pulse is along -x axis)
            mw_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (tau, self.IQ0[0])] + PiPulsesN(pulse_axis, tau, n)[0] + [(tau, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off2, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (tau, self.IQ0[1])] + PiPulsesN(pulse_axis, tau, n)[1] + [(tau, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off2, self.IQ0[1])]

            # assign sequences to respective channels for seq_on
            seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q

            # assign sequences to respective channels for seq_off
            seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # DAQ trigger
            seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q

            return seq + seq_ref

        # concatenate single ODMR sequence "runs" number of times
        seqs = self.Pulser.createSequence()
        
        seqs_total_time = 0
        for tau in params:
            seqs += SingleCPMG(tau, tau_balance)
            seqs_total_time += 2*self.total_time
        print('CPMG sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)
        return seqs

    def WAHUHA_N(self, params, tau_balance, pihalf_x, pihalf_y, pi_x, pi_y, n, init_time, read_time, wait_time, read_wait):
        '''
        Basic WAHUHA pulse sequence. Used CPMG_N Sequence code. The pulse_axis from CPMG is removed. 
        MW sequence: 
            Background: (tau - pi/2(x) - tau - pi/2(-y) - 2*tau - pi/2(y) - tau - pi/2(-x) - tau)*n
            Signal:     (tau - pi/2(x) - tau - pi/2(-y) - 2*tau - pi/2(y) - tau - pi/2(-x) - tau)*n - pi(x)
        '''
        print("Generating WAHUHA Seq")
        #self.laser_time = init_time
        #self.readout_time = read_time
        longest_time = self.convert_type(round(max(params)), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        n = self.convert_type(round(n), int)
        
        print("long time = ", longest_time)
        print("pi/2 x = ", pihalf_x)
        print("n = ", n)

        def WAHUHA(tau, N):
            WAHUHA_I_seq = [(tau, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (tau, self.IQ0[0]), self.PiHalf('-y', pihalf_y)[0], (2*tau, self.IQ0[0]), self.PiHalf('y', pihalf_y)[0], (tau, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (tau, self.IQ0[0])]
            WAHUHA_Q_seq = [(tau, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (tau, self.IQ0[1]), self.PiHalf('-y', pihalf_y)[1], (2*tau, self.IQ0[1]), self.PiHalf('y', pihalf_y)[1], (tau, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (tau, self.IQ0[1])]
            
            return WAHUHA_I_seq, WAHUHA_Q_seq

        def SingleWAHUHA(tau, tau_balance):
            '''
            CREATE SINGLE HAHN-ECHO SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''
            print("Orig Tau = ", tau)
            tau = self.convert_type(round(tau), float) # convert to proper data type to avoid undesired rpyc netref data type
            print("Converted Tau = ", tau)
            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT

            pad_time = padding time to equalize duration of every run (for different tau durations)
            '''
            #pad_time = (longest_time - tau)*2*n
            pad_time = 0 #set pad_time to be 0 for speed up the measurement, we can add it back until we really see temperature/charge effect
            
            # Calculate the time for one run. The time for the background and signal run are different because the signal has an added pi_x pulse at the end.
            WAHUHA_background_time = (tau + pihalf_x + tau + pihalf_y + 2*tau + pihalf_y + tau + pihalf_x + tau) * n
            WAHUHA_signal_time = (tau + pihalf_x + tau + pihalf_y + 2*tau + pihalf_y + tau + pihalf_x + tau) * n + pi_x
            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            init_laser_time = init_time   #note that self.laser_time = init_time (line2056), so init_laser_time = init_time

            #laser_off1 = self.singlet_decay + cpmg_time + self.MW_buffer_time
            background_laser_off1 = wait_time + WAHUHA_background_time + self.MW_buffer_time+ read_wait
            signal_laser_off1 = wait_time + WAHUHA_signal_time + self.MW_buffer_time+ read_wait

            if tau_balance:
                laser_off2 = 200
            else:
                laser_off2 = 200 + pad_time
            
            # Different from other sequences, we have two different sequence times. So for the total time, I will have to add the two sequence times together. 
            # So this total time is the sum of the background and signal sequence times.
            self.total_time = (init_laser_time + background_laser_off1 + read_time + laser_off2) + (init_laser_time + signal_laser_off1 + read_time + laser_off2)
            
            # DAQ trigger windows
            background_clock_off1 = init_laser_time + background_laser_off1 + self.laser_lag
            signal_clock_off1 = init_laser_time + signal_laser_off1 + self.laser_lag

            # These times are not dependent on laser_off1, so we can use them for both signal and background sequences
            clock_off_readout = read_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows
            #iq_off1 = self.laser_lag + init_laser_time + self.singlet_decay
            #iq_off2 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag
            # These times are not dependent on laser_off1, so we can use them for both signal and background sequences
            iq_off1 = self.laser_lag + init_laser_time + wait_time
            iq_off2 = self.MW_buffer_time + read_wait + read_time + laser_off2 - self.laser_lag
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()
            
            # define sequence structure for laser
            bg_laser_seq = [(init_laser_time, 1), (background_laser_off1, 0), (read_time, 1), (laser_off2, 0)]
            sig_laser_seq = [(init_laser_time, 1), (signal_laser_off1, 0), (read_time, 1), (laser_off2, 0)]

            # define sequence structure for readout clock
            bg_daq_clock_seq = [(background_clock_off1, 0), (self.clock_time, 1), (clock_off_readout,0), (self.clock_time, 1), (clock_off2, 0)]
            sig_daq_clock_seq = [(signal_clock_off1, 0), (self.clock_time, 1), (clock_off_readout,0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels
            # This is the signal sequence
            mw_I_seq = [(iq_off1, self.IQ0[0])] + WAHUHA(tau, n)[0] + [self.Pi('x', pi_x)[0], (iq_off2, self.IQ0[0])]
            mw_Q_seq = [(iq_off1, self.IQ0[1])] + WAHUHA(tau, n)[1] + [self.Pi('x', pi_x)[1], (iq_off2, self.IQ0[1])]
            
            # sequence structure for I & Q MW channels (last pi/2 pulse is along -x axis)
            # This is the background sequence
            mw_I_ref_seq = [(iq_off1, self.IQ0[0])] + WAHUHA(tau, n)[0] + [(iq_off2, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off1, self.IQ0[1])] + WAHUHA(tau, n)[1] + [(iq_off2, self.IQ0[1])]

            # assign sequences to respective channels for seq_on
            seq.setDigital(self.channel_dict["laser"], sig_laser_seq) # laser
            seq.setDigital(self.channel_dict["clock"], sig_daq_clock_seq) # integrator trigger
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q

            # assign sequences to respective channels for seq_off
            seq_ref.setDigital(self.channel_dict["laser"], bg_laser_seq) # laser
            seq_ref.setDigital(self.channel_dict["clock"], bg_daq_clock_seq) # DAQ trigger
            seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q

            return seq + seq_ref

        # concatenate single ODMR sequence "runs" number of times
        seqs = self.Pulser.createSequence()
        
        seqs_total_time = 0
        for tau in params:
            seqs += SingleWAHUHA(tau, tau_balance)
            # No need for the total time to be multiplied by 2, alread done in the singleWAHUHA function
            seqs_total_time += self.total_time
        print('WAHUHA sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)
        return seqs

    def DROID_N(self, params, tau_balance, pihalf_x, pihalf_y, pi_x, pi_y, n, init_time, read_time, wait_time, read_wait):
        '''
        Basic DROID pulse sequence from Choi paper. Taken from WAHUHA_N 
        MW sequence: 36 pi pulses, 24 pi/2 pulses, 46 tau
            Background: (tau - pi(x) - tau - pi/2(x) - pi/2(-y) - tau - pi(-x) - tau - pi(-x) - tau - pi(x) - tau - pi/2(x) - pi/2(-y) - tau - 
                        pi(-x) - tau - pi(-x) - tau - pi(x) - tau - pi/2(x) - pi/2(-y) - tau - pi(-x) - tau - pi(-x) - tau - pi(-y) - 
                        tau - pi/2(-y) - pi/2(x) - tau - pi(y) - tau - pi(y) - tau - pi(-y) - tau - pi/2(-y) - pi/2(x) - tau - pi(y) - 
                        tau - pi(y) - tau - pi(-y) - tau - pi/2(-y) - pi/2(x) - tau - pi(y) - tau - pi(y) - tau - pi(-y) - tau - pi/2(x) - 
                        pi/2(y) - tau - pi(y) - tau - pi(-y) - tau - pi(-y) - tau -  pi/2(x) - pi/2(y) - tau - pi(y) - tau - pi(-y) - tau - 
                        pi(-y) - tau - pi/2(x) - pi/2(y) - tau - pi(y) - tau - pi(-x) - tau - pi(-x) - pi/2(y) - pi/2(x) - tau - pi(x) - tau - 
                        pi(-x) - tau - pi(-x) - tau - pi/2(y) - pi/2(x) - tau - pi(x) - tau - pi(-x) - tau - pi(-x) - tau - pi/2(y) - pi/2(x) - 
                        tau - pi(x) - tau - pi(-y)) * N
            Signal:     (tau - pi(x) - tau - pi/2(x) - pi/2(-y) - tau - pi(-x) - tau - pi(-x) - tau - pi(x) - tau - pi/2(x) - pi/2(-y) - tau - 
                        pi(-x) - tau - pi(-x) - tau - pi(x) - tau - pi/2(x) - pi/2(-y) - tau - pi(-x) - tau - pi(-x) - tau - pi(-y) - 
                        tau - pi/2(-y) - pi/2(x) - tau - pi(y) - tau - pi(y) - tau - pi(-y) - tau - pi/2(-y) - pi/2(x) - tau - pi(y) - 
                        tau - pi(y) - tau - pi(-y) - tau - pi/2(-y) - pi/2(x) - tau - pi(y) - tau - pi(y) - tau - pi(-y) - tau - pi/2(x) - 
                        pi/2(y) - tau - pi(y) - tau - pi(-y) - tau - pi(-y) - tau -  pi/2(x) - pi/2(y) - tau - pi(y) - tau - pi(-y) - tau - 
                        pi(-y) - tau - pi/2(x) - pi/2(y) - tau - pi(y) - tau - pi(-x) - tau - pi(-x) - pi/2(y) - pi/2(x) - tau - pi(x) - tau - 
                        pi(-x) - tau - pi(-x) - tau - pi/2(y) - pi/2(x) - tau - pi(x) - tau - pi(-x) - tau - pi(-x) - tau - pi/2(y) - pi/2(x) - 
                        tau - pi(x) - tau - pi(-y)) * N - pi(x)
        '''
        print("Generating DROID Seq")
        #self.laser_time = init_time
        #self.readout_time = read_time
        longest_time = self.convert_type(round(max(params)), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        n = self.convert_type(round(n), int)
        
        print("long time = ", longest_time)
        print("pi/2 x = ", pihalf_x)
        print("n = ", n)

        def DROID(tau, N):
            DROID_I_seq = [
                (tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], self.PiHalf('-y', pihalf_y)[0], self.Pi('x', pi_x)[0], self.Pi('-x', pi_x)[0], 
                (tau, self.IQ0[0]), self.Pi('-x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], 
                self.PiHalf('-y', pihalf_y)[0], (tau, self.IQ0[0]), self.Pi('-x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('-x', pi_x)[0], (tau, self.IQ0[0]),
                self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], self.PiHalf('-y', pihalf_y)[0], (tau, self.IQ0[0]), self.Pi('-x', pi_x)[0],
                (tau, self.IQ0[0]), self.Pi('-x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('-y', pi_y)[0], (tau, self.IQ0[0]), self.PiHalf('-y', pihalf_y)[0], 
                self.PiHalf('x', pihalf_x)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), 
                self.Pi('-y', pi_y)[0], (tau, self.IQ0[0]), self.PiHalf('-y', pihalf_y)[0], self.PiHalf('x', pihalf_x)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0],
                (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('-y', pi_y)[0], (tau, self.IQ0[0]), self.PiHalf('-y', pihalf_y)[0],
                self.PiHalf('x', pihalf_x)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), 
                self.Pi('-y', pi_y)[0], (tau, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], self.PiHalf('y', pihalf_y)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0],
                (tau, self.IQ0[0]), self.Pi('-y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('-y', pi_y)[0], (tau, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0],
                self.PiHalf('y', pihalf_y)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('-y', pi_y)[0], (tau, self.IQ0[0]), 
                self.Pi('-y', pi_y)[0], (tau, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], self.PiHalf('y', pihalf_y)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], 
                (tau, self.IQ0[0]), self.Pi('-x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('-x', pi_x)[0], self.PiHalf('y', pihalf_y)[0], self.PiHalf('x', pihalf_x)[0], 
                (tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('-x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('-x', pi_x)[0], (tau, self.IQ0[0]), 
                self.PiHalf('y', pihalf_y)[0], self.PiHalf('x', pihalf_x)[0], (tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('-x', pi_x)[0], 
                (tau, self.IQ0[0]), self.Pi('-x', pi_x)[0], (tau, self.IQ0[0]), self.PiHalf('y', pihalf_y)[0], self.PiHalf('x', pihalf_x)[0], (tau, self.IQ0[0]), 
                self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('-y', pi_y)[0]
                ]
            DROID_Q_seq = [
                (tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], self.PiHalf('-y', pihalf_y)[1], self.Pi('x', pi_x)[1], self.Pi('-x', pi_x)[1], 
                (tau, self.IQ0[1]), self.Pi('-x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], 
                self.PiHalf('-y', pihalf_y)[1], (tau, self.IQ0[1]), self.Pi('-x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('-x', pi_x)[1], (tau, self.IQ0[1]), 
                self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], self.PiHalf('-y', pihalf_y)[1], (tau, self.IQ0[1]), self.Pi('-x', pi_x)[1],
                (tau, self.IQ0[1]), self.Pi('-x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('-y', pi_y)[1], (tau, self.IQ0[1]), self.PiHalf('-y', pihalf_y)[1], 
                self.PiHalf('x', pihalf_x)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), 
                self.Pi('-y', pi_y)[1], (tau, self.IQ0[1]), self.PiHalf('-y', pihalf_y)[1], self.PiHalf('x', pihalf_x)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1],
                (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('-y', pi_y)[1], (tau, self.IQ0[1]), self.PiHalf('-y', pihalf_y)[1],
                self.PiHalf('x', pihalf_x)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), 
                self.Pi('-y', pi_y)[1], (tau, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], self.PiHalf('y', pihalf_y)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1],
                (tau, self.IQ0[1]), self.Pi('-y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('-y', pi_y)[1], (tau, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1],
                self.PiHalf('y', pihalf_y)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('-y', pi_y)[1], (tau, self.IQ0[1]), 
                self.Pi('-y', pi_y)[1], (tau, self.IQ0[0]), self.PiHalf('x', pihalf_x)[1], self.PiHalf('y', pihalf_y)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], 
                (tau, self.IQ0[1]), self.Pi('-x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('-x', pi_x)[1], self.PiHalf('y', pihalf_y)[1], self.PiHalf('x', pihalf_x)[1],
                (tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('-x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('-x', pi_x)[1], (tau, self.IQ0[1]), 
                self.PiHalf('y', pihalf_y)[1], self.PiHalf('x', pihalf_x)[1], (tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('-x', pi_x)[1],
                (tau, self.IQ0[1]), self.Pi('-x', pi_x)[1], (tau, self.IQ0[1]), self.PiHalf('y', pihalf_y)[1], self.PiHalf('x', pihalf_x)[1], (tau, self.IQ0[1]), 
                self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('-y', pi_y)[1]
                ]
            
            return DROID_I_seq, DROID_Q_seq

        def SingleDROID(tau, tau_balance):
            '''
            CREATE SINGLE HAHN-ECHO SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''
            print("Orig Tau = ", tau)
            tau = self.convert_type(round(tau), float) # convert to proper data type to avoid undesired rpyc netref data type
            print("Converted Tau = ", tau)
            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT

            pad_time = padding time to equalize duration of every run (for different tau durations)
            '''
            #pad_time = (longest_time - tau)*2*n
            pad_time = 0 #set pad_time to be 0 for speed up the measurement, we can add it back until we really see temperature/charge effect
            
            # Calculate the time for one run. The time for the background and signal run are different because the signal has an added pi_x pulse at the end.
            DROID_background_time = (47 * tau + 18 * pi_x + 18 * pi_y + 12 * pihalf_x + 12 * pihalf_y) * n + pi_x
            DROID_signal_time = (47 * tau + 18 * pi_x + 18 * pi_y + 12 * pihalf_x + 12 * pihalf_y) * n 
            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            init_laser_time = init_time   #note that self.laser_time = init_time (line2056), so init_laser_time = init_time

            #laser_off1 = self.singlet_decay + cpmg_time + self.MW_buffer_time
            background_laser_off1 = wait_time + DROID_background_time + self.MW_buffer_time+ read_wait
            signal_laser_off1 = wait_time + DROID_signal_time + self.MW_buffer_time+ read_wait

            if tau_balance:
                laser_off2 = 200
            else:
                laser_off2 = 200 + pad_time
            
            # Different from other sequences, we have two different sequence times. So for the total time, I will have to add the two sequence times together. 
            # So this total time is the sum of the background and signal sequence times.
            self.total_time = (init_laser_time + background_laser_off1 + read_time + laser_off2) + (init_laser_time + signal_laser_off1 + read_time + laser_off2)
            
            # DAQ trigger windows
            background_clock_off1 = init_laser_time + background_laser_off1 + self.laser_lag
            signal_clock_off1 = init_laser_time + signal_laser_off1 + self.laser_lag

            # These times are not dependent on laser_off1, so we can use them for both signal and background sequences
            clock_off_readout = read_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows
            #iq_off1 = self.laser_lag + init_laser_time + self.singlet_decay
            #iq_off2 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag
            # These times are not dependent on laser_off1, so we can use them for both signal and background sequences
            iq_off1 = self.laser_lag + init_laser_time + wait_time
            iq_off2 = self.MW_buffer_time + read_wait + read_time + laser_off2 - self.laser_lag
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()
            
            # define sequence structure for laser
            bg_laser_seq = [(init_laser_time, 1), (background_laser_off1, 0), (read_time, 1), (laser_off2, 0)]
            sig_laser_seq = [(init_laser_time, 1), (signal_laser_off1, 0), (read_time, 1), (laser_off2, 0)]

            # define sequence structure for readout clock
            bg_daq_clock_seq = [(background_clock_off1, 0), (self.clock_time, 1), (clock_off_readout,0), (self.clock_time, 1), (clock_off2, 0)]
            sig_daq_clock_seq = [(signal_clock_off1, 0), (self.clock_time, 1), (clock_off_readout,0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels
            # This is the signal sequence
            mw_I_seq = [(iq_off1, self.IQ0[0])] + DROID(tau, n)[0] + [(iq_off2, self.IQ0[0])]
            mw_Q_seq = [(iq_off1, self.IQ0[1])] + DROID(tau, n)[1] + [(iq_off2, self.IQ0[1])] 
            
            # sequence structure for I & Q MW channels (last pi/2 pulse is along -x axis)
            # This is the background sequence
            mw_I_ref_seq = [(iq_off1, self.IQ0[0])] + DROID(tau, n)[0] + [self.Pi('x', pi_x)[0], (iq_off2, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off1, self.IQ0[1])] + DROID(tau, n)[1] + [self.Pi('x', pi_x)[1], (iq_off2, self.IQ0[1])]

            # assign sequences to respective channels for seq_on
            seq.setDigital(self.channel_dict["laser"], sig_laser_seq) # laser
            seq.setDigital(self.channel_dict["clock"], sig_daq_clock_seq) # integrator trigger
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q

            # assign sequences to respective channels for seq_off
            seq_ref.setDigital(self.channel_dict["laser"], bg_laser_seq) # laser
            seq_ref.setDigital(self.channel_dict["clock"], bg_daq_clock_seq) # DAQ trigger
            seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q

            return seq + seq_ref

        # concatenate single ODMR sequence "runs" number of times
        seqs = self.Pulser.createSequence()
        
        seqs_total_time = 0
        for tau in params:
            seqs += SingleDROID(tau, tau_balance)
            # No need for the total time to be multiplied by 2, alread done in the singleDROID function
            seqs_total_time += self.total_time
        print('DROID sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)
        return seqs

    def DEER_debug(self, pihalf_x, pihalf_y, pi_x, pi_y, tau, num_freqs=0):
        '''
        DEER pulse sequence.
        MW sequence: pi/2(x) - tau - pi(y) - tau - pi/2(x)

        '''
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        tau = self.convert_type(round(tau), float)

        def SingleDEER():
            '''
            CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''            
            # laser_off = self.laser_lag + pihalf_x + tau + pi_y + tau + pihalf_x + self.MW_buffer_time
            # laser_on = self.laser_time
            laser_off1 = self.laser_lag
            laser_off2 = self.singlet_decay + pihalf_x + tau + pi_y + tau + pihalf_x + self.MW_buffer_time
            laser_off3 = self.laser_lag + 1000

            # DAQ trigger windows
            # clock_off1 = laser_off + self.readout_time - self.clock_time
            # clock_off2 = laser_on - self.readout_time
            clock_off1 = laser_off1 + self.laser_time + laser_off2 + self.readout_time - self.trig_spot - self.clock_time
            clock_off2 = self.trig_spot + laser_off3

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            # iq_off1 = self.laser_lag
            # iq_off2 = tau
            # iq_off3 = tau
            # iq_off4 = self.MW_buffer_time + laser_on
            iq_off1 = laser_off1 + self.laser_time + self.singlet_decay
            iq_off2 = tau 
            iq_off3 = tau
            iq_off4 = self.MW_buffer_time + self.readout_time + laser_off3

            awg_off1 = - self.laser_lag + iq_off1 + pihalf_x + self.awg_pulse_delay # additional initial delay at beginning to offset entire AWG pulse seq
            awg_off2 = (tau - self.awg_pulse_delay - self.awg_trig_time) + pi_y + self.awg_pulse_delay
            awg_off3 = (tau - self.awg_pulse_delay - self.awg_trig_time) + pihalf_x + iq_off4 + self.laser_lag

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            dark_seq = self.Pulser.createSequence()
            dark_seq_ref = self.Pulser.createSequence()
            echo_seq = self.Pulser.createSequence()
            echo_seq_ref = self.Pulser.createSequence()

            # define sequence structure for laser
            # laser_seq = [(laser_off, 0), (laser_on, 1)]
            laser_seq = [(laser_off1, 0), (self.laser_time, 1), (laser_off2, 0), (self.readout_time, 1), (laser_off3, 0)]
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels on SRS SG396
            srs_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            srs_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            # awg_seq = [(awg_off1, 0), (self.awg_trig_time, 0), (awg_off2, 0), (self.awg_trig_time, 1), (awg_off3, 0)]
            # awg_ref_seq = [(laser_off1 + self.laser_time + laser_off2 + self.readout_time + laser_off3, 0)] # off the entire time

            print("LASER SEQ: ", laser_seq)
            print("DAQ TRIG SEQ: ", daq_clock_seq)
            print("SRS SEQ: ", srs_I_seq)
            # print("AWG_seq: ", awg_seq)

            # assign sequences to respective channels for seq_on
            dark_seq.setDigital(3, laser_seq) # laser
            dark_seq.setDigital(0, daq_clock_seq) # integrator trigger
            # dark_seq.setDigital(4, awg_seq)
            dark_seq.setAnalog(0, srs_I_seq) # mw_I
            dark_seq.setAnalog(1, srs_Q_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            dark_seq_ref.setDigital(3, laser_seq) # laser
            dark_seq_ref.setDigital(0, daq_clock_seq) # integrator trigger
            # dark_seq_ref.setDigital(4, awg_seq)
            dark_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
            dark_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

            # assign sequences to respective channels for seq_on
            echo_seq.setDigital(3, laser_seq) # laser
            echo_seq.setDigital(0, daq_clock_seq) # integrator trigger
            # echo_seq.setDigital(4, awg_ref_seq)
            echo_seq.setAnalog(0, srs_I_seq) # mw_I
            echo_seq.setAnalog(1, srs_Q_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            echo_seq_ref.setDigital(3, laser_seq) # laser
            echo_seq_ref.setDigital(0, daq_clock_seq) # integrator trigger
            # echo_seq_ref.setDigital(4, awg_ref_seq)
            echo_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
            echo_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

            return echo_seq # + echo_seq_ref # dark_seq + dark_seq_ref + echo_seq + echo_seq_ref
        
        # seqs = self.Pulser.createSequence()

        # for i in range(num_freqs):
        #     seqs += SingleDEER()

        return SingleDEER()
        # return seqs 
    
    def DEER(self, pihalf_x, pihalf_y, pi_x, pi_y, tau, pi_electron, switch_delay, init_time, read_time, wait_time, read_wait, seq_gap):
        '''
        switch delay is a user defined parameter to replace self.singlet decay; seq_gap is used to avoid daq bugs
        DEER pulse sequence.
        MW sequence: pi/2(x) - tau - pi(y) - tau - pi/2(x)
        MW on electron spin generated by WindFreak SG + MW Switch
        '''
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        tau = self.convert_type(round(tau), float)
        pi_electron = self.convert_type(round(pi_electron), float)

        def SingleDEER():
            '''
            CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''
            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''            

            #Tian-Xing: The pulse sequence programming principle is that we firstly write down the total time we need for laser, without considering self.laser_lag. Then all the timing for other devices are shifted by 1*self.laser_lag. And the total sequence time for each device are always the same.
            init_laser_time = init_time
            laser_off1 = wait_time + pihalf_x + tau + pi_y + tau + pihalf_x + self.MW_buffer_time + read_wait
            laser_off2 = 200 + seq_gap
            self.total_time = init_laser_time + laser_off1 + read_time + laser_off2
            # DAQ trigger windows
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            clock_off_readout = read_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off1 = self.laser_lag + init_laser_time + wait_time
            iq_off2 = tau
            iq_off3 = tau
            iq_off4 = self.MW_buffer_time + read_wait + read_time + laser_off2 - self.laser_lag

            # self.wait_SG12 is another piece of waiting time after the pi/2 and pi pulse on NV and before the switch turns on
            # if we don't add this extra buffer, the MW switch will cutoff the NV pi/2 and pi pulse by a little bit, and influence the DEER's original offset
            #self.wait_SG12 = 10 
            switch_off1 = iq_off1 + pihalf_x + self.wait_SG12
            #switch_on1 = pi_electron + self.switch_delay
            #switch_off2 = -self.wait_SG12 + tau - pi_electron - self.switch_delay + pi_y + self.wait_SG12
            #switch_on2 = pi_electron + self.switch_delay
            #switch_off3 = -self.wait_SG12 + tau - pi_electron - self.switch_delay + pihalf_x + iq_off4
            switch_on1 = pi_electron + switch_delay
            switch_off2 = -self.wait_SG12 + tau - pi_electron - switch_delay + pi_y + self.wait_SG12
            switch_on2 = pi_electron + switch_delay
            switch_off3 = -self.wait_SG12 + tau - pi_electron - switch_delay + pihalf_x + iq_off4
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (read_time, 1), (laser_off2, 0)]
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels on SRS SG396
            srs_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            srs_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            # awg_seq = [(awg_off1, 0), (self.awg_trig_time, 0), (awg_off2, 0), (self.awg_trig_time, 1), (awg_off3, 0)]
            # awg_ref_seq = [(laser_off1 + self.laser_time + laser_off2 + self.readout_time + laser_off3, 0)] # off the entire time

            # sequence for driving the electron spin by using the 2nd signal generator and MW switch
            switch_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0), (switch_on2, 1), (switch_off3, 0)]
            switch_ref_seq = [(switch_off1, 0), (switch_on1, 0), (switch_off2, 0), (switch_on2, 0), (switch_off3, 0)]

            # print("LASER SEQ: ", laser_seq)
            # print("DAQ TRIG SEQ: ", daq_clock_seq)
            # print("SRS SEQ: ", srs_I_seq)
            # print("AWG_seq: ", awg_seq)

            # create sequence objects for MW on and off blocks
            dark_seq = self.Pulser.createSequence()
            dark_seq_ref = self.Pulser.createSequence()
            echo_seq = self.Pulser.createSequence()
            echo_seq_ref = self.Pulser.createSequence()

            # assign sequences to respective channels for dark_seq
            dark_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            dark_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            dark_seq.setDigital(self.channel_dict["switch"], switch_seq)
            #dark_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
            dark_seq.setAnalog(0, srs_I_seq) # mw_I
            dark_seq.setAnalog(1, srs_Q_seq) # mw_Q
            
            # assign sequences to respective channels for dark_seq_ref
            dark_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            dark_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            dark_seq_ref.setDigital(self.channel_dict["switch"], switch_seq)
            #dark_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
            dark_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
            dark_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

            # assign sequences to respective channels for echo_seq
            echo_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            echo_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            echo_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)
            echo_seq.setAnalog(0, srs_I_seq) # mw_I
            echo_seq.setAnalog(1, srs_Q_seq) # mw_Q
            
            # assign sequences to respective channels for echo_seq_ref
            echo_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            echo_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            echo_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)
            echo_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
            echo_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

            return dark_seq + dark_seq_ref + echo_seq + echo_seq_ref
        
        #seqs = self.Pulser.createSequence()

        # for i in range(num_freqs):
        #     seqs += SingleDEER()

        return SingleDEER()
        #return seqs

    def DEER_Padding(self, pihalf_x, pihalf_y, pi_x, pi_y, tau, pi_electron, scan_time):
            '''
            DEER pulse sequence with added padding. - Hanyan Cai 05/08/2024
            The purpose of this sequence is to modify the original DEER sequence to have a standard time for each scan point. 
            For samples with shorter T2 times, the echo tau will be too short, which causes issues when the DAQ measures data
            faster than the computer can process. Therefore, we add the parameter scan_time have a longer standardarized
            pulse sequence time for each scan. 

            MW sequence: pi/2(x) - tau - pi(y) - tau - pi/2(x)
            MW on electron spin generated by WindFreak SG + MW Switch
            '''
            pihalf_x = self.convert_type(round(pihalf_x), float)
            pihalf_y = self.convert_type(round(pihalf_y), float)
            pi_x = self.convert_type(round(pi_x), float)
            pi_y = self.convert_type(round(pi_y), float)
            tau = self.convert_type(round(tau), float)
            pi_electron = self.convert_type(round(pi_electron), float)
            scan_time = self.convert_type(round(scan_time), float)

            sequence_time = self.laser_time + self.singlet_decay + pihalf_x + tau + pi_y + tau + pihalf_x + self.MW_buffer_time + self.readout_time
            '''
            The scan time has to be longer than the sequence_time
            '''
            if scan_time <= sequence_time:
                raise ValueError("Total scan time CAN NOT be shorter than the total sequence time")


            def SingleDEER_Padding():
                '''
                CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
                '''
                '''
                DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
                '''            

                #Tian-Xing: The pulse sequence programming principle is that we firstly write down the total time we need for laser, without considering self.laser_lag. Then all the timing for other devices are shifted by 1*self.laser_lag. And the total sequence time for each device are always the same.
                laser_off1 = self.singlet_decay + pihalf_x + tau + pi_y + tau + pihalf_x + self.MW_buffer_time
                '''
                Here is where we make the important change to laser_off2
                '''
                laser_off2 = scan_time - sequence_time
                self.total_time = self.laser_time + laser_off1 + self.readout_time + laser_off2
                # DAQ trigger windows
                clock_off1 = self.laser_time + laser_off1 + self.laser_lag
                clock_off_readout = self.readout_time - 2*self.clock_time
                clock_off2 = laser_off2 - self.laser_lag

                # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
                iq_off1 = self.laser_lag + self.laser_time + self.singlet_decay
                iq_off2 = tau
                iq_off3 = tau
                iq_off4 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag

                # self.wait_SG12 is another piece of waiting time after the pi/2 and pi pulse on NV and before the switch turns on
                # if we don't add this extra buffer, the MW switch will cutoff the NV pi/2 and pi pulse by a little bit, and influence the DEER's original offset
                #self.wait_SG12 = 10 
                switch_off1 = iq_off1 + pihalf_x + self.wait_SG12
                switch_on1 = pi_electron + self.switch_delay
                switch_off2 = -self.wait_SG12 + tau - pi_electron - self.switch_delay + pi_y + self.wait_SG12
                switch_on2 = pi_electron + self.switch_delay
                switch_off3 = -self.wait_SG12 + tau - pi_electron - self.switch_delay + pihalf_x + iq_off4
                '''
                CONSTRUCT PULSE SEQUENCE
                '''
                # define sequence structure for laser
                laser_seq = [(self.laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]
                # define sequence structure for integrator trigger
                daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
                
                # sequence structure for I & Q MW channels on SRS SG396
                srs_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
                srs_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

                # sequence structure for I & Q MW channels (MW off)
                srs_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
                srs_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

                # sequence structure for I & Q MW channels (MW off)
                # awg_seq = [(awg_off1, 0), (self.awg_trig_time, 0), (awg_off2, 0), (self.awg_trig_time, 1), (awg_off3, 0)]
                # awg_ref_seq = [(laser_off1 + self.laser_time + laser_off2 + self.readout_time + laser_off3, 0)] # off the entire time

                # sequence for driving the electron spin by using the 2nd signal generator and MW switch
                switch_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0), (switch_on2, 1), (switch_off3, 0)]
                switch_ref_seq = [(switch_off1, 0), (switch_on1, 0), (switch_off2, 0), (switch_on2, 0), (switch_off3, 0)]

                # print("LASER SEQ: ", laser_seq)
                # print("DAQ TRIG SEQ: ", daq_clock_seq)
                # print("SRS SEQ: ", srs_I_seq)
                # print("AWG_seq: ", awg_seq)

                # create sequence objects for MW on and off blocks
                dark_seq = self.Pulser.createSequence()
                dark_seq_ref = self.Pulser.createSequence()
                echo_seq = self.Pulser.createSequence()
                echo_seq_ref = self.Pulser.createSequence()

                # assign sequences to respective channels for dark_seq
                dark_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
                dark_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                dark_seq.setDigital(self.channel_dict["switch"], switch_seq)
                #dark_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
                dark_seq.setAnalog(0, srs_I_seq) # mw_I
                dark_seq.setAnalog(1, srs_Q_seq) # mw_Q
                
                # assign sequences to respective channels for dark_seq_ref
                dark_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
                dark_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                dark_seq_ref.setDigital(self.channel_dict["switch"], switch_seq)
                #dark_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
                dark_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
                dark_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

                # assign sequences to respective channels for echo_seq
                echo_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
                echo_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                echo_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)
                echo_seq.setAnalog(0, srs_I_seq) # mw_I
                echo_seq.setAnalog(1, srs_Q_seq) # mw_Q
                
                # assign sequences to respective channels for echo_seq_ref
                echo_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
                echo_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                echo_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)
                echo_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
                echo_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

                return dark_seq + dark_seq_ref + echo_seq + echo_seq_ref
            
            #seqs = self.Pulser.createSequence()

            # for i in range(num_freqs):
            #     seqs += SingleDEER()

            return SingleDEER_Padding()
            #return seqs

    def DEER_Rabi(self, params, pihalf_x, pihalf_y, pi_x, pi_y, tau, init_time, read_time, wait_time, read_wait, seq_gap):
        '''
        DEER pulse sequence.
        MW sequence: pi/2(x) - tau - pi(y) - tau - pi/2(x)
        MW on electron spin generated by WindFreak SG + MW Switch, the time of this electron spin MW pulse is sweeping
        Developed by Tian-Xing, April 2024
        '''
        #print('ZTX: params:',params)
        longest_time = self.convert_type(round(max(params)), float)
         
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        tau = self.convert_type(round(tau), float)
        if longest_time >= tau:
            raise ValueError("RF pulse time on electron spin CAN NOT be longer than NV's tau time")
        def SingleDEERRabi(e_pulse_on):
            '''
            CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''
            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''       
            e_pulse_on = float(round(e_pulse_on)) 
            # convert to proper data type to avoid undesired rpyc netref data type     

            #Tian-Xing: The pulse sequence programming principle is that we firstly write down the total time we need for laser, without considering self.laser_lag. Then all the timing for other devices are shifted by 1*self.laser_lag. And the total sequence time for each device are always the same.
            init_laser_time = init_time
            laser_off1 = wait_time + pihalf_x + tau + pi_y + tau + pihalf_x + self.MW_buffer_time + read_wait
            laser_off2 = 200 + seq_gap
            self.total_time = init_laser_time + laser_off1 + read_time + laser_off2
            # DAQ trigger windows
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            clock_off_readout = read_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off1 = self.laser_lag + init_laser_time + wait_time
            iq_off2 = tau
            iq_off3 = tau
            iq_off4 = self.MW_buffer_time + read_wait + read_time + laser_off2 - self.laser_lag

            # self.wait_SG12 is another piece of waiting time after the pi/2 and pi pulse on NV and before the switch turns on
            # if we don't add this extra buffer, the MW switch will cutoff the NV pi/2 and pi pulse by a little bit, and influence the DEER's original offset
            #self.wait_SG12 = 10 
            switch_off1 = iq_off1 + pihalf_x + self.wait_SG12
            switch_on1 = e_pulse_on + self.switch_delay
            switch_off2 = -self.wait_SG12 + tau - e_pulse_on - self.switch_delay + pi_y + self.wait_SG12
            switch_on2 = e_pulse_on + self.switch_delay
            switch_off3 = -self.wait_SG12 + tau - e_pulse_on - self.switch_delay + pihalf_x + iq_off4
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (read_time, 1), (laser_off2, 0)]
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels on SRS SG396
            srs_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            srs_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            # awg_seq = [(awg_off1, 0), (self.awg_trig_time, 0), (awg_off2, 0), (self.awg_trig_time, 1), (awg_off3, 0)]
            # awg_ref_seq = [(laser_off1 + self.laser_time + laser_off2 + self.readout_time + laser_off3, 0)] # off the entire time

            # sequence for driving the electron spin by using the 2nd signal generator and MW switch
            switch_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0), (switch_on2, 1), (switch_off3, 0)]
            switch_ref_seq = [(switch_off1, 0), (switch_on1, 0), (switch_off2, 0), (switch_on2, 0), (switch_off3, 0)]

            # print("LASER SEQ: ", laser_seq)
            # print("DAQ TRIG SEQ: ", daq_clock_seq)
            # print("SRS SEQ: ", srs_I_seq)
            # print("AWG_seq: ", awg_seq)

            # create sequence objects for MW on and off blocks
            dark_seq = self.Pulser.createSequence()
            dark_seq_ref = self.Pulser.createSequence()
            echo_seq = self.Pulser.createSequence()
            echo_seq_ref = self.Pulser.createSequence()

            # assign sequences to respective channels for dark_seq
            dark_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            dark_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            dark_seq.setDigital(self.channel_dict["switch"], switch_seq)
            #dark_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
            dark_seq.setAnalog(0, srs_I_seq) # mw_I
            dark_seq.setAnalog(1, srs_Q_seq) # mw_Q
            
            # assign sequences to respective channels for dark_seq_ref
            dark_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            dark_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            dark_seq_ref.setDigital(self.channel_dict["switch"], switch_seq)
            #dark_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
            dark_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
            dark_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

            # assign sequences to respective channels for echo_seq
            echo_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            echo_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            echo_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)
            echo_seq.setAnalog(0, srs_I_seq) # mw_I
            echo_seq.setAnalog(1, srs_Q_seq) # mw_Q
            
            # assign sequences to respective channels for echo_seq_ref
            echo_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            echo_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            echo_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)
            echo_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
            echo_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

            return dark_seq + dark_seq_ref + echo_seq + echo_seq_ref
        
        seqs = self.Pulser.createSequence()
        seqs_total_time = 0
        for e_pulse_on in params:
            seqs += SingleDEERRabi(e_pulse_on)
            seqs_total_time += 4*self.total_time # we multiply it by 4 here because for DEER, we have two backgrounds and two signals ms=0/1
        print('DEER_Rabi sequence created!')
        print('sequence time for 1 run is (ns):',seqs_total_time)
        return seqs
    
    def DEER_FID_Evan(self, params, pihalf_x, pihalf_y, pi_x, pi_y):
        '''
        DEER FID pulse sequence.
        '''
        longest_time = self.convert_type(round(max(params)), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        
        def SingleDEERFID(tau_time):
            '''
            CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''
            tau_time = self.convert_type(round(tau_time), float) # convert to proper data type to avoid undesired rpyc netref data type
            
            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run (for different tau durations)
            pad_time = longest_time - tau_time

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''            
            laser_off1 = self.laser_lag
            # laser_off2 = self.singlet_decay + pihalf_x + tau_time/2 + pi_y + tau_time/2 + pihalf_x + self.MW_buffer_time
            laser_off2 = self.singlet_decay + pihalf_x + tau_time + pi_y + tau_time + pihalf_x + self.MW_buffer_time
            laser_off3 = self.laser_lag + pad_time 

            # DAQ trigger windows
            clock_off1 = laser_off1 + self.laser_time + laser_off2 + self.readout_time - self.trig_spot - self.clock_time
            clock_off2 = self.trig_spot + laser_off3

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off1 = laser_off1 + self.laser_time + self.singlet_decay
            iq_off2 = tau_time # /2
            iq_off3 = tau_time # /2
            iq_off4 = self.MW_buffer_time + self.readout_time + laser_off3

            awg_off1 = iq_off1 + pihalf_x + iq_off2 + pi_y - self.awg_pulse_delay
            awg_off2 = self.awg_pulse_delay + iq_off3 + pihalf_x + iq_off4

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            dark_seq = self.Pulser.createSequence()
            dark_seq_ref = self.Pulser.createSequence()
            echo_seq = self.Pulser.createSequence()
            echo_seq_ref = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(laser_off1, 0), (self.laser_time, 1), (laser_off2, 0), (self.readout_time, 1), (laser_off3, 0)]
            
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels 
            srs_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            srs_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            awg_seq = [(awg_off1, 0), (self.awg_trig_time, 1), (awg_off2, 0)]
            awg_ref_seq = [(awg_off1, 0), (self.awg_trig_time, 0), (awg_off2, 0)] # off the entire time

            print("LASER SEQ: ", laser_seq)
            print("DAQ TRIG SEQ: ", daq_clock_seq)
            print("SRS SEQ: ", srs_I_seq)
            print("AWG_seq: ", awg_seq)

            # assign sequences to respective channels for seq_on
            dark_seq.setDigital(3, laser_seq) # laser
            dark_seq.setDigital(0, daq_clock_seq) # integrator trigger
            dark_seq.setDigital(4, awg_seq)
            dark_seq.setAnalog(0, srs_I_seq) # mw_I
            dark_seq.setAnalog(1, srs_Q_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            dark_seq_ref.setDigital(3, laser_seq) # laser
            dark_seq_ref.setDigital(0, daq_clock_seq) # integrator trigger
            dark_seq_ref.setDigital(4, awg_seq)
            dark_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
            dark_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

            # assign sequences to respective channels for seq_on
            echo_seq.setDigital(3, laser_seq) # laser
            echo_seq.setDigital(0, daq_clock_seq) # integrator trigger
            echo_seq.setDigital(4, awg_ref_seq)
            echo_seq.setAnalog(0, srs_I_seq) # mw_I
            echo_seq.setAnalog(1, srs_Q_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            echo_seq_ref.setDigital(3, laser_seq) # laser
            echo_seq_ref.setDigital(0, daq_clock_seq) # integrator trigger
            echo_seq_ref.setDigital(4, awg_ref_seq)
            echo_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
            echo_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

            return dark_seq + dark_seq_ref # + echo_seq + echo_seq_ref
        
        seqs = self.Pulser.createSequence()

        for tau in params:
            seqs += SingleDEERFID(tau)

        return seqs 

    def DEER_FID_2_Evan(self, params, pihalf_x, pihalf_y, pi_x, pi_y, n):
            '''
            DEER pulse sequence.
            MW sequence: pi/2(x) - tau - pi(y) - tau - pi/2(x)

            '''
            longest_time = self.convert_type(round(max(params)), float)
            pihalf_x = self.convert_type(round(pihalf_x), float)
            pihalf_y = self.convert_type(round(pihalf_y), float)
            pi_x = self.convert_type(round(pi_x), float)
            pi_y = self.convert_type(round(pi_y), float)
            n = self.convert_type(round(n), int)

            # print("TAU TIMES = ", params)

            def PiPulsesN(tau, N):
                CPMG_I_seq = [self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0])]
                CPMG_Q_seq = [self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1])]
                mw_I = CPMG_I_seq*(N-1) + [self.Pi('y', pi_y)[0]]
                mw_Q = CPMG_Q_seq*(N-1) + [self.Pi('y', pi_y)[1]]
                
                return mw_I, mw_Q
            
            def AWGPulsesN(tau, N):
                '''
                Function to return all the AWG trigger pulses corresponding to the pi pulses in the SRS CPMG sequence.
                An initial pulse after the first pi/2 pulse is left off with the option to set it on.
                '''
                return [(self.awg_trig_time, 1), (tau, 0)] + [(self.awg_trig_time, 1), (2*tau, 0)]*(N-1) + [(self.awg_trig_time, 1)]

            def SingleDEERFID(tau):
                '''
                CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
                '''
                tau = self.convert_type(round(tau), float)
                pad_time = longest_time - tau
                '''
                DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
                '''            
                
                cpmg_time = pihalf_x + tau + (pi_y + 2*tau)*(n-1) + pi_y + tau + pihalf_x
            
                laser_off1 = self.laser_lag
                laser_off2 = self.singlet_decay + cpmg_time + self.MW_buffer_time
                # laser_off2 = self.singlet_decay + pihalf_x + tau + pi_y + tau + pihalf_x + self.MW_buffer_time
                laser_off3 = self.laser_lag + pad_time
                # laser_off3 = 6000

                # DAQ trigger windows
                # clock_off1 = laser_off + self.readout_time - self.clock_time
                # clock_off2 = laser_on - self.readout_time
                clock_off1 = laser_off1 + self.laser_time + laser_off2 + self.readout_time - self.trig_spot - self.clock_time
                clock_off2 = self.trig_spot + laser_off3

                # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
                # iq_off1 = laser_off1 + self.laser_time + self.singlet_decay
                # iq_off2 = tau 
                # iq_off3 = tau
                # iq_off4 = self.MW_buffer_time + self.readout_time + laser_off3
                iq_off1 = laser_off1 + self.laser_time + self.singlet_decay
                iq_off2 = tau
                iq_off3 = tau
                iq_off4 = self.MW_buffer_time + self.readout_time + laser_off3

                # awg_off1 = - self.laser_lag + iq_off1 + pihalf_x + self.awg_pulse_delay # additional initial delay at beginning to offset entire AWG pulse seq
                # # awg_off2 = (tau - self.awg_pulse_delay - self.awg_trig_time) + pi_y + self.awg_pulse_delay
                # # awg_off3 = (tau - self.awg_pulse_delay - self.awg_trig_time) + pihalf_x + iq_off4 + self.laser_lag
                # awg_off2 = (tau - self.awg_pulse_delay - self.awg_trig_time) + pihalf_x + iq_off4 + self.laser_lag

                awg_off1 = iq_off1 + pihalf_x + self.awg_pulse_delay # additional initial delay at beginning to offset entire AWG pulse seq
                # awg_off2 = (tau - self.awg_pulse_delay - self.awg_trig_time) + pi_y + self.awg_pulse_delay
                # awg_off3 = (tau - self.awg_pulse_delay - self.awg_trig_time) + pihalf_x + iq_off4 + self.laser_lag
                awg_off2 = (tau - self.awg_pulse_delay - self.awg_trig_time) + pihalf_x + iq_off4 

                '''
                CONSTRUCT PULSE SEQUENCE
                '''
                # create sequence objects for MW on and off blocks
                dark_seq = self.Pulser.createSequence()
                dark_seq_ref = self.Pulser.createSequence()
                echo_seq = self.Pulser.createSequence()
                echo_seq_ref = self.Pulser.createSequence()

                # define sequence structure for laser
                # laser_seq = [(laser_off, 0), (laser_on, 1)]
                laser_seq = [(laser_off1, 0), (self.laser_time, 1), (laser_off2, 0), (self.readout_time, 1), (laser_off3, 0)]
                # define sequence structure for integrator trigger
                daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off2, 0)]
                
                # sequence structure for I & Q MW channels on SRS SG396
                # srs_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
                # srs_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]
                srs_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0])] + PiPulsesN(tau, n)[0] + [(iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
                srs_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1])] + PiPulsesN(tau, n)[1] + [(iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]
                
                # sequence structure for I & Q MW channels (MW off)
                # srs_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
                # srs_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]
                srs_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0])] + PiPulsesN(tau, n)[0] + [(iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
                srs_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1])] + PiPulsesN(tau, n)[1] + [(iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

                # sequence structure for I & Q MW channels (MW off)
                # awg_seq = [(awg_off1, 0), (self.awg_trig_time, 0), (awg_off2, 0), (self.awg_trig_time, 1), (awg_off3, 0)]
                # awg_ref_seq = [(laser_off1 + self.laser_time + laser_off2 + self.readout_time + laser_off3, 0)] # off the entire time
                awg_seq = [(awg_off1, 0)] + AWGPulsesN(tau, n) + [(awg_off2, 0)]
                awg_ref_seq = [(laser_off1 + self.laser_time + laser_off2 + self.readout_time + laser_off3, 0)] # off the entire time

                # print("LASER SEQ: ", laser_seq)
                # print("DAQ TRIG SEQ: ", daq_clock_seq)
                # print("SRS SEQ: ", srs_I_seq)
                # print("AWG_seq: ", awg_seq)

                # assign sequences to respective channels for seq_on
                dark_seq.setDigital(3, laser_seq) # laser
                dark_seq.setDigital(0, daq_clock_seq) # integrator trigger
                dark_seq.setDigital(4, awg_seq)
                dark_seq.setAnalog(0, srs_I_seq) # mw_I
                dark_seq.setAnalog(1, srs_Q_seq) # mw_Q
                
                # assign sequences to respective channels for seq_off
                dark_seq_ref.setDigital(3, laser_seq) # laser
                dark_seq_ref.setDigital(0, daq_clock_seq) # integrator trigger
                dark_seq_ref.setDigital(4, awg_seq)
                dark_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
                dark_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

                # assign sequences to respective channels for seq_on
                echo_seq.setDigital(3, laser_seq) # laser
                echo_seq.setDigital(0, daq_clock_seq) # integrator trigger
                echo_seq.setDigital(4, awg_ref_seq)
                echo_seq.setAnalog(0, srs_I_seq) # mw_I
                echo_seq.setAnalog(1, srs_Q_seq) # mw_Q
                
                # assign sequences to respective channels for seq_off
                echo_seq_ref.setDigital(3, laser_seq) # laser
                echo_seq_ref.setDigital(0, daq_clock_seq) # integrator trigger
                echo_seq_ref.setDigital(4, awg_ref_seq)
                echo_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
                echo_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

                return dark_seq + dark_seq_ref + echo_seq + echo_seq_ref
            
            seqs = self.Pulser.createSequence()

            for t in params:
                seqs += SingleDEERFID(t)

            # return SingleDEER()
            return seqs 
    
    def DEER_FID(self, params, pihalf_x, pihalf_y, pi_x, pi_y, pi_electron, init_time, read_time, wait_time, read_wait, seq_gap):
        # developed by Hanyan Cai, April 2024

        shortest_tau = self.convert_type(round(min(params[1:])), float)         
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        pi_electron = self.convert_type(round(pi_electron), float)
        
        # 20240809 TianXing and Tengyang, relize that "shortest_tau <= pi_electron" condition will still induce error.
        # Because the 'wait_SG12' and 'self.swith_delay' will make the microwave switch still on the reporter spin MW channel when we need to drive NV.
        if shortest_tau <= pi_electron + 2*self.wait_SG12 + self.switch_delay:
            raise ValueError("NV's tau time CAN NOT be shorter than RF pulse time on electron spin + 2*self.wait_SG12 + self.switch_delay")

        def SingleDEERFID(precession_tau):
            '''
            CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''
            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            precession_tau = float(round(precession_tau))          

            # Tian-Xing: The pulse sequence programming principle is that we firstly write down the total time we need for laser, without considering self.laser_lag. 
            # Then all the timing for other devices are shifted by 1*self.laser_lag. And the total sequence time for each device are always the same.
            init_laser_time = init_time
            laser_off1 = wait_time + pihalf_x + precession_tau + pi_y + precession_tau + pihalf_x + self.MW_buffer_time + read_wait
            laser_off2 = 200 + seq_gap
            self.total_time = init_laser_time + laser_off1 + read_time + laser_off2
            # DAQ trigger windows
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            clock_off_readout = read_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off1 = self.laser_lag + init_laser_time + wait_time
            iq_off2 = precession_tau
            iq_off3 = precession_tau
            iq_off4 = self.MW_buffer_time + read_wait + read_time + laser_off2 - self.laser_lag

            # self.wait_SG12 is another piece of waiting time after the pi/2 and pi pulse on NV and before the switch turns on
            # if we don't add this extra buffer, the MW switch will cutoff the NV pi/2 and pi pulse by a little bit, and influence the DEER's original offset
            #self.wait_SG12 = 10 
            switch_off1 = iq_off1 + pihalf_x + self.wait_SG12
            switch_on1 = pi_electron + self.switch_delay
            switch_off2 = -self.wait_SG12 + precession_tau - pi_electron - self.switch_delay + pi_y + self.wait_SG12
            switch_on2 = pi_electron + self.switch_delay
            switch_off3 = -self.wait_SG12 + precession_tau - pi_electron - self.switch_delay + pihalf_x + iq_off4
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (read_time, 1), (laser_off2, 0)]
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels on SRS SG396
            srs_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            srs_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            # awg_seq = [(awg_off1, 0), (self.awg_trig_time, 0), (awg_off2, 0), (self.awg_trig_time, 1), (awg_off3, 0)]
            # awg_ref_seq = [(laser_off1 + self.laser_time + laser_off2 + self.readout_time + laser_off3, 0)] # off the entire time

            # sequence for driving the electron spin by using the 2nd signal generator and MW switch
            switch_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0), (switch_on2, 1), (switch_off3, 0)]
            switch_ref_seq = [(switch_off1, 0), (switch_on1, 0), (switch_off2, 0), (switch_on2, 0), (switch_off3, 0)]

            # print("LASER SEQ: ", laser_seq)
            # print("DAQ TRIG SEQ: ", daq_clock_seq)
            # print("SRS SEQ: ", srs_I_seq)
            # print("AWG_seq: ", awg_seq)

            # create sequence objects for MW on and off blocks
            dark_seq = self.Pulser.createSequence()
            dark_seq_ref = self.Pulser.createSequence()
            echo_seq = self.Pulser.createSequence()
            echo_seq_ref = self.Pulser.createSequence()

            # assign sequences to respective channels for dark_seq
            dark_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            dark_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            dark_seq.setDigital(self.channel_dict["switch"], switch_seq)
            #dark_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
            dark_seq.setAnalog(0, srs_I_seq) # mw_I
            dark_seq.setAnalog(1, srs_Q_seq) # mw_Q
            
            # assign sequences to respective channels for dark_seq_ref
            dark_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            dark_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            dark_seq_ref.setDigital(self.channel_dict["switch"], switch_seq)
            #dark_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
            dark_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
            dark_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

            # assign sequences to respective channels for echo_seq
            echo_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            echo_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            echo_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)
            echo_seq.setAnalog(0, srs_I_seq) # mw_I
            echo_seq.setAnalog(1, srs_Q_seq) # mw_Q
            
            # assign sequences to respective channels for echo_seq_ref
            echo_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            echo_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            echo_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)
            echo_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
            echo_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

            return dark_seq + dark_seq_ref + echo_seq + echo_seq_ref

        seqs = self.Pulser.createSequence()
        seqs_total_time = 0
        for precession_tau in params:
            seqs += SingleDEERFID(precession_tau)
            seqs_total_time += 4*self.total_time # we multiply it by 4 here because for DEER, we have two backgrounds and two signals ms=0/1
        print('DEER_FID sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)
        return seqs

    def DEER_Corr_Rabi(self, pihalf_x, pihalf_y, pi_x, pi_y, tau, echo_rest_time, awg_pi_trig_delay, num_tau):
            '''
            DEER pulse sequence.
            MW sequence: pi/2(x) - tau - pi(y) - tau - pi/2(x)

            '''
            pihalf_x = self.convert_type(round(pihalf_x), float)
            pihalf_y = self.convert_type(round(pihalf_y), float)
            pi_x = self.convert_type(round(pi_x), float)
            pi_y = self.convert_type(round(pi_y), float)
            tau = self.convert_type(round(tau), float)
            echo_rest_time = self.convert_type(round(echo_rest_time), float)
            awg_pi_trig_delay = self.convert_type(round(awg_pi_trig_delay), float)
            
            def SingleCorrRabi():
                '''
                CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
                '''

                '''
                DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
                '''            
                # laser_off = self.laser_lag + pihalf_x + tau + pi_y + tau + pihalf_x + self.MW_buffer_time
                # laser_on = self.laser_time
                laser_off1 = self.laser_lag
                laser_off2 = self.singlet_decay + 2*(pihalf_x + tau + pi_y + tau + pihalf_y) + echo_rest_time + self.MW_buffer_time
                laser_off3 = self.laser_lag + 1000

                # DAQ trigger windows
                # clock_off1 = laser_off + self.readout_time - self.clock_time
                # clock_off2 = laser_on - self.readout_time
                clock_off1 = laser_off1 + self.laser_time + laser_off2 + self.readout_time - self.trig_spot - self.clock_time
                clock_off2 = self.trig_spot + laser_off3

                # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
                # iq_off1 = self.laser_lag
                # iq_off2 = tau
                # iq_off3 = tau
                # iq_off4 = self.MW_buffer_time + laser_on
                iq_off1 = laser_off1 + self.laser_time + self.singlet_decay
                iq_off2 = tau 
                iq_off3 = tau
                iq_off4 = echo_rest_time
                iq_off5 = self.MW_buffer_time + self.readout_time + laser_off3

                awg_off1 = iq_off1 + pihalf_x + iq_off2 + pi_y - self.laser_lag
                awg_off2 = (self.laser_lag - self.awg_trig_time) + iq_off3 + pihalf_y + awg_pi_trig_delay
                awg_off3 = (echo_rest_time - awg_pi_trig_delay) + pihalf_x + iq_off2 + (pi_y - self.laser_lag)
                awg_off4 = (self.laser_lag - self.awg_trig_time) + iq_off3 + pihalf_y + iq_off5

                '''
                CONSTRUCT PULSE SEQUENCE
                '''
                # create sequence objects for MW on and off blocks
                seq = self.Pulser.createSequence()
                seq_ref = self.Pulser.createSequence()
                
                # define sequence structure for laser
                # laser_seq = [(laser_off, 0), (laser_on, 1)]
                laser_seq = [(laser_off1, 0), (self.laser_time, 1), (laser_off2, 0), (self.readout_time, 1), (laser_off3, 0)]
                # define sequence structure for integrator trigger
                daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off2, 0)]
                
                # sequence structure for I & Q MW channels on SRS SG396
                echo_I_seq = [self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('y', pihalf_x)[0]]
                echo_Q_seq =[self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('y', pihalf_x)[1]]
                echo_I_ref_seq = [self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-y', pihalf_x)[0]]
                echo_Q_ref_seq = [self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-y', pihalf_x)[1]]
                
                srs_I_seq = [(iq_off1, self.IQ0[0])] + echo_I_seq + [(iq_off4, self.IQ0[0])] + echo_I_seq + [(iq_off5, self.IQ0[0])]
                srs_Q_seq = [(iq_off1, self.IQ0[1])] + echo_Q_seq + [(iq_off4, self.IQ0[1])] + echo_Q_seq + [(iq_off5, self.IQ0[1])]

                srs_I_ref_seq = [(iq_off1, self.IQ0[0])] + echo_I_seq + [(iq_off4, self.IQ0[0])] + echo_I_ref_seq + [(iq_off5, self.IQ0[0])]
                srs_Q_ref_seq = [(iq_off1, self.IQ0[1])] + echo_Q_seq + [(iq_off4, self.IQ0[1])] + echo_Q_ref_seq + [(iq_off5, self.IQ0[1])]
                
                # sequence structure for AWG trig
                awg_seq = [(awg_off1, 0), (self.awg_trig_time, 1), (awg_off2, 0), 
                           (self.awg_trig_time, 1), (awg_off3, 0), (self.awg_trig_time, 1), (awg_off4, 0)]

                # print("LASER SEQ: ", laser_seq)
                # print("DAQ TRIG SEQ: ", daq_clock_seq)
                # print("SRS SEQ: ", srs_I_seq)
                # print("AWG_seq: ", awg_seq)

                # assign sequences to respective channels for seq_on
                seq.setDigital(3, laser_seq) # laser
                seq.setDigital(0, daq_clock_seq) # integrator trigger
                seq.setDigital(4, awg_seq)
                seq.setAnalog(0, srs_I_seq) # mw_I
                seq.setAnalog(1, srs_Q_seq) # mw_Q
                
                # assign sequences to respective channels for seq_off
                seq_ref.setDigital(3, laser_seq) # laser
                seq_ref.setDigital(0, daq_clock_seq) # integrator trigger
                seq_ref.setDigital(4, awg_seq)
                seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
                seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

                return seq + seq_ref
            
            seqs = self.Pulser.createSequence()

            for i in range(num_tau):
                seqs += SingleCorrRabi()

            return seqs 

    def Corr_Spectroscopy(self, params, tau, tau_balance, seq_type, pihalf_x, pihalf_y, pi_x, pi_y, n, init_time, read_time, wait_time, read_wait):
        '''
        Feb.2025, By Tian-Xing Zheng and Hanyan Cai
        Correlation Spectroscopy sequence using YY8-N:
        MW sequence: pi/2(y) - tau - (pi(-y) - 2tau - pi(y) - 2tau - pi(y) - 2tau - pi(-y) - 2tau...)^N - tau - pi/2(y, -y)
        Or XY8 NQR: Reference: I.Lovechinsky,..., M.D.Lukin, Magnetic resonance spectroscopy of hBN by NV, Science 2017
        MW sequence: pi/2(x) - (tau - pi(x) - tau - pi(y) - tau - pi(x) - tau - pi(y) - tau - pi(y) - tau - pi(x) - tau - pi(y)- tau - pi(x))^N - tau - pi(x) - tau - pi(y)- tau - pi(x) - tau - pi/2(x, -x)
        Or Spin Echo: Reference: High-resolution correlation spectroscopy of 13C spins near a nitrogen-vacancy centre in diamond https://www.nature.com/articles/ncomms2685
        MW sequence: pi/2(x) - tau - pi(x) - tau - pi(y) - t_corr - pi/2(x) - tau - pi(x) - tau - pi(y,-y)
        '''
        longest_time = self.convert_type(round(max(params)), float)
        tau = self.convert_type(round(tau), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        n = self.convert_type(round(n), int)

        #print("type of tau is 111:\n", type(tau))
        #print("111 tau = ",tau)
        
        def PiPulsesN(seq_type, tau, N):
            tau_two_I_seq = [(2*tau, self.IQ0[0])]
            tau_two_Q_seq = [(2*tau, self.IQ0[1])]
            tau_I_seq = [(tau, self.IQ0[0])]
            tau_Q_seq = [(tau, self.IQ0[1])]

            if seq_type == 'Spin Echo':
                mw_I = [(tau, self.IQ0[0]), self.Pi('x', pi_x)[0],(tau, self.IQ0[0])]
                mw_Q = [(tau, self.IQ0[1]), self.Pi('x', pi_x)[1],(tau, self.IQ0[1])]
            
            elif seq_type == 'YY8':
                # xy4_I_seq = [Pi('x')[0], (tau, self.IQ0[0]), Pi('y')[0], (tau, self.IQ0[0]), Pi('x')[0], (tau, self.IQ0[0]), Pi('y')[0]]
                # xy4_Q_seq = [Pi('x')[1], (tau, self.IQ0[1]), Pi('y')[1], (tau, self.IQ0[1]), Pi('x')[1], (tau, self.IQ0[1]), Pi('y')[1]]
                # mw_I = (tau_half_I_seq + xy4_I_seq + tau_I_seq + list(reversed(xy4_I_seq)) + tau_half_I_seq)*N
                # mw_Q = (tau_half_Q_seq + xy4_Q_seq + tau_Q_seq + list(reversed(xy4_Q_seq)) + tau_half_Q_seq)*N

                yy4_I_seq_1 = [self.Pi('-y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('-y', pi_y)[0]]
                yy4_Q_seq_1 = [self.Pi('-y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('-y', pi_y)[1]]
                yy4_I_seq_2 = [self.Pi('-y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('-y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0]), self.Pi('y', pi_y)[0]]
                yy4_Q_seq_2 = [self.Pi('-y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('-y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1]), self.Pi('y', pi_y)[1]]
                mw_I = (tau_I_seq + yy4_I_seq_1 + tau_two_I_seq + yy4_I_seq_2 + tau_I_seq)*N
                mw_Q = (tau_Q_seq + yy4_Q_seq_1 + tau_two_Q_seq + yy4_Q_seq_2 + tau_Q_seq)*N

            elif seq_type == 'XY8 NQR':
                xy4_I_seq = [self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0]]
                xy4_Q_seq = [self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1]]
                tail_I_seq = [(tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('x', pi_x)[0], (tau, self.IQ0[0])]
                tail_Q_seq = [(tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('x', pi_x)[1], (tau, self.IQ0[1])]
                
                mw_I = (tau_I_seq + xy4_I_seq + tau_I_seq + list(reversed(xy4_I_seq)))*N + tail_I_seq
                mw_Q = (tau_Q_seq + xy4_Q_seq + tau_Q_seq + list(reversed(xy4_Q_seq)))*N + tail_Q_seq
            else:
                raise ValueError("Correlation sequence only has YY8 and XY8 NQR for now!")

            return mw_I, mw_Q

        def SingleCorrSpec(t_corr):
            '''
            CREATE SINGLE HAHN-ECHO SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            t_corr = self.convert_type(round(t_corr), float) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT

            pad_time = padding time to equalize duration of every run (for different tau durations)
            '''
            pad_time = longest_time - t_corr
            init_laser_time = init_time         #the time for laser to initialize the system
            readout_laser_time = read_time      #the time for laser to read out the system

            # total time for correlation spectroscopy MW pulse sequence
            # corr_spec_time = pihalf_x + ((tau/2)/(8*n) + 4*pi_x + 4*pi_y + 7*tau/(8*n) + (tau/2)/(8*n))*n + pihalf_y + t_corr + \
            #                  pihalf_x + ((tau/2)/(8*n) + 4*pi_x + 4*pi_y + 7*tau/(8*n) + (tau/2)/(8*n))*n + pihalf_y
            if seq_type == 'Spin Echo':
                corr_spec_time = pihalf_x + tau + pi_x + tau + pihalf_y + t_corr + pihalf_x + tau + pi_x + tau + pihalf_y
            elif seq_type == 'YY8':
                corr_spec_time = pihalf_x + ((tau) + 0*pi_x + 8*pi_y + 14*tau + (tau))*n + pihalf_y + t_corr + \
                                 pihalf_x + ((tau) + 0*pi_x + 8*pi_y + 14*tau + (tau))*n + pihalf_y
            elif seq_type == 'XY8 NQR':
                corr_spec_time = pihalf_x + tau + (4*pi_x + 4*pi_y + 8*tau)*n + pi_x + tau + pi_y + tau + pi_x + tau + pihalf_y + t_corr + \
                                pihalf_x + tau + (4*pi_x + 4*pi_y + 8*tau)*n + pi_x + tau + pi_y + tau + pi_x + tau + pihalf_y
            else:
                raise ValueError("Correlation sequence only has Spin Echo, YY8, XY8 NQR for now!")
            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''          
            #laser_off1 = self.laser_lag
            laser_off1 = wait_time + corr_spec_time + self.MW_buffer_time + read_wait

            if tau_balance:
                laser_off2 = 200 
            else:
                laser_off2 = 200 + pad_time

            self.total_time = init_laser_time + laser_off1 + readout_laser_time + laser_off2
            # DAQ trigger windows
            clock_off1 = init_laser_time + laser_off1 + self.laser_lag
            clock_off_readout = readout_laser_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag    

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off_start = self.laser_lag + init_laser_time + wait_time
            iq_off_end = self.MW_buffer_time + read_wait + readout_laser_time + laser_off2 - self.laser_lag
            
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (readout_laser_time, 1), (laser_off2, 0)]
            #print('laser_seq:\n',laser_seq)
            
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1),(clock_off2, 0)]
            
            #print("type of tau is:\n", type(tau))
            #print("tau = ",tau)
            # sequence structure for I & Q MW channels 
            mw_I_seq = [(iq_off_start, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0]] + PiPulsesN(seq_type, tau, n)[0] + [self.PiHalf('y', pihalf_y)[0], (t_corr, self.IQ0[0]), self.PiHalf('x', pihalf_y)[0]] + PiPulsesN(seq_type, tau, n)[0] + [self.PiHalf('y', pihalf_x)[0], (iq_off_end, self.IQ0[0])]
            mw_Q_seq = [(iq_off_start, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1]] + PiPulsesN(seq_type, tau, n)[1] + [self.PiHalf('y', pihalf_y)[1], (t_corr, self.IQ0[1]), self.PiHalf('x', pihalf_y)[1]] + PiPulsesN(seq_type, tau, n)[1] + [self.PiHalf('y', pihalf_x)[1], (iq_off_end, self.IQ0[1])]
            
            # sequence structure for I & Q MW channels (MW off)
            mw_I_ref_seq = [(iq_off_start, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0]] + PiPulsesN(seq_type, tau, n)[0] + [self.PiHalf('y', pihalf_y)[0], (t_corr, self.IQ0[0]), self.PiHalf('x', pihalf_y)[0]] + PiPulsesN(seq_type, tau, n)[0] + [self.PiHalf('-y', pihalf_x)[0], (iq_off_end, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off_start, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1]] + PiPulsesN(seq_type, tau, n)[1] + [self.PiHalf('y', pihalf_y)[1], (t_corr, self.IQ0[1]), self.PiHalf('x', pihalf_y)[1]] + PiPulsesN(seq_type, tau, n)[1] + [self.PiHalf('-y', pihalf_x)[1], (iq_off_end, self.IQ0[1])]
            
            # assign sequences to respective channels for seq_on
            seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q
        
            # assign sequences to respective channels for seq_off
            seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q

            return seq + seq_ref

        # concatenate single correlation spectroscopy sequence "runs" number of times
        seqs = self.Pulser.createSequence()
        
        seqs_total_time = 0
        for t_corr in params:
            seqs += SingleCorrSpec(t_corr)
            seqs_total_time += 2*self.total_time
        print('Correlation Spectroscopy sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)
        return seqs

    def CASR(self, params, tau, pihalf_x, pihalf_y, pi_x, pi_y, n):
        '''
        Coherently Averaged Synchronized Readout sequence using YY8-N.
        MW sequence: pi/2(x) - tau/2 - (pi(x) - tau - pi(y) - tau - pi(x) - tau...)^N - tau/2 - pi/2(x, -x)
        '''
        longest_time = self.convert_type(round(max(params)), float)
        tau = self.convert_type(round(tau), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        n = self.convert_type(round(n), int)

        def PiPulsesN(tau, N):
            tau_half_I_seq = [((tau/2), self.IQ0[0])]
            tau_half_Q_seq = [((tau/2), self.IQ0[1])]
            tau_I_seq = [(tau, self.IQ0[0])]
            tau_Q_seq = [(tau, self.IQ0[1])]

            # xy4_I_seq = [Pi('x')[0], (tau, self.IQ0[0]), Pi('y')[0], (tau, self.IQ0[0]), Pi('x')[0], (tau, self.IQ0[0]), Pi('y')[0]]
            # xy4_Q_seq = [Pi('x')[1], (tau, self.IQ0[1]), Pi('y')[1], (tau, self.IQ0[1]), Pi('x')[1], (tau, self.IQ0[1]), Pi('y')[1]]
            # mw_I = (tau_half_I_seq + xy4_I_seq + tau_I_seq + list(reversed(xy4_I_seq)) + tau_half_I_seq)*N
            # mw_Q = (tau_half_Q_seq + xy4_Q_seq + tau_Q_seq + list(reversed(xy4_Q_seq)) + tau_half_Q_seq)*N

            yy4_I_seq_1 = [self.Pi('-y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('-y', pi_y)[0]]
            yy4_Q_seq_1 = [self.Pi('-y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('-y', pi_y)[1]]
            yy4_I_seq_2 = [self.Pi('-y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('-y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0], (tau, self.IQ0[0]), self.Pi('y', pi_y)[0]]
            yy4_Q_seq_2 = [self.Pi('-y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('-y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1], (tau, self.IQ0[1]), self.Pi('y', pi_y)[1]]
            mw_I = (tau_half_I_seq + yy4_I_seq_1 + tau_I_seq + yy4_I_seq_2 + tau_half_I_seq)*N
            mw_Q = (tau_half_Q_seq + yy4_Q_seq_1 + tau_Q_seq + yy4_Q_seq_2 + tau_half_Q_seq)*N

            return mw_I, mw_Q

        def SingleCASR(t_corr):
            '''
            CREATE SINGLE HAHN-ECHO SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            t_corr = self.convert_type(round(t_corr), float) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT

            pad_time = padding time to equalize duration of every run (for different tau durations)
            '''
            pad_time = longest_time - t_corr 

            casr_time = pihalf_x + ((tau/2) + 0*pi_x + 8*pi_y + 7*tau + (tau/2))*n + pihalf_y + t_corr + \
                             pihalf_x + ((tau/2) + 0*pi_x + 8*pi_y + 7*tau + (tau/2))*n + pihalf_y
            # TODO: update CASR time

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''            
            laser_off1 = self.laser_lag
            laser_off2 = self.singlet_decay + casr_time + self.MW_buffer_time
            laser_off3 = 100 + pad_time

            # DAQ trigger windows
            clock_off1 = laser_off1 + self.laser_time + laser_off2 + self.readout_time - self.trig_spot - self.clock_time
            clock_off2 = self.trig_spot + laser_off3           

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off_start = laser_off1 + self.laser_time + self.singlet_decay
            iq_off_end = self.MW_buffer_time + self.readout_time + laser_off3
            
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(laser_off1, 0), (self.laser_time, 1), (laser_off2, 0), (self.readout_time, 1), (laser_off3, 0)]
            
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels 
            mw_I_seq = [(iq_off_start, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0]] + PiPulsesN(tau, n)[0] + [self.PiHalf('y', pihalf_y)[0], (t_corr, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0]] + PiPulsesN(tau, n)[0] + [self.PiHalf('y', pihalf_y)[0], (iq_off_end, self.IQ0[0])]
            mw_Q_seq = [(iq_off_start, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1]] + PiPulsesN(tau, n)[1] + [self.PiHalf('y', pihalf_y)[1], (t_corr, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1]] + PiPulsesN(tau, n)[1] + [self.PiHalf('y', pihalf_y)[1], (iq_off_end, self.IQ0[1])]
            
            # sequence structure for I & Q MW channels (MW off)
            mw_I_ref_seq = [(iq_off_start, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0]] + PiPulsesN(tau, n)[0] + [self.PiHalf('y', pihalf_y)[0], (t_corr, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0]] + PiPulsesN(tau, n)[0] + [self.PiHalf('-y', pihalf_y)[0], (iq_off_end, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off_start, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1]] + PiPulsesN(tau, n)[1] + [self.PiHalf('y', pihalf_y)[1], (t_corr, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1]] + PiPulsesN(tau, n)[1] + [self.PiHalf('-y', pihalf_y)[1], (iq_off_end, self.IQ0[1])]

            print(mw_I_seq)
            
            # assign sequences to respective channels for seq_on
            seq.setDigital(3, laser_seq) # laser
            seq.setDigital(0, daq_clock_seq) # integrator trigger
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q
            
            # print("SEQ 1: ", seq1)

            # assign sequences to respective channels for seq_off
            seq_ref.setDigital(3, laser_seq) # laser
            seq_ref.setDigital(0, daq_clock_seq) # integrator trigger
            seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q

            # print("SEQ 2: ", seq2)

            return seq + seq_ref 

        # concatenate single correlation spectroscopy sequence "runs" number of times
        seqs = self.Pulser.createSequence()
        
        for t_corr in params:
            seqs += SingleCASR(t_corr)

        return seqs

    def AERIS(self, params, pulse_axes, pihalf_x, pihalf_y, pi_x, pi_y, n):

        '''
        Amplitude-Encoded Radio Induced Signal (AERIS) pulse sequence.
        '''
        longest_time = self.convert_type(round(max(params)), float)
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        n = self.convert_type(round(n), int)
        
        def PiPulsesN(axes, tau, N):
            if axes == 'xy':
                xy4_I_seq = [((tau/2)/(4*N), self.IQ0[0]), self.Pi('x', pi_x)[0], (tau/(4*N), self.IQ0[0]), self.Pi('y', pi_y)[0], (tau/(4*N), self.IQ0[0]), self.Pi('x', pi_x)[0], (tau/(4*N), self.IQ0[0]), self.Pi('y', pi_y)[0], ((tau/2)/(4*N), self.IQ0[0])]
                xy4_Q_seq = [((tau/2)/(4*N), self.IQ0[1]), self.Pi('x', pi_x)[1], (tau/(4*N), self.IQ0[1]), self.Pi('y', pi_y)[1], (tau/(4*N), self.IQ0[1]), self.Pi('x', pi_x)[1], (tau/(4*N), self.IQ0[1]), self.Pi('y', pi_y)[1], ((tau/2)/(4*N), self.IQ0[1])]
                mw_I = (xy4_I_seq)*N
                mw_Q = (xy4_Q_seq)*N
            elif axes == 'yy':
                yy4_I_seq = [((tau/2)/(4*N), self.IQ0[0]), self.Pi('y', pi_y)[0], (tau/(4*N), self.IQ0[0]), self.Pi('y', pi_y)[0], (tau/(4*N), self.IQ0[0]), self.Pi('y', pi_y)[0], (tau/(4*N), self.IQ0[0]), self.Pi('y', pi_y)[0], ((tau/2)/(4*N), self.IQ0[0])]
                yy4_Q_seq = [((tau/2)/(4*N), self.IQ0[1]), self.Pi('y', pi_y)[1], (tau/(4*N), self.IQ0[1]), self.Pi('y', pi_y)[1], (tau/(4*N), self.IQ0[1]), self.Pi('y', pi_y)[1], (tau/(4*N), self.IQ0[1]), self.Pi('y', pi_y)[1], ((tau/2)/(4*N), self.IQ0[1])]
                mw_I = (yy4_I_seq)*N
                mw_Q = (yy4_Q_seq)*N

            return mw_I, mw_Q

        def SingleAERIS(tau):
            '''
            CREATE SINGLE HAHN-ECHO SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            tau = self.convert_type(round(tau), float) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT

            pad_time = padding time to equalize duration of every run (for different tau durations)
            '''
            pad_time = longest_time - tau 
            # NOTICE: change if using PiHalf['y'] to pihalf_y
            xy4_time = 2*pihalf_x + (2*(tau/2)/(4*n) + 2*pi_x + 2*pi_y + 3*tau/(4*n))*n
            
            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''            
            laser_off1 = self.laser_lag
            laser_off2 = self.singlet_decay + xy4_time + self.MW_buffer_time
            laser_off3 = 100 + pad_time
            
            # DAQ trigger windows
            clock_off1 = laser_off1 + self.laser_time + laser_off2 + self.readout_time - self.trig_spot - self.clock_time
            clock_off2 = self.trig_spot + laser_off3         

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off_start = laser_off1 + self.laser_time + self.singlet_decay
            iq_off_end = self.MW_buffer_time + self.readout_time + laser_off3
            
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.Pulser.createSequence()
            seq_ref = self.Pulser.createSequence()
            
            # define sequence structure for laser
            laser_seq = [(laser_off1, 0), (self.laser_time, 1), (laser_off2, 0), (self.readout_time, 1), (laser_off3, 0)]
            
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels 
            mw_I_seq = [(iq_off_start, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0]] + PiPulsesN(pulse_axes, tau, n)[0] + [self.PiHalf('x', pihalf_x)[0], (iq_off_end, self.IQ0[0])]
            mw_Q_seq = [(iq_off_start, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1]] + PiPulsesN(pulse_axes, tau, n)[1] + [self.PiHalf('x', pihalf_x)[1], (iq_off_end, self.IQ0[1])]
            
            # sequence structure for I & Q MW channels (MW off)
            mw_I_ref_seq = [(iq_off_start, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0]] + PiPulsesN(pulse_axes, tau, n)[0] + [self.PiHalf('-x', pihalf_x)[0], (iq_off_end, self.IQ0[0])]
            mw_Q_ref_seq = [(iq_off_start, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1]] + PiPulsesN(pulse_axes, tau, n)[1] + [self.PiHalf('-x', pihalf_x)[1], (iq_off_end, self.IQ0[1])]

            # sequence structure for nuclear spin RF generator 
            rf_seq = []
            rf_ref_seq = []

            # assign sequences to respective channels for seq_on
            seq.setDigital(3, laser_seq) # laser
            seq.setDigital(0, daq_clock_seq) # integrator trigger
            seq.setDigital(1, rf_seq) # VSG switch to enable MW
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            seq_ref.setDigital(3, laser_seq) # laser
            seq_ref.setDigital(0, daq_clock_seq) # integrator trigger
            seq_ref.setDigital(1, rf_ref_seq) # VSG switch to enable MW
            seq_ref.setAnalog(0, mw_I_ref_seq) # mw_I
            seq_ref.setAnalog(1, mw_Q_ref_seq) # mw_Q

            return seq + seq_ref

        # concatenate single ODMR sequence "runs" number of times
        seqs = self.Pulser.createSequence()
        
        for tau in params:
            seqs += SingleAERIS(tau)
        
        return seqs
    
    def DEER_CPMG(self, pihalf_x, pihalf_y, pi_x, pi_y, echo_tau, pi_electron, n):
        '''
        Developed by Hanyan May 2024
        Using the basis of DEER_Rabi
        MW sequence: pi/2(x) - tau - pi(y) - tau - pi/2(x)
        MW on electron spin generated by WindFreak SG + MW Switch, the time of this electron spin MW pulse is sweeping
        '''
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)
        n = self.convert_type(round(n), int)
        pi_electron = self.convert_type(round(pi_electron), float)
        # The echo_tau is the t2 CPMG time with the corresponding n.
        echo_tau = float(round(echo_tau))
        # We need to convert this echo_tau to the regular tau, which we say is the actual interaction time
        tau = float(round(echo_tau / n))
 
        print("pi/2 x = ", pihalf_x)
        print("n = ", n)
        '''
        Defining the proper pi pulse sequences during the CPMG sequence. The pi pulses acts on the y axis.
        '''
        def PiPulsesN(tau, N):
            CPMG_I_seq = [self.Pi('y', pi_y)[0], (2*tau, self.IQ0[0])]
            CPMG_Q_seq = [self.Pi('y', pi_y)[1], (2*tau, self.IQ0[1])]
            mw_I = CPMG_I_seq*(N-1) + [self.Pi('y', pi_y)[0]]
            mw_Q = CPMG_Q_seq*(N-1) + [self.Pi('y', pi_y)[1]]
            return mw_I, mw_Q

        def SingleDEER_CPMG(n):
            '''
            CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''
            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''       
            n = int(round(n))
            # convert to proper data type to avoid undesired rpyc netref data type     

            # Get the total cpmg time
            cpmg_time = pihalf_x + (tau + pi_y + tau)*n + pihalf_x

            #Tian-Xing: The pulse sequence programming principle is that we firstly write down the total time we need for laser, without considering self.laser_lag. Then all the timing for other devices are shifted by 1*self.laser_lag. And the total sequence time for each device are always the same.
            laser_off1 = self.singlet_decay + cpmg_time + self.MW_buffer_time
            laser_off2 = 1000
            self.total_time = self.laser_time + laser_off1 + self.readout_time + laser_off2
            # DAQ trigger windows
            clock_off1 = self.laser_time + laser_off1 + self.laser_lag
            clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off1 = self.laser_lag + self.laser_time + self.singlet_decay
            iq_off2 = tau
            iq_off3 = tau
            iq_off4 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag

            # self.wait_SG12 is another piece of waiting time after the pi/2 and pi pulse on NV and before the switch turns on
            # if we don't add this extra buffer, the MW switch will cutoff the NV pi/2 and pi pulse by a little bit, and influence the DEER's original offset
            #self.wait_SG12 = 10 
            switch_off1 = iq_off1 + pihalf_x + self.wait_SG12
            switch_on1 = pi_electron + self.switch_delay
            switch_off2 = -self.wait_SG12 + tau - pi_electron - self.switch_delay + pi_y + self.wait_SG12
            switch_on2 = pi_electron + self.switch_delay
            #This time is defined for the CPMG pi pulse sequence
            switch_CPMG_off = 2 * tau - self.switch_delay - pi_electron + pi_y
            switch_off3 = -self.wait_SG12 + tau - pi_electron - self.switch_delay + pihalf_x + iq_off4

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # define sequence structure for laser
            laser_seq = [(self.laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels on SRS SG396
            srs_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0])] + PiPulsesN(tau, n)[0] + [(iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1])] + PiPulsesN(tau, n)[1] + [(iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            srs_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0])] + PiPulsesN(tau, n)[0] + [(iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1])] + PiPulsesN(tau, n)[1] + [(iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            # awg_seq = [(awg_off1, 0), (self.awg_trig_time, 0), (awg_off2, 0), (self.awg_trig_time, 1), (awg_off3, 0)]
            # awg_ref_seq = [(laser_off1 + self.laser_time + laser_off2 + self.readout_time + laser_off3, 0)] # off the entire time

            # sequence for driving the electron spin by using the 2nd signal generator and MW switch for CPMG
            # To correct for pulse errors, maybe we apply positive negative pi pulses. But we cannot due to limitation of WindFreak
            switch_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0)] + [(switch_on2, 1), (switch_CPMG_off, 0)] * (n - 1) + [(switch_on2, 1), (switch_off3, 0)]
            switch_ref_seq = [(switch_off1, 0), (switch_on1, 0), (switch_off2, 0)] + [(switch_on2, 0), (switch_CPMG_off, 0)] * (n - 1) + [(switch_on2, 0), (switch_off3, 0)]

            # print("LASER SEQ: ", laser_seq)
            # print("DAQ TRIG SEQ: ", daq_clock_seq)
            # print("SRS SEQ: ", srs_I_seq)
            # print("AWG_seq: ", awg_seq)

            # create sequence objects for MW on and off blocks
            dark_seq = self.Pulser.createSequence()
            dark_seq_ref = self.Pulser.createSequence()
            echo_seq = self.Pulser.createSequence()
            echo_seq_ref = self.Pulser.createSequence()

            # assign sequences to respective channels for dark_seq
            dark_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            dark_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            dark_seq.setDigital(self.channel_dict["switch"], switch_seq)
            #dark_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
            dark_seq.setAnalog(0, srs_I_seq) # mw_I
            dark_seq.setAnalog(1, srs_Q_seq) # mw_Q
            
            # assign sequences to respective channels for dark_seq_ref
            dark_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            dark_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            dark_seq_ref.setDigital(self.channel_dict["switch"], switch_seq)
            #dark_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
            dark_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
            dark_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

            # assign sequences to respective channels for echo_seq
            echo_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            echo_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            echo_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)
            echo_seq.setAnalog(0, srs_I_seq) # mw_I
            echo_seq.setAnalog(1, srs_Q_seq) # mw_Q
            
            # assign sequences to respective channels for echo_seq_ref
            echo_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            echo_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            echo_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)
            echo_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
            echo_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

            return dark_seq + dark_seq_ref + echo_seq + echo_seq_ref 
        
        return SingleDEER_CPMG(n)

    def ReporterSpin_T1(self, params, pihalf_x, pihalf_y, pi_x, pi_y, tau0, extra_pipulse, pi_electron):
            #writen by Tengyang based on the code of DEER
            '''
            DEER pulse sequence.
            MW sequence: pi/2(x) - tau0 - pi(y) - tau0 - pi/2(y)
            MW on electron spin generated by WindFreak SG + MW Switch
            '''
            shortest_tau = self.convert_type(round(min(params[1:])), float)
            pihalf_x = self.convert_type(round(pihalf_x), float)
            pihalf_y = self.convert_type(round(pihalf_y), float)
            pi_x = self.convert_type(round(pi_x), float)
            pi_y = self.convert_type(round(pi_y), float)
            tau0 =self.convert_type(round(tau0),float)
            pi_electron = self.convert_type(round(pi_electron), float)
            extra_pipulse = self.convert_type(round(extra_pipulse),float)

            print("Everything is ok after converting data type")

            if shortest_tau <= extra_pipulse:
                raise ValueError("Extra pi pulse on reporter spin time CAN NOT be longer than shortest tau!")

            def SingleT1(tau):
                '''
                CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
                '''
                '''
                DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
                '''            
                tau = float(round(tau))
                #Tian-Xing: The pulse sequence programming principle is that we firstly write down the total time we need for laser, without considering self.laser_lag. Then all the timing for other devices are shifted by 1*self.laser_lag. And the total sequence time for each device are always the same.
                #tau0= #a number needs to fill here
                laser_off1 = self.singlet_decay + pihalf_x + tau0 + pi_y + tau0 + pihalf_y + tau + pihalf_x + tau0 + pi_y + tau0 + pihalf_y + self.MW_buffer_time
                laser_off2 = 1000
                self.total_time = self.laser_time + laser_off1 + self.readout_time + laser_off2
                # DAQ trigger windows
                clock_off1 = self.laser_time + laser_off1 + self.laser_lag
                clock_off_readout = self.readout_time - 2*self.clock_time
                clock_off2 = laser_off2 - self.laser_lag

                # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
                iq_off1 = self.laser_lag + self.laser_time + self.singlet_decay
                iq_off2 = tau0
                iq_off3 = tau0
                iq_off4 = tau
                iq_off5 = tau0
                iq_off6 = tau0
                iq_off7 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag

                # self.wait_SG12 is another piece of waiting time after the pi/2 and pi pulse on NV and before the switch turns on
                # if we don't add this extra buffer, the MW switch will cutoff the NV pi/2 and pi pulse by a little bit, and influence the DEER's original offset
                #self.wait_SG12 = 10 
                switch_off1 = iq_off1 + pihalf_x + self.wait_SG12
                switch_on1 = pi_electron + self.switch_delay
                switch_off2 = -self.wait_SG12 + tau0 - pi_electron - self.switch_delay + pi_y + self.wait_SG12
                switch_on2 = pi_electron + self.switch_delay

                # Below we define new time variables to add the pi pulse to the reporter spin in the middl eof the sequence
                extra_pipulse_off = extra_pipulse + tau0 - self.switch_delay + pihalf_y - pi_electron - self.wait_SG12
                extra_pipulse_on = pi_electron + self.switch_delay

                # There are two definitions of switch_off3, one for switch_ref_seq and the other for switch_seq
                switch_off3 = tau + 2*tau0 + pihalf_x + pi_y + pihalf_y - switch_on1 - switch_off2 - switch_on2
                switch_off3_extra_pipulse = tau + 2*tau0 + pihalf_x + pi_y + pihalf_y - switch_on1 - switch_off2 - switch_on2 - extra_pipulse_off - extra_pipulse_on
                
                
                switch_on3= pi_electron + self.switch_delay
                switch_off4= switch_off2
                switch_on4 = pi_electron + self.switch_delay
                switch_off5= -self.wait_SG12 + tau - pi_electron - self.switch_delay + pihalf_x + iq_off7
                



                #switch_off3 = -self.wait_SG12 + tau - pi_electron - self.switch_delay + pihalf_x + iq_off4
                '''
                CONSTRUCT PULSE SEQUENCE
                '''
                # define sequence structure for laser
                laser_seq = [(self.laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]
                # define sequence structure for integrator trigger
                daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
                
                # sequence structure for I & Q MW channels on SRS SG396
                srs_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('y', pihalf_y)[0], (iq_off4,self.IQ0[0]),self.PiHalf('x', pihalf_x)[0], (iq_off5, self.IQ0[0]), self.Pi('y', pi_y)[0],(iq_off6,self.IQ0[0]),self.PiHalf('y',pihalf_y)[0],(iq_off7, self.IQ0[0])]
                srs_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('y', pihalf_y)[1], (iq_off4,self.IQ0[1]),self.PiHalf('x', pihalf_x)[1], (iq_off5, self.IQ0[1]), self.Pi('y', pi_y)[1],(iq_off6,self.IQ0[1]),self.PiHalf('y',pihalf_y)[1],(iq_off7, self.IQ0[1])]

                # sequence structure for I & Q MW channels (MW off)
                srs_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('y', pihalf_y)[0], (iq_off4,self.IQ0[0]),self.PiHalf('x', pihalf_x)[0], (iq_off5, self.IQ0[0]), self.Pi('y', pi_y)[0],(iq_off6,self.IQ0[0]),self.PiHalf('-y',pihalf_y)[0],(iq_off7, self.IQ0[0])]
                srs_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('y', pihalf_y)[1], (iq_off4,self.IQ0[1]),self.PiHalf('x', pihalf_x)[1], (iq_off5, self.IQ0[1]), self.Pi('y', pi_y)[1],(iq_off6,self.IQ0[1]),self.PiHalf('-y',pihalf_y)[1],(iq_off7, self.IQ0[1])]

                # sequence structure for I & Q MW channels (MW off)
                # awg_seq = [(awg_off1, 0), (self.awg_trig_time, 0), (awg_off2, 0), (self.awg_trig_time, 1), (awg_off3, 0)]
                # awg_ref_seq = [(laser_off1 + self.laser_time + laser_off2 + self.readout_time + laser_off3, 0)] # off the entire time

                # sequence for driving the electron spin by using the 2nd signal generator and MW switch
                switch_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0), (switch_on2, 1),(extra_pipulse_off,0),(extra_pipulse_on,1), (switch_off3_extra_pipulse, 0),(switch_on3,1),(switch_off4,0),(switch_on4,1),(switch_off5,0)]
                switch_ref_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0), (switch_on2, 1), (switch_off3, 0),(switch_on3,1),(switch_off4,0),(switch_on4,1),(switch_off5,0)]

                # print("LASER SEQ: ", laser_seq)
                # print("DAQ TRIG SEQ: ", daq_clock_seq)
                # print("SRS SEQ: ", srs_I_seq)
                # print("AWG_seq: ", awg_seq)

                # create sequence objects for MW on and off blocks
                dark_seq = self.Pulser.createSequence()
                dark_seq_ref = self.Pulser.createSequence()
                echo_seq = self.Pulser.createSequence()
                echo_seq_ref = self.Pulser.createSequence()

                # assign sequences to respective channels for dark_seq
                dark_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
                dark_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                dark_seq.setDigital(self.channel_dict["switch"], switch_seq)
                #dark_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
                dark_seq.setAnalog(0, srs_I_seq) # mw_I
                dark_seq.setAnalog(1, srs_Q_seq) # mw_Q
                
                # assign sequences to respective channels for dark_seq_ref
                dark_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
                dark_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                dark_seq_ref.setDigital(self.channel_dict["switch"], switch_seq)
                #dark_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
                dark_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
                dark_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

                # assign sequences to respective channels for echo_seq
                echo_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
                echo_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                echo_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)
                echo_seq.setAnalog(0, srs_I_seq) # mw_I
                echo_seq.setAnalog(1, srs_Q_seq) # mw_Q
                
                # assign sequences to respective channels for echo_seq_ref
                echo_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
                echo_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                echo_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)
                echo_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
                echo_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

                return dark_seq + dark_seq_ref + echo_seq + echo_seq_ref

            seqs = self.Pulser.createSequence()
            seqs_total_time = 0
            for tau in params:
                seqs += SingleT1(tau)
                seqs_total_time += 4*self.total_time # we multiply it by 4 here because for DEER, we have two backgrounds and two signals ms=0/1
            print('DEER_FID sequence created!')
            print('sequence time for 1 run is (ns):', seqs_total_time)
            return seqs
            
            #seqs = self.Pulser.createSequence()

            # for i in range(num_freqs):
            #     seqs += SingleDEER()
            #return seqs
    
    def DEER_Correlation_Rabi(self, params, pihalf_x, pihalf_y, pi_x, pi_y, tau0, middle_pulse_start_time, tau, pi_electron, init_time, read_time, wait_time, read_wait):
            '''
            20240728 Writen by Tengyang and Hanyan based on the code of DEER
            20250331 modified by Tian-Xing adding init_time, read_time, wait_time, read_wait for Pentacene in hBN
            DEER pulse sequence.
            MW sequence: pi/2(x) - tau0 - pi(y) - tau0 - pi/2(y)
            MW on electron spin generated by WindFreak SG + MW Switch
            '''
            longest_e_pulse_time = self.convert_type(round(max(params[1:])), float)
            
            pihalf_x = self.convert_type(round(pihalf_x), float)
            pihalf_y = self.convert_type(round(pihalf_y), float)
            pi_x = self.convert_type(round(pi_x), float)
            pi_y = self.convert_type(round(pi_y), float)

            # The tau0 time is the set time between the pi/2 pulse and pi pulse in the two DEER sequences
            tau0 = self.convert_type(round(tau0),float)
            # The tau time is the set time between the two DEER sequences
            tau = self.convert_type(round(tau),float)

            pi_electron = self.convert_type(round(pi_electron), float)
            middle_pulse_start_time = self.convert_type(round(middle_pulse_start_time),float)

            if tau <= longest_e_pulse_time + middle_pulse_start_time + 10:
                raise ValueError("The middle reporter spin pulse time plus the milddle pulse start time cannot be longer than tau!")

            def SingleCorrelationRabi(e_pulse_time):
                '''
                CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
                '''
                '''
                DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
                '''            
                e_pulse_time = float(round(e_pulse_time))
                #Tian-Xing: The pulse sequence programming principle is that we firstly write down the total time we need for laser, without considering self.laser_lag. Then all the timing for other devices are shifted by 1*self.laser_lag. And the total sequence time for each device are always the same.
                #tau0= #a number needs to fill here
                init_laser_time = init_time
                laser_off1 = wait_time + pihalf_x + tau0 + pi_y + tau0 + pihalf_y + tau + pihalf_x + tau0 + pi_y + tau0 + pihalf_y + self.MW_buffer_time + read_wait
                laser_off2 = 300
                self.total_time = init_laser_time + laser_off1 + read_time + laser_off2
                # DAQ trigger windows
                clock_off1 = init_laser_time + laser_off1 + self.laser_lag
                clock_off_readout = read_time - 2*self.clock_time
                clock_off2 = laser_off2 - self.laser_lag

                # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
                iq_off1 = self.laser_lag + init_laser_time + wait_time
                iq_off2 = tau0
                iq_off3 = tau0
                iq_off4 = tau
                iq_off5 = tau0
                iq_off6 = tau0
                iq_off7 = self.MW_buffer_time + read_wait + read_time + laser_off2 - self.laser_lag

                # self.wait_SG12 is another piece of waiting time after the pi/2 and pi pulse on NV and before the switch turns on
                # if we don't add this extra buffer, the MW switch will cutoff the NV pi/2 and pi pulse by a little bit, and influence the DEER's original offset
                #self.wait_SG12 = 10 
                switch_off1 = iq_off1 + pihalf_x + self.wait_SG12
                switch_on1 = pi_electron + self.switch_delay
                switch_off2 = -self.wait_SG12 + tau0 - pi_electron - self.switch_delay + pi_y + self.wait_SG12
                switch_on2 = pi_electron + self.switch_delay

                # Below we define new time variables to add the pi pulse to the reporter spin in the middle of the sequence
                extra_pipulse_off = middle_pulse_start_time + tau0 - self.switch_delay + pihalf_x - pi_electron - self.wait_SG12
                extra_pipulse_on = e_pulse_time + self.switch_delay

                # There are two definitions of switch_off3, one for switch_ref_seq and the other for switch_seq
                switch_off3 = tau + 2*tau0 + pihalf_x + pi_y + pihalf_x - switch_on1 - switch_off2 - switch_on2
                switch_off3_extra_pipulse = tau + 2*tau0 + pihalf_x + pi_y + pihalf_x - switch_on1 - switch_off2 - switch_on2 - extra_pipulse_off - extra_pipulse_on
                
                switch_on3= pi_electron + self.switch_delay
                switch_off4= switch_off2
                switch_on4 = pi_electron + self.switch_delay
                switch_off5= -self.wait_SG12 + tau - pi_electron - self.switch_delay + pihalf_x + iq_off7
                #switch_off3 = -self.wait_SG12 + tau - pi_electron - self.switch_delay + pihalf_x + iq_off4
                '''
                CONSTRUCT PULSE SEQUENCE
                '''
                # define sequence structure for laser
                laser_seq = [(init_laser_time, 1), (laser_off1, 0), (read_time, 1), (laser_off2, 0)]
                # define sequence structure for integrator trigger
                daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
                
                # sequence structure for I & Q MW channels on SRS SG396
                srs_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], 
                (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), 
                self.PiHalf('y', pihalf_y)[0], (iq_off4,self.IQ0[0]),self.PiHalf('x', pihalf_x)[0], 
                (iq_off5, self.IQ0[0]), self.Pi('y', pi_y)[0],(iq_off6,self.IQ0[0]),
                self.PiHalf('y',pihalf_y)[0],(iq_off7, self.IQ0[0])]

                srs_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], 
                (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), 
                self.PiHalf('y', pihalf_y)[1], (iq_off4,self.IQ0[1]),self.PiHalf('x', pihalf_x)[1], 
                (iq_off5, self.IQ0[1]), self.Pi('y', pi_y)[1],(iq_off6,self.IQ0[1]),
                self.PiHalf('y',pihalf_y)[1],(iq_off7, self.IQ0[1])]

                # sequence structure for I & Q MW channels (MW off)
                srs_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('y', pihalf_y)[0], (iq_off4,self.IQ0[0]),self.PiHalf('x', pihalf_x)[0], (iq_off5, self.IQ0[0]), self.Pi('y', pi_y)[0],(iq_off6,self.IQ0[0]),self.PiHalf('-y',pihalf_y)[0],(iq_off7, self.IQ0[0])]
                srs_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('y', pihalf_y)[1], (iq_off4,self.IQ0[1]),self.PiHalf('x', pihalf_x)[1], (iq_off5, self.IQ0[1]), self.Pi('y', pi_y)[1],(iq_off6,self.IQ0[1]),self.PiHalf('-y',pihalf_y)[1],(iq_off7, self.IQ0[1])]

                # sequence structure for I & Q MW channels (MW off)
                # awg_seq = [(awg_off1, 0), (self.awg_trig_time, 0), (awg_off2, 0), (self.awg_trig_time, 1), (awg_off3, 0)]
                # awg_ref_seq = [(laser_off1 + self.laser_time + laser_off2 + self.readout_time + laser_off3, 0)] # off the entire time

                # sequence for driving the electron spin by using the 2nd signal generator and MW switch
                switch_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0), 
                (switch_on2, 1),(extra_pipulse_off,0),(extra_pipulse_on,1), 
                (switch_off3_extra_pipulse, 0),(switch_on3,1),(switch_off4,0),
                (switch_on4,1),(switch_off5,0)]

                switch_ref_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0),
                (switch_on2, 1), (switch_off3, 0),(switch_on3,1),(switch_off4,0),
                (switch_on4,1),(switch_off5,0)]

                # print("LASER SEQ: ", laser_seq)
                # print("DAQ TRIG SEQ: ", daq_clock_seq)
                # print("SRS SEQ: ", srs_I_seq)
                # print("AWG_seq: ", awg_seq)

                # create sequence objects for MW on and off blocks
                dark_seq = self.Pulser.createSequence()
                dark_seq_ref = self.Pulser.createSequence()
                echo_seq = self.Pulser.createSequence()
                echo_seq_ref = self.Pulser.createSequence()

                # assign sequences to respective channels for dark_seq
                dark_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
                dark_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                dark_seq.setDigital(self.channel_dict["switch"], switch_seq)
                #dark_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
                dark_seq.setAnalog(0, srs_I_seq) # mw_I
                dark_seq.setAnalog(1, srs_Q_seq) # mw_Q
                
                # assign sequences to respective channels for dark_seq_ref
                dark_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
                dark_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                dark_seq_ref.setDigital(self.channel_dict["switch"], switch_seq)
                #dark_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
                dark_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
                dark_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

                # assign sequences to respective channels for echo_seq
                echo_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
                echo_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                echo_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)
                echo_seq.setAnalog(0, srs_I_seq) # mw_I
                echo_seq.setAnalog(1, srs_Q_seq) # mw_Q
                
                # assign sequences to respective channels for echo_seq_ref
                echo_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
                echo_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                echo_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)
                echo_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
                echo_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

                return dark_seq + dark_seq_ref + echo_seq + echo_seq_ref

            seqs = self.Pulser.createSequence()
            seqs_total_time = 0
            for e_pulse_time in params:
                seqs += SingleCorrelationRabi(e_pulse_time)
                seqs_total_time += 4*self.total_time # we multiply it by 4 here because for DEER, we have two backgrounds and two signals ms=0/1
            print('DEER_correlation_rabi sequence created!')
            print('sequence time for 1 run is (ns):', seqs_total_time)
            return seqs
        
    def ReporterSpin_T2(self, params, pihalf_x, pihalf_y, pi_x, pi_y, tau0, spin_echo_first_DEER_gap_time, tau, pi_electron, pi_half_electron, init_time, read_time, wait_time, read_wait):
            '''
            20240728 Writen by Hanyan based on the code of DEER_Correlation_Rabi
            20250331 Tian-Xing: Added init_time, read_time, wait_time, read_wait for Pentacene in hBN measurements
            DEER pulse sequence.
            MW sequence: pi/2(x) - tau0 - pi(y) - tau0 - pi/2(y)
            MW on electron spin generated by WindFreak SG + MW Switch
            '''
            longest_e_spin_echo_interaction_time = self.convert_type(round(max(params[1:])), float)
            
            pihalf_x = self.convert_type(round(pihalf_x), float)
            pihalf_y = self.convert_type(round(pihalf_y), float)
            pi_x = self.convert_type(round(pi_x), float)
            pi_y = self.convert_type(round(pi_y), float)

            # The tau0 time is the set time between the pi/2 pulse and pi pulse in the two DEER sequences
            tau0 = self.convert_type(round(tau0),float)
            # The tau time is the set time between the two DEER sequences
            tau = self.convert_type(round(tau),float)

            pi_electron = self.convert_type(round(pi_electron), float)
            pi_half_electron = self.convert_type(round(pi_half_electron), float)
            spin_echo_first_DEER_gap_time = self.convert_type(round(spin_echo_first_DEER_gap_time),float)

            max_spin_echo_time = longest_e_spin_echo_interaction_time * 2 + pi_electron + pi_half_electron * 2 + spin_echo_first_DEER_gap_time

            if tau <= max_spin_echo_time + 10:
                raise ValueError("The longest spin echo on the reporter spin is too long for the given set time between two DEER sequences (tau)!")

            def SingleT2(e_spin_echo_interaction_time):
                '''
                CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
                '''
                '''
                DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
                '''            
                e_spin_echo_interaction_time = float(round(e_spin_echo_interaction_time))
                #Tian-Xing: The pulse sequence programming principle is that we firstly write down the total time we need for laser, without considering self.laser_lag. Then all the timing for other devices are shifted by 1*self.laser_lag. And the total sequence time for each device are always the same.
                #tau0= #a number needs to fill here
                init_laser_time = init_time
                laser_off1 = wait_time + pihalf_x + tau0 + pi_y + tau0 + pihalf_y + tau + pihalf_x + tau0 + pi_y + tau0 + pihalf_y + self.MW_buffer_time + read_wait
                laser_off2 = 300
                self.total_time = init_laser_time + laser_off1 + read_time + laser_off2
                # DAQ trigger windows
                clock_off1 = init_laser_time + laser_off1 + self.laser_lag
                clock_off_readout = read_time - 2*self.clock_time
                clock_off2 = laser_off2 - self.laser_lag

                # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
                iq_off1 = self.laser_lag + init_laser_time + wait_time
                iq_off2 = tau0
                iq_off3 = tau0
                iq_off4 = tau
                iq_off5 = tau0
                iq_off6 = tau0
                iq_off7 = self.MW_buffer_time + read_wait + read_time + laser_off2 - self.laser_lag

                # self.wait_SG12 is another piece of waiting time after the pi/2 and pi pulse on NV and before the switch turns on
                # if we don't add this extra buffer, the MW switch will cutoff the NV pi/2 and pi pulse by a little bit, and influence the DEER's original offset
                #self.wait_SG12 = 10 
                switch_off1 = iq_off1 + pihalf_x + self.wait_SG12
                switch_on1 = self.switch_delay + pi_electron 
                switch_off2 = -self.wait_SG12 + tau0 - pi_electron - self.switch_delay + pi_y + self.wait_SG12
                switch_on2 = self.switch_delay + pi_electron 

                # Below we define the time variables for the spin echo on the reporter
                # gap_time_off is the time between the end of switch_on2 and the begiining of the reporter spin echo pi/2 pulse
                gap_time_off = spin_echo_first_DEER_gap_time + tau0 - self.switch_delay - pi_electron - self.wait_SG12 + pihalf_y
                e_spin_echo_on1 = self.switch_delay + pi_half_electron
                e_spin_echo_off1 = -self.switch_delay + e_spin_echo_interaction_time
                e_spin_echo_on2 = self.switch_delay + pi_electron
                e_spin_echo_off2 = e_spin_echo_off1
                e_spin_echo_on3 = e_spin_echo_on1
                total_spin_echo_time = e_spin_echo_on1 + e_spin_echo_off1 + e_spin_echo_on2 + e_spin_echo_off2 + e_spin_echo_on3 + e_spin_echo_on3

                # There are two definitions of switch_off3, one for switch_ref_seq and the other for switch_seq
                switch_off3 = tau + 2*tau0 + pihalf_x + pi_y + pihalf_y - switch_on1 - switch_off2 - switch_on2
                switch_off3_extra_echo = tau + 2*tau0 + pihalf_x + pi_y + pihalf_y - switch_on1 - switch_off2 - switch_on2 - total_spin_echo_time - gap_time_off
                
                switch_on3= pi_electron + self.switch_delay
                switch_off4= switch_off2
                switch_on4 = pi_electron + self.switch_delay
                switch_off5= -self.wait_SG12 + tau - pi_electron - self.switch_delay + pihalf_x + iq_off7
                #switch_off3 = -self.wait_SG12 + tau - pi_electron - self.switch_delay + pihalf_x + iq_off4
                '''
                CONSTRUCT PULSE SEQUENCE
                '''
                # define sequence structure for laser
                laser_seq = [(init_laser_time, 1), (laser_off1, 0), (read_time, 1), (laser_off2, 0)]
                # define sequence structure for integrator trigger
                daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
                
                # sequence structure for I & Q MW channels on SRS SG396
                srs_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], 
                (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), 
                self.PiHalf('y', pihalf_y)[0], (iq_off4,self.IQ0[0]),self.PiHalf('x', pihalf_x)[0], 
                (iq_off5, self.IQ0[0]), self.Pi('y', pi_y)[0],(iq_off6, self.IQ0[0]),
                self.PiHalf('y',pihalf_y)[0],(iq_off7, self.IQ0[0])]

                srs_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], 
                (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), 
                self.PiHalf('y', pihalf_y)[1], (iq_off4, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], 
                (iq_off5, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off6, self.IQ0[1]),
                self.PiHalf('y', pihalf_y)[1], (iq_off7, self.IQ0[1])]

                # sequence structure for I & Q MW channels (MW off)
                srs_I_ref_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('y', pihalf_y)[0], (iq_off4,self.IQ0[0]),self.PiHalf('x', pihalf_x)[0], (iq_off5, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off6, self.IQ0[0]), self.PiHalf('-y', pihalf_y)[0], (iq_off7, self.IQ0[0])]
                srs_Q_ref_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('y', pihalf_y)[1], (iq_off4,self.IQ0[1]),self.PiHalf('x', pihalf_x)[1], (iq_off5, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off6, self.IQ0[1]), self.PiHalf('-y', pihalf_y)[1], (iq_off7, self.IQ0[1])]

                # sequence structure for I & Q MW channels (MW off)
                # awg_seq = [(awg_off1, 0), (self.awg_trig_time, 0), (awg_off2, 0), (self.awg_trig_time, 1), (awg_off3, 0)]
                # awg_ref_seq = [(laser_off1 + self.laser_time + laser_off2 + self.readout_time + laser_off3, 0)] # off the entire time

                # sequence for driving the electron spin by using the 2nd signal generator and MW switch
                switch_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0), 
                (switch_on2, 1),(gap_time_off,0),(e_spin_echo_on1,1), (e_spin_echo_off1, 0), (e_spin_echo_on2, 1), (e_spin_echo_off2, 0), (e_spin_echo_on3, 1),
                (switch_off3_extra_echo, 0),(switch_on3,1),(switch_off4,0),
                (switch_on4,1),(switch_off5,0)]

                switch_ref_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0),
                (switch_on2, 1), (switch_off3, 0),(switch_on3,1),(switch_off4,0),
                (switch_on4,1),(switch_off5,0)]

                # print("LASER SEQ: ", laser_seq)
                # print("DAQ TRIG SEQ: ", daq_clock_seq)
                # print("SRS SEQ: ", srs_I_seq)
                # print("AWG_seq: ", awg_seq)

                # create sequence objects for MW on and off blocks
                dark_seq = self.Pulser.createSequence()
                dark_seq_ref = self.Pulser.createSequence()
                echo_seq = self.Pulser.createSequence()
                echo_seq_ref = self.Pulser.createSequence()

                # assign sequences to respective channels for dark_seq
                dark_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
                dark_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                dark_seq.setDigital(self.channel_dict["switch"], switch_seq)
                #dark_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
                dark_seq.setAnalog(0, srs_I_seq) # mw_I
                dark_seq.setAnalog(1, srs_Q_seq) # mw_Q
                
                # assign sequences to respective channels for dark_seq_ref
                dark_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
                dark_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                dark_seq_ref.setDigital(self.channel_dict["switch"], switch_seq)
                #dark_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
                dark_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
                dark_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

                # assign sequences to respective channels for echo_seq
                echo_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
                echo_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                echo_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)
                echo_seq.setAnalog(0, srs_I_seq) # mw_I
                echo_seq.setAnalog(1, srs_Q_seq) # mw_Q
                
                # assign sequences to respective channels for echo_seq_ref
                echo_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
                echo_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
                echo_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)
                echo_seq_ref.setAnalog(0, srs_I_ref_seq) # mw_I
                echo_seq_ref.setAnalog(1, srs_Q_ref_seq) # mw_Q

                return dark_seq + dark_seq_ref + echo_seq + echo_seq_ref

            seqs = self.Pulser.createSequence()
            seqs_total_time = 0
            for e_spin_echo_interaction_time in params:
                seqs += SingleT2(e_spin_echo_interaction_time)
                seqs_total_time += 4*self.total_time # we multiply it by 4 here because for DEER, we have two backgrounds and two signals ms=0/1
            print('DEER_correlation_rabi sequence created!')
            print('sequence time for 1 run is (ns):', seqs_total_time)
            return seqs

    def Instantaneous_diff_phase_cycling(self, params, tau_balance, pihalf_x, pihalf_y, pi_x, pi_y, init_time, read_time, wait_time, read_wait, seq_gap):
        shortest_tau = self.convert_type(round(min(params[1:])), float)         
        pihalf_x = self.convert_type(round(pihalf_x), float)
        pihalf_y = self.convert_type(round(pihalf_y), float)
        pi_x = self.convert_type(round(pi_x), float)
        pi_y = self.convert_type(round(pi_y), float)

        longest_time = self.convert_type(round(max(params)), float)
        
        # 20240809 TianXing and Tengyang, relize that "shortest_tau <= pi_electron" condition will still induce error.
        # Because the 'wait_SG12' and 'self.swith_delay' will make the microwave switch still on the reporter spin MW channel when we need to drive NV.

        def SinglePhaseCycle(precession_tau, tau_balance):
            '''
            CREATE SINGLE DEER SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''
            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            precession_tau = float(round(precession_tau))     
            pad_time = longest_time - precession_tau     
            
            # Tian-Xing: The pulse sequence programming principle is that we firstly write down the total time we need for laser, without considering self.laser_lag. 
            # Then all the timing for other devices are shifted by 1*self.laser_lag. And the total sequence time for each device are always the same.
            laser_off1 = wait_time + pihalf_x + precession_tau + pi_y + precession_tau + pihalf_x + self.MW_buffer_time + read_wait
            #laser_off2 = 1000
            if tau_balance:
                laser_off2 = 200 + seq_gap
            else:
                laser_off2 = 200 + pad_time + seq_gap
            self.total_time = init_time + laser_off1 + read_time + laser_off2
            # DAQ trigger windows
            clock_off1 = init_time + laser_off1 + self.laser_lag
            clock_off_readout = read_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows (on slightly longer than VSG to ensure it's set)
            iq_off1 = self.laser_lag + init_time + wait_time
            iq_off2 = precession_tau
            iq_off3 = precession_tau
            iq_off4 = self.MW_buffer_time + read_wait + read_time + laser_off2 - self.laser_lag
            """
            # self.wait_SG12 is another piece of waiting time after the pi/2 and pi pulse on NV and before the switch turns on
            # if we don't add this extra buffer, the MW switch will cutoff the NV pi/2 and pi pulse by a little bit, and influence the DEER's original offset
            #self.wait_SG12 = 10 
            switch_off1 = iq_off1 + pihalf_x + self.wait_SG12
            switch_on1 = pi_electron + self.switch_delay
            switch_off2 = -self.wait_SG12 + precession_tau - pi_electron - self.switch_delay + pi_y + self.wait_SG12
            switch_on2 = pi_electron + self.switch_delay
            switch_off3 = -self.wait_SG12 + precession_tau - pi_electron - self.switch_delay + pihalf_x + iq_off4"""
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # define sequence structure for laser
            laser_seq = [(init_time, 1), (laser_off1, 0), (read_time, 1), (laser_off2, 0)]
            # define sequence structure for integrator trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # sequence structure for I & Q MW channels on SRS SG396
            srs_I_seq_y = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_seq_y = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            srs_I_ref_seq_y = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('y', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_ref_seq_y = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('y', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # The below pair of IQ sequences will have the middle pulse on the x axis instead of the y axis
            # sequence structure for I & Q MW channels on SRS SG396
            srs_I_seq_x = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('x', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_seq_x = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('x', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            srs_I_ref_seq_x = [(iq_off1, self.IQ0[0]), self.PiHalf('x', pihalf_x)[0], (iq_off2, self.IQ0[0]), self.Pi('x', pi_y)[0], (iq_off3, self.IQ0[0]), self.PiHalf('-x', pihalf_x)[0], (iq_off4, self.IQ0[0])]
            srs_Q_ref_seq_x = [(iq_off1, self.IQ0[1]), self.PiHalf('x', pihalf_x)[1], (iq_off2, self.IQ0[1]), self.Pi('x', pi_y)[1], (iq_off3, self.IQ0[1]), self.PiHalf('-x', pihalf_x)[1], (iq_off4, self.IQ0[1])]

            # sequence structure for I & Q MW channels (MW off)
            # awg_seq = [(awg_off1, 0), (self.awg_trig_time, 0), (awg_off2, 0), (self.awg_trig_time, 1), (awg_off3, 0)]
            # awg_ref_seq = [(laser_off1 + self.laser_time + laser_off2 + self.readout_time + laser_off3, 0)] # off the entire time

            # sequence for driving the electron spin by using the 2nd signal generator and MW switch
            #switch_seq = [(switch_off1, 0), (switch_on1, 1), (switch_off2, 0), (switch_on2, 1), (switch_off3, 0)]
            #switch_ref_seq = [(switch_off1, 0), (switch_on1, 0), (switch_off2, 0), (switch_on2, 0), (switch_off3, 0)]

            # print("LASER SEQ: ", laser_seq)
            # print("DAQ TRIG SEQ: ", daq_clock_seq)
            # print("SRS SEQ: ", srs_I_seq)
            # print("AWG_seq: ", awg_seq)

            # create sequence objects for MW on and off blocks
            dark_seq = self.Pulser.createSequence()
            dark_seq_ref = self.Pulser.createSequence()
            echo_seq = self.Pulser.createSequence()
            echo_seq_ref = self.Pulser.createSequence()

            # assign sequences to respective channels for dark_seq
            dark_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            dark_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            #dark_seq.setDigital(self.channel_dict["switch"], switch_seq)
            #dark_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
            dark_seq.setAnalog(0, srs_I_seq_y) # mw_I
            dark_seq.setAnalog(1, srs_Q_seq_y) # mw_Q
            
            # assign sequences to respective channels for dark_seq_ref
            dark_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            dark_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            #dark_seq_ref.setDigital(self.channel_dict["switch"], switch_seq)
            #dark_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)#for debug
            dark_seq_ref.setAnalog(0, srs_I_ref_seq_y) # mw_I
            dark_seq_ref.setAnalog(1, srs_Q_ref_seq_y) # mw_Q

            # assign sequences to respective channels for echo_seq
            echo_seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
            echo_seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            #echo_seq.setDigital(self.channel_dict["switch"], switch_ref_seq)
            echo_seq.setAnalog(0, srs_I_seq_x) # mw_I
            echo_seq.setAnalog(1, srs_Q_seq_x) # mw_Q
            
            # assign sequences to respective channels for echo_seq_ref
            echo_seq_ref.setDigital(self.channel_dict["laser"], laser_seq) # laser
            echo_seq_ref.setDigital(self.channel_dict["clock"], daq_clock_seq) # clock trigger
            #echo_seq_ref.setDigital(self.channel_dict["switch"], switch_ref_seq)
            echo_seq_ref.setAnalog(0, srs_I_ref_seq_x) # mw_I
            echo_seq_ref.setAnalog(1, srs_Q_ref_seq_x) # mw_Q

            return dark_seq + dark_seq_ref + echo_seq + echo_seq_ref

        seqs = self.Pulser.createSequence()
        seqs_total_time = 0
        for precession_tau in params:
            seqs += SinglePhaseCycle(precession_tau, tau_balance)
            seqs_total_time += 4*self.total_time # we multiply it by 4 here because for DEER, we have two backgrounds and two signals ms=0/1
        print('Instantanuous Diffusion Phase Cycle sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)
        return seqs

    def RabiNoReadWait(self, params, pi_xy, init_time, read_time):
        '''
        Rabi sequence
        '''
        ## Run a MW pulse of varying duration, then measure the signal
        ## and reference counts from NV.
        # self.total_time = 0
        longest_time = self.convert_type(round(max(params)), float)
        self.laser_time = init_time
        self.readout_time = read_time
        ## we can measure the pi time on x and on y.
        ## they should be the same, but they technically
        ## have different offsets on our pulse streamer.
        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        elif pi_xy == 'y':
            self.IQ_ON = self.IQpy
        else:
            raise ValueError("pi_xy must be 'x' or 'y'!")

        def SingleRabi(iq_on):
            '''
            CREATE SINGLE RABI SEQUENCE TO REPEAT THROUGHOUT EXPERIMENT
            '''

            iq_on = float(round(iq_on)) # convert to proper data type to avoid undesired rpyc netref data type

            '''
            DEFINE SPECIAL TIME INTERVALS FOR EXPERIMENT
            '''
            # padding time to equalize duration of every run (for different vsg_on durations)
            # pad_time = 50000 - self.laser_lag - self.laser_time - self.singlet_decay - iq_on - self.MW_buffer_time - self.readout_time 
            pad_time = longest_time - iq_on

            '''
            DEFINE RELEVANT ON, OFF TIMES FOR DEVICES
            '''
            init_laser_time = self.laser_time
            laser_off1 = self.singlet_decay + iq_on + self.MW_buffer_time
            laser_off2 = 200 + pad_time
            self.total_time = init_laser_time + laser_off1 + self.readout_time + laser_off2

            # mw I & Q off windows
            iq_off1 = self.laser_lag + self.laser_time + self.singlet_decay
            iq_off2 = self.MW_buffer_time + self.readout_time + laser_off2 - self.laser_lag # + self.laser_time # + laser_off4 + laser_off5

            # DAQ trigger windows
            clock_off1 = self.laser_lag + self.laser_time + laser_off1
            clock_off_readout = self.readout_time - 2*self.clock_time
            clock_off2 = laser_off2 - self.laser_lag
                   
            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq_on = self.Pulser.createSequence()
            seq_off = self.Pulser.createSequence()

            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]
            
            # define sequence structure for DAQ trigger
            daq_clock_seq = [(clock_off1, 0), (self.clock_time, 1), (clock_off_readout, 0), (self.clock_time, 1), (clock_off2, 0)]
            
            # define sequence structure for MW I and Q when MW = ON
            mw_I_on_seq = [(iq_off1, self.IQ0[0]), (iq_on, self.IQ_ON[0]), (iq_off2, self.IQ0[0])]
            mw_Q_on_seq = [(iq_off1, self.IQ0[1]), (iq_on, self.IQ_ON[1]), (iq_off2, self.IQ0[1])]

            # when MW = OFF
            mw_I_off_seq = [(iq_off1, self.IQ0[0]), (iq_on, self.IQ0[0]), (iq_off2, self.IQ0[0])]
            mw_Q_off_seq = [(iq_off1, self.IQ0[1]), (iq_on, self.IQ0[1]), (iq_off2, self.IQ0[1])]
            #print('\ndaq_clock_seq is:\n',daq_clock_seq)
            # assign sequences to respective channels for seq_on
            seq_on.setDigital(self.channel_dict["laser"], laser_seq) # laser 
            seq_on.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            # seq_on.setDigital(1, switch_on_seq) # RF control switch
            seq_on.setAnalog(0, mw_I_on_seq) # mw_I
            seq_on.setAnalog(1, mw_Q_on_seq) # mw_Q
            
            # assign sequences to respective channels for seq_off
            seq_off.setDigital(self.channel_dict["laser"], laser_seq) # laser
            seq_off.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            # seq_off.setDigital(1, switch_off_seq) # RF control switch
            seq_off.setAnalog(0, mw_I_off_seq) # mw_I
            seq_off.setAnalog(1, mw_Q_off_seq) # mw_Q

            return seq_on + seq_off

        seqs = self.Pulser.createSequence()
        seqs_total_time = 0
        for mw_time in params:
            seqs += SingleRabi(mw_time)
            seqs_total_time += 2*self.total_time
        print('Rabi sequence created!')
        print('sequence time for 1 run is (ns):',seqs_total_time)
        return seqs

    def ContinousRead(self, readout_time, relaxation_time, read_window_num):
        readout_time = self.convert_type(round(readout_time), float)
        relaxation_time = self.convert_type(round(relaxation_time), float)
        

        #define time for DAQ
        clock_off_init = self.laser_lag
        clock_on = self.clock_time
        clock_off = readout_time - self.clock_time
        clock_off_final = relaxation_time - self.laser_lag

        #define time for laser
        laser_on = (clock_on + clock_off) * read_window_num
        laser_off = relaxation_time # RelaxationTime is the time after laser

        # define sequence structure for clock
        # ReadWindow_Num is the number of daq windows
        daq_clock_seq = [(clock_off_init, 0)] + [(clock_on, 1), (clock_off, 0)] * read_window_num + [(clock_off_final, 0)]

        #define laser sequence
        laser_seq = [(laser_on, 1), (laser_off, 0)]
        
        seq = self.Pulser.createSequence()
        # assign sequences to respective channels for seq_on
        seq.setDigital(self.channel_dict["laser"], laser_seq) # laser
        seq.setDigital(self.channel_dict["clock"], daq_clock_seq) # integrator trigger
            
        return seq
       





        


