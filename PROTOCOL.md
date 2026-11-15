# Campaign protocol, version 2 (fixed before execution)

Version 1 (results_v1/) is superseded. While extending the simulator, a defect was found
in the rule that chooses a car's service direction at a floor: a car arriving at its
turning floor could skip a call in its own direction and, rarely, shuttle between two
floors without opening. The rule was corrected, a test was added, and every result is
regenerated here. Version 1 results are kept only as a record and are not used.

## Questions
Q1. What does priority-first boarding cost other passengers and give priority
    passengers, by demand level, controller and passenger profile?
Q2. Under destination control, does priority-aware allocation (DCSP1, DCSP0) give
    priority passengers more than door-only priority, and at what cost to others?
Q3. Do the served-only average and the capped average of all passengers rank
    controllers alike?

## Development
The new controllers (ETDQ, DCSP1, DCSP0) were developed on pilot passenger streams
with seed keys (9999, rep), which are not used in this campaign. Their settings were
fixed before execution: ETDQ overload penalty 30 s per place; DCSP weight on other
passengers' delay 1 (DCSP1) or 0 (DCSP0); capacity penalty 600 s.

## Grid
- Buildings B1, B2, B3 (buildings.py).
- Constant-demand scenarios: up-peak, lunch, down-peak x demand level
  x in {0.5, 0.7, 0.85, 1.0, 1.15, 1.3} (54 scenarios).
- Ramp scenarios (12): up-peak mix; demand rises linearly from 0.5 to a peak
  xpeak in {1.0, 1.15, 1.3, 1.5} at 1800 s, falls linearly to 0.5 at 3600 s and
  stays at 0.5 until 4500 s.
- Controllers: NC, ETA, ETD, ETDQ, DCS; plus DCSP1 and DCSP0 with priority boarding.
- Passenger profiles and boarding rules:
  FCFS-L   first come first served, all passengers take one place
  PFB-L15  priority-first boarding, 15% priority passengers, one place each
  FCFS-W05 first come first served, 5% wheelchair-like passengers (3 places,
           3 x transfer time)
  PFB-W05  priority-first boarding, same 5% wheelchair-like passengers
  DCSP1 and DCSP0 are run with PFB-L15 and PFB-W05 only.
- Replications: 20, seed key (2027, building, scenario, rep); identical passenger
  streams for every controller and rule within a scenario-replication.
- Runs: 66 x 20 x (5 x 4 + 2 x 2) = 31,680.

## Observation and outcomes
As version 1: arrivals on [0, 4500) s, counted cohort [300, 3600) s, observation to
4500 s. Primary outcome R600 (mean of min(wait, 600 s) over all counted passengers),
by group (all; priority u < s; general u >= s). Also AWT_served, R600_served, served
fraction, R300, R900, RT900.

## Analyses
A1 (Q1). Paired difference PFB minus FCFS in R600, general and priority groups, for
    NC, ETA, ETD, ETDQ, DCS, for profiles L15 and W05.
A2 (Q2). For destination control: DCS+PFB, DCSP1, DCSP0, each minus DCS+FCFS, general
    and priority groups, profiles L15 and W05.
A3 (Q3). FCFS-L runs: for each scenario and each of the 10 controller pairs, sign of the
    paired difference under AWT_served, R600_served, R600, R300, R900.
Intervals: percentile bootstrap, 2,000 resamples of the 20 replications (paired), seed
20261115, no multiplicity correction.

## Stopping rule
All runs are executed once. A run is repeated only if it fails technically.

## Amendment 1 (after execution; pre-submission audit)
During a pre-submission audit it was found that, under destination control with
first-come-first-served boarding, passengers allocated to a car boarded in the order of
their allocation to that car, not in order of arrival. The two orders differ only for
passengers who were re-allocated after being left behind by a full car, which occurs only
when destination control is saturated. Because priority-first boarding orders passengers by
arrival time within each class, the contrast "priority-first minus FCFS" under destination
control at saturated demand levels mixed the priority effect with this difference in order.
The boarding rule was corrected to arrival order (liftsim/sim.py, `_board`), a test was
added (tests/test_model.py), and the 2,640 destination-control FCFS runs of the campaign
(DCS with FCFS-L and FCFS-W05) were re-executed on the same passenger streams. No other run
is affected: all other runs produce identical results before and after the correction.
The analyses were then recomputed. Aggregated effects with paired-bootstrap intervals
(analyse_ci.py, 4,000 resamples, seed 20261116) were added in the same audit; the analyses
A1-A3 are unchanged.
