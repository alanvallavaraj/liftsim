"""Building description, kinematics and the classical up-peak round-trip time."""
from __future__ import annotations
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Building:
    name: str
    floors: int            # floors served above the main lobby (levels 0..floors)
    cars: int
    rated: int             # rated load in persons
    cap: int               # boarding limit used by the simulator (persons)
    v: float               # rated speed (m/s)
    a: float               # acceleration = deceleration (m/s^2)
    h: float = 3.6         # interfloor height (m)
    pop_per_floor: int = 80
    t_open: float = 2.0    # door opening time (s)
    t_close: float = 3.0   # door closing time (s)
    t_p: float = 1.2       # passenger transfer time, per passenger, per transfer (s)
    t_sd: float = 0.5      # motor start delay added to every flight (s)

    @property
    def pop(self) -> int:
        return self.floors * self.pop_per_floor


def kin_time(D: float, v: float, a: float) -> float:
    """Time for a journey of length D (m) with a trapezoidal/triangular speed profile."""
    if D <= 0:
        return 0.0
    if D >= v * v / a:
        return D / v + v / a
    return 2.0 * math.sqrt(D / a)


def decel_start(D: float, v: float, a: float) -> float:
    """Time after motion starts at which deceleration must begin to stop after D metres."""
    if D <= 0:
        return 0.0
    if D >= v * v / a:
        return D / v
    return math.sqrt(D / a)


def flight_time_table(b: Building):
    """tf[k]: flight time over k floors (incl. start delay); ds[k]: latest time after
    departure at which a stop k floors away can still be committed."""
    n = b.floors + 1
    tf = [0.0] + [b.t_sd + kin_time(k * b.h, b.v, b.a) for k in range(1, n)]
    ds = [0.0] + [b.t_sd + decel_start(k * b.h, b.v, b.a) for k in range(1, n)]
    return tf, ds


def rtt_uppeak(b: Building, P: float) -> dict:
    """Classical up-peak round-trip time for uniform floor populations
    (RTT = 2 H tv + (S+1) ts + 2 P tp), using this simulator's kinematics."""
    N = b.floors
    S = N * (1.0 - (1.0 - 1.0 / N) ** P)
    H = N - sum((i / N) ** P for i in range(1, N))
    tv = b.h / b.v
    tf1 = b.t_sd + kin_time(b.h, b.v, b.a)
    ts = tf1 - tv + b.t_open + b.t_close
    rtt = 2.0 * H * tv + (S + 1.0) * ts + 2.0 * P * b.t_p
    return {"S": S, "H": H, "tv": tv, "ts": ts, "RTT": rtt,
            "interval": rtt / b.cars}


def handling_capacity(b: Building, P: float | None = None) -> dict:
    """Up-peak five-minute handling capacity at car load P (default: boarding limit)."""
    P = b.cap if P is None else P
    r = rtt_uppeak(b, P)
    hc5 = 300.0 * P * b.cars / r["RTT"]
    return {**r, "P": P, "HC5": hc5, "HC5_pct": 100.0 * hc5 / b.pop}
