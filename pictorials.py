"""Explanatory pictures: drawn lift diagrams and pictures made from real simulator runs."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, FancyArrowPatch
import pandas as pd

from liftsim import Sim, generate_arrivals, PATTERNS, handling_capacity
from buildings import BUILDINGS

BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, GRID, PALE = "#0b0b0b", "#52514e", "#e4e3df", "#f0efec"
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2,
                     "ytick.color": INK2, "grid.color": GRID, "grid.linewidth": 0.6,
                     "pdf.fonttype": 42})


def person(ax, x, y, s=1.0, color=BLUE, label=None, z=5):
    """A simple person: round head and body. (x, y) is the middle of the feet."""
    ax.add_patch(FancyBboxPatch((x - 0.16 * s, y), 0.32 * s, 0.50 * s,
                                boxstyle=f"round,pad=0,rounding_size={0.1 * s}",
                                fc=color, ec="none", zorder=z))
    ax.add_patch(Circle((x, y + 0.66 * s), 0.14 * s, fc=color, ec="none", zorder=z))
    if label:
        ax.text(x, y + 0.24 * s, label, ha="center", va="center", fontsize=6.5 * s,
                color="white", fontweight="bold", zorder=z + 1)


def arrow(ax, p, q, color=INK2, lw=0.9, style="-|>"):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=8, color=color,
                                 lw=lw, zorder=8, shrinkA=0, shrinkB=0))


def fig_system():
    fig, ax = plt.subplots(figsize=(7.0, 4.6))
    nf = 7                       # floors drawn: lobby + 6
    fh = 1.0
    x0, shaft_w, gap = 3.2, 0.9, 0.25
    # building outline and floors
    ax.add_patch(Rectangle((0.2, 0), x0 + 3 * (shaft_w + gap) + 0.1, nf * fh, fc="white", ec=INK2, lw=1.0))
    for f in range(nf):
        ax.plot([0.2, x0 - 0.1], [f * fh, f * fh], color=INK2, lw=0.8)
        ax.text(0.32, f * fh + 0.42, "Main lobby (floor 0)" if f == 0 else f"Floor {f}",
                fontsize=7.5, color=INK2, va="center")
    # shafts
    car_floor = [0, 4, 2]
    car_dir = [1, -1, 1]
    car_load = [3, 2, 0]
    names = ["Car A", "Car B", "Car C"]
    for k in range(3):
        sx = x0 + k * (shaft_w + gap)
        ax.add_patch(Rectangle((sx, 0), shaft_w, nf * fh, fc=PALE, ec=INK2, lw=0.8))
        cy = car_floor[k] * fh + 0.06
        ax.plot([sx + shaft_w / 2, sx + shaft_w / 2], [cy + 0.86, nf * fh], color=INK2, lw=0.7)
        ax.add_patch(Rectangle((sx + 0.06, cy), shaft_w - 0.12, 0.86, fc="white", ec=INK, lw=1.2, zorder=3))
        for j in range(car_load[k]):
            person(ax, sx + 0.24 + j * 0.21, cy + 0.06, 0.62, BLUE)
        ax.text(sx + shaft_w / 2, nf * fh + 0.16, names[k], ha="center", fontsize=7.5, color=INK)
        ya = cy + 0.43
        if car_dir[k] > 0:
            arrow(ax, (sx + shaft_w + 0.07, ya - 0.25), (sx + shaft_w + 0.07, ya + 0.3), INK, 1.2)
        else:
            arrow(ax, (sx + shaft_w + 0.07, ya + 0.25), (sx + shaft_w + 0.07, ya - 0.3), INK, 1.2)
    # waiting people
    for j in range(4):
        person(ax, 2.05 + j * 0.27, 0.02, 0.8, BLUE)
    for j in range(2):
        person(ax, 2.55 + j * 0.27, 5 * fh + 0.02, 0.8, BLUE)
    person(ax, 2.82, 3 * fh + 0.02, 0.8, ORANGE, "P")
    # call buttons
    for f in (0, 3, 5):
        ax.add_patch(Rectangle((x0 - 0.12, f * fh + 0.3), 0.09, 0.26, fc=INK2, ec="none", zorder=4))
    # notes on the right
    xr = x0 + 3 * (shaft_w + gap) + 0.75
    notes = [
        (6.2, "Lift car", "It carries people up and down. In the small\nbuilding one car takes up to 10 people."),
        (4.75, "Landing", "The place on each floor where people\nwait for a car. They form a queue."),
        (3.3, "Call button", "A person presses UP or DOWN.\nThis is a landing call."),
        (1.85, "Group controller", "A computer program. For each call it\nchooses which car will answer."),
        (0.4, "Priority passenger (P)", "A person who should board first,\nfor example a wheelchair user."),
    ]
    for y, head, body in notes:
        ax.text(xr, y + 0.42, head, fontsize=8.5, fontweight="bold", color=INK, va="center")
        ax.text(xr, y - 0.08, body, fontsize=7.5, color=INK2, va="center", linespacing=1.25)
    person(ax, xr - 0.32, 0.35 - 0.1, 0.8, ORANGE, "P")
    person(ax, xr - 0.32, 4.75 + 0.05, 0.8, BLUE)
    ax.add_patch(Rectangle((xr - 0.5, 6.2 + 0.2), 0.36, 0.42, fc="white", ec=INK, lw=1.2))
    ax.add_patch(Rectangle((xr - 0.365, 3.3 + 0.27), 0.09, 0.26, fc=INK2, ec="none"))
    ax.text(xr - 0.32, 1.85 + 0.4, "?", fontsize=13, fontweight="bold", color=INK, ha="center", va="center")
    ax.set_xlim(0, 11.6); ax.set_ylim(-0.15, nf * fh + 0.45)
    ax.set_aspect("equal"); ax.axis("off")
    fig.tight_layout(pad=0.2)
    fig.savefig("figures/pic_system.pdf"); plt.close(fig)


def fig_stop():
    """One trip of three floors, then one stop, using the B1 values."""
    v, a, D, tsd = 1.6, 1.0, 3 * 3.6, 0.5
    ta = v / a
    tcr = D / v - v / a
    t = [0, tsd, tsd + ta, tsd + ta + tcr, tsd + 2 * ta + tcr]
    sp = [0, 0, v, v, 0]
    t_arr = t[-1]
    seg = [("Doors open", 2.0, YELLOW), ("2 people get out", 2.4, AQUA),
           ("3 people get in", 3.6, BLUE), ("Doors close", 3.0, YELLOW)]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.0, 3.3), sharex=True,
                                   gridspec_kw={"height_ratios": [2.0, 1.0]})
    ax1.plot(t, sp, color=INK, lw=2)
    end = t_arr + sum(s[1] for s in seg)
    ax1.plot([t_arr, end], [0, 0], color=INK, lw=2)
    ax1.fill_between(t, sp, color=PALE)
    ax1.set_ylabel("car speed (m/s)"); ax1.set_ylim(0, 2.1); ax1.grid(True, axis="y")
    ax1.text(tsd + ta + 0.15, 0.55, "speeds up", ha="left", fontsize=7.5, color=INK2)
    ax1.text(tsd + ta + tcr / 2, 1.72, "travels at full speed (1.6 m/s)", ha="center", fontsize=7.5, color=INK2)
    ax1.text(t_arr - ta - 0.15, 0.55, "slows down", ha="right", fontsize=7.5, color=INK2)
    ax1.text((t_arr + end) / 2, 0.3, "car stands at the floor", ha="center", fontsize=7.5, color=INK2)
    ax1.set_title("One trip of 3 floors (10.8 m) and one stop in the small building", fontsize=9, loc="left")
    x = 0.0
    ax2.add_patch(Rectangle((0, 0.2), tsd, 0.6, fc=GRID, ec="white", lw=1.5))
    ax2.add_patch(Rectangle((tsd, 0.2), t_arr - tsd, 0.6, fc="#b9b8b2", ec="white", lw=1.5))
    ax2.text((tsd + t_arr) / 2, 0.5, f"Car moves ({t_arr - tsd:.2f} s)".replace(".35", ".35"), ha="center", va="center", fontsize=7.5, color=INK)
    ax2.text(tsd / 2, 1.0, "start\n0.5 s", ha="center", va="bottom", fontsize=6.5, color=INK2)
    x = t_arr
    for k, (name, d, c) in enumerate(seg):
        ax2.add_patch(Rectangle((x, 0.2), d, 0.6, fc=c, ec="white", lw=1.5))
        ax2.text(x + d / 2, 0.5, f"{d:.1f} s", ha="center", va="center", fontsize=7.5,
                 color="white" if c in (BLUE,) else INK, fontweight="bold")
        ax2.text(x + d / 2, 1.0 + 0.33 * (k % 2), name, ha="center", va="bottom", fontsize=7, color=INK2)
        x += d
    ax2.set_ylim(0, 1.95); ax2.set_yticks([]); ax2.spines["left"].set_visible(False)
    ax2.set_xlabel("time (seconds)"); ax2.set_xlim(0, end + 0.2)
    fig.tight_layout()
    fig.savefig("figures/pic_stop.pdf"); plt.close(fig)
    return t_arr, end


def fig_boarding():
    fig, axes = plt.subplots(2, 1, figsize=(7.0, 3.7))
    order = [1, 2, 3, 4, 5]
    pri = {4}
    cases = [("First come, first served: people board in the order they arrived", [1, 2, 3], [4, 5]),
             ("Priority first: the priority passenger (P) boards first, then the others in order", [4, 1, 2], [3, 5])]
    for ax, (title, inn, out) in zip(axes, cases):
        ax.set_title(title, fontsize=8.5, loc="left", color=INK)
        ax.plot([0, 12.2], [0, 0], color=INK2, lw=0.8)
        # queue before
        ax.text(0.1, 1.55, "Queue when the car arrives", fontsize=7.5, color=INK2)
        for j, p in enumerate(order):
            c = ORANGE if p in pri else BLUE
            person(ax, 3.7 - j * 0.62, 0.03, 1.25, c, "P" if p in pri else str(p))
        ax.text(3.7, -0.32, "arrived first", ha="center", fontsize=6.5, color=INK2)
        ax.text(3.7 - 4 * 0.62, -0.32, "arrived last", ha="center", fontsize=6.5, color=INK2)
        arrow(ax, (4.35, 0.6), (5.15, 0.6), INK, 1.3)
        # car
        ax.add_patch(Rectangle((5.4, 0.0), 2.3, 1.3, fc="white", ec=INK, lw=1.3))
        ax.text(6.55, 1.55, "Car has 3 free places", ha="center", fontsize=7.5, color=INK2)
        for j, p in enumerate(inn):
            c = ORANGE if p in pri else BLUE
            person(ax, 5.85 + j * 0.7, 0.05, 1.25, c, "P" if p in pri else str(p))
        # left behind
        ax.text(9.2, 1.55, "Must wait for the next car", fontsize=7.5, color=INK2)
        for j, p in enumerate(out):
            c = ORANGE if p in pri else BLUE
            person(ax, 9.6 + j * 0.7, 0.03, 1.25, c, "P" if p in pri else str(p))
        ax.set_xlim(0, 12.2); ax.set_ylim(-0.5, 1.9); ax.set_aspect("equal"); ax.axis("off")
    fig.tight_layout(h_pad=1.2)
    fig.savefig("figures/pic_boarding.pdf"); plt.close(fig)


def fig_window():
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    bands = [(0, 300, GRID, "Start-up\n(not counted)"), (300, 3600, "#cde2fb", "Passengers who arrive here are counted"),
             (3600, 4500, GRID, "People still arrive,\nbut are not counted")]
    for a, b, c, lab in bands:
        ax.add_patch(Rectangle((a, 3.3), b - a, 0.8, fc=c, ec="white", lw=1.5))
        ax.text((a + b) / 2, 3.7, lab, ha="center", va="center", fontsize=7, color=INK, linespacing=1.15)
    ex = [(2.4, 1000, 1030, "Passenger A boards after 30 s", "counts as 30 s"),
          (1.5, 3400, 4150, "Passenger B boards after 750 s", "counts as 600 s"),
          (0.6, 3590, None, "Passenger C has not boarded when watching ends", "counts as 600 s")]
    for y, a, b, lab, cnt in ex:
        e = b if b else 4500
        ax.plot([a, e], [y, y], color=BLUE, lw=5, solid_capstyle="butt")
        ax.plot([a], [y], marker="o", color=INK, ms=4)
        if b:
            ax.plot([b], [y], marker="|", color=INK, ms=11, mew=1.6)
        ax.text(a - 60, y + 0.02, f"{lab}  ->  {cnt}", ha="right", va="center", fontsize=7.5, color=INK)
    ax.axvline(4500, color=INK, lw=1.2)
    ax.text(4480, 2.9, "watching\nends", ha="right", va="top", fontsize=7, color=INK2)
    ax.set_xlim(0, 4560); ax.set_ylim(0.1, 4.2)
    ax.set_yticks([]); ax.spines["left"].set_visible(False)
    ax.set_xticks([0, 300, 1000, 2000, 3000, 3600, 4500])
    ax.set_xlabel("time in the simulation (seconds)")
    fig.tight_layout()
    fig.savefig("figures/pic_window.pdf"); plt.close(fig)


class TracedSim(Sim):
    """Sim that also records each car movement, without changing the model."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.moves = []

    def _on_car_arrive(self, c):
        self.moves.append((c.i, c.t0, c.s, self.now, c.target))
        super()._on_car_arrive(c)


