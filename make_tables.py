"""Write LaTeX table bodies for the paper from results/*.csv into paper/tables/."""
import json, os, sys
import pandas as pd
out = sys.argv[1] if len(sys.argv) > 1 else "paper/tables"
os.makedirs(out, exist_ok=True)
ag = pd.read_csv("results/aggregated_effects.csv")
order = [("const", x) for x in (0.5, 0.7, 0.85, 1.0, 1.15, 1.3)] + [("ramp", x) for x in (1.0, 1.15, 1.3, 1.5)]
lab = lambda k, x: (f"Steady, $x={x:g}$" if k == "const" else f"Rise and fall, peak ${x:g}$")


def ci(r, nd=1):
    f = lambda v: ("0.0" if abs(v) < 0.05 else f"{v:+.{nd}f}").replace("-", "$-$").replace("+", "$+$")
    g = lambda v: ("0.0" if abs(v) < 0.05 else f"{v:.{nd}f}").replace("-", "$-$")
    return f"{f(r.d)} {{\\scriptsize[{g(r.lo)}, {g(r.hi)}]}}"


def write(name, rows):
    open(f"{out}/{name}.tex", "w").write("\n".join(rows) + "\n")


def pick(tag, prof, ctrls, grp, k, x, metric="R600"):
    m = ag[(ag.tag == tag) & (ag.profile == prof) & (ag.controllers == ctrls) & (ag.group == grp)
           & (ag.kind == k) & (ag.load == x) & (ag.metric == metric)]
    assert len(m) == 1, (tag, prof, ctrls, grp, k, x, len(m))
    return m.iloc[0]

CB = "NC+ETA+ETD+ETDQ"
rows = []
for k, x in order:
    if (k, x) == ("ramp", 1.0): rows.append("\\midrule")
    rows.append(f"{lab(k, x)} & " + " & ".join(ci(pick("by_load", p, CB, g, k, x)) for p in ("L15", "W05") for g in ("others", "priority")) + "\\\\")
write("tab_prio", rows + ["\\bottomrule"])
for grp, name in (("others", "tab_dcs_others"), ("priority", "tab_dcs_priority")):
    rows = []
    for k, x in order:
        if (k, x) == ("ramp", 1.0): rows.append("\\midrule")
        cells = [ci(pick("by_load_ctrl", "L15", c, grp, k, x)) for c in ("DCS", "DCSP1", "DCSP0")]
        extra = ci(pick("by_load_ctrl", "L15", "DCSP0", "all", k, x)) if grp == "others" else \
            f"{-pick('by_load_ctrl', 'L15', 'DCSP0', 'priority', k, x).pct:.0f}\\%"
        rows.append(f"{lab(k, x)} & " + " & ".join(cells) + f" & {extra}\\\\")
    write(name, rows + ["\\bottomrule"])

g = pd.read_csv("results/agreement_by_load.csv")
rows = []
for _, r in g.iterrows():
    if (r.kind, r.load) == ("ramp", 1.0): rows.append("\\midrule")
    rows.append(f"{lab(r.kind, r.load)} & {r.pairs} & {r['AWT_served_vs_R600']} & {r['R600_served_vs_R600']} & {r['AWT_served_vs_R300']} & {r['R300_vs_R900']}\\\\")
write("tab_agree", rows + ["\\bottomrule"])

v = json.load(open("results/rtt_validation.json"))
write("tab_rtt", [f"{k.split('/')[0]} & {k.split('/')[1]} & {r['full_trips']} & {r['sim_RTT_full']:.1f} ({r['sim_RTT_full_sd']:.1f}) & {r['formula_RTT_full']:.1f} & ${r['rel_diff_full_pct']:+.1f}\\%$\\\\"
                  for k, r in v.items()] + ["\\bottomrule"])

s1 = pd.read_csv("results/S1_distribution.csv")
s1 = s1[s1.pattern == "all"]
rows = []
names = {"ETDQ door priority": "ETDQ, door priority", "DCS door priority": "DCS, door priority", "DCS-P1": "DCS-P1",
         "DCS-P0": "DCS-P0", "DCS-PA": "DCS-PA (exploratory)"}
for x in (1.0, 1.15, 1.3):
    if x != 1.0: rows.append("\\midrule")
    for i, v_ in enumerate(names):
        q = lambda grp, met: s1[(s1.load == x) & (s1.variant == v_) & (s1.group == grp) & (s1.metric == met)].iloc[0]
        pp = lambda r: ("0.0" if abs(100 * r.d) < 0.05 else f"{100 * r.d:+.1f}").replace("-", "$-$").replace("+", "$+$")
        rows.append((f"${x:g}$" if i == 0 else "") + f" & {names[v_]} & {ci(q('gen15', 'R600'))} & {ci(q('pri15', 'R600'))} & {ci(q('all', 'R600'))} & {pp(q('gen15', 'gt300'))} & {pp(q('pri15', 'gt300'))}\\\\")
write("tab_s1", rows + ["\\bottomrule"])

s2 = pd.read_csv("results/S2_sensitivity.csv")
q2 = lambda c, m, g, x: s2[(s2.controller == c) & (s2["mode"] == m) & (s2.group == g) & (s2.load == x)].iloc[0]
rows = []
for c, cn in (("ETD", "ETD, door priority"), ("DCS", "DCS, door priority"), ("DCSP0", "DCS-P0")):
    if c != "ETD": rows.append("\\midrule")
    for i, sh in enumerate(("05", "10", "15")):
        rows.append((cn if i == 0 else "") + f" & {int(sh)}\\% & " + " & ".join(ci(q2(c, f"PFB-L{sh}", g, x)) for x in (1.0, 1.15) for g in ("others", "priority")) + "\\\\")
write("tab_s2_share", rows + ["\\bottomrule"])
rows = []
for m, mn in (("S05", "Space only (3 places)"), ("T05", "Time only (3$\\times$ transfer)"), ("W05", "Both (wheelchair-like)")):
    rows.append(f"{mn} & {ci(q2('ETD', f'FCFS-{m} presence', 'all', 1.0))} & {ci(q2('ETD', f'FCFS-{m} presence', 'all', 1.15))} & {ci(q2('ETD', f'PFB-{m}', 'others', 1.15))} & {ci(q2('ETD', f'PFB-{m}', 'priority', 1.15))}\\\\")
write("tab_s2_prop", rows + ["\\bottomrule"])
print("tables written to", out)
