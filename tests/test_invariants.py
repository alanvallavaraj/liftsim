import sys, os, itertools
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from liftsim import Building, Sim, generate_arrivals, PATTERNS, handling_capacity

B = Building("T", 8, 3, 13, 10, 1.6, 1.0, pop_per_floor=50)
HC = handling_capacity(B)["HC5"]


def run(ctrl, pat, x, seed, prio=True, share=0.15, debug=True, **kw):
    A = generate_arrivals(B.floors, PATTERNS[pat], x * HC / 300, 3000, (seed,))
    return A, Sim(B, ctrl, A, 3000, priority_share=share, priority_boarding=prio,
                  debug=debug, **kw).run()


def test_passenger_invariants():
    for ctrl, pat, x, seed, wide in itertools.product(
            ["NC", "ETA", "ETD", "ETDQ", "DCS", "DCSP1", "DCSP0"], ["uppeak", "lunch", "downpeak"],
            [0.6, 1.4], [1, 2], [False, True]):
        kw = dict(pri_size=3, pri_tp_factor=3.0, share=0.05) if wide else {}
        A, s = run(ctrl, pat, x, seed, **kw)
        T = s.passenger_table()
        b, al = T["board"], T["alight"]
        ok = np.isfinite(b)
        assert np.all(b[ok] >= T["t"][ok] - 1e-9)
        assert np.all(~np.isfinite(al[~ok]))            # nobody alights without boarding
        done = np.isfinite(al)
        assert np.all(al[done] > b[done])
        # each passenger boards at most once
        pids = [e[4] for e in s.blog]
        assert len(pids) == len(set(pids))
        # boarding respects capacity and travel direction
        for (t, c, f, d, p, load) in s.blog:
            assert load <= B.cap
            assert A["o"][p] == f
            assert (A["d"][p] - f) * d > 0
        # DCS passengers board only the car they were allocated
        if ctrl in ("DCS", "DCSP1", "DCSP0"):
            for (t, c, f, d, p, load) in s.blog:
                assert s.pcar[p] == c
        # no car keeps arriving at floors without ever opening its doors
        streak, worst = {}, 0
        for (tt, c, f, ev) in s.pos_log:
            streak[c] = 0 if ev == "open" else streak.get(c, 0) + 1
            worst = max(worst, streak[c])
        assert worst <= 12, (ctrl, pat, x, seed, worst)
        # car positions within building
        for (t, c, f, ev) in s.pos_log:
            assert 0 <= f <= B.floors
        # nobody still queued has boarded
        for f in range(B.floors + 1):
            for k in (0, 1):
                for p in s.queue[f][k]:
                    assert not np.isfinite(b[p])


def test_common_random_numbers_and_priority_neutrality():
    for ctrl in ["NC", "ETD", "DCS"]:
        A, s0 = run(ctrl, "lunch", 1.2, 5, prio=False, share=0.05, debug=False)
        _, s1 = run(ctrl, "lunch", 1.2, 5, prio=False, share=0.15, debug=False)
        _, s2 = run(ctrl, "lunch", 1.2, 5, prio=True, share=0.0, debug=False)
        for s in (s1, s2):
            assert np.array_equal(np.nan_to_num(s0.passenger_table()["board"], nan=-1),
                                  np.nan_to_num(s.passenger_table()["board"], nan=-1))


def test_determinism():
    _, a = run("DCS", "uppeak", 1.1, 9, debug=False)
    _, b = run("DCS", "uppeak", 1.1, 9, debug=False)
    assert np.array_equal(np.nan_to_num(a.passenger_table()["alight"], nan=-1),
                          np.nan_to_num(b.passenger_table()["alight"], nan=-1))


def test_light_traffic_everyone_served():
    for ctrl in ["NC", "ETA", "ETD", "ETDQ", "DCS", "DCSP1", "DCSP0"]:
        for pat in ["uppeak", "lunch", "downpeak"]:
            for seed in (3, 4, 5):
              A, s = run(ctrl, pat, 0.3, seed, debug=False, share=0.05, pri_size=3, pri_tp_factor=3.0)
              T = s.passenger_table()
              assert np.isfinite(T["alight"][T["t"] < 2700]).all(), (ctrl, pat, seed)
            A, s = run(ctrl, pat, 0.3, 3, debug=False)
            T = s.passenger_table()
            m = T["t"] < 2700
            assert np.isfinite(T["alight"][m]).all()


def test_priority_boarding_helps_priority_group_under_overload():
    A, off = run("ETD", "uppeak", 1.4, 4, prio=False, debug=False)
    _, on = run("ETD", "uppeak", 1.4, 4, prio=True, debug=False)
    pri = A["u"] < 0.15
    def mw(s, g):
        T = s.passenger_table(); W = np.where(np.isfinite(T["board"]), T["board"] - T["t"], 3000 - T["t"])
        return np.minimum(W[g], 600).mean()
    assert mw(on, pri) < mw(off, pri)


def test_dcsp_equals_dcs_without_priority():
    _, a = run("DCS", "uppeak", 1.3, 6, prio=True, share=0.0, debug=False)
    _, b = run("DCSP1", "uppeak", 1.3, 6, prio=True, share=0.0, debug=False)
    assert np.array_equal(np.nan_to_num(a.passenger_table()["alight"], nan=-1),
                          np.nan_to_num(b.passenger_table()["alight"], nan=-1))
