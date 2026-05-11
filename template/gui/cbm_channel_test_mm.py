"""
Small CountBetweenMarkers channel test for the Micro-Manager/Time Tagger setup.

This script does not move the MCL stage. It only verifies that the Swabian Time
Tagger receives photon clicks and pixel begin/end marker pulses on the channels
you specify.

Default backend is InstrumentGateway/gw.daq, because in nspyre setups the
instrument server usually owns the Time Tagger USB handle.

Examples:
    python cbm_channel_test_mm.py --backend gateway --click 3 --begin 1 --end -1 --n-values 25
    python cbm_channel_test_mm.py --backend local --click 3 --begin 1 --end -1 --n-values 25
"""
from __future__ import annotations

import argparse
import time
import numpy as np

try:
    from .timetagger_access_mm import GatewayTimeTaggerAdapter, normalize_daq_mode, physical_channel
except Exception:
    try:
        from template.gui.timetagger_access_mm import GatewayTimeTaggerAdapter, normalize_daq_mode, physical_channel
    except Exception:
        from timetagger_access_mm import GatewayTimeTaggerAdapter, normalize_daq_mode, physical_channel

try:
    from template.drivers.TimeTaggerDriver_mm import tt20, CHANNEL_UNUSED
except Exception:
    try:
        from template.drivers.TimeTaggerDriver_mm import tt20, CHANNEL_UNUSED
    except Exception:
        try:
            from template.drivers.TimeTaggerDriver_mm import tt20, CHANNEL_UNUSED
        except Exception:
            tt20 = None
            CHANNEL_UNUSED = 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Swabian CountBetweenMarkers channel wiring.")
    parser.add_argument("--backend", default="gateway", choices=["gateway", "instrument_gateway", "local", "local_timetagger"],
                        help="Use gw.daq from nspyre instrument server, or open a local USB Time Tagger handle")
    parser.add_argument("--click", type=int, required=True, help="Photon/SPCM click channel, e.g. 3")
    parser.add_argument("--begin", type=int, required=True, help="Pixel begin marker channel, e.g. 1")
    parser.add_argument("--end", type=int, default=CHANNEL_UNUSED, help="Pixel end marker channel, e.g. -1 for falling edge on input 1; 0 means unused")
    parser.add_argument("--n-values", type=int, default=25, help="Number of CBM bins/pixels to collect")
    parser.add_argument("--trigger", type=float, default=0.5, help="Trigger level in volts for click/begin/end physical inputs")
    parser.add_argument("--timeout-s", type=float, default=15.0, help="Timeout while waiting for markers")
    parser.add_argument("--poll-s", type=float, default=0.05, help="Polling interval")
    args = parser.parse_args()

    if args.n_values < 1:
        raise ValueError("--n-values must be >= 1")

    backend = normalize_daq_mode(args.backend)
    gateway_cm = None
    detector = None
    local_detector = False
    try:
        if backend == "gateway":
            from nspyre import InstrumentGateway
            gateway_cm = InstrumentGateway()
            gw = gateway_cm.__enter__()
            detector = GatewayTimeTaggerAdapter(getattr(gw, "daq", None))
            print("Using Time Tagger through nspyre InstrumentGateway.gw.daq.")
        else:
            if tt20 is None:
                raise RuntimeError("TimeTaggerDriver_mm.tt20 could not be imported for local backend.")
            detector = tt20()
            local_detector = True
            print("Using local/direct Time Tagger handle.")

        for ch in sorted({c for c in (physical_channel(args.click), physical_channel(args.begin), physical_channel(args.end)) if c is not None}):
            detector.set_trigger_level(ch, args.trigger)
            print(f"Set trigger level: channel {ch} -> {args.trigger} V")

        detector.start_cbm(
            click_channel=args.click,
            begin_channel=args.begin,
            end_channel=args.end,
            n_values=args.n_values,
        )
        detector.CBM_start(clear=True)
        detector.sync()
        print("CountBetweenMarkers armed.")
        print(f"  click={args.click}, begin={args.begin}, end={args.end}, n_values={args.n_values}")
        print("Now generate photon clicks and pixel marker pulses...")

        t0 = time.monotonic()
        while not detector.cbm_ready():
            elapsed = time.monotonic() - t0
            data = np.asarray(detector.count_BM())
            filled_like = int(np.count_nonzero(data))
            print(f"elapsed={elapsed:6.2f} s, nonzero bins={filled_like:4d}/{args.n_values}", end="\r", flush=True)
            if elapsed > args.timeout_s:
                print()
                print("Timed out before CBM filled. Partial data:")
                print(data)
                try:
                    print("Bin widths ps:", np.asarray(detector.cbm_get_BinWidths()))
                except Exception:
                    pass
                return 2
            time.sleep(args.poll_s)

        print()
        print("CBM complete.")
        print("Counts:")
        print(np.asarray(detector.count_BM()))
        try:
            print("Bin widths ps:")
            print(np.asarray(detector.cbm_get_BinWidths()))
        except Exception:
            pass
        return 0
    finally:
        if local_detector and detector is not None:
            try:
                detector.free_time_tagger()
            except Exception:
                pass
        if gateway_cm is not None:
            try:
                gateway_cm.__exit__(None, None, None)
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