def fig_trajectories():
    B = BUILDINGS[0]
    hc = handling_capacity(B)["HC5"]
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.6), gridspec_kw={"height_ratios": [1.6, 1.0]})
    cols = [BLUE, ORANGE, AQUA]
    lss = ["-", (0, (4, 1.5)), (0, (1, 1))]
    info = {}
    for j, x in enumerate([0.7, 1.3]):
        A = generate_arrivals(B.floors, PATTERNS["uppeak"], x * hc / 300, 4500, (2027, 0, 1 if x == 0.7 else 5, 0))
        s = TracedSim(B, "ETD", A, 4500).run()
        ax = axes[0, j]
        t0, t1 = 1500, 1800
        for ci in range(B.cars):
            pts = []
            for (c, ta, fa, tb, fb) in s.moves:
                if c == ci and tb >= t0 - 60 and ta <= t1 + 60:
                    pts += [(ta, fa), (tb, fb)]
            pts.sort()
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=cols[ci], ls=lss[ci], lw=1.5,
                    label=f"Car {'ABC'[ci]}")
        ax.set_xlim(t0, t1); ax.set_ylim(-0.3, B.floors + 2.2)
        ax.set_yticks(range(0, B.floors + 1, 2)); ax.grid(True, axis="y")
        ax.set_title(f"Demand at {int(x * 100)}% of what the lifts can carry", fontsize=8.5)
        ax.set_xlabel("time (seconds)")
        if j == 0:
            ax.set_ylabel("floor (0 = main lobby)")
            ax.legend(frameon=False, fontsize=7, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.0),
                      borderaxespad=0.1, handlelength=2.6)
        # people waiting over time
        T = s.passenger_table()
        ev = [(t, 1) for t in T["t"]] + [(b, -1) for b in T["board"] if np.isfinite(b)]
        ev.sort()
        tt = [e[0] for e in ev]; nn = np.cumsum([e[1] for e in ev])
        ax2 = axes[1, j]
        ax2.step(tt, nn, where="post", color=INK, lw=0.9)
        ax2.axvspan(t0, t1, color="#cde2fb", lw=0)
        ax2.set_xlim(0, 4500); ax2.set_xlabel("time (seconds)"); ax2.grid(True, axis="y")
        if j == 0:
            ax2.set_ylabel("people waiting\nin the building")
        m = (T["t"] >= 300) & (T["t"] < 3600)
        W = np.where(np.isfinite(T["board"]), T["board"] - T["t"], 4500 - T["t"])[m]
        info[x] = {"n": int(m.sum()), "R600": float(np.minimum(W, 600).mean()),
                   "served": float(np.isfinite(T["board"][m]).mean()), "maxq": int(nn.max())}
    fig.tight_layout()
    fig.savefig("figures/pic_trajectories.pdf"); plt.close(fig)
    return info


