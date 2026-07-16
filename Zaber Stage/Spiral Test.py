import time

from zaber_motion import Units
from zaber_motion.ascii import Connection
import TM_Wrapper as tmw
import numpy as np
import Spiral_Wrapper as sw
import matplotlib.pyplot as plt

tm = tmw.Tesla_Wrapper()

with Connection.open_serial_port("COM5") as conn:
    print("Connected to COM5")
    conn.enable_alerts()
    sw = sw.Spiral_Wrapper(conn)

    x = sw.axis_x
    y = sw.axis_y
    z = sw.axis_z
    r = sw.axis_r

    for axis, name, unit, speed in [
        (x, "x", Units.VELOCITY_MILLIMETRES_PER_SECOND, 20),
        (y, "y", Units.VELOCITY_MILLIMETRES_PER_SECOND, 20),
        (z, "z", Units.VELOCITY_MILLIMETRES_PER_SECOND, 20),
        (r, "r", Units.ANGULAR_VELOCITY_DEGREES_PER_SECOND, 15),
    ]:
        axis.settings.set("maxspeed", speed, unit=unit)
        max_speed = axis.settings.get("maxspeed", unit)
        print(f"Maximum speed for {name} [{unit}]:", max_speed)
    
    print("Device info:", tm.count_devices())
    tm.open_device()
    print("Device name:", tm.get_device_name_ch())
    tm.clear_buffer()
    print("Sensor range:", tm.get_range())
    print("Initial raw sensor values:", tm.get_sensor_values_fl())

    cube_configs = [
    {"size": 1, "density": 1},  # 1x1x1cm cube sitting on Z=0
    {"size": 2, "density": 1},  # 2x2x2cm cube sitting on Z=0, skipping the 1x1x1 volume
    {"size": 3, "density": 1},
    ]

    full_trajectory, layers = sw.generate_layered_inside_out_trajectory(cube_configs)
    box_ids = sw.make_box_index_array(full_trajectory, cube_configs)
    full_trajectory = sw.flip_trajectory(full_trajectory)
    full_trajectory = sw.move_starting_position(4, 4, 30, full_trajectory) # Move starting position to (4, 4, 30) cm

    print(f"Generated {len(full_trajectory)} positions starting from Z=0.")

    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection="3d")
    xs, ys, zs = zip(*full_trajectory)
    color_map = {1: "red", 2: "green", 3: "blue"}
    colors = [color_map.get(box_id, "gray") for box_id in box_ids]
    ax.scatter(xs, ys, zs, c=colors, s=10)
    ax.plot(xs, ys, zs, linewidth=0.6, alpha=0.5, color="black")
    ax.set_title("Layered Inside-Out Trajectory")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    plt.show()

    x_pos, y_pos, z_pos = zip(*full_trajectory)

    # Initialize lists to store results
    t = []
    bx = []
    by = []
    bz = []
    br = []
    X = []
    Y = []
    Z = []
    R = []
    print(f"number of layers: {len(layers)}")
    rot_array =sw.make_rot_array(len(layers)-1, 2, 90)
    #add stop past 360
    if any(angle > 360 for angle in rot_array):
        raise ValueError("Rotation angle exceeds 360 degrees. Please exit the code and adjust the rotation parameters, else all angles exceeding 360 will be set to 360.")

    sw.home_all_axes()
    for i, (x, y, z) in enumerate(zip(x_pos, y_pos, z_pos)):
        sw.move_to_position(x, y, z)
        debug_position = i < 2
        if debug_position:
            print("Moved to target position", (x, y, z))
            print("Actual positions:",
                  sw.axis_x.get_position(sw.cm),
                  sw.axis_y.get_position(sw.cm),
                  sw.axis_z.get_position(sw.cm))
            # add if statremnt
        layer_num = box_ids[i]
        angle = rot_array[layer_num]
        if debug_position:
            print(f"Since layer_num is {layer_num}, rotating in increments of {angle} degrees")
        r_pos_array = sw.make_r_pos(angle)
        if debug_position:
            print(f"R positions for position {x}, {y}, {z}: {r_pos_array}")
        for r in r_pos_array:
            sw.rotate(r)
            if debug_position:
                # print("Rotated to", r)
                print("Rotated to", r, "actual rotation:", sw.axis_r.get_position(sw.deg))
            b_field = tm.average_sensor_value(20, 0.05)
            if debug_position:
                print("Sensor values:", b_field)
            t.append(b_field[0])
            bx.append(b_field[1])
            by.append(b_field[2])
            bz.append(b_field[3])
            br.append(r)
            X.append(x)
            Y.append(y)
            Z.append(z)
            R.append(r)
        time.sleep(0.05) # Wait for 0.05 second at each position
    sw.home_all_axes() # Home all axes after scanning

    print("Test completed.")
    #print("Timestamps: \n", t)
    #print("X values: \n", X)
    #print("X values: \n", Y)
    #print("X values: \n", Z)
    #print("R values: \n", R)
    # Close device (TM)
    tm.close_device()
    #print("Bx values: \n", bx)
    #print("By values: \n", by)
    #print("Bz values: \n", bz)

    b_mag = []
    for i in range(len(bx)):
        mag = np.sqrt(bx[i]**2 + by[i]**2 + bz[i]**2)
        b_mag.append(mag)
    print("B magnitude: \n", np.array(b_mag))

    # Save results to a txt file
    data = np.column_stack((X, Y, Z, R, bx, by, bz, np.sqrt(np.array(bx)**2 + np.array(by)**2 + np.array(bz)**2)))
    header = 'x\ty\tz\tr\tbx\tby\tbz\tb_mag'
    np.savetxt('scan_results.txt', data, delimiter='\t', header=header, comments='')
    print('Results saved to scan_results.txt')
