"""
Rolando A. Fimbres G. 3/4/2026
The following script acts as a wrapper for the SENIS 3MTS-2-2m Teslameter.
It allows the user to easily access functions stored in the a3mtslib64.dll file.

In order to properly use the wrapper, the user must have the following .dll files in the same directory as this script.
- a3mtslib64.dll
- D3DCompiler_47.dll
- libgcc_s_dw2-1.dll
- libgcc_s_seh-1.dll
- libstdc++-6.dll
- libwinpthread-1.dll
"""
import ctypes as C
import time
from pathlib import Path

class Tesla_Wrapper:

    def __init__(self):

        dll_path = Path(__file__).parent / "a3mtslib64.dll"
        self.A3mtslib = C.CDLL(str(dll_path))

        # Device number variable
        self.device_number = C.c_int()

        # Variables for sensor values
        self.timestamp = C.c_ulong()
        self.sensor_x = C.c_float()
        self.sensor_y = C.c_float()
        self.sensor_z = C.c_float()

    def count_devices(self):
        i = C.c_ushort()
        self.A3mtslib.count_devices(C.byref(i))
        return i.value

    def open_device(self):
        device_number = self.device_number
        self.A3mtslib.open_device(C.byref(device_number))
        return device_number.value

    def close_device(self):
        device_number = self.device_number
        self.A3mtslib.close_device(C.byref(device_number))
        return device_number.value

    def get_sensor_count(self):
        device_number = self.device_number
        count = C.c_int()
        self.A3mtslib.get_sensor_count(C.byref(device_number), C.byref(count))
        return count.value

    def get_sensor_values_fl(self):
        """
        Gets timestamp and measure values in µT
        """
        device_number = self.device_number
        self.A3mtslib.get_sensor_values_fl(C.byref(device_number),C.byref(self.timestamp),C.byref(self.sensor_x),C.byref(self.sensor_y),C.byref(self.sensor_z))
        return self.timestamp.value, self.sensor_x.value, self.sensor_y.value, self.sensor_z.value
    
    def average_sensor_value(self, n_samples_to_avg, sleeptime):
        """
        Averages n_samples_to_avg sensor readings and returns the average values.
        """
        total_x = 0.0
        total_y = 0.0
        total_z = 0.0
        total_t = 0.0
        for _ in range(n_samples_to_avg):
            t, x, y, z = self.get_sensor_values_fl()
            total_t += t
            total_x += x
            total_y += y
            total_z += z
            time.sleep(sleeptime)  # Wait for 0.1 second between samples
        avg_t = total_t / n_samples_to_avg
        avg_x = total_x / n_samples_to_avg
        avg_y = total_y / n_samples_to_avg
        avg_z = total_z / n_samples_to_avg

        return avg_t, avg_x, avg_y, avg_z


    def set_range(self, range):
        """
        Set the measurement range of the sensor.
        Value   Range (T)
        0       0.1 T
        1       0.5 T
        2         3 T
        3        20 T
        """
        device_number = self.device_number
        self.A3mtslib.set_range(C.byref(device_number), C.c_ushort(range))
        return 
    
    def get_range(self):
        device_number = self.device_number
        range = C.c_ushort()
        self.A3mtslib.get_range(C.byref(device_number), C.byref(range))
        return range.value
    
    def set_speed(self, speed):
        """
        Set measurement speed (Measurement time period).
        """
        device_number = self.device_number
        self.A3mtslib.set_speed(C.byref(device_number), C.c_ushort(speed))
        return
    
    def get_speed(self):
        device_number = self.device_number
        speed = C.c_ushort()
        self.A3mtslib.get_speed(C.byref(device_number), C.byref(speed))
        return speed.value
    
    def get_firmware_version_ch(self):
        device_number = self.device_number
        p = C.create_string_buffer(40)
        self.A3mtslib.get_firmware_version_ch(C.byref(device_number), C.byref(p))
        return p.value.decode()
    
    def get_device_name_ch(self):
        device_number = self.device_number
        p = C.create_string_buffer(40)
        self.A3mtslib.get_device_name_ch(C.byref(device_number), C.byref(p))
        return p.value.decode()
    
    def clear_buffer(self):
        """
        Clear the device's buffer. Useful for ensuring that old data doesn't interfere with new measurements.
        """
        device_number = self.device_number
        self.A3mtslib.clear_buffer(C.byref(device_number))
        return
    
    def set_trigger(self, trigger_mode):
        """
        Set the trigger mode of the device.
        0: off
        1: on 
        """
        device_number = self.device_number
        self.A3mtslib.set_trigger(C.byref(device_number), C.c_ushort(trigger_mode))
        return
    
    def get_trigger(self):
        device_number = self.device_number
        trigger_mode = C.c_ushort()
        self.A3mtslib.get_trigger(C.byref(device_number), C.byref(trigger_mode))
        return trigger_mode.value