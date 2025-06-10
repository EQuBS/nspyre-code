"""
Tian-Xing Zheng for dil-fridge confocal microscope setup
Adapted from Evan Villafranca's nidaq.py
Aug.29.2023
"""
import numpy as np
import time
import math
from itertools import cycle
import logging
import scipy as sp
from scipy import signal
import datetime as Dt

from rpyc.utils.classic import obtain 

# nidaqmx 
import nidaqmx

#For analog readout
# from nidaqmx.constants import (AcquisitionType, Edge, TerminalConfiguration, VoltageUnits,
#     READ_ALL_AVAILABLE, TaskMode, TriggerType)

# from nidaqmx._task_modules.channels.ai_channel import AIChannel
# from nidaqmx.stream_readers import AnalogSingleChannelReader, CounterReader

#For digital readout
from nidaqmx.constants import (AcquisitionType, CountDirection, Edge,
    READ_ALL_AVAILABLE, TaskMode, TriggerType)
from nidaqmx._task_modules.channels.ci_channel import CIChannel
from nidaqmx.stream_readers import CounterReader

#For controlling the FSM
from drivers.ni_motion_controller import NIDAQMotionController, NIDAQAxis

class NIDAQ():

    def __init__(self):
        
        # NI cDAQ-9185 (Evan's setup)
        #self.clk_channel = '/cDAQ9185-214A4EDMod4/PFI0'
        #self.dev_channel = 'cDAQ9185-214A4EDMod2/ai0'
        #self.sampling_rate = 50e3

        # NI USB 6343 (dil-fridge setup)
        ## set up external clock channel. When this clock ticks, data is read from the counter channel
        ## PFI channels corresponding to selected ctr (can be reprogrammed)
        ctrs_pfis = {
                    'ctr0': 'PFI8',
                    'ctr1': 'PFI3',
                    'ctr2': 'PFI0',
                    'ctr3': 'PFI5',
        }
        self.clk_channel = '/Dev1/PFI0'
        self.dev_channel = '/Dev1/ctr1'
        self.pfi_channel = '/Dev1/' + ctrs_pfis['ctr1']
        #TXZ: hard code sampling rate for now, need to be changed to a user-defined variable
        self.sampling_rate = 20e3

        self.read_task = None
        self.reader = None

    # open read task for analog readout    
    # def open_task(self, buffer_len):
            
    #     self.read_task = nidaqmx.Task()
        
    #     self.read_task.ai_channels.add_ai_voltage_chan(
    #                             self.dev_channel,
    #                             terminal_config = TerminalConfiguration.DEFAULT,
    #                             min_val = -10,
    #                             max_val = 10,
    #                             units = VoltageUnits.VOLTS
    #     )

    #     self.read_task.timing.cfg_samp_clk_timing(
    #                             self.sampling_rate,
    #                             source = self.clk_channel,
    #                             active_edge = Edge.FALLING,
    #                             sample_mode = AcquisitionType.FINITE,
    #                             samps_per_chan = buffer_len
    #     )
    #     self.reader = AnalogSingleChannelReader(self.read_task.in_stream)
    
    # open read task for digital readout
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

    def start_task(self):
        self.read_task.start()

    def stop_task(self):  
        print(f"{self.read_task} TASK STOPPED")
        self.read_task.stop()

    def close_task(self):
        print(f"{self.read_task} TASK CLOSED")
        self.read_task.close()
        self.read_task = None
        self.reader = None
    
    def read_samples(self, buffer, buffer_len, timeout):
        
        try:
            # buffer = np.uint32(obtain(buffer)) ## TXZ: we can force the dtype to be unit32 here, but I'm afraid it will make the nidaq.py driver run a little bit slower, so we do it in spin_measurement.py 
            buffer = obtain(buffer)
            print("DAQ received empty buffer. Reading samples...")
            # print(type(obtain(buffer)))
            print(buffer.dtype)
            
            # analog readout
            # self.reader.read_many_sample(
            #                         buffer,
            #                         number_of_samples_per_channel = buffer_len,
            #                         timeout = timeout
            # )

            # digital readout
            self.reader.read_many_sample_uint32(
                                            buffer,
                                            number_of_samples_per_channel= buffer_len,
                                            timeout= timeout
            )
            return buffer
            
        except TypeError:
            self.stop_task()
            self.close_task()
    
