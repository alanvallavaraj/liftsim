"""Aggregated effects with paired-bootstrap intervals (main campaign).

An aggregated effect is the mean over cells (building x scenario x controller) of the mean paired
difference over replications. Replications are resampled within each scenario (building x traffic
x demand level), with the same indices for every controller and boarding rule of that scenario
(they share passenger streams) and independently across scenarios (independent streams).
"""
import json, itertools
import numpy as np
import pandas as pd
from analyse import load_runs

NREP, NB = 20, 4000
CB = ["NC", "ETA", "ETD", "ETDQ"]
PROF = {"L15": ("FCFS-L", "PFB-L15", "15"), "W05": ("FCFS-W05", "PFB-W05", "05")}


def main():
    df = load_runs()
    df["scen"] = df.kind + "/" + df.pattern
    idx = df.set_index(["building", "scen", "load", "controller", "mode", "rep"]).sort_index()
    scen = sorted(set(zip(df.building, df.scen, df.load)))
    rng = np.random.default_rng(20261116)
    boot = {s: rng.integers(0, NREP, size=(NB, NREP)) for s in scen}

    def vec(s, c, mode, col):
        v = idx.loc[(s[0], s[1], s[2], c, mode), col].to_numpy(float)
        assert len(v) == NREP
        return v

    def agg(cells, ratio_base=None):
        """cells: list of (scenario, diff vector[, base vector]). Returns mean, lo, hi."""
        est = np.mean([d.mean() for _, d, *_ in cells])
        bs = np.zeros(NB)
        for s, d, *_ in cells:
            bs += d[boot[s]].mean(axis=1)
        bs /= len(cells)
        out = [float(est), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
        if ratio_base:
            base = np.mean([b.mean() for _, _, b in cells])
            bb = np.zeros(NB)
            for s, _, b in cells:
                bb += b[boot[s]].mean(axis=1)
            bb /= len(cells)
            r = 100 * bs / bb
            out += [float(100 * est / base), float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5)), float(base)]
        return out

    rows = []

    def add(tag, sel, ctrls, prof, **extra):
        m0, m1, g = PROF[prof]
        for grp, name in ((f"gen{g}", "others"), (f"pri{g}", "priority"), ("all", "all")):
            for col in ("R600", "AWT_served", "served"):
                cells = []
                for s in sel:
                    for c in ctrls:
                        base_c = "DCS" if c.startswith("DCSP") else c
                        v0 = vec(s, base_c, m0, f"{grp}.{col}")
                        v1 = vec(s, c, m1, f"{grp}.{col}")
                        cells.append((s, v1 - v0, v0))
                r = agg(cells, ratio_base=True)
                rows.append({"tag": tag, "profile": prof, "controllers": "+".join(ctrls), "group": name,
                             "metric": col, "cells": len(cells), "d": r[0], "lo": r[1], "hi": r[2],
                             "pct": r[3], "pct_lo": r[4], "pct_hi": r[5], "base": r[6], **extra})

    kinds = sorted(set((s[1].split("/")[0], s[2]) for s in scen))
    for kind, x in kinds:
        sel = [s for s in scen if s[1].startswith(kind) and s[2] == x]
        for prof in PROF:
            add("by_load", sel, CB, prof, kind=kind, load=x)
            for c in CB + ["DCS", "DCSP1", "DCSP0"]:
                add("by_load_ctrl", sel, [c], prof, kind=kind, load=x)
        for pat in sorted(set(s[1] for s in sel)):
            ss = [s for s in sel if s[1] == pat]
            for c in CB + ["DCS", "DCSP1", "DCSP0"]:
                add("by_pattern_ctrl", ss, [c], "L15", kind=kind, load=x, pattern=pat)
            add("by_pattern", ss, CB, "L15", kind=kind, load=x, pattern=pat)
            add("by_pattern", ss, CB, "W05", kind=kind, load=x, pattern=pat)
    out = pd.DataFrame(rows)
    out.to_csv("results/aggregated_effects.csv", index=False)

    # presence of wheelchair-like passengers (FCFS-W05 minus FCFS-L), all passengers, 5 controllers
    rows = []
    for kind, x in kinds:
        sel = [s for s in scen if s[1].startswith(kind) and s[2] == x]
        cells = [(s, vec(s, c, "FCFS-W05", "all.R600") - vec(s, c, "FCFS-L", "all.R600"), vec(s, c, "FCFS-L", "all.R600"))
                 for s in sel for c in CB + ["DCS"]]
        r = agg(cells, ratio_base=True)
        rows.append({"kind": kind, "load": x, "d": r[0], "lo": r[1], "hi": r[2], "base": r[6]})
    pd.DataFrame(rows).to_csv("results/wheelchair_presence_ci.csv", index=False)

    # FCFS service levels by controller with intervals
    rows = []
    for kind, x in kinds:
        sel = [s for s in scen if s[1].startswith(kind) and s[2] == x]
        for c in CB + ["DCS"]:
            for col in ("all.R600", "all.AWT_served", "all.served"):
                r = agg([(s, vec(s, c, "FCFS-L", col)) for s in sel])
                rows.append({"kind": kind, "load": x, "controller": c, "metric": col, "mean": r[0], "lo": r[1], "hi": r[2]})
        for pat in sorted(set(s[1] for s in sel)):
            for col in ("all.R600", "all.AWT_served", "all.served"):
                r = agg([(s, vec(s, c, "FCFS-L", col)) for s in sel if s[1] == pat for c in CB + ["DCS"]])
                rows.append({"kind": kind, "load": x, "controller": "ALL/" + pat, "metric": col, "mean": r[0], "lo": r[1], "hi": r[2]})
    pd.DataFrame(rows).to_csv("results/service_levels_ci.csv", index=False)
    print("written", len(out))


if __name__ == "__main__":
    main()
