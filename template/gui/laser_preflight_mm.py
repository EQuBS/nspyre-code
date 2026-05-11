"""Quick laser/Pulse-Streamer preflight for the Micro-Manager scan bundle.

Examples:
    python laser_preflight_mm.py --backend instrument_gateway --power 1 --duration 2
    python laser_preflight_mm.py --backend dlnsec_serial --serial COM5 --power 1 --duration 2 --no-ps-gate

The laser is turned off and the Pulse Streamer is reset in the context-manager
cleanup path.
"""
from __future__ import annotations

import argparse
import time

from laser_control_mm import LaserControl, laser_config_from_params


def main():
    parser = argparse.ArgumentParser(description="Test laser setup/cleanup used by gui_2D_Scan_mm.py.")
    parser.add_argument(
        "--backend",
        default="instrument_gateway",
        choices=["instrument_gateway", "gateway", "dlnsec_serial", "serial", "disabled"],
        help="Laser control backend.",
    )
    parser.add_argument("--power", type=float, default=1.0, help="Laser power in percent, 0-100.")
    parser.add_argument("--serial", default="", help="Serial port for dlnsec_serial mode, for example COM5.")
    parser.add_argument("--duration", type=float, default=2.0, help="How long to keep the laser enabled, in seconds.")
    parser.add_argument("--warmup", type=float, default=0.1, help="Warmup delay after enabling laser/gate, in seconds.")
    parser.add_argument("--no-ps-gate", action="store_true", help="Do not call gw.ps.spcm_laser_on().")
    args = parser.parse_args()

    params = {
        "Laser_Enable": args.backend != "disabled",
        "Laser_Backend": args.backend,
        "Laser_Power": args.power,
        "Laser_Serial_Port": args.serial,
        "Laser_CW_Mode": True,
        "Laser_Warmup_Time": max(0.0, float(args.warmup)),
        "Enable_SPCM_Laser_Gate": not args.no_ps_gate,
        "Laser_Shutdown_On_Finish": True,
    }

    cfg = laser_config_from_params(params)
    with LaserControl(cfg) as laser:
        print("Laser metadata:", laser.metadata)
        if laser.metadata.get("active", False):
            time.sleep(max(0.0, float(args.duration)))
    print("Laser preflight cleanup complete.")


if __name__ == "__main__":
    main()
