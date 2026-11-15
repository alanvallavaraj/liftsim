"""Result figures for the paper (static PDF, light surface)."""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COL = {"NC": "#2a78d6", "ETA": "#eb6834", "ETD": "#1baf7a", "ETDQ": "#eda100", "DCS": "#e87ba4",
       "DCSP1": "#6250d6", "DCSP0": "#0b0b0b"}
MK = {"NC": "o", "ETA": "s", "ETD": "^", "ETDQ": "v", "DCS": "D", "DCSP1": "P", "DCSP0": "X"}
NAME = {"DCS": "DCS, door priority only", "DCSP1": "DCS-P1 (new)", "DCSP0": "DCS-P0 (new)"}
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


def fig_priority(a, prof, fname):
    m = a[(a.profile == prof) & a.scen.str.startswith("const") & a.controller.isin(CTRLS)]
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.3), sharex=True, sharey="row")
    for j, (p, pl) in enumerate(PATS):
        for r, (col, yl) in enumerate([("gen.R600.d", "other passengers\nchange in $R_{600}$ (s)"),
                                       ("pri.R600.d", "priority passengers\nchange in $R_{600}$ (s)")]):
            ax = axes[r, j]
            for c in CTRLS:
                d = m[(m.scen == p) & (m.controller == c)].groupby("load")[col].mean()
                ax.plot(d.index, d.values, color=COL[c], marker=MK[c], ms=3.5, lw=1.5, label=c)
            if r == 0: ax.set_title(pl, fontsize=9)
            ax.axhline(0, color=INK2, lw=0.6); ax.axvline(1.0, color="#b9b8b2", lw=0.8, zorder=0)
            ax.grid(True, axis="y")
            if j == 0: ax.set_ylabel(yl)
            if r == 1: ax.set_xlabel("demand level $x$")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, ncol=5, loc="lower center", frameon=False, fontsize=8)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(f"figures/{fname}.pdf"); plt.close(fig)


def fig_dcs(a):
    fig, axes = plt.subplots(2, 2, figsize=(7.0, 4.3), sharey="row")
    for j, (kind, xl, tl) in enumerate([("const/uppeak", "demand level $x$", "Steady up-peak demand"),
                                        ("ramp/uppeak", "peak demand level", "Rising and falling demand")]):
        m = a[(a.profile == "L15") & (a.scen == kind)]
        for r, (col, yl) in enumerate([("gen.R600.d", "other passengers\nchange in $R_{600}$ (s)"),
                                       ("pri.R600.d", "priority passengers\nchange in $R_{600}$ (s)")]):
            ax = axes[r, j]
            for c in ["DCS", "DCSP1", "DCSP0", "ETDQ"]:
                d = m[m.controller == c].groupby("load")[col].mean()
                ax.plot(d.index, d.values, color=COL[c], marker=MK[c], ms=4, lw=1.5,
                        ls=(0, (3, 2)) if c == "ETDQ" else "-",
                        label=NAME.get(c, "ETDQ (call buttons), door priority"))
            ax.axhline(0, color=INK2, lw=0.6); ax.grid(True, axis="y")
            if r == 0: ax.set_title(tl, fontsize=9)
            if r == 1: ax.set_xlabel(xl)
            if j == 0: ax.set_ylabel(yl)
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, ncol=4, loc="lower center", frameon=False, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig("figures/dcs_priority.pdf"); plt.close(fig)


if __name__ == "__main__":
    a = pd.read_csv("results/priority_contrasts.csv")
    fig_service(pd.read_csv("results/fcfs_means.csv"))
    fig_priority(a, "L15", "priority_cost")
    fig_priority(a, "W05", "priority_cost_wheelchair")
    fig_dcs(a)
    print("figures written")