### Added by Tian-Xing Zheng, September.2023
class FSMSetup():
    def __init__(self, x_ch, y_ch, z_ch, ctr_ch):
        x_Calibration = 0.73/11.42 # V/um
        y_Calibration = 1.00/11.42 # V/um
        x_axis = NIDAQAxis(x_ch, x_Calibration, limits=(-10/x_Calibration, 10/x_Calibration))
        y_axis = NIDAQAxis(y_ch, y_Calibration, limits=(-10/y_Calibration, 10/y_Calibration))
        self.daq_controller = NIDAQMotionController(ctr_ch, 15000, {'x': x_axis, 'y': y_axis}, ao_smooth_steps=5000)
        self.sleep_factor = 1.0
        # print(self.daq_controller.position)
        self.data_dict = dict({'': {'x': 5.0, 'y': 4.0}})

    def initialize(self):
        return self.daq_controller.initialize()
        print('FSM initialized')
        
    def finalize(self):
        return self.daq_controller.finalize()
        print('FSM finalized')
        
    def get_store_position(self):
        print('current position is', self.daq_controller.position)
        print('current data dictionary is', self.data_dict)
        print('we return the index of the last set of the data dictionary')
        print(self.data_dict)
        return str(list(self.data_dict)[-1])

    def store_position(self, key):
        self.data_dict[key] = self.daq_controller.position
        print('position stored in key', key)
        
    ## Don't know what does this do
    # @Feat()
    # def move_to_position(self):
    #     print(self.data_dict)
    #     return str(list(self.data_dict)[-1])

    def move_to_position(self, key):
        print('current dictionary:', self.data_dict)
        print('set to key:', key)
        self.daq_controller.move(self.data_dict[key])
        print('moved to', self.daq_controller.position)
        
    def new_ctr_task(self, ctr_ch):
        return self.daq_controller.new_ctr_task(ctr_ch)
    
    def get_acq_rate(self):
        return self.daq_controller.acq_rate

    def set_acq_rate(self, acq_rate):
        self.daq_controller.acq_rate = acq_rate

    def get_x(self):
        print('x:',self.daq_controller.position['x'])
        return self.daq_controller.position['x']

    def set_x(self, pos):
        print('x set {}'.format(pos))
        #self.daq_controller.move({'x': pos, 'y': self.y, 'z': self.z})
        self.daq_controller.move({'x': pos, 'y': self.daq_controller.position['y']})

    def get_y(self):
        print('y:',self.daq_controller.position['y'])
        return self.daq_controller.position['y']

    def set_y(self, pos):
        print('y set {}'.format(pos))
        #self.daq_controller.move({'x': self.x, 'y': pos, 'z': self.z})
        self.daq_controller.move({'x': self.daq_controller.position['x'], 'y': pos})
    
    ## We don't do Z axis control/readout by DAQ, we do it by using Attocube ANC300
    # def get_z(self):
    #     print('z:',self.daq_controller.position['z'])
    #     return self.daq_controller.position['z']

    # def set_z(self, pos):
    #     print('z set {}'.format(pos))
    #     self.daq_controller.move({'x': self.x, 'y': self.y, 'z': pos})

    def move(self, point):
        return self.daq_controller.move(point)

    # def line_scan(self, init_point, final_point, steps, pts_per_step):
    #     print('Doing line_scan now in nidaq.py')
    #     print('(nidaq) final_point:',final_point)
    #     print('(nidaq) type final_point:',type(final_point))
    #     print('(nidaq) type final_point[x]:',type(final_point['x']))
    #     print('(nidaq) type steps:',type(steps))
    #     print('(nidaq) type pts_per_step:',type(pts_per_step))

    #     return self.daq_controller.line_scan(init_point, final_point, steps, pts_per_step)
    
    # new line_scan that fix the type of point variable  here
    def line_scan(self, init_point, final_point, steps, pts_per_step):
        #init_point_ = {'x': float(init_point['x']), 'y': float(init_point['y'])}
        #final_point_ = {'x': float(final_point['x']), 'y': float(final_point['y'])}
        init_point_ = obtain(init_point)
        final_point_ = obtain(final_point)
        #print('Doing line_scan now in nidaq.py')
        #print('(nidaq) final_point:',final_point_)
        #print('(nidaq) type final_point:',type(final_point_))
        #print('(nidaq) type final_point[x]:',type(final_point_['x']))

        
        return self.daq_controller.line_scan(init_point_, final_point_, steps, pts_per_step)