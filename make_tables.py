"""Write LaTeX table bodies for the paper from results/*.csv."""
import json, sys
import pandas as pd
out = sys.argv[1] if len(sys.argv) > 1 else "tables"
import os; os.makedirs(out, exist_ok=True)
a = pd.read_csv("results/priority_contrasts.csv"); a["kind"] = a.scen.str.split("/").str[0]
CB = ["NC", "ETA", "ETD", "ETDQ"]
order = [("const", x) for x in (0.5, 0.7, 0.85, 1.0, 1.15, 1.3)] + [("ramp", x) for x in (1.0, 1.15, 1.3, 1.5)]
lab = lambda k, x: (f"Steady, {int(round(x*100))}\\%" if k == "const" else f"Rise and fall, peak {int(round(x*100))}\\%")
f = lambda v: f"${v:+.1f}$" if abs(v) >= 0.05 else "0.0"

def agg(prof, ctrls):
    m = a[(a.profile == prof) & a.controller.isin(ctrls)]
    return m.groupby(["kind", "load"]).agg(gen=("gen.R600.d", "mean"), pri=("pri.R600.d", "mean"),
                                           clear=("gen.R600.lo", lambda v: int((v > 0).sum())), n=("gen.R600.d", "size"))
L, W = agg("L15", CB), agg("W05", CB)
rows = []
for k, x in order:
    if (k, x) == ("ramp", 1.0): rows.append("\\midrule")
    rows.append(f"{lab(k,x)} & {f(L.loc[(k,x),'gen'])} & {f(L.loc[(k,x),'pri'])} & {f(W.loc[(k,x),'gen'])} & {f(W.loc[(k,x),'pri'])}\\\\")
open(f"{out}/tab_prio.tex", "w").write("\n".join(rows))
D = {c: agg("L15", [c]) for c in ("DCS", "DCSP1", "DCSP0")}
rows = []
for k, x in order:
    if (k, x) == ("ramp", 1.0): rows.append("\\midrule")
    rows.append(f"{lab(k,x)} & " + " & ".join(f"{f(D[c].loc[(k,x),'gen'])} & {f(D[c].loc[(k,x),'pri'])}" for c in D) + "\\\\")
open(f"{out}/tab_dcs.tex", "w").write("\n".join(rows))
g = pd.read_csv("results/agreement_by_load.csv")
rows = []
for _, r in g.iterrows():
    if (r.kind, r.load) == ("ramp", 1.0): rows.append("\\midrule")
    rows.append(f"{lab(r.kind, r.load)} & {r.pairs} & {r['AWT_served_vs_R600']} & {r['R600_served_vs_R600']} & {r['AWT_served_vs_R300']} & {r['R300_vs_R900']}\\\\")
open(f"{out}/tab_agree.tex", "w").write("\n".join(rows))
v = json.load(open("results/rtt_validation.json"))
open(f"{out}/tab_rtt.tex", "w").write("\n".join(
    f"{k.split('/')[0]} & {k.split('/')[1]} & {r['full_trips']} & {r['sim_RTT_full']:.1f} ({r['sim_RTT_full_sd']:.1f}) & {r['formula_RTT_full']:.1f} & ${r['rel_diff_full_pct']:+.1f}\\%$\\\\"
    for k, r in v.items()))
m = a[(a.profile == "L15") & (a.kind == "const") & a.controller.isin(CB + ["DCS"])].groupby("load")[["gen.R600.d", "pri.R600.d"]].mean().round(2)
print(m)
