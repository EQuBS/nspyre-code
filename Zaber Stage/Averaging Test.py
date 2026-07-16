import time

import matplotlib.pyplot as plt
import numpy as np
import TM_Wrapper as tmw


def raw_speed_test(tm, speed_ms, n_samples=50):
    tm.set_speed(speed_ms)
    tm.clear_buffer()
    samples = []
    interval = speed_ms / 1000.0
    print(f"\nRaw speed test: speed={speed_ms} ms, samples={n_samples}")
    for _ in range(n_samples):
        _, x, y, z = tm.get_sensor_values_fl()
        mag = np.sqrt(x * x + y * y + z * z)
        samples.append([x, y, z, mag])
        time.sleep(interval)
    arr = np.array(samples)
    mean = arr.mean(axis=0)
    std = arr.std(axis=0, ddof=1)
    cv = np.divide(std, mean, out=np.full_like(std, np.nan), where=mean != 0) * 100
    print(f"  mean [x, y, z, |B|]: {mean}")
    print(f"  CV%  [x, y, z, |B|]: {cv}")
    return cv


def averaged_samples_test(tm, speed_ms, avg_counts, n_sets=20):
    tm.set_speed(speed_ms)
    results = []
    print(f"\nAveraging test: speed={speed_ms} ms, averaging counts={avg_counts}, sets={n_sets}")
    for count in avg_counts:
        tm.clear_buffer()
        averaged_readings = []
        for _ in range(n_sets):
            _, x, y, z = tm.average_sensor_value(count, speed_ms / 1000.0)
            mag = np.sqrt(x * x + y * y + z * z)
            averaged_readings.append([x, y, z, mag])
        arr = np.array(averaged_readings)
        mean = arr.mean(axis=0)
        std = arr.std(axis=0, ddof=1)
        cv = np.divide(std, mean, out=np.full_like(std, np.nan), where=mean != 0) * 100
        print(f"  count={count}: mean [x, y, z, |B|]: {mean}")
        print(f"  count={count}: CV%  [x, y, z, |B|]: {cv}")
        results.append(cv)
    return np.array(results)


def main():
    tm = tmw.Tesla_Wrapper()
    print("Device info:", tm.count_devices())
    tm.open_device()
    print("Device name:", tm.get_device_name_ch())
    tm.clear_buffer()
    print("Sensor range:", tm.get_range())
    print("Initial raw sensor values:", tm.get_sensor_values_fl())

    speeds = [1,2,3,5,10,20]  # in milliseconds
    cv_results = []
    for speed in speeds:
        cv = raw_speed_test(tm, speed, n_samples=50)
        cv_results.append(cv)

    avg_counts = [1, 5, 10, 20, 50]
    cv_avg_results = averaged_samples_test(tm, speed_ms=20, avg_counts=avg_counts, n_sets=30)

    tm.close_device()

    cv_results = np.array(cv_results)
    labels = ["x", "y", "z", "|B|"]

    plt.figure(figsize=(8, 6))
    for idx, label in enumerate(labels):
        plt.plot(speeds, cv_results[:, idx], marker="o", label=label)

    plt.xlabel("Sampling speed (ms)")
    plt.ylabel("Coefficient of Variation (CV%)")
    plt.title("Sampling speed vs CV% for x, y, z, and |B|")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(8, 6))
    for idx, label in enumerate(labels):
        plt.plot(avg_counts, cv_avg_results[:, idx], marker="o", label=label)

    plt.xlabel("Number of samples averaged")
    plt.ylabel("Coefficient of Variation (CV%)")
    plt.title("Averaged sample count vs CV% at 20 ms speed")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
