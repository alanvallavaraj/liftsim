# Supplementary experiments (added after the main campaign)

These experiments were designed and run after the main campaign (PROTOCOL.md) had been
analysed, in response to an internal pre-submission audit. They are therefore exploratory.
They do not change any result of the main campaign. The simulator code for the seven
controllers of the main campaign is unchanged in behaviour (checked on 56 configurations:
identical passenger outcomes before and after the additions).

Both experiments reuse replications 0-9 of the main campaign's passenger streams (same
seed keys), steady demand only, three buildings, three traffic patterns.

## S1 Distribution detail and an adaptive variant
- Demand levels x in {0.85, 1.0, 1.15, 1.3}; simple priority passengers, share 15%.
- Runs: ETDQ and DCS with FCFS and with priority-first boarding; DCSP1; DCSP0; DCSPA.
- DCSPA (exploratory extension, not part of the main contribution): priority-aware
  destination control that uses DCSP0 while the number of people waiting in the building
  is at most theta x (cars x boarding limit), and DCSP1 otherwise. theta = 0.5 was chosen on
  pilot streams (seed keys (9999, rep)) from {0.5, 1, 2} and fixed before these runs.
- Extra outcomes: 90th and 95th percentile of the waiting time, share of passengers
  waiting more than 60, 300 and 600 s, share served, restricted time to destination.
  Every counted passenger is followed for at least 900 s, so percentiles and shares
  below 900 s are exact.
- Window sensitivity: R600 recomputed for counted windows [600, 3600) and [300, 3300).

## S2 Sensitivity to priority share and to passenger properties
- Demand levels x in {0.85, 1.0, 1.15}; controllers ETD, DCS (door priority), DCSP0.
- Priority share 5%, 10%, 15% with one-place passengers (separates share from properties).
- At a share of 5%: space only (3 places, normal transfer time), time only (1 place,
  3 x transfer time), both (the wheelchair-like profile of the main campaign).

Runs: 8,730. Bootstrap: 4,000 resamples of the 10 replications within each scenario,
seed 20261117. Programs: run_supplement.py, analyse_supplement.py.
