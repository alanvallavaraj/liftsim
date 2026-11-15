"""Compare simulated up-peak round trips with the classical round-trip-time formula."""
import json, sys
import numpy as np
from liftsim import Building, Sim, generate_arrivals, PATTERNS, handling_capacity, rtt_uppeak
from buildings import BUILDINGS

rows = []
for B in BUILDINGS:
    hc = handling_capacity(B)["HC5"]
    for ctrl in ["NC", "ETD"]:
        for seed in range(1, 6):
            A = generate_arrivals(B.floors, PATTERNS["pure_incoming"], 1.3 * hc / 300, 4500,
                                  (99, seed))
            s = Sim(B, ctrl, A, 4500, log_trips=True).run()
            by_car = {}
            for (ci, t, n) in s.trips:
                by_car.setdefault(ci, []).append((t, n))
            for ci, L in by_car.items():
                for (t, n), (t2, _) in zip(L[:-1], L[1:]):
                    if t >= 600 and n > 0:
                        rows.append((B.name, ctrl, seed, n, t2 - t))
out = {}
for B in BUILDINGS:
    for ctrl in ["NC", "ETD"]:
        R = [(n, r) for (b, c, s, n, r) in rows if b == B.name and c == ctrl]
        full = np.array([r for n, r in R if n == B.cap])
        Pm = np.mean([n for n, r in R])
        f = rtt_uppeak(B, B.cap)["RTT"]
        fm = rtt_uppeak(B, Pm)["RTT"]
        rm = np.mean([r for n, r in R])
        out[f"{B.name}/{ctrl}"] = {
            "trips": len(R), "full_trips": int(len(full)),
            "sim_RTT_full": float(full.mean()), "sim_RTT_full_sd": float(full.std(ddof=1)),
            "formula_RTT_full": f, "rel_diff_full_pct": 100 * (full.mean() - f) / f,
            "mean_P": float(Pm), "sim_RTT_all": float(rm), "formula_RTT_meanP": fm,
            "rel_diff_all_pct": 100 * (rm - fm) / fm,
        }
        # by-P curve
        byP = {}
        for n, r in R:
            byP.setdefault(n, []).append(r)
        out[f"{B.name}/{ctrl}"]["byP"] = {int(n): [float(np.mean(v)), len(v), rtt_uppeak(B, n)["RTT"]]
                                         for n, v in sorted(byP.items()) if len(v) >= 20}
json.dump(out, open("results/rtt_validation.json", "w"), indent=1)
for k, v in out.items():
    print(k, {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "byP"})
