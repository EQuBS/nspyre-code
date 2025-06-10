"""
This script is meant to perfrom a T1 relaxation experiment making use of the Nspyre
framework. It is a template for creating an experiment that can be run in the
Nspyre GUI.
"""

import time
import logging
from pathlib import Path
import TimeTagger as TT
from pulsestreamer import PulseStreamer


import numpy as np
from nspyre import DataSource
from nspyre import experiment_widget_process_queue
from nspyre import StreamingList
from nspyre import nspyre_init_logger

from template.drivers.insmgr import MyInstrumentManager

_HERE = Path(__file__).parent
_logger = logging.getLogger(__name__)

     