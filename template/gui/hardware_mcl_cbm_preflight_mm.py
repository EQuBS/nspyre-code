"""Preflight checks for gui_2D_Scan_mm Scan_Mode='hardware_mcl_cbm'.

This script does not move the stage by default.  It verifies that the nspyre
InstrumentGateway exposes the direct MCL NanoDrive driver as gw.nano and the
Time Tagger driver as gw.daq, that the required methods are present, and that an
MCL handle can be resolved even when gw.nano.handle is not exposed.
"""
from __future__ import annotations

import argparse

try:
    from .mcl_hardware_scan_mm import resolve_mcl_handle
except Exception:
    from mcl_hardware_scan_mm import resolve_mcl_handle


def _safe_getattr(obj, name, default=None):
    try:
        return getattr(obj, name)
    except Exception:
        return default


def _has(obj, name):
    return callable(_safe_getattr(obj, name, None))


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight for hardware MCL + CBM scans.")
    parser.add_argument("--axis1", default="x", choices=["x", "y", "z"], help="Fast axis to test logically.")
    parser.add_argument("--axis2", default="y", choices=["x", "y", "z"], help="Slow axis to test logically.")
    parser.add_argument("--points", type=int, default=10, help="Requested Data_Points.")
    parser.add_argument("--stage-range", type=float, default=200.0, help="Fallback stage range in um.")
    args = parser.parse_args()

    if args.axis1 == args.axis2:
        raise SystemExit("axis1 and axis2 must be different.")

    from nspyre import InstrumentGateway

    with InstrumentGateway() as gw:
        nano = _safe_getattr(gw, "nano", None)
        daq = _safe_getattr(gw, "daq", None)
        if nano is None:
            raise RuntimeError("InstrumentGateway does not expose gw.nano.")
        if daq is None:
            raise RuntimeError("InstrumentGateway does not expose gw.daq.")

        print("gw.nano found:", nano)
        print("gw.daq found:", daq)

        required_nano = [
            "single_read_n",
            "single_write_n",
            "monitor_n",
            "wfma_setup",
            "wfma_trigger",
            "wfma_stop",
            "iss_bind_clock_to_axis",
        ]
        required_daq = [
            "set_trigger_level",
            "start_cbm",
            "CBM_start",
            "cbm_ready",
            "count_BM",
            "cbm_get_BinWidths",
        ]

        missing_nano = [name for name in required_nano if not _has(nano, name)]
        missing_daq = [name for name in required_daq if not _has(daq, name)]
        if missing_nano:
            raise RuntimeError("gw.nano is missing required methods: " + ", ".join(missing_nano))
        if missing_daq:
            raise RuntimeError("gw.daq is missing required methods: " + ", ".join(missing_daq))

        handle, source, acquired_here = resolve_mcl_handle(nano)
        print(f"MCL handle resolved: {handle} from {source} (acquired_here={acquired_here})")

        try:
            version, profile = nano.get_firmware_version(handle)
            print(f"MCL firmware version: {version}; profile bitfield: {profile}")
        except Exception as exc:
            print(f"WARNING: could not read MCL firmware profile: {exc}")

        for axis_id, axis_name in [(1, "X"), (2, "Y"), (3, "Z")]:
            try:
                cal = float(nano.get_calibration(axis_id, handle))
            except Exception:
                cal = float(args.stage_range)
            try:
                pos = float(nano.single_read_n(axis_id, handle))
            except Exception:
                pos = float("nan")
            print(f"{axis_name}: calibration={cal:.6f} um, current={pos:.6f} um")

        setup_points = int(args.points) + 1
        print(f"Requested waveform setup points: {setup_points}")
        if setup_points > 10000:
            raise RuntimeError("Requested points exceed the default 16-bit MCL WFMA limit of 10000.")

        print("Preflight checks passed. No motion was commanded.")
        print("For hardware scans, close Micro-Manager's MCL control path before starting the scan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
