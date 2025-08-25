from nspyre import InstrumentGateway
import time

start_time = time.time()

with InstrumentGateway() as gw:
    gw.sg.set_rf_amplitude(-15)    # Sets the RF amplitude to -15 dBm
    gw.sg.set_frequency(2.87e9)     # Sets frequency to 2.5 GHz
    gw.sg.set_mod_type(3)          # Sets the modulation type to option 3 (Sweep)
    gw.sg.set_sfunction(1)         # A ramp function will drive the sweep
    gw.sg.set_sdeviation(200e6)    # Deviation from the frequency set will be +/- 200 MHz
    gw.sg.set_srate(0.1)             # Sets the sweep rate to 0.1 Hz
    gw.sg.set_mod_toggle(1)        # Turns Modulation On
    gw.sg.set_rf_toggle(1)         # Turns RF On
    

    # We add sleep time to observe the frequency sweep.
    time.sleep(53)
    end_time = time.time()

    gw.sg.set_mod_toggle(0)        # Turns Modulation Off
    gw.sg.set_rf_toggle(0)         # Turns RF Off

    elapsed_time = end_time - start_time
    print(f"Total elapsed time: {elapsed_time:.6f} seconds")

    #gw.sg.set_rf_amplitude(-25)    # Sets the RF amplitude to -15 dBm
    """ gw.sg.set_frequency(2.87e9)    # Sets frequency to 2.87 GHz

    

    i = 0

    for i in range(7):
        gw.sg.set_rf_toggle(1)
        gw.sg.set_rf_amplitude(-20)
        time.sleep(2)
        gw.sg.set_rf_toggle(0)
        time.sleep(2)

    gw.sg.set_rf_toggle(0)
    print("Done :)") """




    