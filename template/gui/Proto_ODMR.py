"""ODMR Testing before implementation into spin measurements"""

from nspyre import InstrumentGateway, StreamingList
import numpy as np
import spin_measurements
import time
from rpyc.utils.classic import obtain
import matplotlib.pyplot as plt
import TimeTagger as tt
from TimeTagger import GatedChannel, CountBetweenMarkers, CHANNEL_UNUSED
#import pulsestreamer as ps
from pulsestreamer import PulseStreamer, OutputState 
import sys
sys.path.append('C:\\Users\\XieLab\\Documents\\Confocal_System\\Drive_template-main\\template-main\\src\\template\\gui')

ps = PulseStreamer("169.254.8.2")

tagger = tt.createTimeTagger()

with InstrumentGateway() as gw:
    """Setting of initial parameters to be taken from gui_ODMR.py"""
    start_freq = 2E9 #Hz
    stop_freq = 3E9 #Hz
    num_points = 100
    sweep_dev = 500E6
    sweep_rate = 1 # Hz
    iterations = 1
    probe_time = 5E-5 # seconds
    runs = 1
    rf_amp = -20
    # Following secondary params. to be calculated from initial taken
    freq_step = (stop_freq - start_freq) / num_points
    sweep_time = 1 / sweep_rate
    bin_width = int((sweep_time / num_points)*1E12) # Num. in picoseconds
    n_values = num_points
    duration = int(bin_width * n_values)

    # We limit the digits for the sig. gen.
    np.set_printoptions(precision=6)

    frequencies = np.linspace(start_freq, stop_freq, num_points)

    sig_sweeps = StreamingList()
    bg_sweeps = StreamingList()

    """Pulse pattern design to be used and set in ps82.py"""
    
    #cw_seq = gw.ps.CW_ODMR_R(runs, probe_time*1E9, read_time=5E-6*1E9)
    
    # Pulse Streamer Channels:
    laser_ch = 7 
    gate_ch = 0
    sync_ch = 1
    spcm_gate = 3
    # Pattern corresponding to gw.ps.CW_ODMR_R() function
    read_time = 5E-6*1E9
    iQ0 = [0.0098, 0.0010]
    iQ = iQ0
    iQpx = [0.497, 0.001]
    iQnx = [-0.479, 0.001]

    seq_on = ps.createSequence()
    #seq_off = self.ps.createSequence()
        
    laser_patt = [((probe_time) + read_time, 1)]
    gate_patt  = [(read_time, 1), (probe_time-read_time, 0), (read_time, 1), (probe_time-read_time, 0)]
    mw_I_patt = [(probe_time, iQpx[0]), (probe_time, iQ[0])]
    mw_Q_patt = [(probe_time, iQpx[1]), (probe_time, iQ[1])]
    sync_patt = [(10, 1), (probe_time-10, 0)]
    #gate_patt = [(probe_time, 1)]

    seq_on.setDigital(laser_ch, laser_patt)
    seq_on.setDigital(sync_ch, sync_patt)
    seq_on.setDigital(gate_ch, gate_patt)
    seq_on.setAnalog(0, mw_I_patt)
    seq_on.setAnalog(1, mw_Q_patt)

    # Turn the laser & SPCM gate on
    #gw.ps.gate_on()
    ps.constant(OutputState([spcm_gate, laser_ch], 0.0, 0.0))
    gw.laser.cw_mode()
    gw.laser.on()
    
    # Trigger levels for the TT, and counter event (gw.daq.CBM)
    tt_gate = 1
    tt_sync = 2
    tt_spcm = 3
    gw.daq.set_trigger_level([tt_gate, tt_sync, tt_spcm], 1.3) # set trigger level for Time Tagger
    gated_detector_vch = GatedChannel(tagger, tt_spcm, tt_gate, -tt_gate)
    # We get the virtual
    gated_detector = gated_detector_vch.getChannel()
    cbm = CountBetweenMarkers(tagger, gated_detector, tt_sync, CHANNEL_UNUSED, len(frequencies))

    # Set the sig. gen parameters.
    gw.sg.set_rf_amplitude(rf_amp)
    gw.sg.set_mod_type('IQ')
    gw.sg.set_rf_toggle(1)
    gw.sg.set_mod_toggle(1)
    gw.sg.set_qmod_function('external')

    for f, freq in enumerate(frequencies):
        gw.sg.set_frequency(freq)
        cbm.startFor(duration) #cbm.start()
        #gw.daq.sync()
        ps.stream(seq_on, 1)

        ready = False

        while ready is False:
            time.sleep(0.2)
            print("Waiting...")
            ready = cbm.ready()
            counts = obtain(cbm.getData())
            sig, bg = spin_measurements.digital_math(counts, 'ODMR')

        # Record photon counts
        sig_sweeps[-1][1][f] = sig
        bg_sweeps[-1][1][f] = bg
        # Notify streamlist
        sig_sweeps.updated_item(-1)
        bg_sweeps.updated_item(-1)

    gw.sg.set_rf_toggle(0)
    gw.sg.set_mod_toggle(0)
    gw.laser.off()
    ps.constant(OutputState([], 0.0, 0.0))
    ps.reset()
    tt.freeTimeTagger(tagger)

    plt.figure()
    plt.plot(frequencies, sig, label='Signal')
    plt.plot(frequencies, bg, label='Background')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Counts')
    plt.title('ODMR Signal and Background')
    plt.legend()
    plt.show()

    """Pulsed ODMR pattern
    gw.ps.Pulsed_ODMR(iterations, probe_time*1E9, read_time*1E9)
    """