def fig_summary():
    a = pd.read_csv("results/priority_contrasts.csv")
    m = a[(a.profile == "L15") & a.scen.str.startswith("const")
          & a.controller.isin(["NC", "ETA", "ETD", "ETDQ", "DCS"])]
    m = m.groupby("load")[["gen.R600.d", "pri.R600.d"]].mean()
    loads = [0.85, 1.0, 1.15, 1.3]
    fig, ax = plt.subplots(figsize=(6.4, 2.9))
    y = np.arange(len(loads))[::-1]
    span = max(-m.loc[loads, "pri.R600.d"].min(), 1.0)
    for yi, x in zip(y, loads):
        g, p = m.loc[x, "gen.R600.d"], -m.loc[x, "pri.R600.d"]
        ax.barh(yi + 0.19, -p, 0.34, color=ORANGE)
        ax.barh(yi - 0.19, g, 0.34, color=BLUE)
        ax.text(-p - 0.02 * span, yi + 0.19, f"{p:.0f} s shorter" if p >= 9.5 else f"{p:.1f} s shorter",
                ha="right", va="center", fontsize=7.5, color=INK)
        ax.text(max(g, 0) + 0.02 * span, yi - 0.19, f"{g:.0f} s longer" if g >= 9.5 else f"{g:.1f} s longer",
                ha="left", va="center", fontsize=7.5, color=INK)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(y); ax.set_yticklabels([f"Demand at {int(round(x * 100))}%\nof lift capacity" for x in loads], fontsize=7.5)
    ax.set_xlim(-1.45 * span, 0.6 * span)
    lo, hi = ax.get_xlim()
    ticks = [t for t in ax.get_xticks() if lo <= t <= hi]
    ax.set_xticks(ticks); ax.set_xticklabels([f"{abs(t):.0f}" for t in ticks])
    ax.set_xlabel("change in average waiting time (seconds)")
    ax.text(-0.7 * span, 3.62, "Priority passengers wait less", ha="center", fontsize=8, color=INK, fontweight="bold")
    ax.text(0.3 * span, 3.62, "Other passengers\nwait more", ha="center", va="center", fontsize=8, color=INK, fontweight="bold")
    ax.set_ylim(-0.6, 3.95); ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
    fig.tight_layout()
    fig.savefig("figures/pic_summary.pdf"); plt.close(fig)


