import numpy as np
import pandas as pd
from lantz.core import Driver
from lantz.drivers.swabian.pulsestreamer.lib.pulse_streamer_grpc import PulseStreamer
from lantz.drivers.swabian.pulsestreamer.lib.Sequence import Sequence
from lantz import Q_
from lantz import Action, Feat, DictFeat, ureg



class Pulses(Driver):

    
    #default_digi_dict = {"laser": "ch0", "offr_laser": "ch1", "EOM": "ch4", "CTR": "ch5", "switch": "ch6", "gate": "ch7", "": None}
    #default_digi_dict = {"laser": 0, "blue": 1, "SRS": 2, "VSG":3, "gate1": 4, "gate2": 5, "gate3": 6, "gate4": 7, "": None}
    #default_digi_dict = {"gate4": 0, "blue": 1, "SRS": 2, "VSG":3, "gate1": 4, "gate2": 5, "gate3": 6, "laser": 7, "": None}
    default_digi_dict = {"clock": 0, "blue": 1, "SRS": 2, "VSG":3, "gate1": 4, "gate2": 5, "gate3": 6, "laser": 7, "": None}
    rev_dict = {0: "clock", 1: "blue", 2: "SRS", 3: "VSG", 4: "gate1", 5: "gate2", 6: "gate3", 7: "laser", 8: "I", 9: "Q"}
    #rev_dict = {0: "laser", 1: "blue", 2: "SRS", 3: "VSG", 4: "gate1", 5: "gate2", 6: "gate3", 7: "gate4", 8: "I", 9: "Q"}
    
