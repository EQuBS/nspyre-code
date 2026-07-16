"""
Testing motion commands for Zaber Stage.
"""
import importlib 
#zaber_motion = importlib.import_module("zaber-motion")
from zaber_motion import Units
from zaber_motion.ascii import Connection
import numpy as np

# Units to be used:
cm = Units.LENGTH_CENTIMETRES
mm = Units.LENGTH_MILLIMETRES
um = Units.LENGTH_MICROMETRES

position_array = np.arange(1, 11, 1)
print(position_array)

with Connection.open_serial_port("COM4") as conn:
    conn.enable_alerts()

    device_list = conn.detect_devices()
    print("Found {} devices".format(len(device_list)))
    print(device_list[0])
    print(device_list[1])
    print(device_list[2])
    print(device_list[3])

    dev_x = device_list[0]
    dev_y = device_list[1]
    dev_z = device_list[3]
    dev_r = device_list[2]

    axis_x = dev_x.get_axis(1)
    print(axis_x.axis_number)
    print(axis_x.get_position(um))
    axis_x.home()
    print(axis_x.is_homed())

    # Test motion in X direction
    for idx, val in enumerate(position_array):
        axis_x.move_absolute(float(val), cm)
        #axis_x.wait_until_idle()
        print("X position: {} cm".format(axis_x.get_position(cm)))

    axis_x.home() 