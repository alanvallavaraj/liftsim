"""Result figures for the paper (static PDF, light surface)."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COL = {"NC": "#2a78d6", "ETA": "#eb6834", "ETD": "#1baf7a", "ETDQ": "#eda100", "DCS": "#e87ba4",
       "DCSP1": "#6250d6", "DCSP0": "#0b0b0b"}
MK = {"NC": "o", "ETA": "s", "ETD": "^", "ETDQ": "v", "DCS": "D", "DCSP1": "P", "DCSP0": "X"}
NAME = {"DCS": "DCS, door priority", "DCSP1": "DCS-P1 (new)", "DCSP0": "DCS-P0 (new)"}
CTRLS = ["NC", "ETA", "ETD", "ETDQ", "DCS"]
PATS = [("const/uppeak", "Up-peak"), ("const/lunch", "Lunch"), ("const/downpeak", "Down-peak")]
BLDS = ["B1", "B2", "B3"]
INK2 = "#52514e"
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": INK2, "axes.labelcolor": "#0b0b0b", "xtick.color": INK2,
                     "ytick.color": INK2, "grid.color": "#e4e3df", "grid.linewidth": 0.6,
                     "pdf.fonttype": 42})


def fig_service(desc):
    fig, axes = plt.subplots(3, 3, figsize=(7.2, 6.4), sharex=True)
    for i, b in enumerate(BLDS):
        for j, (p, pl) in enumerate(PATS):
            ax = axes[i, j]
            for c in CTRLS:
                d = desc[(desc.building == b) & (desc.scen == p) & (desc.controller == c)].sort_values("load")
                ax.plot(d.load, d["all.R600"], color=COL[c], marker=MK[c], ms=3.5, lw=1.5, label=c)
                ax.plot(d.load, d["all.AWT_served"], color=COL[c], lw=0.9, ls=(0, (3, 2)))
            ax.axvline(1.0, color="#b9b8b2", lw=0.8, zorder=0)
            ax.set_yscale("log"); ax.grid(True, axis="y")
            if i == 0: ax.set_title(pl, fontsize=9)
            if j == 0: ax.set_ylabel(f"{b}\nwaiting time (s)")
            if i == 2: ax.set_xlabel("demand level $x$")
    h, l = axes[0, 0].get_legend_handles_labels()
    h += [plt.Line2D([], [], color=INK2, lw=1.5), plt.Line2D([], [], color=INK2, lw=0.9, ls=(0, (3, 2)))]
    l += ["$R_{600}$, all passengers", "served-only average"]
    fig.legend(h, l, ncol=7, loc="lower center", frameon=False, fontsize=7.5, columnspacing=1.0)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig("figures/service_vs_load.pdf"); plt.close(fig)


def _series(ag, ctrl, pattern, group):
    d = ag[(ag.tag == "by_pattern_ctrl") & (ag.metric == "R600") & (ag.profile == "L15")
           & (ag.controllers == ctrl) & (ag.pattern == pattern) & (ag.group == group)].sort_values("load")
    return d.load.values, d.d.values, d.d.values - d.lo.values, d.hi.values - d.d.values


def fig_priority(ag):
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.3), sharex=True, sharey="row")
    for j, (p, pl) in enumerate(PATS):
        for r, (grp, yl) in enumerate([("others", "other passengers\nchange in $R_{600}$ (s)"),
                                       ("priority", "priority passengers\nchange in $R_{600}$ (s)")]):
            ax = axes[r, j]
            for c in CTRLS:
                x, y, lo, hi = _series(ag, c, p, grp)
                ax.errorbar(x, y, yerr=[lo, hi], color=COL[c], marker=MK[c], ms=3.5, lw=1.4,
                            elinewidth=0.8, capsize=1.5, label=c)
            if r == 0: ax.set_title(pl, fontsize=9)
            ax.axhline(0, color=INK2, lw=0.6); ax.axvline(1.0, color="#b9b8b2", lw=0.8, zorder=0)
            ax.grid(True, axis="y")
            if j == 0: ax.set_ylabel(yl)
            if r == 1: ax.set_xlabel("demand level $x$")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, ncol=5, loc="lower center", frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig("figures/priority_cost.pdf"); plt.close(fig)


def fig_dcs(ag):
    fig, axes = plt.subplots(2, 2, figsize=(7.0, 4.3), sharey="row")
    for j, (kind, xl, tl) in enumerate([("const/uppeak", "demand level $x$", "Steady up-peak demand"),
                                        ("ramp/uppeak", "peak demand level", "Rising and falling demand")]):
        for r, (grp, yl) in enumerate([("others", "other passengers\nchange in $R_{600}$ (s)"),
                                       ("priority", "priority passengers\nchange in $R_{600}$ (s)")]):
            ax = axes[r, j]
            for c in ["DCS", "DCSP1", "DCSP0", "ETDQ"]:
                x, y, lo, hi = _series(ag, c, kind, grp)
                ax.errorbar(x, y, yerr=[lo, hi], color=COL[c], marker=MK[c], ms=4, lw=1.4, elinewidth=0.8,
                            capsize=1.5, ls=(0, (3, 2)) if c == "ETDQ" else "-",
                            label=NAME.get(c, "ETDQ, door priority (vs ETDQ FCFS)"))
            ax.axhline(0, color=INK2, lw=0.6); ax.grid(True, axis="y")
            if r == 0: ax.set_title(tl, fontsize=9)
            if r == 1: ax.set_xlabel(xl)
            if j == 0: ax.set_ylabel(yl)
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, ncol=4, loc="lower center", frameon=False, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig("figures/dcs_priority.pdf"); plt.close(fig)


def fig_summary(ag):
    m = ag[(ag.tag == "by_load") & (ag.metric == "R600") & (ag.profile == "L15") & (ag.kind == "const")]
    loads = [0.85, 1.0, 1.15, 1.3]
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    y = np.arange(len(loads))[::-1]
    span = 150.0
    for yi, x in zip(y, loads):
        g = m[(m.load == x) & (m.group == "others")].iloc[0]
        p = m[(m.load == x) & (m.group == "priority")].iloc[0]
        ax.barh(yi + 0.19, p.d, 0.34, color="#eb6834", xerr=[[p.d - p.lo], [p.hi - p.d]],
                error_kw=dict(elinewidth=0.8, capsize=1.5, ecolor="#0b0b0b"))
        ax.barh(yi - 0.19, g.d, 0.34, color="#2a78d6", xerr=[[g.d - g.lo], [g.hi - g.d]],
                error_kw=dict(elinewidth=0.8, capsize=1.5, ecolor="#0b0b0b"))
        fm = lambda v: f"{abs(v):.0f} s" if abs(v) >= 9.5 else f"{abs(v):.1f} s"
        ax.text(p.lo - 3, yi + 0.19, fm(p.d) + " shorter", ha="right", va="center", fontsize=7.5)
        ax.text(g.hi + 3, yi - 0.19, fm(g.d) + " longer", ha="left", va="center", fontsize=7.5)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(y); ax.set_yticklabels([f"$x={x:g}$" for x in loads])
    ax.set_xlim(-1.45 * span, 0.55 * span)
    ticks = [-150, -100, -50, 0, 50]
    ax.set_xticks(ticks); ax.set_xticklabels([str(abs(t)) for t in ticks])
    ax.set_xlabel("change in capped mean waiting time $R_{600}$ (s)")
    ax.text(-0.7 * span, 3.62, "Priority passengers wait less", ha="center", fontsize=8, fontweight="bold")
    ax.text(0.28 * span, 3.62, "Other passengers\nwait more", ha="center", va="center", fontsize=8, fontweight="bold")
    ax.set_ylim(-0.6, 3.95); ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    fig.savefig("figures/pic_summary.pdf"); plt.close(fig)


if __name__ == "__main__":
    ag = pd.read_csv("results/aggregated_effects.csv")
    fig_service(pd.read_csv("results/fcfs_means.csv"))
    fig_priority(ag); fig_dcs(ag); fig_summary(ag)
    print("figures written")
