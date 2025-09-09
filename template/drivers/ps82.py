from pulsestreamer import PulseStreamer, Sequence, OutputState
import numpy as np
import time
from rpyc.utils.classic import obtain
import typing as t


class PS82():
    def __init__(self):
        super().__init__()
        
        """
        The following variables allow the functionality of the copied function from pulses.py
        units in [ns].
        - Rolando

        *** New Channel Dict. *** Proposed 8/27/2025 Rolando
        To be called channel_r 

        Virtual Gate (vrt_gate): 0
        Sync (sync): 1
        Nanodrive (nano): 2
        SPCM gate (spcm_gate): 3
        Laser trigger (laser): 7

        """
        self.channel_r = {"vrt_gate": 0, "sync": 1, "nano": 2, "spcm_gate": 3, "laser": 7}
        self.channel_dict = {"clock": 0, "laser": 7, "switch": 2, "gate":3, "": 4, "": 5, "": 6, "": 1, "": None} # Change done by Rolando in PS channel dictionary.
        self.clock_time = 10
        self.sampling_time = 50000
        self.laser_lag = 130
        self.MW_buffer_time = 200
        self.readout_time = 400
        self.total_time = 0 #update when a pulse sequence is streamed 
        ip="169.254.8.2"
        self.ps = PulseStreamer(ip)
        self.last_wfm = []

        """ Some constants by Tian-Xing """
        # 20250423 calibrated by multimeter and PulseStreamer controller, by Tian-Xing
        self.IQ0 = [0.0098, 0.0010]
        self.IQ = self.IQ0

        self.IQpx = [0.497, 0.001]
        self.IQnx = [-0.479, 0.001]

        self.IQpy = [0.0098, 0.482]
        self.IQny = [0.0098, -0.481]

            # Here, we force the type of time parameters to be an int type in python
    # All times variables here are in unit of ns
    _T = t.TypeVar('_T')

    def convert_type(self, arg: t.Any, converter: _T) -> _T:
        return converter(arg)

    def stream(self, seq, n_runs=1, final=OutputState.ZERO()):
        seq = obtain(seq)
        # print('type(seq) is:', type(seq))
        # print('seq is:', seq)
        self.ps.stream(seq,n_runs, final)

    def stream_wfm(self, wfm, wfm_onoff=1, n_runs='inf'):
        try:
            if wfm_onoff==1:
                if n_runs=='inf':
                    self.stream_channels(wfm, n_runs)
                    print(str(wfm.wfm_name) + ' ...is running for ' + str(n_runs) + ' runs.')
                else:
                    self.stream_channels(wfm, int(n_runs))
                    print(str(wfm.wfm_name) + ' ...is running for ' + str(int(n_runs)) + ' runs.')
            elif wfm_onoff==0:
                print('wfm off')
        except:
            print('warning: wfm could not be streamed, wfm not running')
            pass
        self.last_wfm = wfm

    def stream_channels(self, wfm, n_runs):

        # create new sequence
        self.sequence = self.ps.createSequence()
        this_wfm = self.sequence.getData()

        # update channels
        for key in wfm.wfm_params['ch_dict']:
            if key[0:2] == 'di':
                try:
                    pattern = wfm.wfm_params[key]['pattern']
                    # pattern = self.compress_pattern(pattern) # takes 15 ms, may be useful depending on sequence
                    self.sequence.setDigital(int(wfm.wfm_params[key]['idx']), pattern)
                except:
                    error_msg = 'error, channel: ' + str(key) + ' not loaded.'
                    print(error_msg)
            elif key[0:2] == 'an':
                try:
                    self.sequence.setAnalog(int(wfm.wfm_params[key]['idx']), wfm.wfm.wfm_params[key]['pattern'])
                except:
                    error_msg = 'error, channel: ' + str(key) + ' not loaded.'
                    print('error')
            else:
                print('wfm error: channel must be "digi" or "analog"')

        # stream
        if (n_runs == 'inf'):
            self.ps.stream(self.sequence, PulseStreamer.REPEAT_INFINITELY)
        else:
            self.ps.stream(self.sequence, n_runs)

    def stream_all_channels(self, wfm, n_runs):

        # create new sequence
        self.sequence = self.ps.createSequence()
        this_wfm = self.sequence.getData()

        # update digital channels
        try:
            self.sequence.setDigital(int(wfm.digi0['idx']), wfm.digi0['pattern'])
        except:
            print('error, digi0 not loaded')
        try:
            self.sequence.setDigital(int(wfm.digi1['idx']), wfm.digi1['pattern'])
        except:
            print('error, digi1 not loaded')
        try:
            self.sequence.setDigital(int(wfm.digi2['idx']), wfm.digi2['pattern'])
        except:
            print('error, digi2 not loaded')
        try:
            self.sequence.setDigital(int(wfm.digi3['idx']), wfm.digi3['pattern'])
        except:
            print('error, digi3 not loaded')
        try:
            self.sequence.setDigital(int(wfm.digi4['idx']), wfm.digi4['pattern'])
        except:
            print('error, digi4 not loaded')
        try:
            self.sequence.setDigital(int(wfm.digi5['idx']), wfm.digi5['pattern'])
        except:
            print('error, digi5 not loaded')
        try:
            self.sequence.setDigital(int(wfm.digi6['idx']), wfm.digi6['pattern'])
        except:
            print('error, digi6 not loaded')
        try:
            self.sequence.setDigital(int(wfm.digi7['idx']), wfm.digi7['pattern'])
        except:
            print('error, digi7 not loaded')

        # update analog channels
        try:
            self.sequence.setAnalog(int(wfm.analog0['idx']), wfm.analog0['pattern'])
        except:
            print('error, analog0 not loaded')
        try:
            self.sequence.setAnalog(int(wfm.analog1['idx']), wfm.analog1['pattern'])
        except:
            print('error, analog1 not loaded')

        # stream
        if (n_runs == 'inf'):
            self.ps.stream(self.sequence, PulseStreamer.REPEAT_INFINITELY)
        else:
            self.ps.stream(self.sequence, n_runs)

    def compress_pattern(self, pattern, ch_type='digi'):
        if ch_type == 'digi':
            for idx, val in enumerate(pattern):
                if idx == 0:
                    new_pattern = [val]
                elif idx > 0:
                    if (pattern[idx][1] == pattern[idx-1][1]):
                        new_time = pattern[idx][0] + new_pattern[-1][0]
                        new_amp = pattern[idx][1]
                        new_pattern[-1] = (new_time, new_amp)
                    else:
                        new_pattern.append(val)
        elif ch_type == 'analog':
            print('warning: "analog" channels not supported in "compress_pattern" function, returning pattern.')
            new_pattern = pattern
        else:
            print('warning, ch_type must be "digi" or "analog" in "compress_pattern" function.')

        return new_pattern
    
    # Set the channel on ps for triggering the laser to be 1 
    def laser_on(self):
        return self.ps.constant(OutputState([self.channel_dict["laser"]], 0.0, 0.0))

    def gate_on(self):
        # Gate AND Laser ON
        self.ps.constant(OutputState([self.channel_dict["gate"], self.channel_dict["laser"]], 0.0, 0.0))
    
    def just_gate_on(self):
        self.ps.constant(OutputState([self.channel_dict["gate"]], 0.0, 0.0))

    def gate_off(self):
        # Gate AND Laser OFF
        self.ps.constant(OutputState([], 0.0, 0.0))

    def just_gate_off(self):
        self.ps.constant(OutputState([], 0.0, 0.0))

    def gate_on_cw_odmr(self):
        # Gate on for the ODMR (CW) experiment
        self.ps.constant(OutputState([self.channel_dict["gate"]], 0.0, 0.0))
    """
    The following function was copied from pulses.py as a test.
    - Rolando
    """
    def SigvsTime(self, sampling_interval):
        seq = self.ps.createSequence()
        
        trig_off = sampling_interval - self.clock_time
        daq_clock_seq = [(trig_off, 0), (self.clock_time, 1)]
        print(daq_clock_seq)
        

        #seq.setDigital(0, daq_clock_seq) # integrator trigger
        seq.setDigital(self.channel_dict["clock"], daq_clock_seq)

        # Makre sure the laser trigger is on while ps is streaming the sequence, this is only for fixing the bug of DLnsec laser
        laser_on_seq = [(sampling_interval, 1)]
        seq.setDigital(self.channel_dict["laser"], laser_on_seq)

        return seq
    
    """ 
    Rolando A. Fimbres G. 8/8/2025

    The following function comes from Tian-Xing's script 'pulses.py' driver; modif. adapt.
    """

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
        seq = self.ps.createSequence()
        
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
    
    """
    Rolando A. Fimbres G. 8/8/2025
    
    The following function comes from Tian-Xing's script 'pulses.py' driver; modif. adapt.
    """

    def Pulsed_ODMR(self, pi_xy, pi_time, runs, init_time, read_time, wait_time, read_wait, seq_gap):
        '''
        Pulsed ODMR sequence by Tengyang and Hanyan, Nov.2024
        Need to test it on an known sample
        '''
        ## Run a pi pulse, then measure the signal
        ## and reference counts from NV.
        #pi_time = self.convert_type(round(pi_time), float) # Check. Maybe this causes the Sig. gen's parser error. 8/12/2025
        # In case another parser error occurs, we could maybe try defining 'pi_time' as:
        pi_time = int(pi_time) # 8/13/2025 changed to int() given that times in pulse patterns are required to be integers.
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
            seq_on = self.ps.createSequence()
            seq_off = self.ps.createSequence()

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

        seqs = self.ps.createSequence()
        seqs = SinglePulsed_ODMR()
        # for i in range(runs):
        #     seqs += SinglePulsed_ODMR()

        return seqs
    
    
    def CW_ODMR_R(self, runs, probe_time, read_time):
    
        seq_on = self.ps.createSequence()
        #seq_off = self.ps.createSequence()
        
        laser_patt = [((probe_time)*runs + read_time, 1)]
        spcm_patt = [(2*probe_time*runs, 1)]
        gate_patt  = [(read_time, 1), (probe_time-read_time, 0), (read_time, 1), (probe_time-read_time, 0)]*runs
        mw_I_patt = [(probe_time-100, self.IQpx[0]), (probe_time+100, self.IQ0[0])]*runs # 100 ns mw buffer time
        mw_Q_patt = [(probe_time-100, self.IQpx[1]), (probe_time+100, self.IQ0[1])]*runs
        sync_patt = [(probe_time-20, 0), (10, 1), (probe_time+10, 0)]*runs
        #gate_patt = [(probe_time, 1)]

        seq_on.setDigital(self.channel_r['laser'], laser_patt)
        seq_on.setDigital(self.channel_r['spcm_gate'], spcm_patt)
        seq_on.setDigital(self.channel_r['sync'], sync_patt)
        seq_on.setDigital(self.channel_r['vrt_gate'], gate_patt)
        seq_on.setAnalog(0, mw_I_patt)
        seq_on.setAnalog(1, mw_Q_patt)
        

        #seq.setAnalog(0, mw_I_patt)
        #seq.setAnalog(1, mw_Q_patt)

        return seq_on

    def Pulsed_ODMR_R(self, pi_xy, iterations, probe_time, read_time):
           # Seq. objects for on and off
           """ seq_on = self.ps.createSequence()
           seq_off = self.ps.createSequence() """

           if pi_xy == 'x':
               self.IQ_ON = self.IQpx
           elif pi_xy == 'y':
               self.IQ_ON = self.IQpy
           else:
               raise ValueError("pi_xy must be 'x' or 'y'!")

           init_laser_time = self.laser_time
           laser_patt = [(init_laser_time, 1), (4000, 0), (init_laser_time, 1), (4000, 0)]
           sync_patt = [(10, 1), (8000-10, 0)]
           gate_patt = [(read_time, 1), (4000-read_time, 0), (read_time, 1), (4000-read_time, 0)]
           mw_I_patt = [(init_laser_time, 0), (probe_time, self.IQ_ON[0]), (4000 - init_laser_time - probe_time, 0)]
           mw_Q_patt = [(init_laser_time, 0), (probe_time, self.IQ_ON[1]), (4000 - init_laser_time - probe_time, 0)]

           pul_seq = self.ps.createSequence()
           pul_seq.setDigital(self.channel_r['laser'], laser_patt*iterations)
           pul_seq.setDigital(self.channel_r['sync'], sync_patt*iterations)
           pul_seq.setDigital(self.channel_r['vrt_gate'], gate_patt*iterations)
           pul_seq.setAnalog(0, mw_I_patt*iterations)
           pul_seq.setAnalog(1, mw_Q_patt*iterations)

           return pul_seq
    


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
            seq_on = self.ps.createSequence()
            seq_off = self.ps.createSequence()

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

        seqs = self.ps.createSequence()
        seqs_total_time = 0
        for mw_time in params:
            seqs += SingleRabi(mw_time)
            seqs_total_time += 2*self.total_time
        print('Rabi sequence created!')
        print('sequence time for 1 run is (ns):',seqs_total_time)
        return seqs

    def ps_reset(self):
        self.ps.reset()

