"""Supplementary experiments (run after the main campaign; see SUPPLEMENT.md).

S1  distribution detail and an adaptive variant: steady demand, x in {0.85, 1.0, 1.15, 1.3},
    simple priority 15%; ETDQ and DCS with FCFS and PFB, DCSP1, DCSP0, DCSPA (theta 0.5).
S2  sensitivity: priority share (5, 10, 15%) and the two physical properties of the
    wheelchair-like passenger separately (space only, time only); ETD, DCS, DCSP0;
    x in {0.85, 1.0, 1.15}.
Both use replications 0-9 of the main campaign's passenger streams (same seed keys).
"""
import json, os, sys, time, itertools
from multiprocessing import Pool
import numpy as np
from liftsim import Sim
from liftsim.metrics import summarise_ext
from buildings import BUILDINGS
from run_campaign import SCEN, arrivals, T_END

REPS = 10
OUT = "results/supplement.jsonl"
# mode: (share, priority boarding, places, transfer factor)
M = {"FCFS-L": (0.0, False, 1, 1.0), "PFB-L05": (0.05, True, 1, 1.0), "PFB-L10": (0.10, True, 1, 1.0),
     "PFB-L15": (0.15, True, 1, 1.0),
     "FCFS-S05": (0.05, False, 3, 1.0), "PFB-S05": (0.05, True, 3, 1.0),
     "FCFS-T05": (0.05, False, 1, 3.0), "PFB-T05": (0.05, True, 1, 3.0),
     "FCFS-W05": (0.05, False, 3, 3.0), "PFB-W05": (0.05, True, 3, 3.0)}
S1 = [("ETDQ", "FCFS-L"), ("ETDQ", "PFB-L15"), ("DCS", "FCFS-L"), ("DCS", "PFB-L15"),
      ("DCSP1", "PFB-L15"), ("DCSP0", "PFB-L15"), ("DCSPA", "PFB-L15")]
S2 = [(c, m) for c in ("ETD", "DCS") for m in ("FCFS-L", "PFB-L05", "PFB-L10", "PFB-L15", "FCFS-S05",
                                                 "PFB-S05", "FCFS-T05", "PFB-T05", "FCFS-W05", "PFB-W05")] + \
     [("DCSP0", m) for m in ("PFB-L05", "PFB-L10", "PFB-L15", "PFB-S05", "PFB-T05", "PFB-W05")]


def job(a):
    bi, si, rep, ctrl, mode = a
    B = BUILDINGS[bi]
    A = arrivals(bi, si, rep)
    share, pfb, psize, ptp = M[mode]
    s = Sim(B, ctrl, A, T_END, priority_share=share, priority_boarding=pfb, pri_size=psize,
            pri_tp_factor=ptp, theta=0.5).run()
    u = A["u"]
    g = {"all": np.ones(len(u), bool)}
    for sh in (5, 10, 15):
        g[f"pri{sh:02d}"] = u < sh / 100
        g[f"gen{sh:02d}"] = u >= sh / 100
    tab = s.passenger_table()
    kind, pat, x = SCEN[si]
    return {"building": B.name, "kind": kind, "pattern": pat, "load": x, "rep": rep, "controller": ctrl,
            "mode": mode, "res": summarise_ext(tab, T_END, groups=g),
            "res_warm600": summarise_ext(tab, T_END, window=(600.0, 3600.0), groups={"all": g["all"]}),
            "res_end3300": summarise_ext(tab, T_END, window=(300.0, 3300.0), groups={"all": g["all"]})}


def main():
    jobs = set()
    for bi, rep in itertools.product(range(3), range(REPS)):
        for si, (kind, pat, x) in enumerate(SCEN):
            if kind != "const":
                continue
            if x in (0.85, 1.0, 1.15, 1.3):
                jobs |= {(bi, si, rep, c, m) for c, m in S1}
            if x in (0.85, 1.0, 1.15):
                jobs |= {(bi, si, rep, c, m) for c, m in S2}
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            r = json.loads(line)
            done.add((r["building"], r["pattern"], r["load"], r["rep"], r["controller"], r["mode"]))
    jobs = sorted(j for j in jobs if (BUILDINGS[j[0]].name, SCEN[j[1]][1], SCEN[j[1]][2], j[2], j[3], j[4]) not in done)
    print(len(jobs), "runs", flush=True)
    t0 = time.time()
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 2) as pool, open(OUT, "a") as fh:
        for k, r in enumerate(pool.imap_unordered(job, jobs, chunksize=8), 1):
            fh.write(json.dumps(r) + "\n")
            if k % 500 == 0:
                fh.flush(); print(k, round(time.time() - t0), flush=True)
    print("done", time.time() - t0, flush=True)


if __name__ == "__main__":
    main()
