import numpy as np
from collections import defaultdict
from zaber_motion import Units

class Spiral_Wrapper:
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
        self.axis_r = dev_r.get_axis(1)

        self.new_x_pos = []
        self.new_y_pos = []
        self.new_z_pos = []
        #self.new_r_pos = []

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

    def move_to_position(self, x, y, z):
        self.axis_x.move_absolute(float(x), self.cm)
        self.axis_y.move_absolute(float(y), self.cm)
        self.axis_z.move_absolute(float(z), self.cm)
        print(f"Moved to X={x}, Y={y}, Z={z}")

    def rotate(self, r):
        self.axis_r.move_absolute(float(r), self.deg)
        print(f"Rotated to R={r}")

    def make_axis_coords(self, start, stop, density):
        if density <= 0:
            raise ValueError("density must be positive")
        spacing = 1.0 / density
        num_steps = int(round((stop - start) / spacing))
        coords = start + spacing * np.arange(num_steps + 1)
        coords[0] = start
        coords[-1] = stop
        return coords

    def make_r_pos(self, rss):
        # Create position array for R that goes from 0 to 360 in steps of Rstepsize
        r_pos = list(range(0, 360, rss))
        return r_pos

    def inside_out_sort_key(self, point):
        x, y, _ = point
        chebyshev_radius = max(abs(x), abs(y))
        if chebyshev_radius == 0:
            return (0.0, 0, 0.0)

        eps = 1e-9
        if abs(y + chebyshev_radius) < eps:
            edge = 0
            offset = x + chebyshev_radius
        elif abs(x - chebyshev_radius) < eps:
            edge = 1
            offset = y + chebyshev_radius
        elif abs(y - chebyshev_radius) < eps:
            edge = 2
            offset = chebyshev_radius - x
        else:
            edge = 3
            offset = chebyshev_radius - y

        return (round(chebyshev_radius, 10), edge, round(offset, 10))


    def generate_cube_shell_points(self, size, density, inner_limit):
        xy_coords = self.make_axis_coords(-size / 2, size / 2, density)
        z_coords = self.make_axis_coords(0, size, density)
        points = []
        for z in z_coords:
            for y in xy_coords:
                for x in xy_coords:
                    if abs(x) > inner_limit or abs(y) > inner_limit or z > inner_limit * 2:
                        points.append((round(float(x), 4), round(float(y), 4), round(float(z), 4)))
        return points


    def generate_layered_inside_out_trajectory(self, cube_configs):
        points_by_layer = defaultdict(list)
        seen = set()

        for i, config in enumerate(cube_configs):
            inner_limit = cube_configs[i - 1]["size"] / 2 if i > 0 else -1
            shell_points = self.generate_cube_shell_points(
                size=config["size"],
                density=config["density"],
                inner_limit=inner_limit,
            )

            for point in shell_points:
                if point not in seen:
                    seen.add(point)
                    points_by_layer[point[2]].append(point)

        layers = []
        full_trajectory = []

        for z in sorted(points_by_layer):
            layer_points = sorted(points_by_layer[z], key=self.inside_out_sort_key)
            layers.append({"z": z, "points": layer_points})
            full_trajectory.extend(layer_points)

        return full_trajectory, layers

    def make_box_index_array(self, trajectory, cube_configs):
        if not trajectory:
            raise ValueError("trajectory must be provided")
        if not cube_configs:
            raise ValueError("cube_configs must be provided")

        shell_map = {}
        for index, config in enumerate(cube_configs, start=1):
            inner_limit = cube_configs[index - 2]["size"] / 2 if index > 1 else -1
            for point in self.generate_cube_shell_points(config["size"], config["density"], inner_limit):
                shell_map[point] = index

        return [shell_map.get(point, len(cube_configs)) for point in trajectory]
    
    def make_rot_array(self, num_layers, scale_factor, starting_value):
        rot_array = []
        rot_array.append(0)  # Start with 0 so index 1 corresponds to layer 1
        for i in range(num_layers):
            rot_value = (starting_value * scale_factor ** i)
            rot_array.append(rot_value)
        print(f"Rotation array: {rot_array}")
        return rot_array


    def flip_trajectory(self, trajectory):
        return [(x, y, -z) for x, y, z in trajectory]

    def move_starting_position(self, dx, dy, dz, trajectory):
        return [(x + dx, y + dy, z + dz) for x, y, z in trajectory]