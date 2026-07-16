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
deg = Units.ANGLE_DEGREES

# Distances and resolution
xdist = 2
ydist = 2
zdist = 2
xstepsize = 1
ystepsize = 1
zstepsize = 1
rstepsize = 15
xsteps = xdist/xstepsize+1
ysteps = ydist/ystepsize+1
zsteps = zdist/zstepsize+1
x_pos = []
y_pos = []
z_pos = []
r_pos = []

def make_x_pos(xsteps, xstepsize):
    # Create forward and backward arrays
    forward = [i * xstepsize for i in range(round(xsteps))]
    backward = list(reversed(forward))

    print("Forward sequence:", forward)
    print("Backward sequence:", backward)

    total_size = round(xsteps ** 3)

    i = 1  # start from 1 so first iteration is forward
    while len(x_pos) < total_size:
        seq = forward if i % 2 == 1 else backward
        x_pos.extend(seq)
        i += 1

    print(f"x_pos ({len(x_pos)} elements):")
    print(x_pos)

def make_y_pos(xsteps, ysteps):
    # Create forward and backward arrays for Y
    forward = [i for i in range(round(ysteps))]
    backward = list(reversed(forward))
    
    # Each value repeats ysteps times
    forward = [val for val in forward for _ in range(round(ysteps))]
    backward = [val for val in backward for _ in range(round(ysteps))]

    print("Forward sequence:", forward)
    print("Backward sequence:", backward)
    
    total_size = round(xsteps ** 3)

    i = 1  # start with forward
    while len(y_pos) < total_size:
        seq = forward if i % 2 == 1 else backward
        y_pos.extend(seq)
        i += 1

    print(f"y_pos ({len(y_pos)} elements):")
    print(y_pos)

def make_z_pos(xsteps, ysteps, zsteps):
    # Create forward and backward arrays for Z
    forward = [i for i in range(round(zsteps))]
    backward = list(reversed(forward))

    # Each value repeats zsteps times
    forward = [val for val in forward for _ in range(round(zsteps ** 2))]
    backward = [val for val in backward for _ in range(round(zsteps ** 2))]

    print("Forward sequence:", forward)
    print("Backward sequence:", backward)
    
    total_size = round(xsteps ** 3)

    i = 1  # start with forward
    while len(z_pos) < total_size:
        seq = forward if i % 2 == 1 else backward
        z_pos.extend(seq)
        i += 1

    print(f"z_pos ({len(z_pos)} elements):")
    print(z_pos)

def make_r_pos(zsteps):
    # Create array for Rotation
    r_pos = [i * rstepsize for i in range(int(zsteps**3))]

    print(f"r_pos ({len(r_pos)} elements):")
    print(r_pos)

# Testing position arrays
make_x_pos(xsteps, xstepsize)
make_y_pos(xsteps, ysteps)
make_z_pos(xsteps, ysteps, zsteps)
make_r_pos(zsteps)

# Do the scan
with Connection.open_serial_port("COM5") as conn:
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

    # Setup axis with API

    axis_x = dev_x.get_axis(1)
    axis_y = dev_y.get_axis(1)
    axis_z = dev_z.get_axis(1)
    axis_r = dev_r.get_axis(1)

    #Home all axis
    print("Homing all axis...")
    for axis in (axis_x, axis_y, axis_z, axis_r):
        print(axis.axis_number)
        print(axis.get_position(um))
        axis.home()
        print(axis.is_homed())

    # Move through all positions
    print("Starting scan...")
    for x, y, z, r in zip(x_pos, y_pos, z_pos, r_pos):
        axis_x.move_absolute(x, cm)
        axis_y.move_absolute(y, cm)
        axis_z.move_absolute(z, cm)
        axis_r.move_absolute(r, deg)
        print(f"Moved to X={x}, Y={y}, Z={z}, R={r}")
    print("Scan complete.")

    axis_x.home()
    axis_y.home()
    axis_z.home()
    axis_r.home()
    print("All axis homed.")