import numpy as np
import pandas as pd
from lantz.core import Driver
from lantz.drivers.swabian.pulsestreamer.lib.pulse_streamer_grpc import PulseStreamer
from lantz.drivers.swabian.pulsestreamer.lib.Sequence import Sequence
from lantz import Q_
from lantz import Action, Feat, DictFeat, ureg



class Pulses(Driver):

    default_digi_dict = {"clock": 0, "blue": 1, "SRS": 2, "VSG":3, "gate1": 4, "gate2": 5, "gate3": 6, "laser": 7, "": None}
    rev_dict = {0: "clock", 1: "blue", 2: "SRS", 3: "VSG", 4: "gate1", 5: "gate2", 6: "gate3", 7: "laser", 8: "I", 9: "Q"}
    
## Should change aom to laser
    def __init__(self, channel_dict = default_digi_dict, rev_dict = rev_dict, laser_time = 3.5*Q_(1,"us"), 
                 aom_lag = .73*Q_(1,"us"), readout_time = .4*Q_(1,"us"), laser_buf = .100*Q_(1,"us"), 
                 read_time = 50*Q_(1, "us"), clock_time = Q_(0.1, "us"), IQ=[.4,0], ip="10.135.70.189"):
        """
        :param channel_dict: Dictionary of which channels correspond to which instr controls
        :param readout_time: Laser+gate readout time in us
        :param laser_time: Laser time to reinit post readout
        :param aom_lag: Delay in AOM turning on
        :param laser_buf: Buffer after laser turns off
        :param IQ: IQ modulation/analog channels
        """
        super().__init__()
        self.channel_dict = {"clock": 0, "blue": 1, "SRS": 2, "VSG":3, "gate1": 4, "gate2": 5, "gate3": 6, "laser": 7, "": None}
        #self.channel_dict = {"laser": 0, "blue": 1, "SRS": 2, "VSG":3, "gate1": 4, "gate2": 5, "gate3": 6, "gate4": 7, "": None}
        self._reverse_dict = rev_dict
        self.laser_time = int(round(laser_time.to("ns").magnitude))
        self.aom_lag = int(round(aom_lag.to("ns").magnitude))
        self.readout_time = int(round(readout_time.to("ns").magnitude))
        self.laser_buf = int(round(laser_buf.to("ns").magnitude))
        self.read_time = int(round(read_time.to("ns").magnitude))
        self.clock_time = int(round(clock_time.to("ns").magnitude))
        #self._normalize_IQ(IQ)
        self.Pulser = PulseStreamer(ip)
        print('creating sequence')
        self.sequence = Sequence()
        print('done creating sequence')
        self.latest_streamed = pd.DataFrame({})
        self.total_time = -1 #update when a pulse sequence is streamed

## Should change it according to crosstalk between I and Q. If no crosstalk should be 0.5 and 0
        self.IQ0 = [0,0]

    @Feat()
    def has_sequence(self):
        """
        Has Sequence
        """
        return self.Pulser.hasSequence()
    
    @Action()
    def laser_on(self):
        return self.Pulser.constant((0, [7], 0.0, 0.0))

    def stream(self,seq,n_runs):
        self.latest_streamed = self.convert_sequence(seq)
        self.Pulser.stream(seq,n_runs)

    def clocksource(self,clk_src):
        self.Pulser.selectClock(clk_src)

    def _normalize_IQ(self, IQ):
        self.IQ = IQ/(2.5*np.linalg.norm(IQ))

    def convert_sequence(self, seqs):
         # 0-7 are the 8 digital channels
         # 8-9 are the 2 analog channels
        data = {}
        time = -0.01
        for seq in seqs:
            col = np.zeros(10)
            col[seq[1]] = 1
            col[8] = seq[2]
            col[9] = seq[3]
            init_time = time + 0.01
            data[init_time] = col
            time = time + seq[0]
            #data[prev_time_stamp + 0.01] = col
            data[time] = col
            #prev_time_stamp = seq[0]
        dft = pd.DataFrame(data)
        df = dft.T
        sub_df = df[list(self._reverse_dict.keys())]
        fin = sub_df.rename(columns = self._reverse_dict)
        return fin

    def minimum_rabi(self):
        laser_lag1 = \
            [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
        clock1 = \
            [(self.clock_time, [self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
        read = \
            [(self.readout_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
        between_read = \
            [(self.laser_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
        clock2 = \
            [(self.clock_time, [self.channel_dict["clock"]], *self.IQ0)]
        laser_lag2 = \
            [(self.aom_lag - self.clock_time + self.laser_buf, [], *self.IQ0)]
        seq = laser_lag1 + clock1 + read + clock1 + between_read + clock1 + read + clock2 + laser_lag2
        self.total_time = (self.laser_time + 2*self.aom_lag + 2*self.readout_time) + self.laser_buf
        return seq
        