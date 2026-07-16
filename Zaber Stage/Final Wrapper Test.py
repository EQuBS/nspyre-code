from zaber_motion import Units
from zaber_motion.ascii import Connection
import numpy as np
import TM_Wrapper, time
import CubeScanWrapper
import matplotlib.pyplot as plt

tm = TM_Wrapper.Tesla_Wrapper()

# Units to be used:
cm = Units.LENGTH_CENTIMETRES
deg = Units.ANGLE_DEGREES

with Connection.open_serial_port("COM4") as conn:
    conn.enable_alerts()
    cs = CubeScanWrapper.ZaberScanCube(conn)
    x = cs.axis_x
    y = cs.axis_y
    z = cs.axis_z
    r = cs.axis_r

    for axis, name, unit, speed in [
        (x, "x", Units.VELOCITY_MILLIMETRES_PER_SECOND, 15),
        (y, "y", Units.VELOCITY_MILLIMETRES_PER_SECOND, 15),
        (z, "z", Units.VELOCITY_MILLIMETRES_PER_SECOND, 15),
        (r, "r", Units.ANGULAR_VELOCITY_DEGREES_PER_SECOND, 15),
    ]:
        axis.settings.set("maxspeed", speed, unit=unit)
        max_speed = axis.settings.get("maxspeed", unit)
        print(f"Maximum speed for {name} [{unit}]:", max_speed)
    
    # Print device
    print("Device info: ", tm.count_devices())
    # Opening device
    tm.open_device()
    # Get device name
    print("Device name: ", tm.get_device_name_ch())

    dist = 1 # Dist = 2 cm
    stepsize = 1 # StepSize = 1 cm
    rstepsize = 90  # RStepSize = 90 deg
    xi = 5.0
    yi = 4.3
    zi = 30.0

    cs.set_dim(dist, stepsize, rstepsize) # Dist = 2 cm, StepSize = 1 cm, RStepSize = 90 deg
    cs.make_x_pos()
    cs.make_y_pos()
    cs.make_z_pos()
    cs.make_r_pos()
    #cs.change_start_pos(10, 10, 10) # Move starting position to (10,10,10) cm
    cs.center_bottom_z_plane(xi, yi, zi) # Shift position arrays so bottom z plane is centered at (xi, yi, zi)
    cs.store_initial_pos_arrays() # Store initial position arrays as inner box

    t = []
    bx = []
    by = []
    bz = []
    X = []
    Y = []
    Z = []
    R = []

    x_pos = cs.x_pos
    y_pos = cs.y_pos
    z_pos = cs.z_pos
    r_pos = cs.r_pos

    cs.home_all_axes() # Home all axes before scanning
    # Moves through inner box
    for x, y, z in zip(x_pos, y_pos, z_pos):
        cs.move_to_position(x, y, z)
        for r in r_pos:
            cs.rotate(r)
            #b_field = tm.get_sensor_values_fl()
            b_field = tm.average_sensor_value(20, 0.05) # Average 20 samples with 0.05 second delay between samples
            t.append(b_field[0])
            bx.append(b_field[1])
            by.append(b_field[2])
            bz.append(b_field[3])
            X.append(x)
            Y.append(y)
            Z.append(z)
            R.append(r)
        time.sleep(0.1) # Wait for 0.1 second at each position
    print("Scan complete.")
    t.append(0)
    bx.append(0)
    by.append(0)
    bz.append(0)
    X.append(0)
    Y.append(0)
    Z.append(0)
    R.append(0)

    num_out_box = 2 # Number of ADDITIONAL boxes (total boxes -1)
    scalar = 2

    for i in range(num_out_box):
        dist *= scalar
        cs.set_dim(dist,stepsize,rstepsize) # Update dimensions
        cs.make_x_pos()
        cs.make_y_pos()
        cs.make_z_pos()
        cs.make_r_pos()
        cs.center_bottom_z_plane(xi, yi, zi) # Shift position arrays so bottom z plane is centered at (xi, yi, zi)
        #cs.change_start_pos(10, 10, 10) # Move starting position to (10,10,10) cm

        cs.remove_small_cube() # Remove inner box from position arrays
        cs.store_initial_pos_arrays() # Store larger (with inner box) position arrays as initial position arrays
        cs.update_position_arrays() # Update position arrays to only include positions outside the inner box

        x_pos = cs.x_pos
        y_pos = cs.y_pos
        z_pos = cs.z_pos
        r_pos = cs.r_pos
        for x, y, z in zip(x_pos, y_pos, z_pos):
            cs.move_to_position(x, y, z)
            for r in r_pos:
                cs.rotate(r)
                #b_field = tm.get_sensor_values_fl()
                b_field = tm.average_sensor_value(20, 0.05) # Average 20 samples with 0.05 second delay between samples
                t.append(b_field[0])
                bx.append(b_field[1])
                by.append(b_field[2])
                bz.append(b_field[3])
                X.append(x)
                Y.append(y)
                Z.append(z)
                R.append(r)
            time.sleep(0.1) # Wait for 0.1 second at each position
        print("Scan complete.")
        t.append(0)
        bx.append(0)
        by.append(0)
        bz.append(0)
        X.append(0)
        Y.append(0)
        Z.append(0)
        R.append(0)
    
    cs.home_all_axes() # Home all axes after scanning

    # Close device (TM)
    tm.close_device()

    print("Test completed.")
    #print("Timestamps: \n", t)
    #print("Bx values: \n", bx)
    #print("By values: \n", by)
    #print("Bz values: \n", bz)

    b_mag = []
    for i in range(len(bx)):
        mag = np.sqrt(bx[i]**2 + by[i]**2 + bz[i]**2)
        b_mag.append(mag)

    print("B magnitude: \n", np.array(b_mag))

    """# Plotting the magnitude of the magnetic field
    plt.figure()
    plt.plot(distance_array, b_mag, marker='o')
    plt.title('Magnitude of Magnetic Field vs Distance')
    plt.xlabel('Distance in Z (cm)')
    plt.ylabel('B Magnitude (µT)')
    plt.show()"""

    # Save results to a txt file
    data = np.column_stack((X, Y, Z, R, bx, by, bz, np.sqrt(np.array(bx)**2 + np.array(by)**2 + np.array(bz)**2)))
    header = 'x\ty\tz\tr\tbx\tby\tbz\tb_mag'
    np.savetxt('scan_results.txt', data, delimiter='\t', header=header, comments='')
    print('Results saved to scan_results.txt')

