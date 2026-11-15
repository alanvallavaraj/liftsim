"""Passenger arrival streams with common random numbers across controllers."""
from __future__ import annotations
import numpy as np

# (incoming, outgoing, interfloor) shares of the passenger stream
PATTERNS = {
    "uppeak": (0.85, 0.10, 0.05),
    "lunch": (0.40, 0.40, 0.20),
    "downpeak": (0.05, 0.85, 0.10),
    "pure_incoming": (1.0, 0.0, 0.0),   # used only for RTT validation
}


def generate_arrivals(floors: int, mix, rate: float, t_end: float, seed_key):
    """Poisson arrivals at constant rate (passengers/s) on [0, t_end].

    seed_key is a tuple of non-negative integers; times/origins/destinations use one
    child stream and the priority draws another, so the passenger stream is identical
    whatever priority share is later applied.
    """
    ss = np.random.SeedSequence(list(seed_key))
    s_main, s_pri = ss.spawn(2)
    rng = np.random.default_rng(s_main)
    n = rng.poisson(rate * t_end)
    t = np.sort(rng.uniform(0.0, t_end, n))
    kind = rng.choice(3, size=n, p=np.asarray(mix, float) / np.sum(mix))
    o = np.zeros(n, dtype=np.int64)
    d = np.zeros(n, dtype=np.int64)
    up = rng.integers(1, floors + 1, size=n)
    # interfloor: two distinct upper floors
    i1 = rng.integers(1, floors + 1, size=n)
    i2 = rng.integers(1, floors, size=n)
    i2 = np.where(i2 >= i1, i2 + 1, i2)
    inc, out, inter = kind == 0, kind == 1, kind == 2
    d[inc] = up[inc]
    o[out] = up[out]
    o[inter], d[inter] = i1[inter], i2[inter]
    u = np.random.default_rng(s_pri).random(n)
    return {"t": t, "o": o, "d": d, "u": u, "kind": kind}


def generate_ramp_arrivals(floors: int, mix, rate_base: float, rate_peak: float, t_peak: float,
                           t_ramp_end: float, t_end: float, seed_key):
    """Arrivals whose rate rises linearly from rate_base (t=0) to rate_peak (t_peak), falls
    linearly back to rate_base at t_ramp_end and stays there until t_end (thinning)."""
    def rate(t):
        up = rate_base + (rate_peak - rate_base) * t / t_peak
        down = rate_peak - (rate_peak - rate_base) * (t - t_peak) / (t_ramp_end - t_peak)
        return np.where(t <= t_peak, up, np.where(t <= t_ramp_end, down, rate_base))
    A = generate_arrivals(floors, mix, rate_peak, t_end, seed_key)
    ss = np.random.SeedSequence(list(seed_key) + [777])
    keep = np.random.default_rng(ss).random(len(A["t"])) < rate(A["t"]) / rate_peak
    return {k: v[keep] for k, v in A.items()}
