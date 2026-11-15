"""Unit tests of model components against hand calculations."""
import math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from liftsim import Building, Sim, generate_arrivals, PATTERNS, flight_time_table, rtt_uppeak
from liftsim.metrics import summarise

B1 = Building("U", 6, 1, 13, 10, 1.6, 1.0, pop_per_floor=50)


def arr(rows):
    t, o, d, u = zip(*rows)
    return {"t": np.array(t, float), "o": np.array(o), "d": np.array(d), "u": np.array(u, float),
            "kind": np.zeros(len(t), int)}


def test_flight_times_closed_form():
    tf, ds = flight_time_table(B1)
    # one floor: 3.6 m > v^2/a = 2.56 m, so the car reaches rated speed
    assert math.isclose(tf[1], 0.5 + 3.6 / 1.6 + 1.6, rel_tol=1e-12)
    assert math.isclose(tf[5], 0.5 + 18.0 / 1.6 + 1.6, rel_tol=1e-12)
    fast = Building("F", 6, 1, 13, 10, 3.5, 1.2)        # v^2/a = 10.2 m > 3.6 m
    tf2, ds2 = flight_time_table(fast)
    assert math.isclose(tf2[1], 0.5 + 2 * math.sqrt(3.6 / 1.2), rel_tol=1e-12)
    assert all(ds[k] < tf[k] for k in range(1, 7)) and all(np.diff(tf[1:]) > 0)


def test_round_trip_formula_hand_case():
    b = Building("H", 2, 1, 13, 10, 1.6, 1.0)
    r = rtt_uppeak(b, 1)                                  # one passenger, two floors
    assert math.isclose(r["S"], 1.0) and math.isclose(r["H"], 1.5)
    tv = 3.6 / 1.6
    ts = (0.5 + 3.6 / 1.6 + 1.6) - tv + 2.0 + 3.0
    assert math.isclose(r["RTT"], 2 * 1.5 * tv + 2 * ts + 2 * 1.2, rel_tol=1e-12)


def test_single_passenger_timelines():
    tf, _ = flight_time_table(B1)
    # lobby -> floor 5; the idle car is at the lobby with doors closed
    s = Sim(B1, "ETD", arr([(10.0, 0, 5, 0.9)]), 200.0).run()
    T = s.passenger_table()
    assert math.isclose(T["board"][0], 10.0)
    assert math.isclose(T["alight"][0], 10.0 + 2.0 + 1.2 + 3.0 + tf[5] + 2.0 + 1.2, rel_tol=1e-12)
    # floor 5 -> lobby; the car must first travel five floors
    for ctrl in ("NC", "ETA", "ETD", "ETDQ", "DCS", "DCSP0"):
        s = Sim(B1, ctrl, arr([(10.0, 5, 0, 0.9)]), 200.0).run()
        T = s.passenger_table()
        assert math.isclose(T["board"][0] - 10.0, tf[5], rel_tol=1e-12), ctrl
        assert math.isclose(T["alight"][0], 10.0 + tf[5] + 2.0 + 1.2 + 3.0 + tf[5] + 2.0 + 1.2, rel_tol=1e-12)


def test_slow_wide_passenger_times_and_space():
    tf, _ = flight_time_table(B1)
    s = Sim(B1, "ETD", arr([(10.0, 0, 5, 0.0)]), 200.0, priority_share=0.05, pri_size=3,
            pri_tp_factor=3.0).run()
    T = s.passenger_table()
    assert math.isclose(T["alight"][0], 10.0 + 2.0 + 3.6 + 3.0 + tf[5] + 2.0 + 3.6, rel_tol=1e-12)
    # eleven one-place passengers at once: ten board, the eleventh waits for the car to return
    s = Sim(B1, "ETD", arr([(10.0, 0, 5, 0.9)] * 11), 400.0).run()
    b = np.sort(s.passenger_table()["board"])
    assert (b[:10] == 10.0).all() and b[10] > 10.0 + 2 * tf[5]


def test_arrival_process_statistics_and_reproducibility():
    n = [len(generate_arrivals(10, PATTERNS["lunch"], 0.2, 4500, (5, k))["t"]) for k in range(200)]
    assert abs(np.mean(n) - 900) < 3 * math.sqrt(900 / 200)
    A = generate_arrivals(10, PATTERNS["lunch"], 2.0, 4500, (7,))
    frac = np.bincount(A["kind"], minlength=3) / len(A["t"])
    assert np.allclose(frac, [0.4, 0.4, 0.2], atol=0.02)
    assert (A["o"] != A["d"]).all() and A["o"].min() >= 0 and A["d"].max() <= 10
    A2 = generate_arrivals(10, PATTERNS["lunch"], 2.0, 4500, (7,))
    assert np.array_equal(A["t"], A2["t"]) and np.array_equal(A["u"], A2["u"])
    assert not np.array_equal(A["t"][:50], generate_arrivals(10, PATTERNS["lunch"], 2.0, 4500, (8,))["t"][:50])


def test_passenger_conservation():
    B = Building("T", 8, 3, 13, 10, 1.6, 1.0)
    for ctrl in ("NC", "ETDQ", "DCS", "DCSP0", "DCSPA"):
        A = generate_arrivals(8, PATTERNS["uppeak"], 0.33, 3000, (21,))
        s = Sim(B, ctrl, A, 3000, priority_share=0.15, priority_boarding=True).run()
        T = s.passenger_table()
        arrived = int((A["t"] <= 3000).sum())
        waiting = sum(len(q) for f in s.queue for q in f)
        riding = sum(len(c.onboard) for c in s.cars)
        boarded = int(np.isfinite(T["board"]).sum())
        assert waiting + boarded == arrived
        assert riding <= boarded and s.nwait == waiting
        assert sum(c.load for c in s.cars) == riding


def test_metric_definitions():
    tab = {"t": np.array([400.0, 500.0, 600.0, 3000.0]),
           "board": np.array([430.0, 1300.0, np.nan, 3010.0]),
           "alight": np.array([500.0, 1400.0, np.nan, 3100.0])}
    r = summarise(tab, 4500.0)["all"]
    assert math.isclose(r["R600"], (30 + 600 + 600 + 10) / 4)
    assert math.isclose(r["AWT_served"], (30 + 800 + 10) / 3)
    assert math.isclose(r["served"], 0.75)


def test_adaptive_variant_limits():
    B = Building("T", 8, 3, 13, 10, 1.6, 1.0)
    A = generate_arrivals(8, PATTERNS["uppeak"], 0.33, 3000, (22,))
    run = lambda c, **k: np.nan_to_num(Sim(B, c, A, 3000, priority_share=0.15, priority_boarding=True,
                                           **k).run().passenger_table()["alight"], nan=-1)
    assert np.array_equal(run("DCSPA", theta=1e9), run("DCSP0"))
    assert np.array_equal(run("DCSPA", theta=-1.0), run("DCSP1"))


def test_fcfs_boarding_is_in_arrival_order_under_destination_control():
    B = Building("T", 8, 3, 13, 10, 1.6, 1.0)
    A = generate_arrivals(8, PATTERNS["uppeak"], 0.45, 3000, (23,))
    s = Sim(B, "DCS", A, 3000, debug=True).run()
    stops = {}
    for (t, c, f, d, p, load) in s.blog:
        stops.setdefault((c, f, d, round(t, 6)), []).append(A["t"][p])
    assert all(v == sorted(v) for v in stops.values())
    # a passenger who boards a car arrived no later than anyone left waiting for that car there
    assert len(stops) > 100
