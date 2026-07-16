"""
Testing motion commands for Zaber Stage.
"""
import importlib
# If you need a dynamic import, use the underscore name (valid Python identifier):
# zaber_motion = importlib.import_module("zaber_motion")
from zaber_motion import Units
from zaber_motion.ascii import Connection
import numpy as np

# Units to be used:
cm = Units.LENGTH_CENTIMETRES
mm = Units.LENGTH_MILLIMETRES
um = Units.LENGTH_MICROMETRES

# Distances and resolution
xdist = 2
ydist = 2
zdist = 2
xstops = 2
ystops = 2
zstops = 2
xres = xdist / (xstops)
yres = ydist / (ystops)
zres = zdist / (zstops)

print("Resolution:")
print("X: {} cm".format(xres))
print("Y: {} cm".format(yres))
print("Z: {} cm".format(zres))

# Make position arrays
x_pos = [i * xres for i in range(xstops+1)]
y_pos = [i * yres for i in range(ystops+1)]
z_pos = [i * zres for i in range(zstops+1)]

print([round(p,4) for p in x_pos])
print([round(p,4) for p in y_pos])
print([round(p,4) for p in z_pos])

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

    # Setup axis with API

    axis_x = dev_x.get_axis(1)
    axis_y = dev_y.get_axis(1)
    axis_z = dev_z.get_axis(1)

    #Home all axis
    print("Homing all axis...")
    for axis in (axis_x, axis_y, axis_z):
        print(axis.axis_number)
        print(axis.get_position(um))
        axis.home()
        print(axis.is_homed())

    # Test motion in X direction
    for zi, z in enumerate(z_pos):
        if zi % 2 == 0:
            for yi, y in enumerate(y_pos):
                if yi % 2 == 0:
                    x_scan = x_pos
                else:
                    x_scan = reversed(x_pos)
                for x in x_scan:
                    print(f"Moved to X={x:.3f}. Y={y:.3f}. Z={z:.3f}")
                    axis_x.move_absolute(x, cm)
                    axis_y.move_absolute(y, cm)
                    axis_z.move_absolute(z, cm)
        else:
            for yi, y in enumerate(reversed(y_pos)):
                if yi % 2 == 0:
                    x_scan = x_pos
                else:
                    x_scan = reversed(x_pos)
                for x in x_scan:
                    print(f"Moved to X={x:.3f}. Y={y:.3f}. Z={z:.3f}")
                    axis_x.move_absolute(x, cm)
                    axis_y.move_absolute(y, cm)
                    axis_z.move_absolute(z, cm)
    print("Scan complete.")

    axis_x.home()
    axis_y.home()
    axis_z.home()
    print("All axis homed.")