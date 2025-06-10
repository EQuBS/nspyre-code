"""DLnsec laser driver.

https://labs-electronics.com/

Author: Jacob Feder, Will Burke
Date: 2/22/2022
"""
import time
import logging

import serial

_logger = logging.getLogger(__name__)

class DLnsec():
    def __init__(self, serial_port: str, timeout=1.0):
        """
        Args:
            serial_port: serial COM port (see pyserial docs)
        """
        self.serial_port = serial_port
        self.timeout = timeout
        self.connected = False
        #self.open() # Added by Rolando, to open the connection when the class is instantiated.

    def open(self):
        """Connect to the laser."""
        self.conn = serial.Serial(self.serial_port, baudrate=9600, timeout=self.timeout)
        self.conn.reset_input_buffer()
        self.conn.reset_output_buffer()
        self.reboot()
        # query the laser serial number
        self.idn = self._query('*IDN')
        if not self.idn:
            raise RuntimeError('Failed getting laser ID number.')
        self.connected = True
        _logger.info(f'Connected to DLnsec [{self.idn}].')

    def close(self):
        """Disconnect from the laser."""
        self.connected = False
        self.conn.close()

    def __str__(self):
        if self.connected:
            return f'[{self.idn}]'
        else:
            return f'DLnsec [Not Connected]'

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.off()
        self.close()

    def _send_raw(self, msg):
        """Send a command to the laser."""
        # add a newline and encode the message into a binary string
        msg_bin = (msg + '\n').encode('ascii')
        # send the message on the serial port
        self.conn.write(msg_bin)
        _logger.debug(f'Sent message to DLnsec: [{msg}].')
        # wait for the laser to process the message
        time.sleep(0.1)

    def _send(self, msg):
        """Send a command to the laser and check for errors."""
        # number of times to try sending the command
        attempts = 3
        while attempts:
            # send the command
            self._send_raw(msg)
            # ask if an error occurred
            response = self._query('ERR?')
            if response == '0; No error':
                break
            else:
                attempts -= 1
                err_str = f'Failed sending DLnsec command [{msg}]: response [{response}].'
                if attempts:
                    _logger.warning(err_str)
                else:
                    raise RuntimeError(err_str)
                # wait a moment before trying again
                time.sleep(0.25)

    def _query(self, msg):
        """Send a query command to the laser and return the response."""
        self._send_raw(msg)
        # receive the response
        response = self.conn.read_until(b'\n\r')
        response = response.decode('ascii').strip('\n\r')
        _logger.debug(f'Response from DLnsec: [{response}].')

        return response

    def set_power(self, p):
        """Set the output power (integer percentage)"""
        if not isinstance(p, int) or p > 100 or p < 0:
            raise ValueError(f'The power [{p}] must be an integer between 0-100.')
        self._send(f'PWR{p}')
        _logger.info(f'Setting {self} power to [{p}%].')

    def get_power(self):
        """Get the output power (integer percentage)"""
        p = int(self._query(f'PWR?'))
        _logger.info(f'Got {self} power [{p}%]')
        return p

    def get_error(self):
        """Getting error"""
        err = self._query(f'ERR?')
        _logger.info(f'Checking for error in {self}. Error response is: {err}.')
        
    def cw_mode(self):
        """Put the laser into CW mode. This isn't a real CW mode, because a low
        on the trigger input will still turn the lasing off."""
        self._send('LASE')
        _logger.info(f'Setting {self} to CW mode.')

    def trig_mode(self):
        """Put the laser into external trigger mode."""
        self._send('EXT')
        _logger.info(f'Setting {self} to external trigger mode.')

    def on(self):
        """Turn the output stage on."""
        self._send('*ON')
        _logger.info(f'Turned {self} power on.')

    def off(self):
        """Turn the output stage off."""
        self._send('*OFF')
        _logger.info(f'Turned {self} power off.')

    def reboot(self):
        """Reboot the laser, applying default settings on startup."""
        self._send_raw('*RBT')
        # wait for the laser to fully restart
        time.sleep(2)
        _logger.info(f'Rebooted {self}.')
