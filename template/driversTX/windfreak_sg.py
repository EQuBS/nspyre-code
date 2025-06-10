"""WindFreak SynthHD pro v2 Microwave Generator driver.

https://windfreaktech.com/product/microwave-signal-generator-synthhd-pro/

Author: Tian-Xing Zheng
Date: Sept.2023
"""
from windfreak import SynthHD
#import time
#import logging

#_logger = logging.getLogger(__name__)

class WindFreakSG():
    def __init__(self, port: str):
        """
        Args:
            port: serial COM port (see pyserial docs)
        """
        self.synth = SynthHD(port)
        self.synth.init()
    
    # Set channel 0 power
    def set_power_ch0(self,power):
        self.synth[0].power = power
    
    # Set channel 0 frequency
    def set_freq_ch0(self,freq):
        self.synth[0].frequency = freq

    # Get channel 0 frequency
    def get_freq_ch0(self):
        return self.synth[0].frequency
    
    def ch0_on(self):
        self.synth[0].enable = True
    
    def ch0_off(self):
        self.synth[0].enable = False

    # Set channel 1 power
    def set_power_ch1(self,power):
        self.synth[1].power = power
    
    # Set channel 1 frequency
    def set_freq_ch1(self,freq):
        self.synth[1].frequency = freq
    
    def ch1_on(self):
        self.synth[1].enable = True
    
    def ch1_off(self):
        self.synth[1].enable = False
