"""
Preflight check for the nspyre InstrumentGateway Time Tagger path.

Use this before running gui_2D_Scan_mm.py when the instrument server owns the
Time Tagger. It verifies that gw.daq is reachable and that the adapter can count
one short software dwell without opening a second local TimeTagger handle.

Example:
    python timetagger_gateway_preflight_mm.py --channel 3 --trigger 1.0 --dwell-ms 10
"""
from __future__ import annotations

import argparse

try:
    from .timetagger_access_mm import GatewayTimeTaggerAdapter
except Exception:
    try:
        from template.gui.timetagger_access_mm import GatewayTimeTaggerAdapter
    except Exception:
        from timetagger_access_mm import GatewayTimeTaggerAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Time Tagger access through nspyre InstrumentGateway.gw.daq.")
    parser.add_argument("--channel", type=int, default=3, help="Photon/SPCM channel to count")
    parser.add_argument("--trigger", type=float, default=1.0, help="Trigger level in volts")
    parser.add_argument("--dwell-ms", type=float, default=10.0, help="Software count dwell in milliseconds")
    parser.add_argument("--raw", action="store_true", help="Return raw counts instead of counts/s")
    args = parser.parse_args()

    from nspyre import InstrumentGateway

    with InstrumentGateway() as gw:
        detector = GatewayTimeTaggerAdapter(getattr(gw, "daq", None))
        print("Connected to nspyre InstrumentGateway.")
        print("gw.daq:", getattr(gw, "daq", None))
        detector.set_trigger_level(args.channel, args.trigger)
        value = detector.count_for_ms(
            channel=args.channel,
            dwell_ms=args.dwell_ms,
            trigger_level=args.trigger,
            normalized=not args.raw,
        )
        units = "counts" if args.raw else "counts/s"
        print(f"Channel {args.channel}: {value:.6g} {units} for dwell {args.dwell_ms} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
