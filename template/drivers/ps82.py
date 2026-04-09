from pulsestreamer import PulseStreamer, Sequence, OutputState #, getDuration
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
        self.singlet_decay = 600
        self.MW_buffer_time = 200
        self.readout_time = 400
        self.total_time = 0 #update when a pulse sequence is streamed
        self.rest_time_btw_seqs = 1e3 
        ip="169.254.8.2"
        self.ps = PulseStreamer(ip)
        self.last_wfm = []

        """ Some constants by Tian-Xing """
        # 20250423 calibrated by multimeter and PulseStreamer controller, by Tian-Xing
        self.IQ0 = [0.0098, 0.0010]
        self.IQ = self.IQ0

        # 2026-1-7, changed by Rolando to check for Ext Modulation Oveload issue in Signal Gen., Previous values on OneNote 'Signal Generator External Modulation overload'
        self.IQpx = [0.470, 0.080]
        self.IQnx = [-0.474, 0.080]

        self.IQpy = [0.0795, 0.470]
        self.IQny = [0.0795, -0.473]

            # Here, we force the type of time parameters to be an int type in python
    # All times variables here are in unit of ns
    _T = t.TypeVar('_T')

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

    def create_sequence(self):
        return self.ps.createSequence()

    def convert_type(self, arg: t.Any, converter: _T) -> _T:
        return converter(arg)

    def stream(self, seq, n_runs):
        seq = obtain(seq)
        # print('type(seq) is:', type(seq)
        # print('seq is:', seq
        # For cw_odmr_r
        # final = OutputState.ZERO()
        self.ps.stream(seq, n_runs)

    def stream_final(self, seq, n_runs):
        seq = obtain(seq)
        final = OutputState.ZERO()
        self.ps.stream(seq, n_runs, final)

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

    def spcm_laser_on(self):
        # Gate AND Laser ON
        self.ps.constant(OutputState([self.channel_dict["gate"], self.channel_dict["laser"]], 0.0, 0.0))
    
    def just_gate_on(self):
        self.ps.constant(OutputState([self.channel_dict["gate"]], 0.0, 0.0))

    def constant_off(self):
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
    
    """ def plot_seq(self, seq):
        seq.plot() """
    
    def CW_ODMR_R(self, dwell_time, runs):
    
        cw_odmr_seq = self.ps.createSequence()
        #seq_off = self.ps.createSequence()
        
        laser_patt = [(dwell_time, 1)]*runs
        spcm_patt = [(dwell_time, 1)]*runs
        mw_I_patt = [(int(dwell_time/2), self.IQpx[0]), (int(dwell_time/2), self.IQ0[0])]*runs # 100 ns mw buffer time
        mw_Q_patt = [(int(dwell_time/2), self.IQpx[1]), (int(dwell_time/2), self.IQ0[1])]*runs

        cw_odmr_seq.setDigital(self.channel_r['laser'], laser_patt)
        cw_odmr_seq.setDigital(self.channel_r['spcm_gate'], spcm_patt)
        cw_odmr_seq.setAnalog(0, mw_I_patt)
        cw_odmr_seq.setAnalog(1, mw_Q_patt)

        return cw_odmr_seq
    
    """ def cw_seq_duration(self, seq_on):
        return seq_on.getDuration() """

    def New_CW_ODMR_R(self, dwell_time, buffer_time, runs):
        """
        New_CW_ODMR_R
        :param self: Description
        :param dwell_time: Duration of a single measurement point
        :param buffer_time: Buffer time (off) before and after the readout window
        :param runs: Runs of the sequence at the same frequency point

        1/30/2026 - Rolando A. Fimbres G.
        - Laser pattern commented; for the following test we will keep the laser always on at the start
          of the loop and only turning it off after the loop has ended.

        """
        cw_seq = self.ps.createSequence()
        #seq_off = self.ps.createSequence()
        buffer_time = int(buffer_time*1e9) # convert to ns
        
        laser_patt = [(dwell_time, 1)]*runs
        spcm_patt = [(dwell_time, 1)]*runs
        mw_I_patt = [(int(dwell_time/2), self.IQpx[0]), (int(dwell_time/2), self.IQ0[0])]*runs # 100 ns mw buffer time
        mw_Q_patt = [(int(dwell_time/2), self.IQpx[1]), (int(dwell_time/2), self.IQ0[1])]*runs
        read_patt = [(buffer_time, 0), (int(dwell_time/2)-2*buffer_time, 1), (buffer_time, 0), (buffer_time, 0), (int(dwell_time/2)-2*buffer_time, 1), (buffer_time, 0)]*runs

        cw_seq.setDigital(self.channel_r['laser'], laser_patt)
        cw_seq.setDigital(self.channel_r['spcm_gate'], spcm_patt)
        cw_seq.setDigital(self.channel_r['vrt_gate'], read_patt)
        cw_seq.setAnalog(0, mw_I_patt)
        cw_seq.setAnalog(1, mw_Q_patt)

        return cw_seq

    def Pulsed_ODMR_R(self, init_time, wait_time, pi_xy, probe_time, read_wait, read_time):
        # Seq. objects for on and off
        laser_lag = self.laser_lag
        laser_init = int(init_time)
        laser_mw_gap = int(wait_time)
        mw_dur = int(probe_time)
        mw_read_gap = int(read_wait)

        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        elif pi_xy == 'y':
            self.IQ_ON = self.IQpy
        else:
            raise ValueError("pi_xy must be 'x' or 'y'!")

        spcm_gate = [(laser_init + laser_mw_gap + mw_dur + mw_read_gap, 1)]
        laser_patt = [(laser_init, 1), (laser_mw_gap + mw_dur + mw_read_gap, 0)]
        mw_I_patt = [(laser_init + laser_mw_gap, self.IQ0[0]), (mw_dur, self.IQpx[0]), (mw_read_gap, self.IQ0[0])]
        mw_Q_patt = [(laser_init + laser_mw_gap, self.IQ0[1]), (mw_dur, self.IQpx[1]), (mw_read_gap, self.IQ0[1])]
        read_patt = [(laser_lag, 0), (read_time, 1), (laser_init - 2*read_time - laser_lag, 0), (read_time, 1), (laser_mw_gap + mw_dur + mw_read_gap, 0)]
        #sync_patt = [(10, 1)]

        p_odmr_seq1 = self.ps.createSequence()
        p_odmr_seq1.setDigital(self.channel_r["spcm_gate"], spcm_gate)
        p_odmr_seq1.setDigital(self.channel_r["laser"], laser_patt)
        p_odmr_seq1.setDigital(self.channel_r["vrt_gate"], read_patt)
        #p_odmr_seq1.setDigital(ps_sync_ch, sync_patt)
        p_odmr_seq1.setAnalog(0, mw_I_patt)
        p_odmr_seq1.setAnalog(1, mw_Q_patt)

        return p_odmr_seq1
    
    def Pulsed_ODMR_R_2(self, init_time, wait_time, pi_xy, probe_time, read_wait, read_time, seq_gap):
        # Adapt. from TX's Pulsed_ODMR
        # Seq. objects for on and off
        self.laser_lag = 60
        laser_init = int(init_time)
        laser_mw_gap = int(wait_time)
        mw_dur = int(self.convert_type(round(probe_time), float))
        mw_read_gap = int(read_wait)

        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        elif pi_xy == 'y':
            self.IQ_ON = self.IQpy
        else:
            raise ValueError("pi_xy must be 'x' or 'y'!")
        
        self.IQ_OFF = self.IQ0
        
        def SinglePulsed_ODMR_R():

            pad_time = 200

            laser_off1 = laser_mw_gap + mw_dur + self.MW_buffer_time + mw_read_gap 
            laser_off2 = 200 + pad_time + seq_gap
            self.total_time = laser_init + laser_off1 + read_time + laser_off2

            # mw I & Q off windows
            iq_off1 = self.laser_lag + laser_init + laser_mw_gap
            iq_off2 = self.MW_buffer_time + mw_read_gap + read_time + laser_off2 - self.laser_lag

            # Readout windows
            read_off1 = self.laser_lag + laser_init + laser_off1
            read_off2 = laser_off2 - self.laser_lag

            # Creation of Sequence
            seq_on = self.ps.createSequence()
            seq_off = self.ps.createSequence()

            spcm_gate = [(self.total_time, 1)]

            laser_patt = [
                (laser_init, 1),
                (laser_off1, 0),
                (read_time, 1),
                (laser_off2, 0)
                ]
            
            mw_I_patt_ON = [
                (iq_off1, self.IQ_OFF[0]),
                (mw_dur, self.IQ_ON[0]),
                (iq_off2, self.IQ_OFF[0])
                ]

            mw_Q_patt_ON = [
                (iq_off1, self.IQ_OFF[1]),
                (mw_dur, self.IQ_ON[1]),
                (iq_off2, self.IQ_OFF[1])
                ]
            
            mw_I_patt_OFF = [
                (iq_off1, self.IQ_OFF[0]),
                (mw_dur, self.IQ_OFF[0]),
                (iq_off2, self.IQ_OFF[0])
                ]

            mw_Q_patt_OFF = [
                (iq_off1, self.IQ_OFF[1]),
                (mw_dur, self.IQ_OFF[1]),
                (iq_off2, self.IQ_OFF[1])
                ]

            read_patt = [
                (read_off1, 0),
                (read_time, 1),
                (read_off2, 0)
                ]
            #sync_patt = [(10, 1)]

            # Sequence ON
            seq_on.setDigital(self.channel_r["spcm_gate"], spcm_gate)
            seq_on.setDigital(self.channel_r["laser"], laser_patt)
            seq_on.setDigital(self.channel_r["vrt_gate"], read_patt)
            seq_on.setAnalog(0, mw_I_patt_ON)
            seq_on.setAnalog(1, mw_Q_patt_ON)
            # Sequence OFF
            seq_off.setDigital(self.channel_r["spcm_gate"], spcm_gate)
            seq_off.setDigital(self.channel_r["laser"], laser_patt)
            seq_off.setDigital(self.channel_r["vrt_gate"], read_patt)
            seq_off.setAnalog(0, mw_I_patt_OFF)
            seq_off.setAnalog(1, mw_Q_patt_OFF)

            return seq_on + seq_off
        
        seqs = self.ps.createSequence()
        seqs = SinglePulsed_ODMR_R()

        return seqs

    def Pulsed_ODMR_R_3(self, init_time, wait_time, pi_xy, mw_time, read_wait, read_time):
        
        self.laser_lag = 90
        # opt_lag = self.laser_lag + lag_timing
        init_time = int(init_time)
        wait_time = int(wait_time)
        mw_time = int(mw_time)
        read_wait = int(read_wait)
        read_time = int(read_time)
        
        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        elif pi_xy == 'y':
            self.IQ_ON = self.IQpy
        else:
            raise ValueError("pi_xy must be 'x' or 'y'!")
        self.IQ_OFF = self.IQ0

        def single_pulsed_odmr():
            seq_on = self.ps.createSequence()
            #seq_off = self.ps.createSequence()

            cycle_duration = init_time + wait_time + mw_time + read_wait + init_time
            laser_off = cycle_duration - 2*init_time
            mw_off1 = init_time + wait_time
            mw_off2 = read_wait + init_time
            read_off1 = init_time - 2*read_time
            read_off2 = laser_off 

            spcm_gate = [(cycle_duration +  laser_off, 1)]
            laser_patt = [(init_time, 1), (laser_off, 0), (init_time, 1), (laser_off, 0)]
            mw_I_patt_ON = [(mw_off1, self.IQ_OFF[0]), (mw_time, self.IQ_ON[0]), (mw_off2, self.IQ_OFF[0]), (laser_off, self.IQ_OFF[0])]
            mw_Q_patt_ON = [(mw_off1, self.IQ_OFF[1]), (mw_time, self.IQ_ON[1]), (mw_off2, self.IQ_OFF[1]), (laser_off, self.IQ_OFF[1])]
            #mw_I_patt_OFF = [(mw_off1, self.IQ_OFF[0]), (mw_time, self.IQ_OFF[0]), (mw_off2, self.IQ_OFF[0])]
            #mw_Q_patt_OFF = [(mw_off1, self.IQ_OFF[1]), (mw_time, self.IQ_OFF[1]), (mw_off2, self.IQ_OFF[1])]
            read_patt = [(read_time, 1), (read_off1, 0), (read_time, 1), (read_off2, 0), (read_time, 1), (read_off1, 0), (read_time, 1), (read_off2, 0)]

            # Sequence ON
            seq_on.setDigital(self.channel_r["spcm_gate"], spcm_gate)
            seq_on.setDigital(self.channel_r["laser"], laser_patt)
            seq_on.setDigital(self.channel_r["vrt_gate"], read_patt)
            seq_on.setAnalog(0, mw_I_patt_ON)
            seq_on.setAnalog(1, mw_Q_patt_ON)
            

            return seq_on 
        
        seqs = self.ps.createSequence()
        seqs = single_pulsed_odmr()

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
    
    def calibration_pulsed(self, init_time, wait_time, pi_xy, time_resolution):
        """
        Rolando A. Fimbres G. 9/22/2025
        This function creates a calibration sequence for the pulsed ODMR experiment, where we only apply the initialization laser and the MW pulse of duration (wait_times) without the readout laser. This can be used to calibrate the pi time on x and y axes.
        """
        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        elif pi_xy == 'y':
            self.IQ_ON = self.IQpy
        else:
            raise ValueError("pi_xy must be 'x' or 'y'!")
        
        laser_init = int(init_time)
        wait_time = int(wait_time)
        time_btw_seqs = 1e3 # 1 us gap between sequences for reinitialization, can be adjusted if needed
        time_resolution = int(time_resolution) # time resolution for the sequence, can be adjusted if needed
        single_seq_duration = laser_init + wait_time #+ time_btw_seqs
        read_pulses =  int(single_seq_duration/time_resolution) # number of read pulses we can fit in one sequence, so we want to have multiple read pulses during the sequence to make sure we can capture the signal during the readout window.

        seq_off = self.ps.createSequence() # During this sequence, the laser is on but the MW is off.
        seq_on = self.ps.createSequence()  # During this sequence, the laser is on and the MW is on for 'wait_time' duration.      
    
        spcm_gate = [(wait_time + laser_init, 1)]
        laser_patt = [(wait_time, 0), (laser_init, 1), (time_btw_seqs, 0)]
        #read_patt =  [(time_resolution, 1)]*read_pulses + [(time_btw_seqs, 0)] # read pulses during the sequence, followed by a gap for reinitialization
        mw_I_on_patt = [(wait_time, self.IQ_ON[0]), (laser_init, self.IQ0[0]), (time_btw_seqs, self.IQ0[0])]
        mw_Q_on_patt = [(wait_time, self.IQ_ON[1]), (laser_init, self.IQ0[1]), (time_btw_seqs, self.IQ0[1])]
        mw_I_off_patt = [(wait_time, self.IQ0[0]), (laser_init, self.IQ0[0]), (time_btw_seqs, self.IQ0[0])]
        mw_Q_off_patt = [(wait_time, self.IQ0[1]), (laser_init, self.IQ0[1]), (time_btw_seqs, self.IQ0[1])]

        seq_on.setDigital(self.channel_r["spcm_gate"], spcm_gate)
        seq_on.setDigital(self.channel_r["laser"], laser_patt)
        #seq_on.setDigital(self.channel_r["vrt_gate"], read_patt)
        seq_on.setAnalog(0, mw_I_on_patt)
        seq_on.setAnalog(1, mw_Q_on_patt)
        seq_off.setDigital(self.channel_r["spcm_gate"], spcm_gate)
        seq_off.setDigital(self.channel_r["laser"], laser_patt)
        #seq_off.setDigital(self.channel_r["vrt_gate"], read_patt)
        seq_off.setAnalog(0, mw_I_off_patt)
        seq_off.setAnalog(1, mw_Q_off_patt)

        return seq_on + seq_off
    
    def Calibrate_LaserLag_R(self, params, buffer_time, read_window, laser_window):

        """
        Version adapted from Tian-Xing's script 'pulses.py' driver; modif. adapt. by Rolando A. Fimbres G. 3/9/2026
        """
        
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
            read_off1 = read_time
            readout = read_window 
            read_off2 = longest_time - read_time - read_window
            #int_trig_off3 = (self.trig_delay - self.clock_time) + pad_time + self.rest_time_btw_seqs       

            # Total time
            self.total_time = laser_off1 + laser_window + laser_off2

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.ps.createSequence()

            # define sequence structure for laser
            spcm_gate = [(self.total_time, 1)]
            laser_seq = [(laser_off1, 0), (laser_window, 1), (laser_off2, 0)]

            # define sequence structure for integrator trigger
            #int_trig_seq = [(int_trig_off1, 0), (self.clock_time, 1), (int_trig_off2, 0)]
            read_seq = [(read_off1, 0), (readout, 1), (read_off2, 0)]
            
            seq.setDigital(self.channel_r["spcm_gate"], spcm_gate) # spcm gate
            seq.setDigital(self.channel_r["laser"], laser_seq) # laser 
            seq.setDigital(self.channel_r["vrt_gate"], read_seq) # integrator trigger

            return seq

        seqs = self.ps.createSequence()

        for read in params:
            seqs += SingleLag(read)

        return seqs

    def Calibrate_Initialize_R(self, params, init_pulse_length):
        
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

            # define sequence structure for laser and spcm
            spcm_gate = [(self.initialize + laser_off1 + laser_off2, 1)]
            laser_seq = [(laser_off1, 0), (self.initialize, 1), (laser_off2, 0)]

            # define sequence structure for the readout
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
    
    def Rabi_R(self, tau_times, pi_xy, init_time, read_time, wait_time, read_wait, seq_gap): # Rolando A. Fimbres G. 9/22/2025
        '''
        Rabi sequence
        init_time: laser duration for initialize the qubit
        read_time: laser duration for readout the qubit
        wait_time: waiting duration after the initialization laser
        read_wait: waiting duration before the readout laser
        seq_gap: waiting time after each sequence is done, for reinitialization. If needed
        '''
        
        #laser_lag = int(round(self.laser_lag))
        laser_init = int(round(init_time))
        laser_mw_gap = int(round(wait_time))
        read_time = int(round(read_time))
        read_wait = int(round(read_wait))
        seq_gap = int(round(seq_gap))
        self.laser_lag = 60 # hardcoded laser lag for now, can be adjusted if needed

        longest_time = self.convert_type(round(max(tau_times)), float)
        
        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        elif pi_xy == 'y':
            self.IQ_ON = self.IQpy
        else:
            raise ValueError("pi_xy must be 'x' or 'y'!")
        
        self.IQ_OFF = self.IQ0

        def SingleRabi_R(mw_dur):

            mw_dur = int(round(mw_dur))

            # Definition of timings
            pad_time = longest_time - mw_dur  # padding time to equalize duration of every run (for different MW_on durations)
            # Laser
            laser_off1 = laser_mw_gap + mw_dur + self.MW_buffer_time + read_wait
            laser_off2 = 200 + pad_time + seq_gap
            # Total Time
            self.total_time = laser_init + laser_off1 + read_time + laser_off2
            # MW
            iq_off1 = self.laser_lag + laser_init + laser_mw_gap
            iq_off2 = self.MW_buffer_time + read_wait + read_time + laser_off2 - self.laser_lag
            # Readout
            read_off1 = self.laser_lag + laser_init + laser_off1
            read_off2 = laser_off2 - self.laser_lag

            #####################
            # Create Pulsed Seq.#
            #####################

            # create sequence objects for MW on and off blocks
            seq_on = self.ps.createSequence()
            seq_off = self.ps.createSequence()

            spcm_gate = [(self.total_time, 1)]
            
            laser_patt = [
                (laser_init, 1),
                (laser_off1, 0),
                (read_time, 1),
                (laser_off2, 0)
            ]

            mw_I_ON_patt = [
                (iq_off1, self.IQ_OFF[0]), #0.0098
                (mw_dur, self.IQ_ON[0]),
                (iq_off2, self.IQ_OFF[0]) #0.0098
            ]
            
            mw_Q_ON_patt = [
                (iq_off1, self.IQ_OFF[1]),
                (mw_dur, self.IQ_ON[1]),
                (iq_off2, self.IQ_OFF[1]) #0.08
            ]

            mw_I_OFF_patt = [
                (iq_off1, self.IQ_OFF[0]),
                (mw_dur, self.IQ_OFF[0]),
                (iq_off2, self.IQ_OFF[0])
            ]
            
            mw_Q_OFF_patt = [
                (iq_off1, self.IQ_OFF[1]),
                (mw_dur, self.IQ_OFF[1]),
                (iq_off2, self.IQ_OFF[1])
            ]

            read_patt = [
                (read_off1, 0),
                (read_time, 1), 
                (read_off2, 0)
            ]

            # Sequence ON
            seq_on.setDigital(self.channel_r["spcm_gate"], spcm_gate)
            seq_on.setDigital(self.channel_r["laser"], laser_patt)
            seq_on.setDigital(self.channel_r["vrt_gate"], read_patt)
            seq_on.setAnalog(0, mw_I_ON_patt)
            seq_on.setAnalog(1, mw_Q_ON_patt)
            # Sequence OFF
            seq_off.setDigital(self.channel_r["spcm_gate"], spcm_gate)
            seq_off.setDigital(self.channel_r["laser"], laser_patt)
            seq_off.setDigital(self.channel_r["vrt_gate"], read_patt)
            seq_off.setAnalog(0, mw_I_OFF_patt)
            seq_off.setAnalog(1, mw_Q_OFF_patt)

            return seq_on + seq_off

        seqs = self.ps.createSequence()
        seqs_total_time = 0   
        for t in tau_times:
            seqs += SingleRabi_R(t)
            seqs_total_time += 2*self.total_time
        print('Rabi sequence created!')
        print('sequence time for 1 run is (ns):',seqs_total_time) 
        return seqs

    def cw_odmr_test(self, runs, probe_time):

        #read_time = int(probe_time) - 2 

        cw_seq = self.ps.createSequence()
        laser_patt = [(int(probe_time)*2, 1)]*runs
        spcm_patt = [(int(probe_time)*2, 1)]*runs
        mw_I_patt = [(int(probe_time), self.IQpx[0]), (int(probe_time), self.IQ0[0])]*runs # 100 ns mw buffer time
        mw_Q_patt = [(int(probe_time), self.IQpx[1]), (int(probe_time), self.IQ0[1])]*runs
        read_patt = [(int(probe_time)-2, 1), (2, 0), (int())]*runs

        cw_seq.setDigital(self.channel_r['laser'], laser_patt)
        cw_seq.setDigital(self.channel_r['spcm_gate'], spcm_patt)
        cw_seq.setAnalog(0, mw_I_patt)
        cw_seq.setAnalog(1, mw_Q_patt)

        return cw_seq

    def rabi_R2(self, tau, pi_xy, init_time, read_time, wait_time, read_wait):
        '''
        Rolando A. Fimbres G. 10/2/2025
        This approach uses a single Rabi sequence that will be streamed per tau_time value.
        ------------------------------------------------------------------------------------
        tau: value from an array of varying MW pulse durations (mw_times or tau_times)
        pi_xy: axis of rotation for the MW pulse, either 'x' or 'y'
        init_time: laser duration for initialize the qubit
        read_time: laser duration for readout the qubit
        wait_time: waiting duration after the initialization laser
        read_wait: waiting duration before the readout laser
        '''
        ## Run a MW pulse of varying duration, then measure the signal
        ## and reference counts from NV.
        # self.total_time = 0
        laser_lag = self.laser_lag
        laser_init = int(init_time)
        laser_mw_gap = int(wait_time)
        tau = int(tau)
        mw_read_gap = int(read_wait - tau)
        ## we can measure the pi time on x and on y.
        ## they should be the same, but they technically
        ## have different offsets on our pulse streamer.
        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        elif pi_xy == 'y':
            self.IQ_ON = self.IQpy
        else:
            raise ValueError("pi_xy must be 'x' or 'y'!")
        
        spcm_gate = [(int(2*laser_init + 2*laser_mw_gap + 2*tau + 2*mw_read_gap), 1)]
        laser_patt = [(laser_init, 1), (laser_mw_gap + tau + mw_read_gap, 0), (laser_init, 1), (laser_mw_gap + tau + mw_read_gap, 0)]
        mw_I_patt = [(laser_init + laser_mw_gap, self.IQ0[0]), (tau, self.IQpx[0]), (mw_read_gap + laser_init + laser_mw_gap + tau + mw_read_gap, self.IQ0[0])]
        mw_Q_patt = [(laser_init + laser_mw_gap, self.IQ0[1]), (tau, self.IQpx[1]), (mw_read_gap + laser_init + laser_mw_gap + tau + mw_read_gap, self.IQ0[1])]
        read_patt = [(laser_lag, 0), (read_time, 1), (laser_init - read_time + laser_mw_gap + tau + mw_read_gap - laser_lag, 0), (read_time, 1), (laser_init + laser_mw_gap + tau + mw_read_gap - read_time, 0)]

        single_rabi = self.ps.createSequence()
        single_rabi.setDigital(self.channel_r["spcm_gate"], spcm_gate)
        single_rabi.setDigital(self.channel_r["laser"], laser_patt)
        single_rabi.setDigital(self.channel_r["vrt_gate"], read_patt)
        single_rabi.setAnalog(0, mw_I_patt)
        single_rabi.setAnalog(1, mw_Q_patt)

        return single_rabi

    def Diff_T1_R(self, params, tau_balance, pi_xy, pi_time, init_time, read_time, seq_gap):#the wait time here is used to replace the self.singlet_decay
        '''
        Rolando's adaptation of Tian-Xing Zheng's Differential T1 sequence
        1/19/2026
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

            #(DAQ trigger) to be Time tagger windows
            read_off1 = init_laser_time + laser_off1 + self.laser_lag
            read_readout = self.readout_time 
            read_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows
            iq_off1 = init_laser_time + self.singlet_decay + self.laser_lag
            #iq_off1 = init_laser_time + wait_time + self.laser_lag
            iq_off2 = tau_time + self.readout_time + laser_off2 - self.laser_lag

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq_on = self.ps.createSequence()
            seq_off = self.ps.createSequence()

            # define sequence for spcm gate
            spcm_gate = [(self.total_time, 1)]

            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]

            # define sequence structure for TimeTagger (CBM) trigger
            readout_trig_seq = [(read_off1, 0), (read_readout, 1), (read_off2, 0)]

            # define sequence structure for MW I and Q when MW = ON
            mw_I_on_seq = [(iq_off1, self.IQ0[0]), self.Pi(pi_xy, pi_time)[0], (iq_off2, self.IQ0[0])]
            mw_Q_on_seq = [(iq_off1, self.IQ0[1]), self.Pi(pi_xy, pi_time)[1], (iq_off2, self.IQ0[1])]
            # when MW = OFF
            mw_I_off_seq = [(iq_off1, self.IQ0[0]), (pi_time, self.IQ0[0]), (iq_off2, self.IQ0[0])]
            mw_Q_off_seq = [(iq_off1, self.IQ0[1]), (pi_time, self.IQ0[1]), (iq_off2, self.IQ0[1])]

            # assign sequences to respective channels for seq_on
            seq_on.setDigital(self.channel_r["spcm_gate"], spcm_gate) # spcm gate
            seq_on.setDigital(self.channel_r["laser"], laser_seq) # laser
            seq_on.setDigital(self.channel_r["vrt_gate"], readout_trig_seq) # integrator trigger
            seq_on.setAnalog(0, mw_I_on_seq) # mw_I
            seq_on.setAnalog(1, mw_Q_on_seq) # mw_Q

            # assign sequences to respective channels for seq_off
            seq_off.setDigital(self.channel_r["spcm_gate"], spcm_gate) # spcm gate   
            seq_off.setDigital(self.channel_r["laser"], laser_seq) # laser
            seq_off.setDigital(self.channel_r["vrt_gate"], readout_trig_seq) # integrator trigger
            seq_off.setAnalog(0, mw_I_off_seq) # mw_I
            seq_off.setAnalog(1, mw_Q_off_seq) # mw_Q

            return seq_on + seq_off

        seqs = self.ps.createSequence()
            
        seqs_total_time = 0
        for tau in params:
            seqs += SingleDiff_T1(tau, tau_balance)
            seqs_total_time += 2*self.total_time
        print('Diff T1 sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)

        return seqs
    
    def Diff_T1rho_R(self, params, tau_balance, pihalf_y, init_time, read_time, seq_gap):
        '''
        By Rolando 1/19/2026
        Adaptation of Tian-Xing Zheng's Differential T1rho sequence

        -(Developed by Tian-Xing Zheng, Aug.2024
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


            #(DAQ trigger) to be Time tagger windows
            read_off1 = init_laser_time + laser_off1 + self.laser_lag
            read_readout = self.readout_time 
            read_off2 = laser_off2 - self.laser_lag

            # mw I & Q off windows
            iq_off1 = self.laser_lag + init_laser_time + self.singlet_decay
            iq_off2 = self.MW_buffer_time + self.readout_time + laser_off2 - self.singlet_decay

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # create sequence objects for MW on and off blocks
            seq = self.ps.createSequence()
            seq_ref = self.ps.createSequence()

            # define sequence for spcm gate
            spcm_gate = [(self.total_time, 1)]

            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]

            # define sequence structure for DAQ trigger
            daq_clock_seq = [(read_off1, 0), (read_readout, 1), (read_off2, 0)]

            # define sequence structure for MW I and Q 
            mw_I_seq = [(iq_off1, self.IQ0[0]), self.PiHalf('y', pihalf_y)[0], self.PiHalf('x', tau_time)[0], self.PiHalf('y', pihalf_y)[0], (iq_off2, self.IQ0[0])]
            mw_Q_seq = [(iq_off1, self.IQ0[1]), self.PiHalf('y', pihalf_y)[1], self.PiHalf('x', tau_time)[1], self.PiHalf('y', pihalf_y)[1], (iq_off2, self.IQ0[1])]
            
            mw_I_seq_ref = [(iq_off1, self.IQ0[0]), self.PiHalf('y', pihalf_y)[0], self.PiHalf('x', tau_time)[0], self.PiHalf('-y', pihalf_y)[0], (iq_off2, self.IQ0[0])]
            mw_Q_seq_ref = [(iq_off1, self.IQ0[1]), self.PiHalf('y', pihalf_y)[1], self.PiHalf('x', tau_time)[1], self.PiHalf('-y', pihalf_y)[1], (iq_off2, self.IQ0[1])]

            # assign sequences to respective channels for seq_on
            seq.setDigital(self.channel_r["spcm_gate"], spcm_gate) # spcm gate
            seq.setDigital(self.channel_r["laser"], laser_seq) # laser
            seq.setDigital(self.channel_r["vrt_gate"], daq_clock_seq) # integrator trigger
            seq.setAnalog(0, mw_I_seq) # mw_I
            seq.setAnalog(1, mw_Q_seq) # mw_Q

            # assign sequences to respective channels for seq_off
            seq_ref.setDigital(self.channel_r["spcm_gate"], spcm_gate) # spcm gate
            seq_ref.setDigital(self.channel_r["laser"], laser_seq) # laser
            seq_ref.setDigital(self.channel_r["vrt_gate"], daq_clock_seq) # integrator trigger
            seq_ref.setAnalog(0, mw_I_seq_ref) # mw_I
            seq_ref.setAnalog(1, mw_Q_seq_ref) # mw_Q

            return seq + seq_ref

        seqs = self.ps.createSequence()
        
        seqs_total_time = 0
        for tau in params:
            seqs += SingleDiff_T1rho(tau, tau_balance)
            seqs_total_time += 2*self.total_time
        print('Diff T1_rho sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)

        return seqs

    def Optical_T1_R(self, params, tau_balance, init_time, read_time, seq_gap ,forNV=True):
        '''
        By Rolando A. Fimbres G. 1/19/2026, modification of Tian-Xing Zheng's Optical T1 sequence:

        - Optical T1 sequence with integrator
        (By Tian-Xing Zheng and Tengyang Ruan Sept.2024. Modified from Evan's code)
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

            #(DAQ trigger) to be Time tagger windows
            read_off1 = init_laser_time + laser_off1 + self.laser_lag
            read_readout = self.readout_time 
            read_off2 = laser_off2 - self.laser_lag

            '''
            CONSTRUCT PULSE SEQUENCE
            '''
            # define sequence for spcm gate
            spcm_gate = [(self.total_time, 1)]

            # create sequence objects
            seq = self.ps.createSequence()

            # define sequence structure for laser
            laser_seq = [(init_laser_time, 1), (laser_off1, 0), (self.readout_time, 1), (laser_off2, 0)]

            # define sequence structure for TimeTagger (CBM) trigger
            readout_trig_seq = [(read_off1, 0), (read_readout, 1), (read_off2, 0)]

            # print("LASER SEQ: ", laser_seq)

            # assign sequences to respective channels for seq_on
            seq.setDigital(self.channel_r["spcm_gate"], spcm_gate) # spcm gate
            seq.setDigital(self.channel_r["laser"], laser_seq) # laser
            seq.setDigital(self.channel_r["vrt_gate"], readout_trig_seq) # integrator trigger            

            return seq 

        seqs = self.ps.createSequence()
        seqs_total_time = 0
        for tau in params:
            seqs += SingleOptical_T1(tau, tau_balance, seq_gap, forNV)
            seqs_total_time += 1*self.total_time

        print('Optical T1 sequence created!')
        print('sequence time for 1 run is (ns):', seqs_total_time)

        return seqs


    def T1_R(self, pi_dur, tau_times, pi_xy, init_time, read_time, wait_time):
        '''
        T1 sequence
        init_time: laser duration for initialize the qubit
        read_time: laser duration for readout the qubit
        wait_time: waiting duration after the initialization laser
        read_wait: waiting duration before the readout laser
        seq_gap: waiting time after each sequence is done, for reinitialization. If needed
        '''
        ## Run a MW pulse of varying duration, then measure the signal
        laser_lag = self.laser_lag
        laser_init = int(init_time)
        laser_mw_gap = int(wait_time)
        mw_dur = int(pi_dur)

        if pi_xy == 'x':
            self.IQ_ON = self.IQpx
        elif pi_xy == 'y':
            self.IQ_ON = self.IQpy
        else:
            raise ValueError("pi_xy must be 'x' or 'y'!")

        def Single_T1(tau_times):
           
            spcm_gate = [(int(2*laser_init + 2*laser_mw_gap + 2*mw_dur + 2*tau_times)    , 1)]
            laser_patt = [(laser_init, 1), (laser_mw_gap + mw_dur + tau_times, 0), (laser_init, 1), (laser_mw_gap + mw_dur + tau_times, 0)]
            mw_I_patt = [(laser_init + laser_mw_gap, self.IQ0[0]), (mw_dur, self.IQpx[0]), (tau_times + laser_init + laser_mw_gap + mw_dur + tau_times, self.IQ0[0])]
            mw_Q_patt = [(laser_init + laser_mw_gap, self.IQ0[1]), (mw_dur, self.IQpx[1]), (tau_times + laser_init + laser_mw_gap + mw_dur + tau_times, self.IQ0[1])]
            read_patt = [(laser_lag, 0), (read_time, 1), (laser_init - read_time + laser_mw_gap + mw_dur + tau_times, 0), (read_time, 1), (laser_init - read_time + laser_mw_gap + mw_dur + tau_times, 0)]

            single_T1 = self.ps.createSequence()
            single_T1.setDigital(self.channel_r["spcm_gate"], spcm_gate)
            single_T1.setDigital(self.channel_r["laser"], laser_patt)
            single_T1.setDigital(self.channel_r["vrt_gate"], read_patt)
            single_T1.setAnalog(0, mw_I_patt)
            single_T1.setAnalog(1, mw_Q_patt)

            return single_T1

        full_T1_seq = self.ps.createSequence()

        for t in tau_times:
            tau = int(t)
            mw_read_gap = int(tau)
            T1_seq = Single_T1(mw_read_gap)
            full_T1_seq += T1_seq

        return full_T1_seq

    def ps_reset(self):
        self.ps.reset()