## Should change aom to laser
    def __init__(self, channel_dict = default_digi_dict, rev_dict = rev_dict, laser_time = 3.5*Q_(1,"us"), 
                 aom_lag = .73*Q_(1,"us"), aom_ramp = .15*Q_(1,"us"), readout_time = .4*Q_(1,"us"), 
                 laser_buf = .100*Q_(1,"us"), read_time = 50*Q_(1, "us"), clock_time = Q_(0.1, "us"),
                 IQ=[.4,0], ip="10.135.70.189"):
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
        self.aom_ramp = int(round(aom_ramp.to("ns").magnitude))
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
        self.IQ0 = [0,0]#[-.0177,-.0045]
        self.IQ = self.IQ0
        self.IQpx = [0.5,0]#[0.4,-.005]
        self.IQnx = [-0.5,0]#[-.435,-.0045]
        self.IQpy = [0,0.5]#[-.0178,.4195]

    @Feat()
    def has_sequence(self):
        """
        Has Sequence
        """
        return self.Pulser.hasSequence()

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

    #IQ mod testing (getting side peaks when modulating IQ with a sinewave- 
                     #run with a sepectrum analyzer to see the peaks and ensure IQ is working well)
    def IQ_test(self, params, T):
        period = int(round(T.to("ns").magnitude))
        def single_test(time):
            stream = \
                [(1, [], 0,.4*np.cos(2*np.pi*time/period))]
            self.total_time = 1
            return stream
        seqs = [single_test(int(round(t))) for t in params]
        return seqs

    # one clock tick
    def Clock_tick(self):
        #clock_time = int(round(params).to('ns').magnitude)
        clock = \
            [(self.tick_time, [self.channel_dict["clock"]], *self.IQ0)]
        return clock
    
    #AOM lag testing (jonathan)
    def AOM_lag(self, params):
        latest_time = int(round(params["stop"].to("ns").magnitude))
        end = latest_time + self.gate_time
        def single_lag(gate_start):
            if gate_start + self.gate_time < self.laser_start:
                wait1 = \
                    [(gate_start, [], *self.IQ0)]
                gate_on = \
                    [(self.gate_time, [self.channel_dict["gate1"]], *self.IQ0)]
                wait2 = \
                    [(self.laser_start - gate_start - self.gate_time, [], *self.IQ0)]
                laser_on = \
                    [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
                wait3 = \
                    [(end - self.laser_start - self.laser_time, [], *self.IQ0)]
                self.total_time = end
                return wait1 + gate_on + wait2 + laser_on + wait3
            elif gate_start + self.gate_time >= self.laser_start and gate_start < self.laser_start:
                wait1 = \
                    [(gate_start, [], *self.IQ0)]
                gate_on = \
                    [(self.laser_start - gate_start, [self.channel_dict["gate1"]], *self.IQ0)]
                both_on = \
                    [(self.gate_time - self.laser_start + gate_start, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
                laser_on = \
                    [(self.laser_time - (self.gate_time - self.laser_start + gate_start), [self.channel_dict["laser"]], *self.IQ0)]
                wait3 = \
                    [(end - self.laser_start - self.laser_time, [], *self.IQ0)]
                self.total_time = end
                return wait1 + gate_on + both_on + laser_on + wait3

            elif gate_start >= self.laser_start and gate_start + self.gate_time < self.laser_start + self.laser_time:
                wait1 = \
                    [(self.laser_start, [], *self.IQ0)]
                laser_on = \
                    [(gate_start - self.laser_start, [self.channel_dict["laser"]], *self.IQ0)]
                both_on = \
                    [(self.gate_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
                laser_on2 = \
                    [(self.laser_time - self.gate_time - (gate_start - self.laser_start), [self.channel_dict["laser"]], *self.IQ0)]
                wait3 = \
                    [(end - self.laser_start - self.laser_time, [], *self.IQ0)]
                self.total_time = end
                return wait1 + laser_on + both_on + laser_on2 + wait3

            elif gate_start < self.laser_start + self.laser_time and gate_start + self.gate_time >= self.laser_start + self.laser_time:
                wait1 = \
                    [(self.laser_start, [], *self.IQ0)]
                laser_on = \
                    [(gate_start - self.laser_start, [self.channel_dict["laser"]], *self.IQ0)]
                both_on = \
                    [(self.laser_start + self.laser_time - gate_start, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
                gate_on = \
                    [(self.gate_time - (self.laser_start + self.laser_time - gate_start), [self.channel_dict["gate1"]], *self.IQ0)]
                wait3 = \
                    [(end - gate_start - self.gate_time, [], *self.IQ0)]
                self.total_time = end
                return wait1 + laser_on + both_on + gate_on + wait3

            else:
                wait1 = \
                    [(self.laser_start, [], *self.IQ0)]
                laser_on = \
                    [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
                wait2 = \
                    [(gate_start - self.laser_start - self.laser_time, [], *self.IQ0)]
                gate_on = \
                    [(self.gate_time, [self.channel_dict["gate1"]], *self.IQ0)]
                wait3 = \
                    [(end - gate_start - self.gate_time, [], *self.IQ0)]
                self.total_time = end
                return wait1 + laser_on + wait2 + gate_on + wait3
        seqs = [single_lag(int(round(gate_start.to("ns").magnitude))) for gate_start in params.array]
        return seqs
    
    #laser lag new
    def Laser_lag_p(self, params):
        print('params:', params[-1]) #params["stop"])
        latest_time = params[-1]
        end = latest_time + self.gate_time

        def lag_p(gate_start):
            if gate_start + self.gate_time <= self.laser_start:
                print('****read window fully before laser start****')
                print('wait2:', self.laser_start - (gate_start + self.gate_time + self.tick_time))
                wait1 = \
                    [(gate_start, [], *self.IQ0)]
                read1 = \
                    [(self.gate_time, [self.channel_dict["clock"]], *self.IQ0)]
                wait2 = \
                    [(self.laser_start - gate_start - self.gate_time, [], *self.IQ0)]# - self.tick_time, [], *self.IQ0)]
                laser_on = \
                    [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
                wait3 = \
                    [(end - self.laser_start - self.laser_time, [], *self.IQ0)]
                bg_wait = \
                    [(self.laser_start, [], *self.IQ0)]
                bg_read = \
                    [(self.gate_time, [self.channel_dict["clock"]], *self.IQ0)]
                
                self.total_time = end + self.laser_start + self.gate_time
                print('total time:', self.total_time)
                return wait1 + read1 + wait2 + laser_on + wait3 + bg_wait + bg_read
                        
            elif gate_start + self.gate_time > self.laser_start and gate_start <= self.laser_start:
                print('****read window during the start of the laser****')
                print('reading without laser for:', self.laser_start - gate_start)
                print('reading with laser for:', self.gate_time + gate_start - self.laser_start)
                wait1 = \
                    [(gate_start, [], *self.IQ0)]
                read_off = \
                    [(self.laser_start - gate_start, [self.channel_dict["clock"]], *self.IQ0)]
                read_on = \
                    [(self.gate_time + gate_start - self.laser_start, [self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
                laser_on = \
                    [(self.laser_time - (self.gate_time + gate_start - self.laser_start), [self.channel_dict["laser"]], *self.IQ0)]
                wait2 = \
                    [(end - self.laser_start - self.laser_time, [], *self.IQ0)]
                bg_wait = \
                    [(self.laser_start, [], *self.IQ0)]
                bg_read = \
                    [(self.gate_time, [self.channel_dict["clock"]], *self.IQ0)]
                
                self.total_time = end + self.laser_start + self.gate_time
                print('total time:', self.total_time)
                return wait1 + read_off + read_on + laser_on + wait2 + bg_wait + bg_read
      
            elif gate_start >= self.laser_start and gate_start + self.gate_time <= self.laser_start + self.laser_time:
                print('****read window fully during the laser on time****')
                time_val = self.gate_time + gate_start - self.laser_start
                wait1 = \
                    [(self.laser_start, [], *self.IQ0)]
                laser_on1 = \
                    [(gate_start - self.laser_start, [self.channel_dict["laser"]], *self.IQ0)]
                read1 = \
                    [(self.gate_time, [self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
                laser_on2 = \
                    [(self.laser_time - time_val, [self.channel_dict["laser"]], *self.IQ0)]
                wait2 = \
                    [(end - self.laser_start - self.laser_time, [], *self.IQ0)]
                bg_wait = \
                    [(self.laser_start, [], *self.IQ0)]
                bg_read = \
                    [(self.gate_time, [self.channel_dict["clock"]], *self.IQ0)]
                    
                self.total_time = end + self.laser_start + self.gate_time
                print('total time:', self.total_time)
                return wait1 + laser_on1 + read1 + laser_on2 + wait2 + bg_wait + bg_read
                       
            elif gate_start < self.laser_start + self.laser_time and gate_start + self.gate_time > self.laser_start + self.laser_time:
                print('****read window during laser shut off****')
                time_val = self.laser_time - (gate_start - self.laser_start)               
                wait1 = \
                    [(self.laser_start, [], *self.IQ0)]
                laser_on = \
                    [(gate_start - self.laser_start, [self.channel_dict["laser"]], *self.IQ0)]
                read_on = \
                    [(time_val, [self.channel_dict["laser"], self.channel_dict["clock"]], *self.IQ0)]
                read_off = \
                    [(self.gate_time - time_val, [self.channel_dict["clock"]], *self.IQ0)]
                wait2 = \
                    [(end - gate_start - self.gate_time, [], *self.IQ0)]
                bg_wait = \
                    [(self.laser_start, [], *self.IQ0)]
                bg_read = \
                    [(self.gate_time, [self.channel_dict["clock"]], *self.IQ0)]
                
                self.total_time = end  + self.laser_start + self.gate_time
                print('total time:', self.total_time)
                return wait1 + laser_on + read_on + read_off + wait2 + bg_wait + bg_read
                       
            elif gate_start >= self.laser_start + self.laser_time:
                print('****read window fully after laser shut off****')
                wait1 = \
                    [(self.laser_start, [], *self.IQ0)]
                laser_on = \
                    [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
                wait2 = \
                    [(gate_start - self.laser_start - self.laser_time, [], *self.IQ0)]
                read1 = \
                    [(self.gate_time, [self.channel_dict["clock"]], *self.IQ0)]
                wait3 = \
                    [(end - gate_start - self.gate_time, [], *self.IQ0)]
                bg_wait = \
                    [(self.laser_start, [], *self.IQ0)]
                bg_read = \
                    [(self.gate_time, [self.channel_dict["clock"]], *self.IQ0)]

                self.total_time = end  + self.laser_start + self.gate_time
                print('total time:', self.total_time)
                return wait1 + laser_on + wait2 + read1 + wait3 + bg_wait + bg_read
                       
        seqs = [lag_p(gate_start) for gate_start in params]
        return seqs
    
    #laser lag new
    def Laser_lag(self, params):
        print('params:', params) #params["stop"])
        latest_time = params[-1]
        end = latest_time + self.gate_time + self.tick_time

        def lag(gate_start):
            if gate_start + self.gate_time + self.tick_time <= self.laser_start:
                print('****read window fully before laser start****')
                print('wait2:', self.laser_start - (gate_start + self.gate_time + self.tick_time))
                wait1 = \
                    [(gate_start, [], *self.IQ0)]
                read_tick1 = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                read_wait1 = \
                    [(self.gate_time - self.tick_time, [], *self.IQ0)]
                read_tick2 = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                wait2 = \
                    [(self.laser_start - gate_start - self.gate_time - self.tick_time, [], *self.IQ0)]# - self.tick_time, [], *self.IQ0)]
                laser_on = \
                    [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
                wait3 = \
                    [(end - self.laser_start - self.laser_time, [], *self.IQ0)]
                bg_wait = \
                    [(self.laser_start, [], *self.IQ0)]
                bg_tick = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                bg_read = \
                    [(self.gate_time - self.tick_time, [], *self.IQ0)]
                bg_tock = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                
                self.total_time = end + self.laser_start + self.gate_time + self.tick_time
                print('total time:', self.total_time)
                return wait1 + read_tick1 + read_wait1 + read_tick2 + wait2 + laser_on + wait3 + \
                       bg_wait + bg_tick + bg_read + bg_tock
                       
            elif gate_start + self.gate_time >= self.laser_start and gate_start + self.tick_time <= self.laser_start:
                print('****read window during the start of the laser****')
                print('reading without laser for:', self.laser_start - gate_start - self.tick_time)
                print('reading with laser for:', self.gate_time + gate_start - self.laser_start)
                time3 = self.gate_time + gate_start - self.laser_start
                wait1 = \
                    [(gate_start, [], *self.IQ0)]
                read_tick1 = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                read_alone = \
                    [(self.laser_start - gate_start - self.tick_time, [], *self.IQ0)]
                read_wait1 = \
                    [(time3, [self.channel_dict["laser"]], *self.IQ0)]
                read_tick2 = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
                laser_on = \
                    [(self.laser_time - time3 - self.tick_time, [self.channel_dict["laser"]], *self.IQ0)]
                wait3 = \
                    [(end - self.laser_start - self.laser_time, [], *self.IQ0)]
                bg_wait = \
                    [(self.laser_start, [], *self.IQ0)]
                bg_tick = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                bg_read = \
                    [(self.gate_time - self.tick_time, [], *self.IQ0)]
                bg_tock = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                
                self.total_time = end + self.laser_start + self.gate_time + self.tick_time
                print('total time:', self.total_time)
                return wait1 + read_tick1 + read_alone + read_wait1 + read_tick2 + laser_on + wait3 + \
                       bg_wait + bg_tick + bg_read + bg_tock
      
            elif gate_start >= self.laser_start and gate_start + self.gate_time + self.tick_time <= self.laser_start + self.laser_time:
                print('****read window fully during the laser on time****')
                time23 = self.gate_time + gate_start - self.laser_start
                wait1 = \
                    [(self.laser_start, [], *self.IQ0)]
                laser_on1 = \
                    [(gate_start - self.laser_start, [self.channel_dict["laser"]], *self.IQ0)]
                read_tick1 = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
                read_wait1 = \
                    [(self.gate_time - self.tick_time, [self.channel_dict["laser"]], *self.IQ0)]
                read_tick2 = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
                laser_on2 = \
                    [(self.laser_time - time23 - self.tick_time, [self.channel_dict["laser"]], *self.IQ0)]
                wait3 = \
                    [(end - self.laser_start - self.laser_time, [], *self.IQ0)]
                bg_wait = \
                    [(self.laser_start, [], *self.IQ0)]
                bg_tick = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                bg_read = \
                    [(self.gate_time - self.tick_time, [], *self.IQ0)]
                bg_tock = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                    
                self.total_time = end + self.laser_start + self.gate_time + self.tick_time
                print('total time:', self.total_time)
                return wait1 + laser_on1 + read_tick1 + read_wait1 + read_tick2 + laser_on2 + wait3 + \
                       bg_wait + bg_tick + bg_read + bg_tock
                
            elif gate_start + self.tick_time <= self.laser_start + self.laser_time and gate_start + self.gate_time >= self.laser_start + self.laser_time:
                print('****read window during laser shut off****')
                time3 = self.laser_time - (gate_start - self.laser_start) - self.tick_time                
                wait1 = \
                    [(self.laser_start, [], *self.IQ0)]
                laser_on = \
                    [(gate_start - self.laser_start, [self.channel_dict["laser"]], *self.IQ0)]
                read_tick1 = \
                    [(self.tick_time, [self.channel_dict["laser"], self.channel_dict["gate1"], self.channel_dict["clock"]], *self.IQ0)]
                read_on = \
                    [(time3, [self.channel_dict["laser"]], *self.IQ0)]
                read_alone = \
                    [(self.gate_time - time3 - self.tick_time, [], *self.IQ0)]
                read_tick2 = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                wait3 = \
                    [(end - gate_start - self.gate_time - self.tick_time, [], *self.IQ0)]
                bg_wait = \
                    [(self.laser_start, [], *self.IQ0)]
                bg_tick = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                bg_read = \
                    [(self.gate_time - self.tick_time, [], *self.IQ0)]
                bg_tock = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                
                self.total_time = end  + self.laser_start + self.gate_time + self.tick_time
                print('total time:', self.total_time)
                return wait1 + laser_on + read_tick1 + read_on + read_alone + read_tick2 + wait3 + \
                       bg_wait + bg_tick + bg_read + bg_tock
                       
            elif gate_start >= self.laser_start + self.laser_time:
                print('****read window fully after laser shut off****')
                wait1 = \
                    [(self.laser_start, [], *self.IQ0)]
                laser_on = \
                    [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
                wait2 = \
                    [(gate_start - self.laser_start - self.laser_time, [], *self.IQ0)]
                read_tick1 = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                read_wait1 = \
                    [(self.gate_time - self.tick_time, [], *self.IQ0)]
                read_tick2 = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                wait3 = \
                    [(end - gate_start - self.gate_time - self.tick_time, [], *self.IQ0)]
                bg_wait = \
                    [(self.laser_start, [], *self.IQ0)]
                bg_tick = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]
                bg_read = \
                    [(self.gate_time - self.tick_time, [], *self.IQ0)]
                bg_tock = \
                    [(self.tick_time, [self.channel_dict["gate1"],self.channel_dict["clock"]], *self.IQ0)]

                self.total_time = end  + self.laser_start + self.gate_time + self.tick_time
                print('total time:', self.total_time)
                return wait1 + laser_on + wait2 + read_tick1 + read_wait1 + read_tick2 + wait3 + \
                       bg_wait + bg_tick + bg_read + bg_tock
                       
        seqs = [lag(gate_start) for gate_start in params]
        return seqs

    #Laser Lag Testing
    def Uri_lag(self, params):
        print('params:', params[-1]) #params["stop"])
        latest_time = params[-1]
        end = latest_time + self.gate_time + self.tick_time
        #reassigning values to make it really clear
        #self.gate_time = Q_(10, 'ns')
        #self.laser_start = Q_(2, 'us')
        #self.laser_time = Q_(1, 'us')
        #self.tick_time = Q_(5, 'ns')
        def single_lag(gate_start):
            if gate_start + self.gate_time < self.laser_start:
                wait1 = \
                    [(gate_start, [], *self.IQ0)]
                # gate_on = \
                    # [(self.gate_time, [self.channel_dict["gate1"]], *self.IQ0)]
                read_tick1 = \
                    [(self.tick_time, [self.channel_dict["clock"]], *self.IQ0)]
                read_wait1 = \
                    [(self.gate_time - self.tick_time, [], *self.IQ0)]
                read_tick2 = \
                    [(self.tick_time, [self.channel_dict["clock"]], *self.IQ0)]
                wait2 = \
                    [(self.laser_start - gate_start - self.gate_time - self.tick_time, [], *self.IQ0)]# - self.tick_time, [], *self.IQ0)]
                laser_on = \
                    [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
                wait3 = \
                    [(end - self.laser_start - self.laser_time, [], *self.IQ0)]
                self.total_time = end
                #print("pulse 1 works")
                #return wait1 + gate_on + wait2 + laser_on + wait3
                return wait1 + read_tick1 + read_wait1 + read_tick2 + wait2 + laser_on + wait3
            elif gate_start + self.gate_time >= self.laser_start and gate_start <= self.laser_start:
                time3 = self.gate_time + gate_start - self.laser_start
                wait1 = \
                    [(gate_start, [], *self.IQ0)]
                # gate_on = \
                    # [(self.laser_start - gate_start, [self.channel_dict["gate1"]], *self.IQ0)]
                read_tick1 = \
                    [(self.tick_time, [self.channel_dict["clock"]], *self.IQ0)]
                read_alone = \
                    [(self.laser_start - gate_start - self.tick_time, [], *self.IQ0)]
                print("I at least can read without the laser for this long:", self.laser_start - gate_start - self.tick_time)
                # both_on = \
                    # [(self.gate_time - self.laser_start + gate_start, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
                read_wait1 = \
                    [(time3, [self.channel_dict["laser"]], *self.IQ0)]
                read_tick2 = \
                    [(self.tick_time, [self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
                # laser_on = \
                    # [(self.laser_time - (self.gate_time - self.laser_start + gate_start), [self.channel_dict["laser"]], *self.IQ0)]
                laser_on = \
                    [(self.laser_time - time3 - self.tick_time, [self.channel_dict["laser"]], *self.IQ0)]
                wait3 = \
                    [(end - self.laser_start - self.laser_time, [], *self.IQ0)]
                self.total_time = end
                print("pulse 2 works")
                #return wait1 + gate_on + both_on + laser_on + wait3
                return wait1 + read_tick1 + read_alone + read_wait1 + read_tick2 + laser_on + wait3
            elif gate_start >= self.laser_start and gate_start + self.gate_time < self.laser_start + self.laser_time:
                time23 = self.gate_time + gate_start - self.laser_start
                wait1 = \
                    [(self.laser_start, [], *self.IQ0)]
                laser_on = \
                    [(gate_start - self.laser_start, [self.channel_dict["laser"]], *self.IQ0)]
                read_tick1 = \
                    [(self.tick_time, [self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
                read_wait1 = \
                    [(self.gate_time - self.tick_time, [self.channel_dict["laser"]], *self.IQ0)]
                read_tick2 = \
                    [(self.tick_time, [self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
                laser_on2 = \
                    [(self.laser_time - time23 - self.tick_time, [self.channel_dict["laser"]], *self.IQ0)]
                # both_on = \
                    # [(self.gate_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
                # laser_on2 = \
                    # [(self.laser_time - self.gate_time - (gate_start - self.laser_start), [self.channel_dict["laser"]], *self.IQ0)]
                wait3 = \
                    [(end - self.laser_start - self.laser_time, [], *self.IQ0)]
                self.total_time = end
                #print("pulse 3 works")
                #return wait1 + laser_on + both_on + laser_on2 + wait3
                return wait1 + laser_on + read_tick1 + read_wait1 + read_tick2 + laser_on2 + wait3
            elif gate_start < self.laser_start + self.laser_time and gate_start + self.gate_time >= self.laser_start + self.laser_time:
                time3 = self.laser_time - (gate_start - self.laser_start)                
                wait1 = \
                    [(self.laser_start, [], *self.IQ0)]
                laser_on = \
                    [(gate_start - self.laser_start, [self.channel_dict["laser"]], *self.IQ0)]
                # might be giving us problems. combining the two together.
                # read_tick1 = \
                    # [(self.tick_time, [self.channel_dict["laser"], self.channel_dict["clock"]], *self.IQ0)]
                # read_wait1 = \
                    # [(time3 - self.tick_time, [self.channel_dict["laser"]], *self.IQ0)]
                read_tick1 = \
                    [(time3, [self.channel_dict["laser"], self.channel_dict["clock"]], *self.IQ0)]
                read_alone = \
                    [(self.gate_time - time3, [], *self.IQ0)]
                read_tick2 = \
                    [(self.tick_time, [self.channel_dict["clock"]], *self.IQ0)]
                # both_on = \
                    # [(self.laser_start + self.laser_time - gate_start, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
                # gate_on = \
                    # [(self.gate_time - (self.laser_start + self.laser_time - gate_start), [self.channel_dict["gate1"]], *self.IQ0)]
                # wait3 = \
                    # [(end - gate_start - self.gate_time, [], *self.IQ0)]
                wait3 = \
                    [(end - gate_start - self.gate_time - self.tick_time, [], *self.IQ0)]
                self.total_time = end
                print("pulse 4 works")
                #return wait1 + laser_on + both_on + gate_on + wait3
                return wait1 + laser_on + read_tick1 + read_alone + read_tick2 + wait3
            else:
                wait1 = \
                    [(self.laser_start, [], *self.IQ0)]
                laser_on = \
                    [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
                wait2 = \
                    [(gate_start - self.laser_start - self.laser_time, [], *self.IQ0)]
                read_tick1 = \
                    [(self.tick_time, [self.channel_dict["clock"]], *self.IQ0)]
                read_wait1 = \
                    [(self.gate_time - self.tick_time, [], *self.IQ0)]
                read_tick2 = \
                    [(self.tick_time, [self.channel_dict["clock"]], *self.IQ0)]
                # gate_on = \
                    # [(self.gate_time, [self.channel_dict["gate1"]], *self.IQ0)]
                # wait3 = \
                    # [(end - gate_start - self.gate_time, [], *self.IQ0)]
                wait3 = \
                    [(end - gate_start - self.gate_time - self.tick_time, [], *self.IQ0)]
                self.total_time = end
                #print("pulse 5 works")
                #return wait1 + laser_on + wait2 + gate_on + wait3
                return wait1 + laser_on + wait2 + read_tick1 + read_wait1 + read_tick2 + wait3
        seqs = [single_lag(gate_start) for gate_start in params]
        return seqs
            
    #** readout calibration- use with readout/init calibration spyrelet: varies the readouttime to maximize signal- pi pulse minus bg to chose optimized time before adding noise 
    def readout(self, params, pi):
        pi_ns = int(round(pi.to("ns").magnitude))
        def single_readout(readtime):
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            read_tick = \
                [(self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            read_wait = \
                [(readtime - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            # readout_high = \
                # [(readtime, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            # readout_low = \
                # [(readtime, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            init = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
            aom_buffer = \
                [(self.aom_lag, [], *self.IQ0)]
            buffer = \
                #[(self.laser_buf, [], *self.IQpx)]
                [(self.laser_buf, [], *self.IQpx)] ### self.laser_buf is time for pi pulse to turn on.
            # setup_high = aom_lag + readout_high + init + aom_buffer + buffer
            # setup_low = aom_lag + readout_low + init + aom_buffer + buffer
            setup = aom_lag + read_tick + read_wait + read_tick + init + aom_buffer + buffer
            setup_time = 2*self.aom_lag + self.readout_time + self.laser_time + self.laser_buf
            #experiment
            pi_pulse = \
                #[(pi_ns, [self.channel_dict["SRS"]], *self.IQpx)]
                [(pi_ns, [], *self.IQpx)]
            pi_pulse_D = \
                [(pi_ns, [], *self.IQ0)]
            pi_pulse_buffer = \
                [(self.laser_buf, [], *self.IQ0)]
            self.total_time = 2*setup_time + 2*pi_ns + 2*self.laser_buf
            #return setup_high + pi_pulse + buffer + setup_low + pi_pulse_D + buffer
            return setup + pi_pulse + buffer + setup + pi_pulse_D + buffer
        seqs = [single_readout(int(round(read_time.to("ns").magnitude))) for read_time in params.array]
        return seqs

    # init calibration- varying initialization time with fixed readout time
    def initcal(self, params, pi):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        pi_ns = int(round(pi.to("ns").magnitude))
        def single_init(inittime):
            wait = longest_time - inittime
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            read_tick = \
                [(self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            read_wait = \
                [(self.readout_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            # # readout_high = \
                # # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            # # readout_low = \
                # # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            init = \
                [(inittime, [self.channel_dict["laser"]], *self.IQ0)]
            aom_buffer = \
                [(self.aom_lag, [], *self.IQ0)]
            buffer = \
                [(self.laser_buf, [], *self.IQpx)]
            # setup_high = aom_lag + init + readout_high + aom_buffer + buffer
            # setup_low = aom_lag + init + readout_low + aom_buffer + buffer
            setup = aom_lag + init + read_tick + read_wait + read_tick + aom_buffer + buffer
            setup_time = 2*self.aom_lag + self.readout_time + inittime + self.laser_buf
            #experiment
            pi_pulse = \
                [(pi_ns, [self.channel_dict["SRS"]], *self.IQpx)]
            pi_pulse_D = \
                [(pi_ns, [], *self.IQ0)]
            pi_pulse_buffer = \
                [(self.laser_buf, [], *self.IQ0)]
            waiting = [(wait, [], *self.IQpx)]
            self.total_time = 2*setup_time + 2*pi_ns + 2*self.laser_buf + 2*wait
            #return setup_high + waiting + pi_pulse + buffer + setup_low + waiting + pi_pulse_D + buffer
            return setup + waiting + pi_pulse + pi_pulse_buffer + setup + waiting + pi_pulse_D + pi_pulse_buffer
        seqs = [single_init(int(round(init_time.to("ns").magnitude))) for init_time in params.array]
        return seqs

    # readout calibration w/ MW overlap init - for really short T1, that are too short for proper initialization 
    def readout_MWoverlap(self, params, pi):
        pi_ns = int(round(pi.to("ns").magnitude))
        def single_readout(readtime):
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            read_tick = \
                [(self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            read_wait = \
                [(readtime - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            # readout_high = \
                # [(readtime, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            # readout_low = \
                # [(readtime, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            init = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
            aom_buffer = \
                [(self.aom_lag, [], *self.IQ0)]
            buffer = \
                [(self.laser_buf, [], *self.IQpx)]
            setup_high = aom_lag + readout_high + init + aom_buffer + buffer
            setup_low = aom_lag + readout_low + init + aom_buffer + buffer
            setup_time = 2*self.aom_lag + self.readout_time + self.laser_time + self.laser_buf
            #experiment
            pi_pulse1 = \
                [(pi_ns - self.aom_lag, [self.channel_dict["laser"],self.channel_dict["SRS"]], *self.IQpx)]
            pi_pulse2 = \
                [(self.aom_lag, [self.channel_dict["SRS"]], *self.IQpx)]
            pi_pulse_D1 = \
                [(pi_ns - self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            pi_pulse_D2 = \
                [(self.aom_lag, [], *self.IQ0)]
            self.total_time = 2*setup_time + 2*pi_ns + 2*self.laser_buf
            return setup_high + pi_pulse1 + pi_pulse2 + buffer + setup_low + pi_pulse_D1 + pi_pulse_D2 + buffer
        seqs = [single_readout(int(round(read_time.to("ns").magnitude))) for read_time in params.array]
        return seqs

    # MW overlap init length - same
    def MWoverlapinit(self, params):
        MWmax = int(round(params["stop"].to("ns").magnitude))
        def single_MWoverlapinit(MWtime):
            init = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
            MWs = \
                [(MWtime, [self.channel_dict["laser"],self.channel_dict["SRS"]], *self.IQpx)]
            MWsoff = \
                [(MWmax - MWtime, [self.channel_dict["laser"]], *self.IQ0)]
            readout_low = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            self.total_time = self.laser_time + MWmax + self.readout_time
            seq = init + MWs + readout_low + MWsoff
            return seq
        seqs = [single_MWoverlapinit(int(round(MWtime.to("ns").magnitude))) for MWtime in params.array]
        return seqs
            
    ###
    # default_digi_dict = {"clock": 0, "blue": 1, "SRS": 2, "VSG":3, "gate1": 4, "gate2": 5, "gate3": 6, "laser": 7, "": None}
    # rev_dict = {0: "clock", 1: "blue", 2: "SRS", 3: "VSG", 4: "gate1", 5: "gate2", 6: "gate3", 7: "laser", 8: "I", 9: "Q"}
        
        # def __init__(self, channel_dict = default_digi_dict, rev_dict = rev_dict, laser_time = 3.5*Q_(1,"us"), 
                 # aom_lag = .73*Q_(1,"us"), aom_ramp = .15*Q_(1,"us"), readout_time = .4*Q_(1,"us"), 
                 # laser_buf = .200*Q_(1,"us"), uriread_time = 50*Q_(1, "us"), uriclock_time = Q_(1, "us"),
                 # IQ=[.4,0], ip="10.135.70.127"):
        # """
        # :param channel_dict: Dictionary of which channels correspond to which instr controls
        # :param readout_time: Laser+gate readout time in us
        # :param laser_time: Laser time to reinit post readout
        # :param aom_lag: Delay in AOM turning on
        # :param laser_buf: Buffer after laser turns off
        # :param IQ: IQ modulation/analog channels
        # """
        # super().__init__()
        # self.channel_dict = {"clock": 0, "blue": 1, "SRS": 2, "VSG":3, "gate1": 4, "gate2": 5, "gate3": 6, "laser": 7, "": None}
        # #self.channel_dict = {"laser": 0, "blue": 1, "SRS": 2, "VSG":3, "gate1": 4, "gate2": 5, "gate3": 6, "gate4": 7, "": None}
        # self._reverse_dict = rev_dict
        # self.laser_time = int(round(laser_time.to("ns").magnitude))
        # self.aom_lag = int(round(aom_lag.to("ns").magnitude))
        # self.aom_ramp = int(round(aom_ramp.to("ns").magnitude))
        # self.readout_time = int(round(readout_time.to("ns").magnitude))
        # self.laser_buf = int(round(laser_buf.to("ns").magnitude))
        # self.uriread_time = int(round(uriread_time.to("ns").magnitude))
        # self.uriclock_time = int(round(uriclock_time.to("ns").magnitude))
        # #self._normalize_IQ(IQ)
        # self.Pulser = PulseStreamer(ip)
        # self.latest_streamed = pd.DataFrame({})
        # self.total_time = -1 #update when a pulse sequence is streamed
    ###
    
    # Constant Pulse Sequences
    def TestCWODMR(self, probe_time, clock_time):
        self.read_time = probe_time
        self.clock_time = clock_time        
        
        clock1 = \
            [(self.clock_time, [self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQpx)] #self.channel_dict["SRS"]], *self.IQ0)]
        count1 = \
            [(self.clock_time, [self.channel_dict["gate1"], self.channel_dict["laser"]], *self.IQpx)]
        unclock1 = \
            [((self.read_time - 2*self.uriclock_time), [self.channel_dict["laser"]], *self.IQpx)] #self.channel_dict["SRS"]], *self.IQ0)]
        clock2 = \
            [(self.clock_time, [self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
        count2 = \
            [(self.clock_time, [self.channel_dict["gate1"], self.channel_dict["laser"]], *self.IQ0)]
        unclock2 = \
            [((self.read_time - 2*self.uriclock_time), [self.channel_dict["laser"]], *self.IQ0)]
        #print("repepitition")
        self.total_time = 2 * self.read_time
        print(clock1)
        return clock1 + count1 + unclock1 + clock2 + count2 + unclock2
    
    def CWUriMR(self):
        # self.read_time = probe_time
        # self.clock_time = clock_time
        print('self.read_time:', self.read_time)
        print(' self.clock_time:',  self.clock_time)
        clock1 = \
            [(self.clock_time, [self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQpx)] #self.channel_dict["SRS"]], *self.IQ0)]
        unclock1 = \
            [((self.read_time - self.clock_time), [self.channel_dict["laser"]], *self.IQpx)] #self.channel_dict["SRS"]], *self.IQ0)]
        clock2 = \
            [(self.clock_time, [self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
        unclock2 = \
            [((self.read_time - self.clock_time), [self.channel_dict["laser"]], *self.IQ0)]#self.channel_dict["laser"]
        #print("repepitition")
        self.total_time = 2 * self.read_time
        print(clock1)
        return clock1 + unclock1 + clock2 + unclock2
    

    # # In the event that we figure out how to count rising and falling together in one counter task:
    # # def CWODMencodeR(self):
        # # risingclock = \
            # # [(self.uriread_time, [self.channel_dict["clock"]. self.channel_dict["laser"], self.channel_dict["SRS"]], *self.IQ0)]
        # # fallingclock = \
            # # [(self.uriread_time, [self.channel_dict["laser"]], *self.IQ0)]
        # # self.total_time = 2 * self.uriread_time
        # # return risingclock + fallingclock
        
    def Laser_On(self):
        excitation = \
            [(self.laser_time, [self.channel_dict["laser"], self.channel_dict["gate1"]], *self.IQ0)]
        self.total_time = self.laser_time
        return excitation

    def CWODMR(self):
        excitation_read = \
            [(self.laser_time, [self.channel_dict["laser"], self.channel_dict["SRS"], self.channel_dict["gate1"]], *self.IQpx)]
        self.total_time = self.laser_time
        return excitation_read
    
    
    def Diff_Pulsed_ODMR(self, pi):
        pi_noround = pi.to("ns").magnitude
        pi_ns = int(round(pi.to("ns").magnitude))
        # init/readout setup
        aom_lag = \
            [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
        read_tick = \
            [(self.tick_time, [self.channel_dict["laser"], self.channel_dict["clock"]], *self.IQ0)]
        read_wait = \
            [(self.readout_time - self.tick_time, [self.channel_dict["laser"]], *self.IQ0)]
        # readout_high = \
            # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
        # readout_low = \
            # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
        init = \
            [(self.laser_time - self.tick_time, [self.channel_dict["laser"]], *self.IQ0)]
        buffer = \
            [(self.laser_buf, [], *self.IQ0)]
        setup = aom_lag + read_tick + read_wait + read_tick  + init + buffer
        #setup_high = aom_lag + readout_high + init + buffer
        #setup_low = aom_lag + readout_low + init + buffer
        setup_time = self.aom_lag + self.readout_time + self.laser_time + self.laser_buf
        # experiment
        pi_pulse = \
            [(pi_ns, [], *self.IQpx)]
        pi_pulse_D = \
            [(pi_ns, [], *self.IQ0)]
        exp_seq1 = pi_pulse + buffer
        exp_seq2 = pi_pulse_D + buffer
        exp_time = pi_ns + self.laser_buf
        self.total_time = 2*(setup_time + exp_time)
        return setup + exp_seq1 + setup + exp_seq2
    # Differential Pulsed ODMR
    def sweep_Pulsed_ODMR(self, pi, num_data):
        def single_pulse(pi):
            pi_noround = pi.to("ns").magnitude
            pi_ns = int(round(pi.to("ns").magnitude))
            # init/readout setup
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            read_tick = \
                [(self.tick_time, [self.channel_dict["laser"], self.channel_dict["clock"]], *self.IQ0)]
            read_wait = \
                [(self.readout_time - self.tick_time, [self.channel_dict["laser"]], *self.IQ0)]
            # readout_high = \
                # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            # readout_low = \
                # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            init = \
                [(self.laser_time - self.tick_time, [self.channel_dict["laser"]], *self.IQ0)]
            buffer = \
                [(self.laser_buf, [], *self.IQ0)]
            setup = aom_lag + read_tick + read_wait + read_tick  + init + buffer
            #setup_high = aom_lag + readout_high + init + buffer
            #setup_low = aom_lag + readout_low + init + buffer
            setup_time = self.aom_lag + self.readout_time + self.laser_time + self.laser_buf
            # experiment
            pi_pulse = \
                [(pi_ns, [], *self.IQpx)]
            pi_pulse_D = \
                [(pi_ns, [], *self.IQ0)]
            exp_seq1 = pi_pulse + buffer
            exp_seq2 = pi_pulse_D + buffer
            exp_time = pi_ns + self.laser_buf
            self.total_time = 2*(setup_time + exp_time)
            seq = setup + exp_seq1 + setup + exp_seq2
            return seq
        
        # # seqs = single_cpmg(params[0])
        # # for tau_time in params[1:]:        
            # # seqs += single_cpmg(tau_time)
        seqs = single_pulse(pi)
        for i in range(num_data):
            seqs += single_pulse(pi)
        # # seqs = sum([single_pulse(pi) for i in num_data])
        return seqs
    
    # Time Varying Pulse Sequences
    def PSrabi(self, params, pi_xy):
        print('now in the driver')
        longest_time = params[-1]#int(round(params[-1]].to("ns").magnitude))
        if pi_xy == 'x':
            self.IQhere = self.IQpx
        else:
            self.IQhere = self.IQpy
        def single_PSrabi(mw_on):
            print('MW time is now:', mw_on)
            print('driver aom_lag:', self.aom_lag)
            print('driver clock time:', self.clock_time)
            print('driver readout time:', self.readout_time)
            print('driver laser time:', self.laser_time)
            print('driver laser buffer:', self.laser_buf)
            wait = longest_time - mw_on
            #init/readout setup
            laser_lag1 = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            clock1 = \
                [(self.clock_time, [self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
            read = \
                [(self.readout_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            init = \
                [(self.laser_time - 2*self.readout_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            clock2 = \
                [(self.clock_time, [self.channel_dict["clock"]], *self.IQ0)]
            laser_lag2 = \
                [(self.aom_lag - self.clock_time, [], *self.IQ0)]
            pi_pulse = \
                [(mw_on, [], *self.IQhere)] 
            MW_buffer = \
                [(self.laser_buf, [], *self.IQ0)]
            
            seq = laser_lag1 + clock1 + read + clock1 + init + clock1 + read + clock2 + laser_lag2 + pi_pulse + MW_buffer 
            # + laser_lag1 + clock1 + read + clock1 + init + clock1 + read + clock2 + laser_lag2 + pi_pulse + MW_buffer
            self.total_time = (self.laser_time + 2*self.aom_lag + mw_on + self.laser_buf)
            print('aom lag is:', self.aom_lag)
            print('laser time is:', self.laser_time)
            print('laser buffer time is:', self.laser_buf)
            print('total time from seq:', self.total_time)
            return seq
            # readout_high = \
                # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            # readout_low = \
                # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            # aom_buffer = \
                # [(self.aom_lag, [], *self.IQ0)]
            # buffer = \
                # [(self.laser_buf, [], *self.IQhere)]
            # setup_high = aom_lag + readout_high + init + aom_buffer + buffer
            # setup_low = aom_lag + readout_low + init + aom_buffer + buffer
            # setup_time = 2*self.aom_lag + self.readout_time + self.laser_time + self.laser_buf
            # readouts = readout_low + init + readout_high + aom_buffer + buffer
            # readouts_time = 2*self.aom_lag + 2*self.readout_time + self.laser_time + self.laser_buf
            
            # ##experiment
            # pi_pulse = \
                # [(mw_on, [self.channel_dict["SRS"]], *self.IQhere)]
            # # pi_pulse_D = \
            # #    [(mw_on, [], *self.IQ0)]
            # waiting = [(wait, [], *self.IQhere)]
            # rabi = pi_pulse + waiting + buffer
            # #rabi_D = pi_pulse_D + waiting + buffer
            # rabi_time = longest_time + self.laser_buf
            # self.total_time = readouts_time + rabi_time # 2*(setup_time + rabi_time)
            # return readouts + rabi # setup_high + rabi + setup_low + rabi_D
        print('calling single PSrabi')
        print('example sequence:', single_PSrabi(params[0]))
        seqs = [single_PSrabi(mw_time) for mw_time in params] #.array]
        print('first sequence from driver:', seqs[0])
        return seqs
    
    def PS_rabi(self, params, pi_xy):
        print('now in the driver')
        longest_time = params[-1]#int(round(params[-1]].to("ns").magnitude))
        if pi_xy == 'x':
            self.IQhere = self.IQpx
        else:
            self.IQhere = self.IQpy
        def single_PS_rabi(mw_on):
            print('MW time is now:', mw_on)
            print('driver aom_lag:', self.aom_lag)
            print('driver clock time:', self.clock_time)
            print('driver readout time:', self.readout_time)
            print('driver laser time:', self.laser_time)
            print('driver laser buffer:', self.laser_buf)
            wait = longest_time - mw_on
            #init/readout setup
            laser_lag1 = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            clock1 = \
                [(self.clock_time, [self.channel_dict["clock"], self.channel_dict["laser"]], *self.IQ0)]
            read = \
                [(self.readout_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            init = \
                [(self.laser_time - 2*self.readout_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            clock2 = \
                [(self.clock_time, [self.channel_dict["clock"]], *self.IQ0)]
            laser_lag2 = \
                [(self.aom_lag - self.clock_time + self.laser_buf, [], *self.IQ0)]
            pi_pulse = \
                [(mw_on, [], *self.IQhere)] 
            MW_buffer = \
                [(self.laser_buf, [], *self.IQ0)]
            duty_cycle_balance  = \
                [(wait, [], *self.IQ0)]
            
            seq = laser_lag1 + clock1 + read + clock1 + init + clock1 + read + clock2 + laser_lag2 + pi_pulse + MW_buffer + duty_cycle_balance
            # + laser_lag1 + clock1 + read + clock1 + init + clock1 + read + clock2 + laser_lag2 + pi_pulse + MW_buffer
            self.total_time = (self.laser_time + 2*self.aom_lag + mw_on + self.laser_buf)+wait
            print('aom lag is:', self.aom_lag)
            print('laser time is:', self.laser_time)
            print('laser buffer time is:', self.laser_buf)
            print('total time from seq:', self.total_time)
            return seq
        
        # # seqs = single_cpmg(params[0])
        # # for tau_time in params[1:]:        
            # # seqs += single_cpmg(tau_time)
        print('calling single PSrabi')
        print('example sequence:', single_PS_rabi(params[0]))
        seqs = single_PS_rabi(params[0])
        for mw_time in params[1:]:
            seqs += single_PS_rabi(mw_time)
        # # seqs = [single_PS_rabi(mw_time) for mw_time in params] #.array]
        print('first sequence from driver:', seqs[0])
        return seqs
  
    def Diff_Rabi(self, params, pi_xy): # Jonathan
        longest_time = params[-1]#int(round(params[-1]].to("ns").magnitude))
        if pi_xy == 'x':
            self.IQhere = self.IQpx
        else:
            self.IQhere = self.IQpy
        def single_rabi(mw_on):
            print('!!!!!!!!!!!!!!!!!!!!!!')
            wait = longest_time - mw_on
            #init/readout setup
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            readout_high = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            readout_low = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            init = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
            aom_buffer = \
                [(self.aom_lag, [], *self.IQ0)]
            buffer = \
                [(self.laser_buf, [], *self.IQhere)]
            # setup_high = aom_lag + readout_high + init + aom_buffer + buffer
            # setup_low = aom_lag + readout_low + init + aom_buffer + buffer
            # setup_time = 2*self.aom_lag + self.readout_time + self.laser_time + self.laser_buf
            readouts = aom_lag + readout_low + init + readout_high + aom_buffer + buffer
            readouts_time = 2*self.aom_lag + 2*self.readout_time + self.laser_time + self.laser_buf
            
            ##experiment
            pi_pulse = \
                [(mw_on, [self.channel_dict["SRS"]], *self.IQhere)]
            # pi_pulse_D = \
            #    [(mw_on, [], *self.IQ0)]
            waiting = [(wait, [], *self.IQhere)]
            rabi = pi_pulse + waiting + buffer
            #rabi_D = pi_pulse_D + waiting + buffer
            rabi_time = longest_time + self.laser_buf
            self.total_time = readouts_time + rabi_time # 2*(setup_time + rabi_time)
            return readouts + rabi # setup_high + rabi + setup_low + rabi_D
        seqs = [single_rabi(mw_time) for mw_time in params] #.array]
        return seqs

    def Diff_Rabi_bluecharge(self, params, pi_xy): # Jonathan
        longest_time = int(round(params["stop"].to("ns").magnitude))
        if pi_xy == 0:
            self.IQhere = self.IQpx
        else:
            self.IQhere = self.IQpy
        def single_rabi_bc(mw_on):
            wait = longest_time - mw_on
            #init/readout setup
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            readout_high = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            readout_low = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            init = \
                [(self.laser_time, [self.channel_dict["laser"], self.channel_dict["blue"]], *self.IQ0)]
            buffer = \
                [(self.laser_buf, [], *self.IQ0)]
            setup_high = aom_lag + readout_high + init + buffer
            setup_low = aom_lag + readout_low + init + buffer
            setup_time = self.aom_lag + self.readout_time + self.laser_time + self.laser_buf
            #experiment
            pi_pulse = \
                [(mw_on, [self.channel_dict["SRS"]], *self.IQhere)]
            pi_pulse_D = \
                [(mw_on, [], *self.IQhere)]
            waiting = [(wait, [], *self.IQhere)]
            rabi = pi_pulse + waiting + buffer
            rabi_D = pi_pulse_D + waiting + buffer
            rabi_time = longest_time + self.laser_buf
            self.total_time = 2*(setup_time + rabi_time)
            return setup_high + rabi + setup_low + rabi_D
        seqs = [single_rabi_bc(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs

    def Diff_Ramsey(self,params,pi):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        pi_noround = pi.to("ns").magnitude
        pihalf_ns = int(round(pi_noround // 2))
        iq_side = 15
        def single_ramsey(tau):
            wait = int(round(longest_time - tau))
            #init/readout setup
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ)]
            readout_high = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ)]
            readout_low = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ)]
            init = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
            aom_buffer = \
                [(self.aom_lag, [], *self.IQ)]
            buffer = \
                [(self.laser_buf, [], *self.IQ)]
            setup_high = aom_lag + readout_high + init + aom_buffer + buffer
            setup_low = aom_lag + readout_low + init + aom_buffer + buffer
            setup_time = 2*self.aom_lag + self.readout_time + self.laser_time + self.laser_buf
            #experiment
            iq_rise_p = \
            [(iq_side, [], *self.IQ)]
            iq_rise_n = \
            [(iq_side, [], -.5, 0)]
            pihalf_pulse = \
                [(pihalf_ns, [self.channel_dict["SRS"]], *self.IQ)]
            piminushalf_pulse = \
                [(pihalf_ns, [self.channel_dict["SRS"]], -.5, 0)]
            dephase = \
                [(tau, [], *self.IQ)]
            wait = \
                [(wait, [], *self.IQ)]
            pihalfiq = iq_rise_p + pihalf_pulse + iq_rise_p
            piminushalfiq = iq_rise_n + piminushalf_pulse + iq_rise_n
            exp1 =  pihalfiq + dephase + pihalfiq + wait + buffer
            exp2 = pihalfiq + dephase + piminushalfiq + wait + buffer
            exp_time = 2*pihalf_ns + longest_time + self.laser_buf + 4*iq_side
            self.total_time = 2*(setup_time + exp_time)
            return setup_high + exp1 + setup_low + exp2
        seqs = [ramsey(int(round(tau_time.to("ns").magnitude))) for tau_time in params.array]
        return seqs
    
    def Diff_Hahn(self,params,pi):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        pi_noround = pi.to("ns").magnitude
        pi_ns = int(round(pi.to("ns").magnitude))
        pihalf_ns = int(round(pi_noround // 2))
        iq_side = 15
        def single_hahn(tau):
            wait = int(round(longest_time - tau))
            tauhalf = int(round(tau // 2))
            #init/readout setup
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ)]
            readout_high = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ)]
            readout_low = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ)]
            init = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
            aom_buffer = \
                [(self.aom_lag, [], *self.IQ)]
            buffer = \
                [(self.laser_buf, [], *self.IQ)]
            setup_high = aom_lag + readout_high + init + aom_buffer + buffer
            setup_low = aom_lag + readout_low + init + aom_buffer + buffer
            setup_time = 2*self.aom_lag + self.readout_time + self.laser_time + self.laser_buf
            #experiment
            iq_rise_p = \
            [(iq_side, [], *self.IQ)]
            iq_rise_n = \
            [(iq_side, [], -.5, 0)]
            pi_pulse = \
                [(pi_ns, [self.channel_dict["SRS"]], *self.IQ)]
            pihalf_pulse = \
                [(pihalf_ns, [self.channel_dict["SRS"]], *self.IQ)]
            piminushalf_pulse = \
                [(pihalf_ns, [self.channel_dict["SRS"]], -.5, 0)]
            dephase = \
                [(tauhalf, [], *self.IQ)]
            wait = \
                [(wait, [], *self.IQ)]
            echo1 = iq_rise_p + pihalf_pulse + iq_rise_p + dephase + iq_rise_p +\
                pi_pulse + iq_rise_p + dephase + iq_rise_p + pihalf_pulse + iq_rise_p + wait + buffer
            echo2 = iq_rise_p + pihalf_pulse + iq_rise_p + dephase + iq_rise_p +\
                pi_pulse + iq_rise_p + dephase + iq_rise_n + piminushalf_pulse + iq_rise_n + wait + buffer
            echo_time = pi_ns + 2*pihalf_ns + longest_time + self.laser_buf + 6*iq_side
            self.total_time = 2*(setup_time + echo_time)
            return setup_high + echo1 + setup_low + echo2
        seqs = [single_hahn(int(round(tau_time.to("ns").magnitude))) for tau_time in params.array]
        return seqs
    
    # tau is full NV evolution time (vs 1/2 evolution time)
    def Diff_JCPMG(self,params,pi,n,xy,iq_side): # also do ramsey (with n = 0) and hahn (n = 1)
        longest_time = int(round(params["stop"].to("ns").magnitude))
        shortest_time = int(round(params["start"].to("ns").magnitude))
        pi_noround = pi.to("ns").magnitude
        pi_ns = int(round(pi.to("ns").magnitude))
        pihalf_ns = int(round(pi_noround // 2))
        iq_side = int(round(iq_side.to("ns").magnitude))
        def single_Jcpmg(tau):
            wait = int(round(longest_time + shortest_time - tau))
            if n > 0.5:
                tauspacing_ns = int(round(tau // n))
                tauinit_ns = int(round(tau // (2*n)))
            if n < 0.5:
                tauinit_ns = int(round(tau // 2))
            #init/readout setup
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ)]
            readout_high = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ)]
            readout_low = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ)]
            init = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
            aom_buffer = \
                [(self.aom_lag, [], *self.IQ)]
            buffer = \
                [(self.laser_buf, [], *self.IQ)]
            setup_high = aom_lag + readout_high + init + aom_buffer + buffer
            setup_low = aom_lag + readout_low + init + aom_buffer + buffer
            setup_time = 2*self.aom_lag + self.readout_time + self.laser_time + self.laser_buf
            #experiment
            iq_rise_p = \
            [(iq_side, [], *self.IQ)]
            iq_rise_n = \
            [(iq_side, [], -.5, 0)]
            if xy == False:
                pi_pulse = \
                    [(pi_ns, [self.channel_dict["SRS"]], *self.IQ)]
            if xy == True:
                pi_pulse = \
                    [(pi_ns, [self.channel_dict["SRS"]], 0, .5)]
            pihalf_pulse = \
                [(pihalf_ns, [self.channel_dict["SRS"]], *self.IQ)]
            piminushalf_pulse = \
                [(pihalf_ns, [self.channel_dict["SRS"]], -.5, 0)]
            wait = \
                [(wait, [], *self.IQ)]
            piiq = iq_rise_p + pi_pulse + iq_rise_p
            pihalfiq = iq_rise_p + pihalf_pulse + iq_rise_p
            piminushalfiq = iq_rise_n + piminushalf_pulse + iq_rise_n
            tauinit = \
                [(tauinit_ns, [], *self.IQ)]
            middle = tauinit
            middle_time = 0
            if n > 0.5:
                middle = middle + piiq
                middle_time = middle_time + pi_ns + 2*iq_side
                if n > 1.5:
                    for i in range(n-1):
                        middle = middle + [(tauspacing_ns, [], *self.IQ)] + piiq
                        middle_time = middle_time + pi_ns + 2*iq_side
            middle = middle + tauinit
            middle_time = middle_time
            echo1 = pihalfiq + middle + pihalfiq + wait + buffer
            echo2 = pihalfiq + middle + piminushalfiq + wait + buffer
            echo_time = middle_time + 2*pihalf_ns + 4*iq_side + longest_time + self.laser_buf
            self.total_time = 2*(setup_time + echo_time)
            return setup_high + echo1 + setup_low + echo2
        seqs = [single_Jcpmg(int(round(tau_time.to("ns").magnitude))) for tau_time in params.array]
        return seqs
    
    def Diff_CPMG_Jon(self,params,pi,pi2,n):
        longest_time = params[-1]
        shortest_time = params[0]
        pi_noround = pi.to("ns").magnitude
        pi_ns = int(round(pi.to("ns").magnitude))
        pihalf_ns = int(round(pi2.to("ns").magnitude))
        #iq_side = int(round(iq_side.to("ns").magnitude))
        def single_cpmg(tau):
            tau_rev_ns = int(round(longest_time + shortest_time - tau))
            if n > 0.5:
                tauspacing_ns = int(round(tau // n))
                taurevspacing_ns = int(round(tau_rev_ns // n))
                tauinit_ns = int(round(tau // (2*n)))
                taurevinit_ns = int(round(tau_rev_ns // (2*n)))
            if n < 0.5:
                tauinit_ns = int(round(tau // 2))
                taurevinit_ns = int(round(tau_rev_ns // 2))
            #pi pulses
            pi_pulse = \
                [(pi_ns, [self.channel_dict["SRS"]], *self.IQpy)]
            pi_pulse_D = \
                [(pi_ns, [], *self.IQ0)]
            pihalf_pulse = \
                [(pihalf_ns, [self.channel_dict["SRS"]], *self.IQpx)]
            piminushalf_pulse = \
                [(pihalf_ns, [self.channel_dict["SRS"]], *self.IQnx)]

            #init/readout setup
            #high S=ctr1
            #high R=ctr0
            #low  S=ctr3
            #low  R=ctr2
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            readout_high_S = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            readout_high_R = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            readout_low_S = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"],self.channel_dict["gate3"]], *self.IQ0)]
            readout_low_R = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate4"]], *self.IQ0)]
            init = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
            aom_buffer = \
                [(self.aom_lag, [], *self.IQ0)]
            buffer = \
                [(self.laser_buf, [], *self.IQ0)]
            setup_high_SR = aom_lag + readout_high_S + init + readout_high_R + aom_buffer + buffer
            setup_low_SR = aom_lag + readout_low_S + init + readout_low_R + aom_buffer + buffer
            self.setup_time = 2*self.aom_lag + 2*self.readout_time + self.laser_time + self.laser_buf
            #experiment
            
            # reverse = \
            #     [(reverse_ns, [], *self.IQ)]
            
            tauinit = \
                [(tauinit_ns, [], *self.IQ0)]
            taurevinit = \
                [(taurevinit_ns, [], *self.IQ0)]
            middle = tauinit
            middle_rev = taurevinit
            middle_time = 0
            middlerev_time = 0
            if n > 0.5:
                middle = middle + pi_pulse #piiq
                middle_time = middle_time + pi_ns # + 2*iq_side
                middle_rev = middle_rev + pi_pulse #piiq
                middlerev_time = middlerev_time + pi_ns # + 2*iq_side
                if n > 1.5:
                    for i in range(n-1):
                        middle = middle + [(tauspacing_ns, [], *self.IQ0)] + pi_pulse #piiq
                        middle_time = middle_time + pi_ns #+ 2*iq_side
                        middle_rev = middle_rev + [(taurevspacing_ns, [], *self.IQ0)] + pi_pulse #piiq
                        middlerev_time = middlerev_time + pi_ns #+ 2*iq_side
            middle = middle + tauinit
            middle_time = middle_time
            middle_rev = middle_rev + taurevinit
            middlerev_time = middlerev_time
            
            #####
            # # here we have a mistake, I think, it should be pihalf_pulse and then piminushalf_pulse
            #####
            echo = pihalf_pulse + middle + piminushalf_pulse + buffer #pihalfiq + middle + piminushalfiq + buffer #### PI Y, MINUS HALF, BRIGHT STATE READOUT
            echo_rev = pihalf_pulse + middle_rev + pihalf_pulse + buffer #pihalfiq + middle_rev + pihalfiq + buffer ####### PI Y, PLUS HALF, DARK STATE
            #####
            # # end mistake
            #####
            
            echo_time = middle_time + 2*pihalf_ns + tau + self.laser_buf#+ 4*iq_side + tau + self.laser_buf
            echorev_time = middlerev_time + 2*pihalf_ns + tau_rev_ns + self.laser_buf#+ 4*iq_side + tau_rev_ns + self.laser_buf
            self.total_time = 2*self.setup_time + echo_time + echorev_time
            return setup_high_SR + echo + setup_low_SR + echo_rev
        seqs = [single_cpmg(tau_time) for tau_time in params]
        # #feedback sequence with same MW duty cycle
        # middle_time = params[int(params.__len__()/2)]
        return seqs
        
    def Diff_CPMG4(self,params,pi,pi2,n,iq_buffer):
        longest_time = params[-1]
        shortest_time = params[0]
        pi_noround = pi.to("ns").magnitude
        pi_ns = int(round(pi.to("ns").magnitude))
        pihalf_ns = int(round(pi2.to("ns").magnitude))
        iq_buffer = None
        #iq_side = int(round(iq_side.to("ns").magnitude))
        def single_cpmg(tau):
            tau_rev_ns = int(round(longest_time + shortest_time - tau))
            if n > 0.5:
                tauspacing_ns = int(round(tau // n))
                taurevspacing_ns = int(round(tau_rev_ns // n))
                tauinit_ns = int(round(tau // (2*n)))
                taurevinit_ns = int(round(tau_rev_ns // (2*n)))
            if n < 0.5:
                tauinit_ns = int(round(tau // 2))
                taurevinit_ns = int(round(tau_rev_ns // 2))
            #pi pulses
            pi_pulse = \
                [(pi_ns, [], *self.IQpy)]#SRS
            pi_pulse_D = \
                [(pi_ns, [], *self.IQ0)]
            pihalf_pulse = \
                [(pihalf_ns, [], *self.IQpx)]
            piminushalf_pulse = \
                [(pihalf_ns, [], *self.IQnx)]
            #init/readout setup
            #high S=ctr1
            #high R=ctr0
            #low  S=ctr3
            #low  R=ctr2
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            read_tick = \
                [(self.clock_time, [self.channel_dict["laser"], self.channel_dict["clock"]], *self.IQ0)]
            read_window = \
                [(self.readout_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            # # readout_high_S = \
                # # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            # # readout_high_R = \
                # # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            # # readout_low_S = \
                # # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"],self.channel_dict["gate3"]], *self.IQ0)]
            # # readout_low_R = \
                # # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate4"]], *self.IQ0)]
            init = \
                [(self.laser_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            aom_buffer = \
                [(self.aom_lag - self.clock_time, [], *self.IQ0)]
            buffer = \
                [(self.laser_buf, [], *self.IQ0)]
            setupSR = aom_lag + read_tick + read_window + read_tick + init + read_tick + read_window + read_tick + aom_buffer + buffer
            #setup_low_SR = aom_lag + readout_low_S + init + readout_low_R + aom_buffer + buffer
            self.setup_time = 2*self.aom_lag + 2*self.readout_time + self.laser_time + self.laser_buf
            #experiment
            # reverse = \
            #     [(reverse_ns, [], *self.IQ)]
            tauinit = \
                [(tauinit_ns, [], *self.IQ0)]
            taurevinit = \
                [(taurevinit_ns, [], *self.IQ0)]
            middle = tauinit
            middle_rev = taurevinit
            middle_time = 0
            middlerev_time = 0
            if n > 0.5:
                middle = middle + pi_pulse #piiq
                middle_time = middle_time + pi_ns # + 2*iq_side
                middle_rev = middle_rev + pi_pulse #piiq
                middlerev_time = middlerev_time + pi_ns # + 2*iq_side
                if n > 1.5:
                    for i in range(n-1):
                        middle = middle + [(tauspacing_ns, [], *self.IQ0)] + pi_pulse #piiq
                        middle_time = middle_time + pi_ns #+ 2*iq_side
                        middle_rev = middle_rev + [(taurevspacing_ns, [], *self.IQ0)] + pi_pulse #piiq
                        middlerev_time = middlerev_time + pi_ns #+ 2*iq_side
            middle = middle + tauinit
            middle_time = middle_time
            middle_rev = middle_rev + taurevinit
            middlerev_time = middlerev_time
            echo = pihalf_pulse + middle + piminushalf_pulse + buffer #pihalfiq + middle + piminushalfiq + buffer # prepares BRIGHT STATE
            echo_rev = pihalf_pulse + middle_rev + pihalf_pulse + buffer #pihalfiq + middle_rev + pihalfiq + buffer # prepares DARK STATE
            echo_time = middle_time + 2*pihalf_ns + tau + self.laser_buf#+ 4*iq_side + tau + self.laser_buf
            echorev_time = middlerev_time + 2*pihalf_ns + tau_rev_ns + self.laser_buf#+ 4*iq_side + tau_rev_ns + self.laser_buf
            self.total_time = 2*self.setup_time + echo_time + echorev_time
            return setupSR + echo + setupSR + echo_rev
        seqs = single_cpmg(params[0])
        for tau_time in params[1:]:        
            seqs += single_cpmg(tau_time)
        # #feedback sequence with same MW duty cycle
        return seqs
        
    def CPMG_Norm(self,params,pi,pi2,n,iq_buffer):
        longest_time = params[-1]
        shortest_time = params[0]
        pi_noround = pi.to("ns").magnitude
        pi_ns = int(round(pi.to("ns").magnitude))
        pihalf_ns = int(round(pi2.to("ns").magnitude))
        iq_buffer = None
        #iq_side = int(round(iq_side.to("ns").magnitude))
        def single_cpmg(tau):
            tau_rev_ns = int(round(longest_time + shortest_time - tau))
            if n > 0.5:
                tauspacing_ns = int(round(tau // n))
                taurevspacing_ns = int(round(tau_rev_ns // n))
                tauinit_ns = int(round(tau // (2*n)))
                taurevinit_ns = int(round(tau_rev_ns // (2*n)))
            if n < 0.5:
                tauinit_ns = int(round(tau // 2))
                taurevinit_ns = int(round(tau_rev_ns // 2))
            #pi pulses
            pi_pulse = \
                [(pi_ns, [], *self.IQpy)]#SRS
            pi_pulse_D = \
                [(pi_ns, [], *self.IQ0)]
            pihalf_pulse = \
                [(pihalf_ns, [], *self.IQpx)]
            piminushalf_pulse = \
                [(pihalf_ns, [], *self.IQnx)]
            #init/readout setup
            #high S=ctr1
            #high R=ctr0
            #low  S=ctr3
            #low  R=ctr2
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            read_tick = \
                [(self.clock_time, [self.channel_dict["laser"], self.channel_dict["clock"]], *self.IQ0)]
            read_window = \
                [(self.readout_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            # # readout_high_S = \
                # # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            # # readout_high_R = \
                # # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            # # readout_low_S = \
                # # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"],self.channel_dict["gate3"]], *self.IQ0)]
            # # readout_low_R = \
                # # [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate4"]], *self.IQ0)]
            init = \
                [(self.laser_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            aom_buffer = \
                [(self.aom_lag - self.clock_time, [], *self.IQ0)]
            buffer = \
                [(self.laser_buf, [], *self.IQ0)]
            setupSR = aom_lag + read_tick + read_window + read_tick + init + read_tick + read_window + read_tick + aom_buffer + buffer
            #setupSR = aom_lag + read_tick + read_window + read_tick + init + aom_buffer + buffer
            #setup_low_SR = aom_lag + readout_low_S + init + readout_low_R + aom_buffer + buffer
            self.setup_time = 2*self.aom_lag + 2*self.readout_time + self.laser_time + self.laser_buf
            #experiment
            # reverse = \
            #     [(reverse_ns, [], *self.IQ)]
            tauinit = \
                [(tauinit_ns, [], *self.IQ0)]
            taurevinit = \
                [(taurevinit_ns, [], *self.IQ0)]
            middle = tauinit
            middle_rev = taurevinit
            middle_time = 0
            middlerev_time = 0
            if n > 0.5:
                middle = middle + pi_pulse #piiq
                middle_time = middle_time + pi_ns # + 2*iq_side
                middle_rev = middle_rev + pi_pulse #piiq
                middlerev_time = middlerev_time + pi_ns # + 2*iq_side
                if n > 1.5:
                    for i in range(n-1):
                        middle = middle + [(tauspacing_ns, [], *self.IQ0)] + pi_pulse #piiq
                        middle_time = middle_time + pi_ns #+ 2*iq_side
                        middle_rev = middle_rev + [(taurevspacing_ns, [], *self.IQ0)] + pi_pulse #piiq
                        middlerev_time = middlerev_time + pi_ns #+ 2*iq_side
            middle = middle + tauinit
            middle_time = middle_time
            middle_rev = middle_rev + taurevinit
            middlerev_time = middlerev_time
            echo = pihalf_pulse + middle + piminushalf_pulse + buffer #pihalfiq + middle + piminushalfiq + buffer # prepares BRIGHT STATE
            echo_rev = pihalf_pulse + middle_rev + pihalf_pulse + buffer #pihalfiq + middle_rev + pihalfiq + buffer # prepares DARK STATE
            echo_time = middle_time + 2*pihalf_ns + tau + self.laser_buf#+ 4*iq_side + tau + self.laser_buf
            echorev_time = middlerev_time + 2*pihalf_ns + tau_rev_ns + self.laser_buf#+ 4*iq_side + tau_rev_ns + self.laser_buf
            self.total_time = 2*self.setup_time + echo_time + echorev_time
            return setupSR + echo + setupSR + echo_rev
        def norm_seq():
            pi_pulse = \
                [(pi_ns, [], *self.IQpx)]#SRS
            wait = \
                [(self.mw_wait - self.aom_lag, [], *self.IQ0)]
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            read_tick = \
                [(self.clock_time, [self.channel_dict["laser"], self.channel_dict["clock"]], *self.IQ0)]
            read_window = \
                [(self.readout_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            init = \
                [(self.laser_time - self.clock_time, [self.channel_dict["laser"]], *self.IQ0)]
            aom_buffer = \
                [(self.aom_lag - self.clock_time, [], *self.IQ0)]
            buffer = \
                [(self.norm_lag, [], *self.IQ0)]
            return (pi_pulse + wait + aom_lag + read_tick + read_window + read_tick + init + aom_buffer + buffer
                  + aom_lag + read_tick + read_window + read_tick + init + aom_buffer)
        seqs = single_cpmg(params[0])
        for tau_time in params[1:]:        
            seqs += single_cpmg(tau_time)
        seqs += norm_seq()
        ## this means one repeat will have len(tau_times) * data_ct * 8 + 4 reads.
        # #feedback sequence with same MW duty cycle
        return seqs
    
    # adaptive sequences don't have fixed laser and MW duty cycle (their total time  changes- might be prone to charge dynamics)       
    def Diff_Hahn_adaptive(self,params,pi):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        pi_noround = pi.to("ns").magnitude
        pi_ns = int(round(pi.to("ns").magnitude))
        pihalf_ns = int(round(pi_noround // 2))
        def single_hahn(tau):
            wait = int(round(longest_time - tau))
            tauhalf = int(round(tau // 2))
            #init/readout setup
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ)]
            readout_high = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ)]
            readout_low = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ)]
            init = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
            buffer = \
                [(self.laser_buf, [], *self.IQ)]
            setup_high = aom_lag + readout_high + init + buffer
            setup_low = aom_lag + readout_low + init + buffer
            setup_time = self.aom_lag + self.readout_time + self.laser_time + self.laser_buf
            #experiment
            pi_pulse = \
                [(pi_ns, [self.channel_dict["SRS"]], *self.IQ)]
            pihalf_pulse = \
                [(pihalf_ns, [self.channel_dict["SRS"]], *self.IQ)]
            piminushalf_pulse = \
                [(pihalf_ns, [self.channel_dict["SRS"]], -0.4, 0)]
            dephase = \
                [(tauhalf, [], *self.IQ)]
            echo1 = pihalf_pulse + dephase + pi_pulse + dephase + pihalf_pulse + buffer
            echo2 = pihalf_pulse + dephase + pi_pulse + dephase + piminushalf_pulse + buffer
            echo_time = pi_ns + 2*pihalf_ns + 2*tauhalf + self.laser_buf
            self.total_time = 2*(setup_time + echo_time)
            return setup_high + echo1 + setup_low + echo2
        seqs = [single_hahn(int(round(tau_time.to("ns").magnitude))) for tau_time in params.array]
        return seqs    

    #single f differential T1
    def S_Diff_T1(self, params, pi, iq_side):
        longest_time = params[-1]
        pi_noround = pi.to("ns").magnitude
        pi_ns = int(round(pi.to("ns").magnitude))
        iq_side = int(round(iq_side.to("ns").magnitude))
        def single_T1(tau):
            wait = int(round(longest_time - tau))
            #init/readout setup
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            readout1 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            readout2 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            readout3 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"],self.channel_dict["gate3"]], *self.IQ0)]
            readout_blank = \
            [(self.readout_time, [self.channel_dict["laser"]], *self.IQ0)]
            init = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
            buffer = \
                [(self.laser_buf, [], *self.IQ0)]
            setup1 = aom_lag + readout1 + init + readout3 + buffer
            setup2 = aom_lag + readout2 + init + readout_blank + buffer
            self.setup_time = self.aom_lag + 2*self.readout_time + self.laser_time + self.laser_buf
            #experiment
            iq_rise_p = \
                [(iq_side, [], *self.IQpx)]
            pi_pulse = \
                [(pi_ns, [self.channel_dict["SRS"]], *self.IQpx)]
            pi_pulse_empty = \
                [(pi_ns, [], *self.IQpx)]
            piiq = iq_rise_p + pi_pulse + iq_rise_p
            pidiq = iq_rise_p + pi_pulse_empty + iq_rise_p
            tau_decay = \
                [(tau, [], *self.IQ0)]
            reverse_tau_decay = \
                [(wait, [], *self.IQ0)]
            decay_D = tau_decay + piiq + buffer
            decay = reverse_tau_decay + pidiq + buffer
            decay_time = 2*(pi_ns + 2*iq_side + self.laser_buf) + tau + wait
            self.total_time = 2*self.setup_time + decay_time
            return setup1 + decay_D + setup2 + decay
        seqs = [single_T1(tau_time) for tau_time in params]
        return seqs


#single f differential T1 with MW overlap initialization
    def S_Diff_T1_MWoverlap(self, params, pi):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        start_time = int(round(params["start"].to("ns").magnitude))
        pi_noround = pi.to("ns").magnitude
        pi_ns = int(round(pi.to("ns").magnitude))
        def single_T1(tau):
            wait = int(round(longest_time - tau + start_time)) # to account for non-zero start time parity 
            #init/readout setup
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            readout1 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            readout2 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            readout3 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"],self.channel_dict["gate3"]], *self.IQ0)]
            readout_blank = \
                [(self.readout_time, [self.channel_dict["laser"]], *self.IQ0)]
            init = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ0)]
            # MWoverlap = \
            #     [(pi_ns - self.aom_lag - self.aom_ramp, [self.channel_dict["laser"],self.channel_dict["SRS"]], *self.IQpx)]
            # MWs = \
            #     [(self.aom_lag + self.aom_ramp, [self.channel_dict["SRS"]], *self.IQpx)]
            # MWoverlapoff = \
            #     [(pi_ns - self.aom_lag - self.aom_ramp, [self.channel_dict["laser"]], *self.IQ0)]
            # MWsoff = \
            #     [(self.aom_lag + self.aom_ramp, [], *self.IQpx)]
            buffer = \
                [(self.laser_buf, [], *self.IQ0)]

            if tau <= self.aom_lag:# + self.aom_ramp:
                MWoverlap = \
                    [(pi_ns - self.aom_lag - self.aom_ramp, [self.channel_dict["laser"],self.channel_dict["SRS"]], *self.IQpx)]
                MWs1 = \
                    [(tau + self.aom_ramp, [self.channel_dict["SRS"]], *self.IQpx)]
                MWs2 = \
                    [(self.aom_lag - tau, [self.channel_dict["laser"],self.channel_dict["SRS"]], *self.IQpx)]
                tau_decay = \
                    [(tau, [self.channel_dict["laser"]], *self.IQ0)]
                MWs = MWs1 + MWs2
            else:
                MWoverlap = \
                    [(pi_ns - self.aom_lag - self.aom_ramp, [self.channel_dict["laser"],self.channel_dict["SRS"]], *self.IQpx)]
                MWs = \
                    [(self.aom_lag + self.aom_ramp, [self.channel_dict["SRS"]], *self.IQpx)]
                tau_decay = \
                    [(tau - self.aom_lag, [], *self.IQ0)] + aom_lag

            if wait <= self.aom_lag:# + self.aom_ramp:
                MWoverlapoff = \
                    [(pi_ns - self.aom_lag - self.aom_ramp, [self.channel_dict["laser"]], *self.IQ0)]
                MWs1 = \
                    [(wait + self.aom_ramp, [], *self.IQ0)]
                MWs2 = \
                    [(self.aom_lag - wait, [self.channel_dict["laser"]], *self.IQ0)]
                reverse_tau_decay = \
                    [(wait, [self.channel_dict["laser"]], *self.IQ0)]
                MWsoff = MWs1 + MWs2
            else:
                MWoverlapoff = \
                    [(pi_ns - self.aom_lag - self.aom_ramp, [self.channel_dict["laser"]], *self.IQ0)]
                MWsoff = \
                    [(self.aom_lag + self.aom_ramp, [], *self.IQ0)]
                reverse_tau_decay = \
                    [(wait - self.aom_lag, [], *self.IQ0)] + aom_lag


            setup1 = readout1 + init + readout3 + MWoverlap + MWs + buffer
            setup2 = readout2 + init + readout_blank + MWoverlapoff + MWsoff + buffer
            self.setup_time = 2*self.readout_time + self.laser_time + pi_ns + self.laser_buf
            #experiment
            # tau_decay = \
            #     [(tau, [], *self.IQ0)]
            # reverse_tau_decay = \
            #     [(wait, [], *self.IQ0)]
            decay_D = tau_decay
            decay = reverse_tau_decay
            decay_time = tau + wait
            self.total_time = 2*self.setup_time + decay_time
            return setup1 + decay_D + setup2 + decay
        seqs = [single_T1(int(round(tau_time.to("ns").magnitude))) for tau_time in params.array]
        return seqs

    # repolarization relaxometry- for very short T1 
    def repol_relax_T1(self,params,wait_time):
        wait_time_ns = int(round(wait_time.to("ns").magnitude))
        def single_seq(tau):
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            readout1 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            readout2 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            init1 = \
                [(tau, [self.channel_dict["laser"]], *self.IQ0)]
            init2 = \
                [(self.laser_time - tau - 2*self.readout_time, [self.channel_dict["laser"]], *self.IQ0)]
            wait = \
                [(wait_time_ns, [], *self.IQ0)]
            self.total_time = self.aom_lag + self.laser_time + wait_time_ns
            return aom_lag + init1 + readout1 + init2 + readout2 + wait
        seqs = [single_seq(int(round(tau_time.to("ns").magnitude))) for tau_time in params.array]
        return seqs
    
    # for very short T1
    def repol_relax_pipulse_T1(self,params,wait_time,pi):
        wait_time_ns = int(round(wait_time.to("ns").magnitude))
        pi_ns = int(round(pi.to("ns").magnitude))
        def single_seq(tau):
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            readout1 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            readout2 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            init1 = \
                [(tau, [self.channel_dict["laser"]], *self.IQ0)]
            init2 = \
                [(self.laser_time - tau - self.readout_time, [self.channel_dict["laser"]], *self.IQ0)]
            wait = \
                [(wait_time_ns, [], *self.IQ0)]
            lag_lesspi = \
                [(self.aom_lag - pi_ns, [self.channel_dict["laser"]], *self.IQ0)]
            pi_pulse_lag = \
                [(pi_ns, [self.channel_dict["laser"],self.channel_dict["SRS"]], *self.IQpx)]
            self.total_time = 2*(self.aom_lag + self.laser_time + wait_time_ns)
            return aom_lag + init1 + readout1 + init2 + wait + lag_lesspi + pi_pulse_lag + init1 + readout2 + init2 + wait
        seqs = [single_seq(int(round(tau_time.to("ns").magnitude))) for tau_time in params.array]
        return seqs

    #single f differential T1- for comparing T1 times with ionization times (changing init times)
    def S_Diff_T1_varyinit(self, params, tau, pi, iq_side):
        longest_time = int(round(params.array[-1].to("ns").magnitude))
        shortest_time = int(round(params.array[0].to("ns").magnitude))
        pi_noround = pi.to("ns").magnitude
        pi_ns = int(round(pi.to("ns").magnitude))
        iq_side = int(round(iq_side.to("ns").magnitude))
        tau_t = int(round(tau.to("ns").magnitude))
        def single_T1(t_init):
            t_init1 = t_init
            t_init2 = int(round(longest_time + shortest_time - t_init))
            #init/readout setup
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ0)]
            readout1 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ0)]
            readout2 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ0)]
            init1 = \
                [(t_init1, [self.channel_dict["laser"]], *self.IQ0)]
            init2 = \
                [(t_init2, [self.channel_dict["laser"]], *self.IQ0)]
            buffer = \
                [(self.laser_buf, [], *self.IQ0)]
            setup1 = aom_lag + readout1 + init1 + buffer
            setup2 = aom_lag + readout2 + init2 + buffer
            setup_time = self.aom_lag + self.readout_time + self.laser_buf
            #experiment
            iq_rise_p = \
                [(iq_side, [], *self.IQpx)]
            pi_pulse = \
                [(pi_ns, [self.channel_dict["SRS"]], *self.IQpx)]
            pi_pulse_empty = \
                [(pi_ns, [], *self.IQpx)]
            piiq = iq_rise_p + pi_pulse + iq_rise_p
            pidiq = iq_rise_p + pi_pulse_empty + iq_rise_p
            tau_decay = \
                [(tau_t, [], *self.IQ0)]
            reverse_tau_decay = \
                [(tau_t, [], *self.IQ0)]
            decay_D = tau_decay + pidiq + buffer
            decay = reverse_tau_decay + piiq + buffer
            decay_time = pi_ns + 2*iq_side + tau_t + self.laser_buf
            self.total_time = 2*(setup_time + decay_time) + t_init1 + t_init2
            return setup1 + decay_D + setup2 + decay
        seqs = [single_T1(int(round(init_time.to("ns").magnitude))) for init_time in params.array]
        return seqs

    #single f differential T1, adaptive time
    def S_Diff_T1_adaptive(self, params, pi, iq_side):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        pi_noround = pi.to("ns").magnitude
        pi_ns = int(round(pi.to("ns").magnitude))
        iq_side = int(round(iq_side.to("ns").magnitude))
        def single_T1(tau):
            wait = int(round(longest_time - tau))
            #init/readout setup
            aom_lag = \
                [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ)]
            readout1 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ)]
            readout2 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ)]
            readout3 = \
                [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"],self.channel_dict["gate3"]], *self.IQ0)]
            readout_blank = \
            [(self.readout_time, [], *self.IQ0)]
            init = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
            buffer = \
                [(self.laser_buf, [], *self.IQ)]
            setup1 = aom_lag + readout1 + init + readout3 + buffer
            setup2 = aom_lag + readout2 + init + readout_blank + buffer
            self.setup_time = self.aom_lag + 2*self.readout_time + self.laser_time + self.laser_buf
            #experiment
            iq_rise_p = \
                [(iq_side, [], *self.IQpx)]
            pi_pulse = \
                [(pi_ns, [self.channel_dict["SRS"]], *self.IQpx)]
            pi_pulse_empty = \
                [(pi_ns, [], *self.IQpx)]
            piiq = iq_rise_p + pi_pulse + iq_rise_p
            pidiq = iq_rise_p + pi_pulse_empty + iq_rise_p
            tau_decay = \
                [(tau, [], *self.IQ0)]

            # pi_pulse = \
            #     [(pi_ns, [self.channel_dict["SRS"]], *self.IQ)]
            # pi_pulse_empty = \
            #     [(pi_ns, [], *self.IQ)]
            # tau_decay = \
            #     [(tau, [], *self.IQ)]
            decay = tau_decay + piiq + buffer
            decay_D = tau_decay + pidiq + buffer
            decay_time = pi_ns + 2*iq_side + tau + self.laser_buf

            self.total_time = 2*(self.setup_time + decay_time)
            return setup1 + decay + setup2 + decay_D
        seqs = [single_T1(int(round(tau_time.to("ns").magnitude))) for tau_time in params.array]
        return seqs

    # beta version
    # double f differential T1, adaptive time- for multiple MW sources for transitioning of two different states- measuring signal difference between +1 and -1
    def D_Diff_T1(self, params, pi1, pi2, tau):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        wait = longest_time - tau
        #init/readout setup
        aom_lag = \
            [(self.aom_lag, [self.channel_dict["laser"]], *self.IQ)]
        readout_high = \
            [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"],self.channel_dict["gate2"]], *self.IQ)]
        readout_low = \
            [(self.readout_time, [self.channel_dict["laser"],self.channel_dict["gate1"]], *self.IQ)]
        init = \
            [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
        buffer = \
            [(self.laser_buf, [], *self.IQ)]
        setup_high = aom_lag + readout_high + init + buffer
        setup_low = aom_lag + readout_low + init + buffer
        setup_time = self.aom_lag + self.readout_time + self.laser_time + self.laser_buf
        #experiment
        pi_pulse1 = \
            [(pi1, [self.channel_dict["SRS"]], *self.IQ)]
        pi_pulse2 = \
            [(pi2, [self.channel_dict["VSG"]], *self.IQ)]
        pi_pulse1_empty = \
            [(pi1, [], *self.IQ)]
        pi_pulse2_empty = \
            [(pi2, [], *self.IQ)]    
        tau_decay = \
            [(tau, [], *self.IQ)]
        decay1 = pi_pulse1 + pi_pulse2_empty + tau_decay + buffer
        decay2 = pi_pulse2 + pi_pulse1_empty + tau_decay + buffer
        decay_D = pi_pulse1_empty + pi_pulse2_empty + tau_decay + buffer
        decay_time = pi1 + pi2 + tau + self.laser_buf

        self.total_time = 3*(setup_time + decay_time)
        return setup1 + decay1 + setup2 + decay2 + setup3 + decay_D




#############################################################################################################################
    def Resetting_L_Ramsey(self, params, pi):
        '''
        :param params: the iteration array
        :param pi: length of the pi pulse
        :return: an array of pulse sequences
        '''
        longest_time = int(round(params["stop"].to("ns").magnitude))
        pi_ns = int(pi.to("ns").magnitude)
        def single_ramsey(tau):
            wait = longest_time-tau
            reset = \
                [(self.reset, [self.channel_dict["offr_laser"]], *self.IQ)]
            polarize = \
                [(self.polarize_time, [self.channel_dict["laser"], self.channel_dict["EOM"]], *self.IQ)]
            background = \
                [(self.settle, [], *self.IQ)]
            first_pi = \
                [(pi_ns//2, [self.channel_dict["switch"]], *self.IQ)]
            dephase = \
                [(tau, [], *self.IQ)]
            second_pi = \
                [(pi_ns // 2, [self.channel_dict["switch"]], *self.IQ)]
            probe = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
            bg_decay = \
                [(self.buf_after_init, [], *self.IQ)]
            readout = \
                [(self.readout_time, [self.channel_dict["gate"]], *self.IQ)]
            # Lockin Part
            L_first_pi = \
                [(pi_ns//2, [], *self.IQ)]
            L_dephase = \
                [(tau, [], *self.IQ)]
            L_second_pi = \
                [(pi_ns // 2, [], *self.IQ)]
            L_readout = \
                [(self.readout_time, [self.channel_dict["gate"], self.channel_dict["CTR"]], *self.IQ)]
            wait = \
                [(wait, [], *self.IQ)]
            return reset + polarize + background + first_pi + dephase + second_pi + wait + probe + bg_decay + readout + \
                   reset + polarize + background + L_first_pi + L_dephase + L_second_pi + wait + probe + bg_decay + L_readout
        self.total_time = self.reset + self.polarize_time + self.settle + pi_ns + longest_time + self.laser_time + self.buf_after_init + self.readout_time
        seqs = [single_ramsey(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs

    def Resetting_L_T2(self, params, pi, style=[[-1,0],[1,0],[1,0]]):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        pi_ns = int(round(pi.to("ns").magnitude))
        if style[0] == [0,0]:
            f_pi2 = [0,0]
            first_pi2gate = []
        else:
            f_pi2 = style[0] / (2 * np.linalg.norm(style[0]))
            first_pi2gate = [self.channel_dict["switch"]]
        if style[1] == [0,0]:
            L_pi = [0,0]
            pigate = []
        else:
            L_pi = style[1] / (2 * np.linalg.norm(style[1]))
            pigate  = [self.channel_dict["switch"]]
        if style[2] == [0,0]:
            s_pi2 = [0,0]
            second_pi2gate = []
        else:
            s_pi2 = style[2] / (2 * np.linalg.norm(style[2]))
            second_pi2gate = [self.channel_dict["switch"]]

        def single_T2(tau):
            wait = longest_time - tau
            reset = \
                [(self.reset, [self.channel_dict["offr_laser"]], *self.IQ)]
            polarize = \
                [(self.polarize_time, [self.channel_dict["laser"], self.channel_dict["EOM"]], *self.IQ)]
            background = \
                [(self.settle, [], *self.IQ)]
            first_pi2 = \
                [(pi_ns // 2, [self.channel_dict["switch"]], *self.IQ)]
            dephase = \
                [(tau // 2, [], *self.IQ)]
            flip = \
                [(pi_ns, [self.channel_dict["switch"]], *self.IQ)]
            rephase = \
                [(tau // 2, [], *self.IQ)]
            second_pi2 = \
                [(pi_ns // 2, [self.channel_dict["switch"]], *self.IQ)]
            probe = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
            bg_decay = \
                [(self.buf_after_init, [], *self.IQ)]
            readout = \
                [(self.readout_time, [self.channel_dict["gate"]], *self.IQ)]
            # Lockin Part
            L_background = \
                [(self.settle, [], *f_pi2)]
            L_first_pi2 = \
                [(pi_ns // 2, first_pi2gate, *f_pi2)]
            L_dephase = \
                [(tau // 2, [], *L_pi)]
            L_flip = \
                [(pi_ns, pigate, *L_pi)]
            L_rephase = \
                [(tau // 2, [], *s_pi2)]
            L_second_pi2 = \
                [(pi_ns // 2, second_pi2gate, *s_pi2)]
            L_readout = \
                [(self.readout_time, [self.channel_dict["gate"], self.channel_dict["CTR"]], *self.IQ)]
            wait = \
                [(wait, [], *self.IQ)]

            return reset + polarize + background + first_pi2 + dephase + flip + rephase + second_pi2 + wait + probe + bg_decay + readout + \
                   reset + polarize + L_background + L_first_pi2 + L_dephase + L_flip + L_rephase + L_second_pi2 + wait + probe + bg_decay + L_readout
        self.total_time = self.reset + self.polarize_time + self.settle + pi_ns*2 + longest_time + self.laser_time + self.buf_after_init + self.readout_time
        seqs = [single_T2(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs

    def Resetting_L_Y_T2(self, params, pi):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        pi_ns = int(round(pi.to("ns").magnitude))
        def single_T2(tau):
            wait = longest_time - tau
            reset = \
                [(self.reset, [self.channel_dict["offr_laser"]], *self.IQ)]
            polarize = \
                [(self.polarize_time, [self.channel_dict["laser"], self.channel_dict["EOM"]], *self.IQ)]
            background = \
                [(self.settle, [], -0.5,0)]
            first_pi2 = \
                [(pi_ns // 2, [self.channel_dict["switch"]], -0.5,0)]
            dephase = \
                [(tau // 2, [], 0,0.5)]
            flip = \
                [(pi_ns, [self.channel_dict["switch"]], 0,0.5)]
            rephase = \
                [(tau // 2, [], 0.5,0)]
            second_pi2 = \
                [(pi_ns // 2, [self.channel_dict["switch"]], 0.5,0)]
            probe = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
            bg_decay = \
                [(self.buf_after_init, [], *self.IQ)]
            readout = \
                [(self.readout_time, [self.channel_dict["gate"]], *self.IQ)]
            # Lockin Part
            L_background = \
                [(self.settle, [], 0.5,0)]
            L_first_pi2 = \
                [(pi_ns // 2, [self.channel_dict["switch"]], 0.5,0)]
            L_dephase = \
                [(tau // 2, [], 0,0.5)]
            L_flip = \
                [(pi_ns, [self.channel_dict["switch"]], 0,0.5)]
            L_rephase = \
                [(tau // 2, [], 0.5,0)]
            L_second_pi2 = \
                [(pi_ns // 2, [self.channel_dict["switch"]], 0.5,0)]
            L_readout = \
                [(self.readout_time, [self.channel_dict["gate"], self.channel_dict["CTR"]], *self.IQ)]
            wait = \
                [(wait, [], *self.IQ)]

            return reset + polarize + background + first_pi2 + dephase + flip + rephase + second_pi2 + wait + probe + bg_decay + readout + \
                   reset + polarize + L_background + L_first_pi2 + L_dephase + L_flip + L_rephase + L_second_pi2 + wait + probe + bg_decay + L_readout
        self.total_time = self.reset + self.polarize_time + self.settle + pi_ns*2 + longest_time + self.laser_time + self.buf_after_init + self.readout_time
        seqs = [single_T2(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs


    def Resetting_L_CPMG(self, params, pi, N):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        pi_ns = int(round(pi.to("ns").magnitude))

        def CPMG_core(tau, N, IQ=[1,0]):
            L_pi2_IQ = IQ / (2 * np.linalg.norm(IQ))
            L_pi2 = \
                [(pi_ns // 2, [self.channel_dict["switch"]], *L_pi2_IQ)]
            pi2 = \
                [(pi_ns // 2, [self.channel_dict["switch"]], *self.IQ)]
            wait_pi2 = \
                [(tau // (2 * N), [], *self.IQ)]
            pi = [(pi_ns, [self.channel_dict["switch"]], *self.IQ)]
            return L_pi2 + N*( wait_pi2 + pi + wait_pi2) + pi2

        def single_T2(tau):
            wait = longest_time - tau
            reset = \
                [(self.reset, [self.channel_dict["offr_laser"]], *self.IQ)]
            polarize = \
                [(self.polarize_time, [self.channel_dict["laser"], self.channel_dict["EOM"]], *self.IQ)]
            background = \
                [(self.settle, [], *self.IQ)]
            CPMG_Core = CPMG_core(tau, N=N, IQ=[1,0])
            probe = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
            bg_decay = \
                [(self.buf_after_init, [], *self.IQ)]
            readout = \
                [(self.readout_time, [self.channel_dict["gate"]], *self.IQ)]
            # Lockin Part
            L_background = \
                [(self.settle, [], -0.5, 0)]
            L_CPMG_Core = CPMG_core(tau, N=N, IQ=[-1,0])
            L_readout = \
                [(self.readout_time, [self.channel_dict["gate"], self.channel_dict["CTR"]], *self.IQ)]
            wait = \
                [(wait, [], *self.IQ)]

            return reset + polarize + background + CPMG_Core + wait + probe + bg_decay + readout + \
                   reset + polarize + L_background + L_CPMG_Core + wait + probe + bg_decay + L_readout
        
        self.total_time = self.reset + self.polarize_time + self.settle + pi_ns*(1+N) + longest_time + self.laser_time + self.buf_after_init + self.readout_time
        seqs = [single_T2(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs

    def Resetting_L_T1(self, params, pi):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        pi_ns = int(round(pi.to("ns").magnitude))
        def single_T1(tau):
            #wait = self.reset + self.polarize_time + self.buf_after_init * 2 + self.settle + longest_time + self.laser_time + self.readout_time - mw_on
            wait = longest_time - tau
            reset = \
                [(self.reset, [self.channel_dict["offr_laser"]], *self.IQ)]
            polarize = \
                [(self.polarize_time, [self.channel_dict["laser"], self.channel_dict["EOM"]], *self.IQ)]
            background = \
                [(self.settle, [], *self.IQ)]
            tau_wait = \
                [(tau, [], *self.IQ)]
            flip = \
                [(pi_ns, [self.channel_dict["switch"]], *self.IQ)]

            probe = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
            bg_decay = \
                [(self.buf_after_init, [], *self.IQ)]
            readout = \
                [(self.readout_time, [self.channel_dict["gate"]], *self.IQ)]
            # Lockin Part
            L_flip = \
                [(pi_ns, [], 0, 0)]
            L_readout = \
                [(self.readout_time, [self.channel_dict["gate"], self.channel_dict["CTR"]], 0, 0)]
            wait = \
                [(wait, [], 0, 0)]
            return reset + polarize + background + flip + tau_wait + probe + bg_decay + readout  + wait + \
                   reset + polarize + background + L_flip + tau_wait + probe + bg_decay + L_readout + wait

        self.total_time = self.reset + self.polarize_time + self.settle + pi_ns + longest_time + self.laser_time + self.buf_after_init + self.readout_time
        seqs = [single_T1(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs

    def Resetting_L_T1_Adaptive(self, params, pi):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        pi_ns = int(round(pi.to("ns").magnitude))
        def single_T1(tau):
            #wait = self.reset + self.polarize_time + self.buf_after_init * 2 + self.settle + longest_time + self.laser_time + self.readout_time - mw_on
            wait = longest_time - tau
            reset = \
                [(self.reset, [self.channel_dict["offr_laser"]], *self.IQ)]
            polarize = \
                [(self.polarize_time, [self.channel_dict["laser"], self.channel_dict["EOM"]], *self.IQ)]
            background = \
                [(self.settle, [], *self.IQ)]
            tau_wait = \
                [(tau, [], *self.IQ)]
            flip = \
                [(pi_ns, [self.channel_dict["switch"]], *self.IQ)]

            probe = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
            bg_decay = \
                [(self.buf_after_init, [], *self.IQ)]
            readout = \
                [(self.readout_time, [self.channel_dict["gate"]], *self.IQ)]
            # Lockin Part
            L_flip = \
                [(pi_ns, [], 0, 0)]
            L_readout = \
                [(self.readout_time, [self.channel_dict["gate"], self.channel_dict["CTR"]], 0, 0)]
            wait = \
                [(wait, [], 0, 0)]
            return reset + polarize + background + flip + tau_wait + probe + bg_decay + readout  + \
                   reset + polarize + background + L_flip + tau_wait + probe + bg_decay + L_readout
        
        self.total_time = self.reset + self.polarize_time + self.settle + pi_ns + longest_time + self.laser_time + self.buf_after_init + self.readout_time
        seqs = [single_T1(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs

    def res_background_Topt(self, params):
        start_time = int(round(params["start"].to("ns").magnitude))
        end_time = int(round(params["stop"].to("ns").magnitude))
        bin_time = int(round(params["step"].to("ns").magnitude))
        num_bins = len(params.array)
        dur = end_time - start_time
        def single_Topt(i):
            # While the bin overlaps with the laser but not the transient
            remainin_laser_overlap = self.laser_time - bin_time*(i+1) - start_time
            if remainin_laser_overlap > 0:
                excitation = \
                        [(int(start_time+i*bin_time), [self.channel_dict["laser"]], *self.IQ)]
                binned_excitation = \
                        [(bin_time, [self.channel_dict["laser"], self.channel_dict["gate"]], *self.IQ)]
                rest_excitation = \
                        [(int(self.laser_time - bin_time*(i+1) - start_time), [self.channel_dict["laser"]], *self.IQ)]
                wait = \
                        [(self.settle, [], *self.IQ)]
                return excitation + binned_excitation + rest_excitation + wait
            # While the bin overlaps with transient but not the laser
            else:
                bin_in_laser = bin_time + remainin_laser_overlap
                if bin_in_laser < 0:
                    rev_bin_number = num_bins - i
                    excitation = \
                        [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
                    before_bin = \
                        [(int(i*bin_time) - self.laser_time, [], *self.IQ)]
                    binned_PL = \
                        [(bin_time, [self.channel_dict["gate"]], *self.IQ)]
                    after_bin = \
                        [(int(self.settle +self.laser_time - bin_time*(i+1)+1), [], *self.IQ)]
                    return excitation + before_bin + binned_PL + after_bin
                # If the bin overlaps with both the laser and the transient
                else:
                    bin_in_readout = -1*remainin_laser_overlap
                    excitation1 = \
                        [(int(self.laser_time - bin_in_laser), [self.channel_dict["laser"]], *self.IQ)]
                    excitation2 = \
                        [(bin_in_laser, [self.channel_dict["laser"], self.channel_dict["gate"]], *self.IQ)]
                    readout1 = \
                        [(bin_in_readout, [self.channel_dict["gate"]], *self.IQ)]
                    readout2 = \
                        [(int(self.settle-bin_in_readout), [], *self.IQ)]
                    return excitation1 + excitation2 + readout1 + readout2
        self.total_time = end_time
        seqs = [single_Topt(i) for i in np.arange(num_bins)]
        return seqs

    def res_Topt(self, params):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        bin_time = int(round(params["step"].to("ns").magnitude))
        def single_T1(start):
            wait = longest_time-start+bin_time
            excitation = \
                [(self.laser_time, [self.channel_dict["laser"]], *self.IQ)]
            bg_decay = \
                [(self.buf_after_init, [], *self.IQ)]
            before_bin = \
                [(start, [], *self.IQ)]
            readout = \
                [(bin_time, [self.channel_dict["gate"]], *self.IQ)]
            wait = \
                [(wait, [], *self.IQ)]
            return excitation + bg_decay + before_bin + readout + wait
        self.total_time = self.laser_time + self.buf_after_init + longest_time + bin_time
        seqs = [single_T1(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs


    def res_Topt_MW(self, params):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        bin_time = int(round(params["step"].to("ns").magnitude))
        def single_T1(start):
            wait = longest_time-start+bin_time+self.buf_after_readout
            excitation = \
                [(self.laser_time, [self.channel_dict["laser"], self.channel_dict["switch"]], *self.IQ)]
            bg_decay = \
                [(self.buf_after_init, [self.channel_dict["switch"]], *self.IQ)]
            before_bin = \
                [(start, [self.channel_dict["switch"]], *self.IQ)]
            readout = \
                [(bin_time, [self.channel_dict["gate"], self.channel_dict["switch"]], *self.IQ)]
            wait = \
                [(wait, [self.channel_dict["switch"]], *self.IQ)]
            return excitation + bg_decay + before_bin + readout + wait
        self.total_time = self.laser_time + self.buf_after_init + longest_time + bin_time
        seqs = [single_T1(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs

    def off_res_Topt(self, params):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        bin_time = int(round(params["step"].to("ns").magnitude))
        def single_T1(start):
            wait = longest_time-start+bin_time+self.buf_after_readout
            excitation = \
                [(self.laser_time, [self.channel_dict["offr_laser"]], *self.IQ)]
            bg_decay = \
                [(self.buf_after_init, [], *self.IQ)]
            before_bin = \
                [(start, [], *self.IQ)]
            readout = \
                [(bin_time, [self.channel_dict["gate"]], *self.IQ)]
            wait = \
                [(wait, [], *self.IQ)]
            return excitation + bg_decay + before_bin + readout + wait
        self.total_time = self.laser_time + self.buf_after_init + longest_time + bin_time
        seqs = [single_T1(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs


    def red_Laser_Power(self, params):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        def single_RLP(e_time):
            wait = longest_time-e_time+self.buf_after_readout
            #wait = self.buf_after_readout
            excitation = \
                [(e_time, [self.channel_dict["offr_laser"]], *self.IQ)]
            bg_decay = \
                [(self.buf_after_init, [], *self.IQ)]
            readout = \
                [(self.readout_time, [self.channel_dict["gate"]], *self.IQ)]
            wait = \
                [(wait, [], *self.IQ)]
            return excitation + bg_decay + readout + wait
        self.total_time = longest_time + self.buf_after_init + self.readout_time + self.buf_after_readout
        seqs = [single_RLP(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs

    def Laser_Power(self, params):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        def single_LP(e_time):
            wait = longest_time-e_time+self.buf_after_readout
            #wait = self.buf_after_readout
            excitation = \
                [(e_time, [self.channel_dict["laser"]], *self.IQ)]
            bg_decay = \
                [(self.buf_after_init, [], *self.IQ)]
            readout = \
                [(self.readout_time, [self.channel_dict["gate"]], *self.IQ)]
            wait = \
                [(wait, [], *self.IQ)]
            return excitation + bg_decay + readout + wait
        self.total_time = longest_time + self.buf_after_init + self.readout_time + self.buf_after_readout
        seqs = [single_LP(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs

    def Laser_Power_MW(self, params):
        longest_time = int(round(params["stop"].to("ns").magnitude))
        def single_LP(e_time):
            wait = longest_time-e_time+self.buf_after_readout
            #wait = self.buf_after_readout
            excitation = \
                [(e_time, [self.channel_dict["laser"], self.channel_dict["switch"]], *self.IQ)]
            bg_decay = \
                [(self.buf_after_init, [self.channel_dict["switch"]], *self.IQ)]
            readout = \
                [(self.readout_time, [self.channel_dict["gate"], self.channel_dict["switch"]], *self.IQ)]
            wait = \
                [(wait, [self.channel_dict["switch"]], *self.IQ)]
            return excitation + bg_decay + readout + wait
        self.total_time = longest_time + self.buf_after_init + self.readout_time + self.buf_after_readout
        seqs = [single_LP(int(round(mw_time.to("ns").magnitude))) for mw_time in params.array]
        return seqs
