#!/usr/bin/env python
"""
Start up an instrument server to host drivers. For the purposes of this demo,
it's assumed that this is running on the same system that will run experimental
code.
"""
from pathlib import Path
import logging

from nspyre import InstrumentServer
from nspyre import InstrumentGateway
from nspyre import nspyre_init_logger
from nspyre import serve_instrument_server_cli

""" 
# Debugging attempt: 5/29/2025
import debugpy
debugpy.listen(("127.0.0.1", 5678))  # Let VS Code connect
debugpy.wait_for_client()            # Pause and wait
"""

_HERE = Path(__file__).parent

# log to the console as well as a file inside the logs folder
nspyre_init_logger(
    logging.INFO,
    log_path=_HERE / '../logs',
    log_path_level=logging.DEBUG,
    prefix='local_inserv',
    file_size=10_000_000,
)

with InstrumentServer() as inserv, InstrumentGateway(port=42068) as gw:
    inserv.add('subs', _HERE / 'subsystems_driver.py', 'SubsystemsDriver', args=[inserv, gw], local_args=True)
    inserv.add('odmr_driver', _HERE / 'fake_odmr_driver.py', 'FakeODMRInstrument')
    inserv.add('laser', _HERE / 'dlnsec.py', 'DLnsec', args=['COM3'])
    #gw.laser.open() #Added by Rolando, to open the connection when the class is instantiated.
    inserv.add('ps', _HERE / 'ps82.py', 'PS82') # inserv.add('ps', _HERE / 'ps82.py', 'PS82', args=['169.254.8.2']); inserv.add('ps', "C:\\Users\\XieLab\\Documents\\Confocal_System\\Drive_template-main\\template-main\\src\\template\\driversTX\\pulses.py", 'Pulses')
    inserv.add('daq', _HERE / 'TimeTaggerDriver.py', 'tt20')
    inserv.add('nano', _HERE / 'MCL_Madlib_Wrapper.py', 'MCL_Nanodrive') # Rolando added this 8/21/2025 temporal during repair
    inserv.add('sg', _HERE / 'srs_386.py', 'SG386', args=["TCPIP0::169.254.50.253::inst0::INSTR"])
    # run a CLI (command-line interface) that allows the user to enter
    # commands to control the server
    serve_instrument_server_cli(inserv)
    




