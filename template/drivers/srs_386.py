'''
Stanford RS SG396 Driver for Updated Nspyre

Based on: Implementation of SG396 signal generator
          Author: Kevin Miao & Berk Diler
          Date: 12/15/2015 & 8/21/2017

Author: Evan Villafranca
Date: 8/25/2022

##########################################################

Rolando A. Fimbres G.     8/7/2025

The syst. we are using is SG386. I haven't changed the name of
the class (SG396). Later, I'll work on some tests to verify its
functions.

##########################################################

Rolando A. Fimbres G.     8/8/2025

I've began to noticed some differences between the SG380 and SG390 Series.
One of the available Modulation Types. The current script includes modulations
not available for our system. Since we're working with SG386, slight changes 
must be made, such as the ordered dictionary for modulation types.
I'll keep an eye on future changes needed.

'''

import logging
logger = logging.getLogger(__name__)

from collections import OrderedDict

from pyvisa import ResourceManager

logger = logging.getLogger(__name__)
#TXZ: Why you have two loggers here?

#This SRS driver take the imput MW power in unit of W, and transform it to dBm here
from math import log10
def W_to_dBm(power):
    return 10*log10(1000*power)

class SG386:
    DEFAULTS = {
        'COMMON': {
            'write_termination': '\r\n',
            'read_termination': '\r\n',
        }
    }
    MODULATION_TYPE = OrderedDict([
        ('AM', 0),
        ('FM', 1),
        ('Phase', 2),
        ('Sweep', 3),
        ('Pulse', 4),
        ('Blank', 5),
        ('IQ', 6),
    ])
    MODULATION_FUNCTION = OrderedDict([
        ('sine', 0),
        ('ramp', 1),
        ('triangle', 2),
        ('square', 3),
        ('noise', 4),
        ('external', 5)
    ])

    def __init__(self, address):

        '''
        add pyvisa open function to connect to IP address
        '''

        self.rm = ResourceManager('@py')
        self.address = address
        #print("SRS address is:",address)
        self.device = self.rm.open_resource(self.address)
        logger.info(f"Connected to SG396 [{self.address}].")

        self.output_en = False
        self._amplitude = 0.0
        self._frequency = 100e3


    def get_lf_amplitude(self):
        """
        low frequency amplitude (BNC output)
        """
        return float(self.device.query('AMPL?'))

    def set_lf_amplitude(self, value):
        #self.device.write('AMPL{:.2f}'.format(W_to_dBm(value)))
        self.device.write('AMPL{:.2f}'.format(value))


    def get_rf_amplitude(self):
        """
        RF amplitude (Type N output)
        """
        return float(self.device.query('AMPR?'))

    def set_rf_amplitude(self, value):
       #self.device.write(f"AMPR{W_to_dBm(value)}")
       self.device.write(f"AMPR{value}")  


    def get_lf_toggle(self):
        """
        low frequency output state
        """
        return self.device.query('ENBL?')
    
    def set_lf_toggle(self, value):
        self.device.write(f"ENBL{value}")


    def get_rf_toggle(self):
        """
        RF output state
        """
        return self.device.query('ENBR?')

    # 1 = True (on), 0 = False (off)
    def set_rf_toggle(self, value):
        self.device.write(f"ENBR{value}")

    def get_lf_offset(self):
        """
        low frequency offset voltage
        """
        return self.device.query('OFSL?')

    def set_lf_offset(self, value):
        self.device.write(f"OFSL{value}")

    def get_phase(self):
        """
        carrier phase
        """
        return self.device.query('PHAS?')

    def set_phase(self, value):
        self.device.write(f"PHAS{value}")
        

    def set_rel_phase(self):
        """
        sets carrier phase to 0 degrees
        """
        self.device.write('RPHS')

    def get_mod_toggle(self):
        """
        Modulation State
        """
        return int(self.device.query('MODL?'))

    def set_mod_toggle(self, value):
        self.device.write(f"MODL {value}")

    def get_mod_type(self):
        """
        Modulation State
        """
        return int(self.device.query('TYPE?'))

    def set_mod_type(self, value):
        self.device.write(f"TYPE {value}")

    def get_mod_function(self):
        """
        Modulation Function
        """
        return int(self.device.query('MFNC?'))

    def set_mod_function(self, value):
        self.device.write(f"MFNC {value}")

    def get_qmod_function(self):
        return int(self.device.query('QFNC?'))

    def set_qmod_function(self, value):
        self.device.write(f"QFNC {value}")
    
    # units = "Hz", limits = (0.1, 100.e3))
    def get_mod_rate(self):
        """
        Modulation Rate
        """
        return float(self.device.query('RATE?'))
    
    def set_mod_rate(self, value):
        self.device.write(f"RATE {value}")
    
    # units = "pc", limits = (0., 100.))  
    # created percentage unit 'pc' to bypass problems with the instrument manager and pint
    def get_AM_mod_depth(self):
        """
        AM Modulation Depth
        """
        return float(self.device.query('ADEP?'))

    def set_AM_mod_depth(self, value):
        self.device.write(f"ADEP {value}")
    
    # units = "Hz", limits = (0.1, 8.e6))
    def get_FM_mod_dev(self):
        """
        FM Modulation Deviation
        """
        return float(self.device.query("FDEV?"))
    
    
    def set_FM_mod(self, value):
        self.device.write(f"FDEV {value}")

    def get_frequency(self):
        """
        signal frequency
        """
        return self.device.query('FREQ?')
    
    def set_frequency(self, value):
        """Change the frequency (Hz)"""
        if value < 100e3 or value > 6e9:
            raise ValueError("Frequency must be in range [100 kHz, 6 GHz].")
        
        self.device.write(f"FREQ{value}")
        
        logger.info(f"Set frequency to {value} Hz")

    def amplitude(self):
        return self._amplitude

    def set_amplitude(self, value):
        """Change the amplitude (dBm)"""
        if value < -30 or value > 10:
            raise ValueError("Amplitude must be in range [-30 dBm, 10 dBm].")

        logger.info(f"Set amplitude to {value} dBm")

    def calibrate(self):
        logger.info("SG396 calibration succeeded.")

    def get_sfunction(self):
        """Get the Sweep Modulation Function"""
        return self.device.query('SFNC?')
    
    def set_sfunction(self, value):
        """Set the Sweep Modulation Function"""
        allowed = (0, 1, 2, 5)
        # If value is a string, map it to its integer using the dictionary
        if isinstance(value, str):
            value_int = self.MODULATION_FUNCTION.get(value)
        else:
            value_int = value
            # Find the key for this value_int
            key = next((k for k, v in self.MODULATION_FUNCTION.items() if v == value_int), str(value_int))
        if value_int not in allowed:
            logger.error(f"Invalid Sweep Modulation Function: {value} (mapped: {value_int})")
            raise ValueError("Value must be 0, 1, 2, or 5 (or their string keys).")
        self.device.write(f"SFNC {value_int}")
        logger.info(f"Set Sweep Modulation Function to {key} ({value_int})")

    def get_srate(self):
        """Get the Sweep Rate"""
        return (self.device.query('SRAT?'))

    def set_srate(self, value):
        """Set the Sweep Rate"""
        if not (1e-6 <= value <= 120):
            logger.error(f"Sweep Rate {value} is out of allowed range [1e-6, 120] Hz.")
            raise ValueError("Sweep Rate must be between 1e-6 and 120 Hz.")
        self.device.write(f"SRAT {value}")
        logger.info(f"Set Sweep Rate to {value}")

    def get_sdeviation(self):
        """Get the Sweep Deviation"""
        return (self.device.query('SDEV?'))

    def set_sdeviation(self, value):
        """Set the Sweep Deviation"""
        if not (0.1 <= value <= 1e9):
            logger.error(f"Sweep Deviation {value} is out of allowed range [0.1, 1e9] Hz.")
            raise ValueError("Sweep Deviation must be between 0.1 and 1e9 Hz.")
        self.device.write(f"SDEV {value}")
        logger.info(f"Set Sweep Deviation to {value}")

    # Update: 4/13/2026 Rolando A. Fimbres G.- Added to make use of load list capability of the SG386. 
    # After testing we will check if this allows for faster frequency switching during scans.
    LIST_STATE_LEN = 15

    def write_scpi(self, cmd):
        """Write a raw SCPI command."""
        self.device.write(cmd)

    def query_scpi(self, cmd):
        """Query a raw SCPI command and return stripped text."""
        return str(self.device.query(cmd)).strip()

    def opc(self):
        """
        Return True when all prior commands have completed.
        Uses *OPC? as documented by the SG380 manual.
        """
        return int(float(self.query_scpi('*OPC?'))) == 1

    def clear_status(self):
        self.write_scpi('*CLS')

    def last_error(self):
        """Return the next entry from the SG error queue."""
        return self.query_scpi('LERR?')

    def drain_errors(self, max_reads=20):
        """
        Read out the SG error queue until it reports no error.
        Returns a list of non-zero errors.
        """
        errs = []
        for _ in range(max_reads):
            err = self.last_error()
            # SRS returns 0 / no-error when empty; keep the check permissive.
            if err.startswith('0'):
                break
            errs.append(err)
        return errs

    def option_installed(self, option_number):
        """Query installed option number, e.g. 3 for IQ."""
        return int(float(self.query_scpi(f'OPTN? {int(option_number)}'))) == 1

    def get_frequency_float(self):
        return float(self.query_scpi('FREQ?'))

    def list_delete(self):
        self.write_scpi('LSTD')

    def list_create(self, size):
        size = int(size)
        if size < 1:
            raise ValueError('List size must be >= 1.')
        ok = int(float(self.query_scpi(f'LSTC? {size}')))
        if ok != 1:
            raise RuntimeError(f'Could not create SG386 list of size {size}.')

    def list_enable(self, enable=True):
        self.write_scpi(f'LSTE {1 if enable else 0}')

    def list_reset(self):
        self.write_scpi('LSTR')

    def list_index(self, index=None):
        """
        Query or set the current list index.
        """
        if index is None:
            return int(float(self.query_scpi('LSTI?')))
        index = int(index)
        self.write_scpi(f'LSTI {index}')
        return index

    def list_size(self):
        return int(float(self.query_scpi('LSTS?')))

    def list_set_point(self, index, state_fields):
        """
        state_fields must be a length-15 iterable matching the SG380 list-state format.
        Use 'N' for unchanged fields.
        """
        if len(state_fields) != self.LIST_STATE_LEN:
            raise ValueError(
                f'Each list state must have {self.LIST_STATE_LEN} fields.'
            )
        payload = ','.join(str(x) for x in state_fields)
        self.write_scpi(f'LSTP {int(index)},{payload}')

    def list_set_frequency_point(self, index, freq_hz):
        """
        Convenience helper: only change frequency, leave all other fields unchanged.
        """
        self.list_set_point(
            index,
            [f'{float(freq_hz):.12g}'] + ['N'] * 14
        )

    def list_load_frequencies(self, freqs_hz, enable=True):
        """
        Build a frequency-only list.
        """
        freqs_hz = list(freqs_hz)
        if not freqs_hz:
            raise ValueError('freqs_hz must not be empty.')

        # Delete any old list, create a new one, fill it, and arm it.
        self.list_delete()
        self.list_create(len(freqs_hz))
        for i, f_hz in enumerate(freqs_hz):
            self.list_set_frequency_point(i, f_hz)

        self.list_reset()
        self.list_enable(enable)

    def list_trigger(self, wait_until_done=False):
        """
        Advance to the next list point.
        """
        self.write_scpi('*TRG')
        if wait_until_done:
            return self.opc()
        return True