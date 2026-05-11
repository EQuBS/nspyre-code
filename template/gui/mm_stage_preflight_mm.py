"""
Preflight check for the MCL NanoDrive Micro-Manager/Pycro-Manager backend.

This script verifies that Pycro-Manager can connect to Micro-Manager Core,
that the configured MCL XY/Z devices are visible, and that positions can be
read. By default it does not move the stage.
"""
from __future__ import annotations

import argparse

try:
    from drivers.MCL_MicroManager_Wrapper_mm import MCLStageConfig, MicroManagerMCLStage
except Exception as exc:  # pragma: no cover - lab environment only
    raise RuntimeError(
        "Could not import MCL_MicroManager_Wrapper_mm.py. Run this script from "
        "the folder containing the *_mm.py files."
    ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Micro-Manager MCL NanoDrive connection.")
    parser.add_argument("--config", default="", help="Optional Micro-Manager .cfg path")
    parser.add_argument("--mm-app-path", default="", help="Optional Micro-Manager application path for headless mode")
    parser.add_argument("--xy-device", default="MCL NanoDrive XY Stage")
    parser.add_argument("--z-device", default="MCL NanoDrive Z Stage")
    parser.add_argument("--stage-range-um", type=float, default=200.0)
    parser.add_argument("--origin", choices=["center", "current"], default="center")
    parser.add_argument("--settling-ms", type=float, default=None)
    parser.add_argument("--move-test-um", type=float, default=0.0, help="Optional tiny X move out-and-back in user um; default 0 disables motion")
    args = parser.parse_args()

    cfg = MCLStageConfig(
        xy_device=args.xy_device,
        z_device=args.z_device,
        axis_max_um=(args.stage_range_um, args.stage_range_um, args.stage_range_um),
        user_origin_mode=args.origin,
        settling_time_ms=args.settling_ms,
        mm_config_file=args.config or None,
        mm_app_path=args.mm_app_path or None,
    )
    stage = MicroManagerMCLStage(config=cfg)
    try:
        print("Connected to Micro-Manager Core.")
        print("Configured XY device:", args.xy_device)
        print("Configured Z device:", args.z_device)
        print("User position um:", stage.read_user())
        print("Hardware position um:", stage.read_hw())
        print("User limits um:")
        for axis in ("x", "y", "z"):
            print(f"  {axis}: {stage.user_limits(axis)}")

        print("\nDevice properties:")
        props = stage.describe_devices()
        for dev, items in props.items():
            print(f"[{dev}]")
            if not items:
                print("  <no properties returned>")
            for key, value in items.items():
                print(f"  {key}: {value}")

        if args.move_test_um:
            start = stage.read_user()[1]
            print(f"\nMoving X by +{args.move_test_um} um and back...")
            stage.step_axis("x", args.move_test_um, wait=True)
            print("After step:", stage.read_user())
            stage.move_axis("x", start, wait=True)
            print("Returned:", stage.read_user())
        return 0
    finally:
        stage.close()


if __name__ == "__main__":
    raise SystemExit(main())
