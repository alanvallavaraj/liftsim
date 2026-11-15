"""Analyses A1-A3 of PROTOCOL.md (version 2). Writes results/*.csv and results/summary.json."""
import itertools, json
import numpy as np
import pandas as pd

RES = "results"
CTRLS = ["NC", "ETA", "ETD", "ETDQ", "DCS"]
NREP = 20
rng = np.random.default_rng(20261115)
BOOT = rng.integers(0, NREP, size=(2000, NREP))
PROF = {"L15": ("FCFS-L", "PFB-L15", "15"), "W05": ("FCFS-W05", "PFB-W05", "05")}


def load_runs(path=f"{RES}/runs.jsonl"):
    rows = []
    import gzip, os
    fh = open(path) if os.path.exists(path) else gzip.open(path + ".gz", "rt")
    for line in fh:
        r = json.loads(line)
        base = {k: r[k] for k in ("building", "kind", "pattern", "load", "rep", "controller",
                                  "mode", "n_arrivals", "seconds")}
        for g, m in r["res"].items():
            for k, v in m.items():
                base[f"{g}.{k}"] = v
        rows.append(base)
    return pd.DataFrame(rows)


def ci(d):
    d = np.asarray(d, float)
    bm = d[BOOT].mean(axis=1)
    return float(d.mean()), float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))


def main():
    df = load_runs()
    df["scen"] = df.kind + "/" + df.pattern
    idx = df.set_index(["building", "scen", "load", "controller", "mode", "rep"]).sort_index()

    def arr(b, s, x, c, mode, col):
        try:
            v = idx.loc[(b, s, x, c, mode), col].to_numpy(float)
        except KeyError:
            return None
        return v if len(v) == NREP else None

    scen = sorted(set(zip(df.building, df.scen, df.load)))
    summary = {"runs": int(len(df)), "scenarios": len(scen),
               "passenger_streams": int(len(scen) * NREP),
               "passengers_generated": int(df[(df.controller == "NC") & (df["mode"] == "FCFS-L")].n_arrivals.sum()),
               "cpu_seconds": float(df.seconds.sum())}

    f = df[df["mode"] == "FCFS-L"]
    cols = ["all.R600", "all.AWT_served", "all.R600_served", "all.served", "all.R300", "all.R900"]
    f.groupby(["building", "scen", "load", "controller"])[cols].mean().reset_index().to_csv(
        f"{RES}/fcfs_means.csv", index=False)

    # ---- A1 / A2: priority contrasts
    rows = []
    for (b, s, x) in scen:
        for prof, (m0, m1, g) in PROF.items():
            for c in CTRLS + ["DCSP1", "DCSP0"]:
                base_c = "DCS" if c.startswith("DCSP") else c
                row = {"building": b, "scen": s, "load": x, "controller": c, "profile": prof}
                ok = True
                for grp, col in ((f"gen{g}", "R600"), (f"pri{g}", "R600"), ("all", "R600"),
                                 (f"gen{g}", "AWT_served"), (f"gen{g}", "RT900"), (f"pri{g}", "RT900")):
                    v0 = arr(b, s, x, base_c, m0, f"{grp}.{col}")
                    v1 = arr(b, s, x, c, m1, f"{grp}.{col}")
                    if v0 is None or v1 is None:
                        ok = False
                        break
                    mu, lo, hi = ci(v1 - v0)
                    k = f"{grp[:3]}.{col}"
                    row[f"{k}.base"] = float(v0.mean())
                    row[f"{k}.d"], row[f"{k}.lo"], row[f"{k}.hi"] = mu, lo, hi
                if ok:
                    rows.append(row)
    a = pd.DataFrame(rows)
    a.to_csv(f"{RES}/priority_contrasts.csv", index=False)

    # effect of wheelchair-like passengers being present at all (FCFS-W05 minus FCFS-L)
    rows = []
    for (b, s, x) in scen:
        for c in CTRLS:
            v0, v1 = arr(b, s, x, c, "FCFS-L", "all.R600"), arr(b, s, x, c, "FCFS-W05", "all.R600")
            if v0 is None or v1 is None:
                continue
            mu, lo, hi = ci(v1 - v0)
            rows.append({"building": b, "scen": s, "load": x, "controller": c, "base": float(v0.mean()),
                         "d": mu, "lo": lo, "hi": hi})
    pd.DataFrame(rows).to_csv(f"{RES}/wheelchair_presence.csv", index=False)

    # ---- A3: metric agreement
    metrics = {"AWT_served": "all.AWT_served", "R600_served": "all.R600_served", "R600": "all.R600",
               "R300": "all.R300", "R900": "all.R900"}
    rows = []
    for (b, s, x) in scen:
        vals = {c: {m: arr(b, s, x, c, "FCFS-L", col) for m, col in metrics.items()} for c in CTRLS}
        if any(vals[c]["R600"] is None for c in CTRLS):
            continue
        for c1, c2 in itertools.combinations(CTRLS, 2):
            row = {"building": b, "scen": s, "load": x, "c1": c1, "c2": c2}
            for m in metrics:
                mu, lo, hi = ci(vals[c1][m] - vals[c2][m])
                row[f"{m}.d"], row[f"{m}.lo"], row[f"{m}.hi"] = mu, lo, hi
            rows.append(row)
    p = pd.DataFrame(rows)
    p.to_csv(f"{RES}/pairwise_contrasts.csv", index=False)
    res = lambda m: (p[f"{m}.lo"] > 0) | (p[f"{m}.hi"] < 0)
    out = []
    for (kind, x), g in p.groupby([p.scen.str.split("/").str[0], "load"]):
        row = {"kind": kind, "load": x, "pairs": len(g)}
        for m1, m2 in (("AWT_served", "R600"), ("R600_served", "R600"), ("AWT_served", "R300"),
                       ("AWT_served", "R900"), ("R300", "R900")):
            o = np.sign(g[f"{m1}.d"]) != np.sign(g[f"{m2}.d"])
            r = o & res(m1)[g.index] & res(m2)[g.index]
            row[f"{m1}_vs_{m2}"] = f"{int(o.sum())} ({int(r.sum())})"
        row["R600.resolved"] = int(res("R600")[g.index].sum())
        out.append(row)
    pd.DataFrame(out).to_csv(f"{RES}/agreement_by_load.csv", index=False)
    o = np.sign(p["AWT_served.d"]) != np.sign(p["R600.d"])
    summary["A3"] = {"pairs": len(p), "discordant": int(o.sum()),
                     "resolved": int((o & res("AWT_served") & res("R600")).sum()),
                     "R600_resolved_pairs": int(res("R600").sum())}
    json.dump(summary, open(f"{RES}/summary.json", "w"), indent=1)
    print(json.dumps(summary, indent=1))
    print(pd.DataFrame(out).to_string())


if __name__ == "__main__":
    main()
