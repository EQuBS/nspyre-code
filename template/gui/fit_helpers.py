"""
Rolando A. Fimbres Grijalva, 3/30/2026
Script to help with fitting on ODMR and Rabi data (for now).
"""
import numpy as np
from .. import stuttgart_fitting as sf

def _clean_xy(x, y):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    keep = np.isfinite(x) & np.isfinite(y)
    return x[keep], y[keep]

def average_trace(sweeps):
    """
    sweeps: list of arrays shaped (2, n)
    returns x_avg, y avg
    """
    arr = np.stack(sweeps, axis=0)
    x = np.asarray(arr[0, 0], dtype=float)
    y = np.nanmean(arr[:, 1, :], axis=0)
    return _clean_xy(x, y)

def fit_odmr_trace(x, y, n_dips=2):
    """
    Fit ODMR dips on a normalized trace, preferably 'norm' or 'div'.
    Returns None on failure.
    """
    x, y = _clean_xy(x, y)
    if x.size < max(8, 3 * n_dips + 1):
        return None

    try:
        if n_dips == 1:
            p = sf.fit(x, y, sf.Lorentzian, sf.LorentzianEstimator)
            yfit = sf.Lorentzian(*p)(x)
            x0, g, a, c = map(float, p)
            return {
                'params': p,
                'curve': np.stack([x, yfit]),
                'centers_hz': [x0],
                'fwhm_hz': [2 * abs(g)],
                'depth': [abs(a / (np.pi * g))],
                'offset': c,
            }

        # Turn dips into peaks only for seeding.
        c0 = float(sf.baseline(y))
        dip_seed = sf.run_sum(c0 - y, n=3)

        # Find the n deepest dip locations.
        idx = np.sort(sf.find_local_maxima(dip_seed, n_dips))

        # Initial width guess = a few percent of scan width.
        g0 = 0.03 * float(x.max() - x.min())

        # NLorentzians expects: (c, x01, g1, a1, x02, g2, a2, ...)
        p0 = [c0]
        for k in idx:
            a0 = np.pi * g0 * (float(y[k]) - c0)  # negative area for a dip
            p0.extend([float(x[k]), g0, a0])

        p = sf.fit(x, y, sf.NLorentzians, tuple(p0))
        yfit = sf.NLorentzians(*p)(x)

        peaks = []
        for i in range((len(p) - 1) // 3):
            x0, g, a = map(float, p[1 + 3*i : 4 + 3*i])
            peaks.append({
                'center_hz': x0,
                'fwhm_hz': 2 * abs(g),
                'depth': abs(a / (np.pi * g)),
            })
        peaks.sort(key=lambda d: d['center_hz'])

        result = {
            'params': p,
            'curve': np.stack([x, yfit]),
            'peaks': peaks,
            'offset': float(p[0]),
        }
        if len(peaks) >= 2:
            result['splitting_hz'] = peaks[-1]['center_hz'] - peaks[0]['center_hz']
        return result

    except Exception:
        return None
    
def fit_rabi_trace(x, y):
    """
    Fit a phase-aware cosine to a Rabi contrast trace.
    Returns None on failure.
    """
    x, y = _clean_xy(x, y)
    if x.size < 8:
        return None

    try:
        c0 = float(np.mean(y))
        y0 = y - c0

        ymax = float(np.max(y0))
        ymin = float(np.min(y0))
        amp0 = 0.5 * (ymax - ymin)

        # Reuse only the FFT period guess from the Stuttgart helper.
        _, T0 = sf.CosinusNoOffsetEstimator(x, y0)

        # Seed phase from the dominant extremum.
        if abs(ymax) >= abs(ymin):
            a0 = amp0
            x0 = float(x[np.argmax(y0)])
        else:
            a0 = -amp0
            x0 = float(x[np.argmin(y0)])

        p = sf.fit(x, y, sf.Cosinus_phase, (a0, float(T0), x0, c0))
        a, T, x0, c = map(float, p)

        # Normalize sign so x0 marks a bright-state maximum.
        if a < 0:
            a = -a
            x0 = x0 + 0.5 * T

        yfit = sf.Cosinus_phase(a, T, x0, c)(x)
        return {
            'params': (a, T, x0, c),
            'curve': np.stack([x, yfit]),
            'period_s': T,
            'rabi_freq_hz': 1.0 / T,
            'pi2_s': x0 + 0.25 * T,
            'pi_s': x0 + 0.50 * T,
            'three_pi_2_s': x0 + 0.75 * T,
        }

    except Exception:
        return None    