def fig_ramp():
    fig, ax = plt.subplots(figsize=(5.6, 2.6))
    t = np.array([0, 30, 60, 75])
    for pk, c, ls in zip([1.0, 1.15, 1.3, 1.5], [BLUE, ORANGE, AQUA, YELLOW], ["-", (0, (4, 1.5)), (0, (1, 1)), "-."]):
        ax.plot(t, [50, pk * 100, 50, 50], color=c, ls=ls, lw=1.6, label=f"peak {int(round(pk * 100))}%")
    ax.axhline(100, color="#b9b8b2", lw=1.0, zorder=0, label="handling capacity")
    ax.set_xlabel("time (minutes)"); ax.set_ylabel("demand (% of handling capacity)")
    ax.set_xlim(0, 75); ax.set_ylim(0, 170); ax.set_xticks([0, 15, 30, 45, 60, 75]); ax.grid(True, axis="y")
    # legend outside the plotting area, to the right
    ax.legend(frameon=False, fontsize=7.5, loc="center left", bbox_to_anchor=(1.02, 0.5), handlelength=2.8,
              borderaxespad=0.0)
    fig.tight_layout(); fig.savefig("figures/pic_ramp.pdf", bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    fig_system(); print(fig_stop()); fig_boarding(); fig_window(); fig_ramp()
    print(fig_trajectories())
