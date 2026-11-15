"""Passenger-level outcome summaries with explicit treatment of unserved passengers."""
from __future__ import annotations
import numpy as np

HORIZONS = (60, 300, 600, 900)


def summarise(tab: dict, t_obs: float, window=(300.0, 3600.0), groups=None) -> dict:
    """Summaries for passengers arriving in `window`, observed until t_obs.

    W_i = board - arrival if boarded by t_obs, else t_obs - arrival (censored).
    R_h = mean(min(W_i, h)) over all arrivals; fully observed when t_obs - window[1] >= h.
    AWT_served = mean waiting over passengers boarded by t_obs (conventional).
    AWT_completed = mean waiting over passengers who reached their destination by t_obs.
    """
    t, b, al = tab["t"], tab["board"], tab["alight"]
    m = (t >= window[0]) & (t < window[1])
    boarded = np.isfinite(b) & (b <= t_obs)
    done = np.isfinite(al) & (al <= t_obs)
    W = np.where(boarded, b - t, t_obs - t)
    J = np.where(done, al - t, t_obs - t)          # time to destination, censored
    out = {}
    groups = groups or {"all": np.ones_like(m)}
    for g, gm in groups.items():
        sel = m & gm
        n = int(sel.sum())
        r = {"n": n}
        if n == 0:
            out[g] = r
            continue
        Wg, Jg = W[sel], J[sel]
        bg, dg = boarded[sel], done[sel]
        for h in HORIZONS:
            r[f"R{h}"] = float(np.minimum(Wg, h).mean())
        r["RT900"] = float(np.minimum(Jg, 900).mean())
        r["R600_served"] = float(np.minimum(Wg[bg], 600).mean()) if bg.any() else float("nan")
        r["W_accrued"] = float(Wg.mean())
        r["served"] = float(bg.mean())
        r["completed"] = float(dg.mean())
        r["AWT_served"] = float(Wg[bg].mean()) if bg.any() else float("nan")
        r["AWT_completed"] = float(Wg[dg].mean()) if dg.any() else float("nan")
        r["P60_all"] = float((Wg > 60).mean())
        r["P60_served"] = float((Wg[bg] > 60).mean()) if bg.any() else float("nan")
        r["ATTD_completed"] = float(Jg[dg].mean()) if dg.any() else float("nan")
        out[g] = r
    return out


def summarise_ext(tab: dict, t_obs: float, window=(300.0, 3600.0), groups=None) -> dict:
    """Distribution measures used in the supplementary experiments. Waits are censored at
    t_obs; every passenger in `window` is followed for at least t_obs - window[1] seconds,
    so quantiles and exceedance shares below that follow-up are exact."""
    t, b, al = tab["t"], tab["board"], tab["alight"]
    m = (t >= window[0]) & (t < window[1])
    boarded = np.isfinite(b) & (b <= t_obs)
    done = np.isfinite(al) & (al <= t_obs)
    W = np.where(boarded, b - t, t_obs - t)
    J = np.where(done, al - t, t_obs - t)
    out = {}
    groups = groups or {"all": np.ones_like(m)}
    for g, gm in groups.items():
        sel = m & gm
        if not sel.any():
            out[g] = {"n": 0}
            continue
        Wg, Jg = W[sel], J[sel]
        out[g] = {"n": int(sel.sum()), "R600": float(np.minimum(Wg, 600).mean()),
                  "R900": float(np.minimum(Wg, 900).mean()),
                  "P90": float(np.quantile(Wg, 0.90)), "P95": float(np.quantile(Wg, 0.95)),
                  "gt60": float((Wg > 60).mean()), "gt300": float((Wg > 300).mean()),
                  "gt600": float((Wg > 600).mean()), "served": float(boarded[sel].mean()),
                  "RT900": float(np.minimum(Jg, 900).mean())}
    return out
