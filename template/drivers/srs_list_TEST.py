"""
4/15/2026 by Rolando A. Fimbres G.
This is a test script to test the srs list functionality in the context of frequency sweeps.
The Spectrum analyzer will be used to visualize the sweep.
"""
import srs_386 as srs
import time
import numpy as np
from nspyre import InstrumentGateway

with InstrumentGateway() as gw:
    data_points = 40
    frequencies = np.linspace(2.67e9, 3.07e9, data_points)  # Example frequency span around the NV center's resonance

    gw.sg.set_frequency(2.87e9)
    gw.sg.set_rf_amplitude(-30.0)
    gw.sg.set_rf_toggle(1)

    time.sleep(2.5)

    gw.sg.set_rf_toggle(0)

    print(frequencies)

    gw.sg.list_load_frequencies(frequencies)

    gw.sg.set_rf_toggle(1)
    
    # We set a timer
    start_time = time.perf_counter()

    for freq in frequencies:
        gw.sg.list_trigger()
        # time.sleep(0.1)  # Adjust the delay as needed for your system's response time

    end_time = time.perf_counter()
    gw.sg.set_rf_toggle(0)
    print("Frequency sweep completed. Check the spectrum analyzer for results.")
    print(f"Total time taken: {end_time - start_time:.4f} seconds")


