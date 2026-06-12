"""
Swabian Time Tagger helper for Micro-Manager/Pycro-Manager confocal scans.

This version keeps the original tt20-style API where practical, but adds:
    - count_for_ms(...) for software raster pixels
    - CountBetweenMarkers helpers for hardware-gated confocal images
    - corrected input-delay units: picoseconds, not nanoseconds
    - setMaxRollovers fallback handling for newer/older Time Tagger APIs
"""
from __future__ import annotations

import time
from typing import Callable, Iterable, Optional, Sequence, Tuple

import numpy as np

try:
    import TimeTagger as tt
    from TimeTagger import CHANNEL_UNUSED
except Exception as exc:  # pragma: no cover - depends on lab install
    tt = None
    #CHANNEL_UNUSED = 0
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

try:
    from rpyc.utils.classic import obtain
except Exception:  # pragma: no cover
    def obtain(value):
        return value

PS_PER_MS = 1_000_000_000
PS_PER_S = 1_000_000_000_000


class tt20:
    """Small wrapper around the Swabian Time Tagger Python API."""

    def __init__(self):
        if tt is None:
            raise RuntimeError(
                "TimeTagger could not be imported. Install Swabian-TimeTagger "
                "in the Python environment used for acquisition."
            ) from _IMPORT_ERROR
        self.tagger = tt.createTimeTagger()
        self.counter = None
        self.countrate = None
        self.Time_Differences = None
        self.correlation = None
        self.cbm = None
        self.synchro_measurement = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.free_time_tagger()
        return False

    def set_trigger_level(self, channel, voltage):
        self.tagger.setTriggerLevel(int(channel), float(voltage))

    def set_in_delay(self, channel, delay_ps):
        """Set channel input delay in picoseconds."""
        self.tagger.setInputDelay(int(channel), int(delay_ps))

    def sync(self):
        self.tagger.sync()

    # ------------------------------------------------------------------
    # Counter helpers for software-raster scans
    # ------------------------------------------------------------------
    def start_counter(self, channels, binwidth, n_values, tagger=None):
        if tagger is None:
            tagger = self.tagger
        if not isinstance(channels, (list, tuple)) or not all(isinstance(ch, int) for ch in channels):
            raise ValueError("channels must be a list/tuple of integers.")
        if int(binwidth) <= 0:
            raise ValueError("binwidth must be a positive integer in picoseconds.")
        if int(n_values) <= 0:
            raise ValueError("n_values must be a positive integer.")
        self.counter = tt.Counter(
            tagger,
            channels=[int(ch) for ch in channels],
            binwidth=int(binwidth),
            n_values=int(n_values),
        )
        return self.counter

    def count_for_ms(self, channel, dwell_ms, trigger_level=None, clear=True, normalized=False):
        """Count events on one channel for one pixel dwell.

        Args:
            channel: Time Tagger input channel for photon events.
            dwell_ms: dwell time in milliseconds.
            trigger_level: optional voltage trigger threshold to set before counting.
            clear: clear the Counter buffer when starting.
            normalized: if True return counts/s. Otherwise return raw counts.
        """
        channel = int(channel)
        dwell_ps = int(round(float(dwell_ms) * PS_PER_MS))
        if dwell_ps <= 0:
            raise ValueError("dwell_ms must be positive.")
        if trigger_level is not None:
            self.set_trigger_level(channel, trigger_level)
        counter = tt.Counter(self.tagger, channels=[channel], binwidth=dwell_ps, n_values=1)
        counter.startFor(dwell_ps, clear=bool(clear))
        counter.waitUntilFinished(timeout=-1)
        if normalized:
            data = np.asarray(obtain(counter.getDataNormalized()))
        else:
            data = np.asarray(obtain(counter.getData()))
        return float(data.reshape(-1)[0])

    def clear_counter(self):
        if self.counter is not None:
            self.counter.clear()

    def sFor_Counter(self, measurement_duration):
        self.counter.startFor(int(measurement_duration))

    def wait_until_counter(self):
        self.counter.waitUntilFinished(timeout=-1)

    def get_counter_data(self):
        if self.counter is None:
            raise AttributeError("Counter has not been initialized. Call start_counter first.")
        self.counter.waitUntilFinished(timeout=-1)
        return obtain(self.counter.getData())
    
    def get_c_data(self):
        return self.counter.getData()

    def count_data_Norm(self):
        if self.counter is None:
            raise AttributeError("Counter has not been initialized. Call start_counter first.")
        self.counter.waitUntilFinished(timeout=-1)
        return obtain(self.counter.getDataNormalized())

    def get_total_counter_counts(self):
        return self.counter.getDataTotalCounts()

    # ------------------------------------------------------------------
    # Countrate / histogram compatibility methods from the original driver
    # ------------------------------------------------------------------
    def start_countrate(self, channels, measurement_duration, tagger=None):
        if tagger is None:
            tagger = self.tagger
        self.countrate = tt.Countrate(tagger, channels=[int(ch) for ch in channels])
        self.countrate.startFor(int(measurement_duration))
        return self.countrate

    def get_countrate_data(self):
        self.countrate.waitUntilFinished(timeout=-1)
        return obtain(self.countrate.getData())

    def TimeDifferences(self, click_channel, start_channel, next_channel, sync_channel,
                        bin_width, n_bins, n_histograms, tagger=None):
        if tagger is None:
            tagger = self.tagger
        self.Time_Differences = tt.TimeDifferences(
            tagger,
            int(click_channel),
            int(start_channel),
            int(next_channel),
            int(sync_channel),
            int(bin_width),
            int(n_bins),
            int(n_histograms),
        )
        return self.Time_Differences

    def TD_getData(self):
        return obtain(self.Time_Differences.getData())

    def TD_getIndex(self):
        return obtain(self.Time_Differences.getIndex())

    def TD_setMaxRollovers(self, max_rollovers):
        max_rollovers = int(max_rollovers)
        if hasattr(self.Time_Differences, "setMaxRollovers"):
            return self.Time_Differences.setMaxRollovers(max_rollovers)
        # Older API fallback.
        return self.Time_Differences.setMaxCounts(max_rollovers)

    def TD_getHistogramIndex(self):
        return self.Time_Differences.getHistogramIndex()

    def TD_getCounts(self):
        return self.Time_Differences.getCounts()

    def TD_ready(self):
        return self.Time_Differences.ready()
    
    # Rolando 6/1/2026
    # Introducing the "Histogram" method from "Time histograms" Section of measurements.
    def Histogram(self, click_channel, start_channel, bin_width, n_bins, tagger=None):
        """
        Docstring for Histogram

        :param self: Description from Swabian's Time Tagger API
        :param click_channel: Channel on which stop clicks are received.
        :param start_channel: Channel that sets start times relative to 
                              which clicks on the click channel are measured.
        :param bin_width: Binwidth in picoseconds.
        :param n_bins: Number of bins in each histogram.
        :param tagger: Time tagger object instance.
        :return: Description
        :rtype: Any

        """
        if tagger is None:
            tagger = self.tagger
        self.th_Histogram = tt.Histogram(tagger, click_channel, start_channel, bin_width, n_bins)

    def H_getData(self):
        """
        Docstring for H_getData

        :param self: Description
        :return: A one-dimensional array of size n_bins 
                containing the histograms.
        :rtype: Any
        """
        data = self.th_Histogram.getData()
        return obtain(data)
    
    def H_getIndex(self):
        """
        Docstring for H_getIndex

        :param self: Description
        :return: A vector of size n_bins containing the time bins in ps.
        :rtype: Any
        """
        index = self.th_Histogram.getIndex()
        return obtain(index)
    
    def H_clear(self):
        self.th_Histogram.clear()

    def start_correlation(self, channels, binwidth, n_values=None, max_period=None,
                          n_bins=1000, measurement_duration=None):
        # The modern Correlation signature is Correlation(tagger, ch1, ch2, binwidth, n_bins).
        if len(channels) != 2:
            raise ValueError("channels must contain exactly two channel numbers.")
        self.correlation = tt.Correlation(
            self.tagger,
            int(channels[0]),
            int(channels[1]),
            int(binwidth),
            int(n_bins),
        )
        if measurement_duration is not None:
            self.correlation.startFor(int(measurement_duration), clear=True)
        return self.correlation

    def measure_correlation(self, channel_1, channel_2, binwidth, n_bins=1000, tagger=None):
        if tagger is None:
            tagger = self.tagger
        self.correlation = tt.Correlation(tagger, int(channel_1), int(channel_2), int(binwidth), int(n_bins))
        return self.correlation

    def get_correlation_data(self):
        self.correlation.waitUntilFinished(timeout=-1)
        return obtain(self.correlation.getData())

    def is_measurement_running(self, measurement_type):
        return measurement_type.isRunning()

    # ------------------------------------------------------------------
    # CountBetweenMarkers helpers for hardware-gated scans
    # ------------------------------------------------------------------
    def start_cbm(self, click_channel, begin_channel, end_channel=CHANNEL_UNUSED,
                  n_values=1000, tagger=None):
        if tagger is None:
            tagger = self.tagger
        self.cbm = tt.CountBetweenMarkers(
            tagger,
            int(click_channel),
            int(begin_channel),
            end_channel,
            int(n_values),
        )
        return self.cbm

    def CBM_start(self, clear=True):
        if clear:
            self.cbm.clear()
        self.cbm.start()

    def CBM_sFor(self, duration_ps, clear=True):
        """Run CountBetweenMarkers for a fixed duration in picoseconds."""
        self.cbm.startFor(int(duration_ps), clear=bool(clear))
        # waitUntilFinished timeout is in milliseconds in the common Measurement API.
        self.cbm.waitUntilFinished(timeout=-1)

    def cbm_clear(self):
        self.cbm.clear()

    def cbm_get_BinWidths(self):
        return obtain(self.cbm.getBinWidths())

    def count_BM(self):
        if self.cbm is None:
            raise AttributeError("CountBetweenMarkers has not been initialized. Call start_cbm first.")
        return obtain(self.cbm.getData())

    def cbm_ready(self):
        return bool(self.cbm.ready())

    def count_between_markers_image(self, click_channel, begin_channel, end_channel,
                                    nx, ny, start_callback=None, poll_interval_s=0.02,
                                    timeout_s=None, partial_callback=None):
        """Acquire a gated confocal image using CountBetweenMarkers.

        start_callback should start the external scanner or waveform that emits
        the marker pulses. The returned image has shape (ny, nx).
        """
        nx = int(nx)
        ny = int(ny)
        n_values = nx * ny
        cbm = self.start_cbm(click_channel, begin_channel, end_channel, n_values)
        cbm.clear()
        cbm.start()
        if start_callback is not None:
            start_callback()
        t0 = time.monotonic()
        while not cbm.ready():
            if partial_callback is not None:
                data = np.asarray(obtain(cbm.getData()), dtype=float)
                if data.size >= n_values:
                    partial_callback(data[:n_values].reshape((ny, nx)))
            if timeout_s is not None and (time.monotonic() - t0) > float(timeout_s):
                raise TimeoutError("Timed out waiting for CountBetweenMarkers image.")
            time.sleep(float(poll_interval_s))
        data = np.asarray(obtain(cbm.getData()), dtype=float)
        return data[:n_values].reshape((ny, nx))

    # ------------------------------------------------------------------
    # Synchronization and virtual channel helpers
    # ------------------------------------------------------------------
    def synchro(self):
        self.synchro_measurement = tt.SynchronizedMeasurements(self.tagger)
        return self.synchro_measurement.getTagger()

    def sync_sFor(self, duration):
        self.synchro_measurement.startFor(int(duration))

    def sync_wait(self):
        self.synchro_measurement.waitUntilFinished(timeout=-1)

    def gated_ch(self, input_ch, gate_start, gate_stop, tagger=None):
        if tagger is None:
            tagger = self.tagger
        self.gated_channel = tt.GatedChannel(tagger, int(input_ch), int(gate_start), int(gate_stop))
        return self.gated_channel

    def get_channel(self):
        return self.gated_channel.getChannel()

    def free_time_tagger(self):
        if getattr(self, "tagger", None) is not None:
            tt.freeTimeTagger(self.tagger)
            self.tagger = None

    close = free_time_tagger


TT20 = tt20
