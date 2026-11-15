"""Execute the version-2 protocol grid; one JSON line per run, resumable."""
import json, os, sys, time, itertools
from multiprocessing import Pool
import numpy as np
from liftsim import Sim, generate_arrivals, generate_ramp_arrivals, PATTERNS, handling_capacity
from liftsim.metrics import summarise
from buildings import BUILDINGS

LOADS = [0.5, 0.7, 0.85, 1.0, 1.15, 1.3]
PEAKS = [1.0, 1.15, 1.3, 1.5]
SCEN = [("const", p, x) for p in ("uppeak", "lunch", "downpeak") for x in LOADS] + \
       [("ramp", "uppeak", x) for x in PEAKS]
CTRLS = ["NC", "ETA", "ETD", "ETDQ", "DCS"]
MODES = {"FCFS-L": (0.0, False, 1, 1.0), "PFB-L15": (0.15, True, 1, 1.0),
         "FCFS-W05": (0.05, False, 3, 3.0), "PFB-W05": (0.05, True, 3, 3.0)}
REPS = 20
T_END = 4500.0
OUT = "results/runs.jsonl"


def arrivals(bi, si, rep):
    B = BUILDINGS[bi]
    kind, pat, x = SCEN[si]
    hc = handling_capacity(B)["HC5"] / 300.0
    key = (2027, bi, si, rep)
    if kind == "const":
        return generate_arrivals(B.floors, PATTERNS[pat], x * hc, T_END, key)
    return generate_ramp_arrivals(B.floors, PATTERNS[pat], 0.5 * hc, x * hc, 1800.0, 3600.0,
                                  T_END, key)


def job(args):
    bi, si, rep, ctrl, mode = args
    B = BUILDINGS[bi]
    A = arrivals(bi, si, rep)
    share, pfb, psize, ptp = MODES[mode]
    t0 = time.time()
    s = Sim(B, ctrl, A, T_END, priority_share=share, priority_boarding=pfb,
            pri_size=psize, pri_tp_factor=ptp).run()
    u = A["u"]
    groups = {"all": np.ones(len(u), bool), "pri05": u < 0.05, "gen05": u >= 0.05,
              "pri15": u < 0.15, "gen15": u >= 0.15}
    res = summarise(s.passenger_table(), T_END, groups=groups)
    kind, pat, x = SCEN[si]
    return {"building": B.name, "kind": kind, "pattern": pat, "load": x, "rep": rep,
            "controller": ctrl, "mode": mode, "n_arrivals": int(len(u)),
            "seconds": round(time.time() - t0, 3), "res": res}


def main():
    done = set()
    if os.path.exists(OUT):
        for line in open(OUT):
            r = json.loads(line)
            done.add((r["building"], r["kind"], r["pattern"], r["load"], r["rep"],
                      r["controller"], r["mode"]))
    jobs = []
    for rep, bi, si in itertools.product(range(REPS), range(3), range(len(SCEN))):
        combos = [(c, m) for c in CTRLS for m in MODES] + \
                 [(c, m) for c in ("DCSP1", "DCSP0") for m in ("PFB-L15", "PFB-W05")]
        for c, m in combos:
            kind, pat, x = SCEN[si]
            if (BUILDINGS[bi].name, kind, pat, x, rep, c, m) not in done:
                jobs.append((bi, si, rep, c, m))
    print(f"{len(jobs)} runs to execute", flush=True)
    t0 = time.time()
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 2) as pool, open(OUT, "a") as fh:
        for k, r in enumerate(pool.imap_unordered(job, jobs, chunksize=8), 1):
            fh.write(json.dumps(r) + "\n")
            if k % 500 == 0:
                fh.flush()
                print(f"{k}/{len(jobs)} {time.time()-t0:.0f}s", flush=True)
    print("done", time.time() - t0, flush=True)


if __name__ == "__main__":
    main()
