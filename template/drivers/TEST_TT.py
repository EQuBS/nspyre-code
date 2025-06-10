"""
This is a TimeTagger test driver that will translate the functions used in Tian-Xing's nidaq.py
to the TimeTagger API.
This driver is not intended to be used in the final version of the code, but rather as a test to
verify that the TimeTagger API works as intended.
- Rolando 
"""
import TimeTagger as tt 
import numpy as np
import time
import math
from itertools import cycle
import logging
import scipy as sp
from scipy import signal
import datetime as Dt

from rpyc.utils.classic import obtain 
from TimeTagger import createTimeTagger, Counter

"""
As an initial attempt, the focus will be to make it functional for the I-t widget.
"""

class tt20:
    def __init__(self):
        super().__init__()
        self.tagger = tt.createTimeTagger()
        self.dev_channel = 3  # Time Tagger channel 3
        self.tagger.setTriggerLevel(3, 1.1)

    """
    1)
        def open_task(self, buffer_len):
            ## create the read task for each counter channel
            self.read_task = nidaqmx.Task()
        
            self.read_task.ci_channels.add_ci_count_edges_chan(
                                        self.dev_channel,
                                        edge=Edge.RISING,
                                        initial_count=0,
                                        count_direction=CountDirection.COUNT_UP
        )

        self.read_task.ci_channels.all.ci_count_edges_term = self.pfi_channel

        ## set up read_task timing by external PS clock (triggers automatically when tasks starts)
        self.read_task.timing.cfg_samp_clk_timing(
                                    self.sampling_rate, # must be equal or larger than max rate expected by PS
                                    source = self.clk_channel,
                                    sample_mode = AcquisitionType.FINITE, #CONTINUOUS, # can also limit the number of points
                                    samps_per_chan= buffer_len
        )
        ## create counter stream object 
        self.reader = CounterReader(self.read_task.in_stream)

    2)
        def close_task(self):
            print(f"{self.read_task} TASK CLOSED")
            self.read_task.close()
            self.read_task = None
            self.reader = None

    """

    

    def open_task(self, buffer_len):
        """
        Configures a time-tagging task using Swabian's Time Tagger API.

        Args:
            buffer_len (int): Number of samples to acquire.
        """
         # Create a Time Tagger instance
        #self.tagger = createTimeTagger()

        # Configure the counter channel
        self.counter = Counter(
            tagger=self.tagger,
            channels=[3], # Replace with the appropriate channel number
            binwidth=int(1000),            # Bin width in picoseconds (e.g., 1000 = 1 ns)
            n_values=int(buffer_len)       # Number of bins (equivalent to buffer_len)
        )

        # Set the clock source (if applicable)
        # Swabian's Time Tagger uses an internal clock by default, but you can configure
        # an external clock if needed. For example:
        # self.tagger.setTriggerLevel(self.clk_channel, level=0.5)  # Example for external clock

        # The Counter object will automatically start counting edges when created.

    def close_task(self):
        """
        Closes the Time Tagger task and releases resources.
        """
        if self.tagger is not None:
            print(f"{self.tagger} TASK CLOSED")
            tt.freeTimeTagger(self.tagger)  # Frees the Time Tagger resources
            self.tagger = None
            self.counter = None  # Clear the counter reference if used