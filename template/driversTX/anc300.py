'''
Lantz driver for ANC300 Attocube Controller for ANSz100std/LT/HV z-Scanner

Created on 20220909 by Sanskriti Chitransh

Tian-Xing Zheng, Sept.2023 Modified

'''

import serial
import time
import numpy as np

class ANC300():
    def __init__(self, *args, **kwargs):
        #print('init function')
        self.port = args[0]
        # self.pre = None
        # self.width = None
        # self.laserison = None
        # self.modeis = None
        # self.powerset = None
        # self.t_cycle = None
        # self.freq = None

    def initialize(self):
        self.serial = serial.Serial(port=self.port,baudrate=38400,bytesize=serial.EIGHTBITS,parity=serial.PARITY_NONE,timeout=2)
        self.serial.write_timeout = 1
        self.serial.read_timeout = 1
        self.serial.write(b'seta 1 0 \r\n')
        print('Offset_voltage set as 0V')
        print('ANC300 initialized \n')

    def finalize(self):
        self.serial.close()
        print('ANC300 finalized \n')

    def write(self,cmd):
        self.serial.write(cmd + b'\n')

    def read(self, cmd):
        answer = ""
        self.serial.write(cmd)
        while self.serial.readline() != b'':
            answer = answer + self.serial.readline().strip().decode()
        return answer

    def Get_Offset_Voltage(self):
        answer = self.read(b'geta 1\r\n')
        i = answer.index('=')
        val = answer[(i+2):(i+10)]
        return val

    def Set_Offset_Voltage(self, value):
        msg = "seta 1 "+ str(value)
        self.write(msg.encode())
        print('ANC300 Set Voltage to (V)')
        print(str(value))
