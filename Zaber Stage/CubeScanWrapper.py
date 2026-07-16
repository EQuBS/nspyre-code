"""
Testing motion commands for Zaber Stage.
"""
import importlib 
#zaber_motion = importlib.import_module("zaber-motion")
from matplotlib import cm
from zaber_motion import Units
from zaber_motion.ascii import Connection
import numpy as np

class ZaberScanCube:
   
    def __init__(self, conn):
        conn.enable_alerts()
        # Units to be used:
        self.cm = Units.LENGTH_CENTIMETRES
        self.mm = Units.LENGTH_MILLIMETRES
        self.um = Units.LENGTH_MICROMETRES
        self.deg = Units.ANGLE_DEGREES

        device_list = conn.detect_devices()
        """print("Found {} devices".format(len(device_list)))
        print(device_list[0])
        print(device_list[1])
        print(device_list[2])
        print(device_list[3])"""

        dev_x = device_list[0]
        dev_y = device_list[1]
        dev_z = device_list[3]
        dev_r = device_list[2]

        # Setup axis with API
        self.axis_x = dev_x.get_axis(1)
        self.axis_y = dev_y.get_axis(1)
        self.axis_z = dev_z.get_axis(1)
        self.axis_r = dev_r.get_axis(1) # 1 means linear stage, 2 means rotary stage, from API

        self.new_x_pos = []
        self.new_y_pos = []
        self.new_z_pos = []
        #self.new_r_pos = []

    def set_dim(self, Dist, StepSize, RStepSize):
        # Distances and resolution
        self.dist = Dist
        self.stepsize = StepSize
        self.rstepsize = RStepSize
        self.steps = self.dist/self.stepsize+1
        self.rsteps = 360/self.rstepsize
        self.x_pos = []
        self.y_pos = []
        self.z_pos = []
        self.r_pos = []
        self.arrayLength = round(self.steps ** 3)


    def make_x_pos(self):
        # Create forward and backward arrays
        forward = [i * self.stepsize for i in range(round(self.steps))]
        backward = list(reversed(forward))

        #print("Forward sequence: ", forward)
        #print("Backward sequence: ", backward)

        i = 1  # start from 1 so first iteration is forward
        while len(self.x_pos) < self.arrayLength:
            seq = forward if i % 2 == 1 else backward
            self.x_pos.extend(seq)
            i += 1

        #print(f"X Array: ", self.x_pos)

    def make_y_pos(self):
        # Create forward and backward arrays for Y
        forward = [i for i in range(round(self.steps))]
        
        # Each value repeats Ysteps times
        forward = [val for val in forward for _ in range(round(self.steps))]
        backward = list(reversed(forward))

        #print("Forward sequence: ", forward)
        #print("Backward sequence: ", backward)

        i = 1  # start with forward
        while len(self.y_pos) < self.arrayLength:
            seq = forward if i % 2 == 1 else backward
            self.y_pos.extend(seq)
            i += 1

        #print(f"Y Array: ", self.y_pos)

    def make_z_pos(self):
        # Create forward and backward arrays for Z
        forward = [i for i in range(round(self.steps))]

        # Each value repeats Zsteps times
        forward = [val for val in forward for _ in range(round(self.steps ** 2))]
        """   backward = list(reversed(forward))

        print("Forward sequence: ", forward)
        print("Backward sequence: ", backward) """

        self.z_pos.extend(forward)

        """ i = 1  # start with forward
        while len(self.z_pos) < self.arrayLength:
            seq = forward if i % 2 == 1 else backward
            self.z_pos.extend(seq)
            i += 1 """

        #print(f"Z Array: ", self.z_pos)

    def make_r_pos(self, rss):
        # Create position array for R that goes from 0 to 360 in steps of Rstepsize
        self.r_pos = list(range(0, 360, rss))
        print(f"r_pos ({len(self.r_pos)} elements):")
        print(self.r_pos)

        """ # Testing position arrays
        ZaberScanCube.make_x_pos(xsteps, xstepsize)
        make_y_pos(xsteps, ysteps)
        make_z_pos(xsteps, ysteps, zsteps)
        make_r_pos(rsteps, rstepsize) """

    def home_all_axes(self):
        print("Homing all axes...")
        for axis, unit in [
            (self.axis_x, self.cm),
            (self.axis_y, self.cm),
            (self.axis_z, self.cm),
            (self.axis_r, self.deg),  # Use degrees for rotary!
        ]:
            print(axis.axis_number)
            print(axis.get_position(unit))
            axis.home()
            print(f"Axis {axis.axis_number} is homed: {axis.is_homed()}")

    def perform_scan(self):
        # Move through all positions
        print("Starting scan...")
        for x, y, z in zip(self.x_pos, self.y_pos, self.z_pos):
            self.axis_x.move_absolute(x, self.cm)
            self.axis_y.move_absolute(y, self.cm)
            self.axis_z.move_absolute(z, self.cm)
            print(f"Moved to X={x}, Y={y}, Z={z}")
            for r in self.r_pos:
                self.axis_r.move_absolute(r, self.deg)
                print(f"Moved to R={r}")
        print("Scan complete.")

    def move_to_position(self, x, y, z):
        self.axis_x.move_absolute(float(x), self.cm)
        self.axis_y.move_absolute(float(y), self.cm)
        self.axis_z.move_absolute(float(z), self.cm)
        print(f"Moved to X={x}, Y={y}, Z={z}")

    def rotate(self, r):
        self.axis_r.move_absolute(float(r), self.deg)
        print(f"Rotated to R={r}")

    def change_start_pos(self, x_start, y_start, z_start):
        # Append arrays to 'move' to a different starting position BEFORE SCANNING
        for i in range(len(self.x_pos)):
            self.x_pos[i] += x_start  # Move all X positions by x_start cm
            self.y_pos[i] += y_start  # Move all Y positions by y_start cm
            self.z_pos[i] += z_start  # Move all Z positions by z_start cm

    def center_bottom_z_plane(self, x_c, y_c, z_c):
        # Find the greatest z value (bottom plane)
        max_z = max(self.z_pos)
        # Indices of all points in the bottom z plane
        indices = [i for i, z in enumerate(self.z_pos) if z == max_z]
        # Get x and y values for those indices
        x_plane = [self.x_pos[i] for i in indices]
        y_plane = [self.y_pos[i] for i in indices]
        # Find the center of the plane
        x_center = np.mean(x_plane)
        y_center = np.mean(y_plane)
        # The z value to align to
        z_center = max_z
        # Compute shifts
        dx = x_c - x_center
        dy = y_c - y_center
        dz = z_c - z_center
        # Shift all positions
        self.x_pos = [x + dx for x in self.x_pos]
        self.y_pos = [y + dy for y in self.y_pos]
        self.z_pos = [z + dz for z in self.z_pos]
        print(f"Shifted arrays so bottom z plane is centered at ({x_c}, {y_c}, {z_c})")
        print("X Array ({} elements): ".format(len(self.x_pos)), self.x_pos)
        print("Y Array ({} elements): ".format(len(self.y_pos)), self.y_pos)
        print("Z Array ({} elements): ".format(len(self.z_pos)), self.z_pos)

    def store_initial_pos_arrays(self):
        # check if arrays exists
        if not hasattr(self, 'x_pos'):
            raise ValueError("Position arrays not initialized")
        if not hasattr(self, 'y_pos'):
            raise ValueError("Position arrays not initialized")
        if not hasattr(self, 'z_pos'):
            raise ValueError("Position arrays not initialized")
        if not hasattr(self, 'r_pos'):
            raise ValueError("Position arrays not initialized")
        
        # Store initial position arrays for later use
        self.initial_x_pos = self.x_pos.copy()
        self.initial_y_pos = self.y_pos.copy()
        self.initial_z_pos = self.z_pos.copy()
        self.initial_r_pos = self.r_pos.copy()

        #print("X array: ", self.initial_x_pos)
        #print("Y array: ", self.initial_y_pos)
        #print("Z array: ", self.initial_z_pos)
        #print("R array: ", self.initial_r_pos)

        return self.initial_x_pos, self.initial_y_pos, self.initial_z_pos, self.initial_r_pos

    def remove_small_cube(self):
        x_min = min(self.initial_x_pos)
        x_max = max(self.initial_x_pos)
        y_min = min(self.initial_y_pos)
        y_max = max(self.initial_y_pos)
        z_min = min(self.initial_z_pos)
        z_max = max(self.initial_z_pos)

        for x, y, z in zip(self.x_pos, self.y_pos, self.z_pos):
            if not (x_min <= x <= x_max and y_min <= y <= y_max and z_min <= z <= z_max):
                self.new_x_pos.append(x)
                self.new_y_pos.append(y)
                self.new_z_pos.append(z)
                #self.new_r_pos.append(r)
        return self.new_x_pos, self.new_y_pos, self.new_z_pos #, self.new_r_pos
        
    
    def update_position_arrays(self):
        # Update the position arrays to only include positions outside the initial cube
        self.x_pos = self.new_x_pos
        self.y_pos = self.new_y_pos
        self.z_pos = self.new_z_pos
        #self.r_pos = self.new_r_pos

        print("Positions within the cube removed.")
        print("X Array ({} elements): ".format(len(self.x_pos)), self.x_pos)
        print("Y Array ({} elements): ".format(len(self.y_pos)), self.y_pos)
        print("Z Array ({} elements): ".format(len(self.z_pos)), self.z_pos)

        return self.x_pos, self.y_pos, self.z_pos, self.r_pos