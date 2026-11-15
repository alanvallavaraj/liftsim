# Campaign protocol (fixed before execution)

## Purpose
1. Test whether conventional served-passenger mean waiting time (AWT) and an
   all-arrival restricted mean waiting time order four lift group controllers
   differently, as demand moves from below to above up-peak handling capacity.
2. Quantify the waiting-time cost that priority-first boarding imposes on other
   passengers as a function of demand, and whether conventional AWT reports that
   cost correctly.

## Model
Event-driven simulator in `liftsim/` (trapezoidal kinematics, start delay 0.5 s,
door opening 2.0 s, closing 3.0 s, transfer 1.2 s per passenger, interfloor height
3.6 m, directional-collective movement, lobby homing of idle cars). Validated
against the classical up-peak round-trip time (`validate_rtt.py`) before this
protocol was fixed.

## Grid
- Buildings (`buildings.py`): B1 (10 floors, 3 cars, 13-person cars, 1.6 m/s),
  B2 (16 floors, 4 cars, 17-person, 2.5 m/s), B3 (24 floors, 6 cars, 21-person,
  3.5 m/s). Boarding limit 10, 13 and 16 persons (80% of rated load).
- Traffic patterns (incoming/outgoing/interfloor): up-peak 0.85/0.10/0.05,
  lunch 0.40/0.40/0.20, down-peak 0.05/0.85/0.10.
- Load ratio x = arrival rate / up-peak five-minute handling capacity at the
  boarding limit: 0.5, 0.7, 0.85, 1.0, 1.15, 1.3, 1.5.
- Controllers: NC, ETA, ETD, DCS.
- Boarding: first come first served (FCFS); priority-first boarding (PFB) with
  priority share 0.05; PFB with priority share 0.15.
- Replications: 10 per scenario (rep 0-9), seed key (2026, building, pattern,
  load, rep). Every controller and boarding rule in a scenario-replication sees
  the identical passenger stream (common random numbers). Priority flags use a
  separate stream, so FCFS runs are identical for both priority shares and are
  run once.
- Runs: 3 x 3 x 7 x 10 x 4 x 3 = 7,560.

## Observation
Arrivals on [0, 4500) s. Measured cohort: arrivals in [300, 3600) s. Observation
ends at T = 4500 s, so every measured passenger has at least 900 s of follow-up
and the restricted means below are fully observed for horizons up to 900 s.

## Outcomes
- Waiting W_i = boarding time - arrival time if boarded by T, else T - arrival.
  Boarding time is when the doors of the car the passenger boards begin to open
  (or the arrival time, if the passenger arrives while doors are open).
- Primary: R600 = mean of min(W_i, 600 s) over all measured arrivals.
- Conventional: AWT_served = mean W_i over measured passengers boarded by T.
- Decomposition: R600_served = mean of min(W_i, 600) over boarded passengers
  only (isolates passenger selection from capping).
- Secondary: served and completed fractions, share of arrivals waiting > 60 s
  (all arrivals vs served only), R300, R900, restricted time to destination RT900.
- Groups: all; for each share s in {0.05, 0.15}, priority (u < s) and general
  (u >= s).

## Analyses
A1. FCFS runs. For each scenario (63) and each controller pair (6), the paired
    difference over replications under AWT_served, R600_served and R600.
    A pair is "discordant" when the two metrics' mean differences have opposite
    signs, and "resolved discordant" when, in addition, both 95% paired bootstrap
    intervals exclude zero. Reported by load ratio.
A2. For each controller, scenario and share: paired difference PFB - FCFS in
    R600 for the general and priority groups, and in AWT_served for the general
    group. Reported by load ratio.
A3. Horizon sensitivity of A1 with R300 and R900.

Bootstrap: resample replications within a scenario (paired across controllers and
boarding rules), 2,000 draws, seed 20261115, percentile 95% intervals, no
multiplicity correction. Intervals describe replication variability for the
fixed scenario, not uncertainty about real buildings.

## Stopping rule
All 7,560 runs are executed once. A run is repeated only if it fails technically;
no run is excluded or repeated on the basis of its outcome.
