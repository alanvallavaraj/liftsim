"""Analysis of the supplementary experiments S1 and S2 (results/supplement.jsonl)."""
import json, os, gzip
import numpy as np
import pandas as pd

NREP, NB = 10, 4000


def load():
    p = "results/supplement.jsonl"
    fh = open(p) if os.path.exists(p) else gzip.open(p + ".gz", "rt")
    rows = []
    for line in fh:
        r = json.loads(line)
        b = {k: r[k] for k in ("building", "pattern", "load", "rep", "controller", "mode")}
        for g, m in r["res"].items():
            for k, v in m.items():
                b[f"{g}.{k}"] = v
        b["w600.R600"] = r["res_warm600"]["all"]["R600"]
        b["e3300.R600"] = r["res_end3300"]["all"]["R600"]
        rows.append(b)
    return pd.DataFrame(rows)


def main():
    df = load()
    idx = df.set_index(["building", "pattern", "load", "controller", "mode", "rep"]).sort_index()
    scen = sorted(set(zip(df.building, df.pattern, df.load)))
    rng = np.random.default_rng(20261117)
    boot = {s: rng.integers(0, NREP, size=(NB, NREP)) for s in scen}

    def vec(s, c, mode, col):
        v = idx.loc[(s[0], s[1], s[2], c, mode), col].to_numpy(float)
        assert len(v) == NREP, (s, c, mode, len(v))
        return v

    def agg(cells):
        est = np.mean([d.mean() for _, d in cells])
        bs = sum(d[boot[s]].mean(axis=1) for s, d in cells) / len(cells)
        return float(est), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))

    # ---- S1: distribution detail, steady demand, simple priority 15%
    rows = []
    variants = [("ETDQ door priority", "ETDQ", "PFB-L15", "ETDQ"), ("DCS door priority", "DCS", "PFB-L15", "DCS"),
                ("DCS-P1", "DCSP1", "PFB-L15", "DCS"), ("DCS-P0", "DCSP0", "PFB-L15", "DCS"),
                ("DCS-PA", "DCSPA", "PFB-L15", "DCS")]
    cols = ["R600", "P90", "P95", "gt60", "gt300", "gt600", "served", "RT900"]
    for x in (0.85, 1.0, 1.15, 1.3):
        for pat in ("all", "uppeak", "lunch", "downpeak"):
            sel = [s for s in scen if s[2] == x and (pat == "all" or s[1] == pat)]
            for name, c, mode, base_c in variants:
                for grp in ("all", "gen15", "pri15"):
                    for col in cols:
                        d, lo, hi = agg([(s, vec(s, c, mode, f"{grp}.{col}") - vec(s, base_c, "FCFS-L", f"{grp}.{col}")) for s in sel])
                        b, _, _ = agg([(s, vec(s, base_c, "FCFS-L", f"{grp}.{col}")) for s in sel])
                        rows.append({"load": x, "pattern": pat, "variant": name, "group": grp, "metric": col,
                                     "base": b, "d": d, "lo": lo, "hi": hi})
    pd.DataFrame(rows).to_csv("results/S1_distribution.csv", index=False)

    # warm-up and window sensitivity (FCFS runs of ETDQ and DCS)
    rows = []
    for x in (0.85, 1.0, 1.15, 1.3):
        sel = [s for s in scen if s[2] == x]
        for c in ("ETDQ", "DCS"):
            for alt in ("w600.R600", "e3300.R600"):
                d, lo, hi = agg([(s, vec(s, c, "FCFS-L", alt) - vec(s, c, "FCFS-L", "all.R600")) for s in sel])
                b, _, _ = agg([(s, vec(s, c, "FCFS-L", "all.R600")) for s in sel])
                rows.append({"load": x, "controller": c, "window": alt, "base": b, "d": d, "lo": lo, "hi": hi})
    # does the window change the priority contrast? (ETDQ PFB - FCFS, DCS-P0 - DCS FCFS, all passengers)
    pd.DataFrame(rows).to_csv("results/S1_window_sensitivity.csv", index=False)

    # ---- S2: share and physical properties
    rows = []
    for x in (0.85, 1.0, 1.15):
        sel = [s for s in scen if s[2] == x]
        for ctrl, base_c in (("ETD", "ETD"), ("DCS", "DCS"), ("DCSP0", "DCS")):
            for mode, m0, g in (("PFB-L05", "FCFS-L", "05"), ("PFB-L10", "FCFS-L", "10"), ("PFB-L15", "FCFS-L", "15"),
                                ("PFB-S05", "FCFS-S05", "05"), ("PFB-T05", "FCFS-T05", "05"), ("PFB-W05", "FCFS-W05", "05")):
                for grp, nm in ((f"gen{g}", "others"), (f"pri{g}", "priority"), ("all", "all")):
                    d, lo, hi = agg([(s, vec(s, ctrl, mode, f"{grp}.R600") - vec(s, base_c, m0, f"{grp}.R600")) for s in sel])
                    rows.append({"load": x, "controller": ctrl, "mode": mode, "group": nm, "d": d, "lo": lo, "hi": hi})
        for ctrl in ("ETD", "DCS"):
            for mode in ("FCFS-S05", "FCFS-T05", "FCFS-W05"):
                d, lo, hi = agg([(s, vec(s, ctrl, mode, "all.R600") - vec(s, ctrl, "FCFS-L", "all.R600")) for s in sel])
                rows.append({"load": x, "controller": ctrl, "mode": mode + " presence", "group": "all", "d": d, "lo": lo, "hi": hi})
    pd.DataFrame(rows).to_csv("results/S2_sensitivity.csv", index=False)
    print("supplement analysed:", len(df), "runs")


if __name__ == "__main__":
    main()
