# liftsim

Seconds-based lift group simulator (`liftsim`) and the full study behind the paper
"Priority boarding in lift groups: its cost to other passengers and a priority-aware
destination control rule".

## Contents
- `liftsim/` simulator: `model.py` (buildings, kinematics, round-trip formula),
  `traffic.py` (passenger streams), `sim.py` (cars, doors, controllers NC, ETA, ETD,
  ETDQ, DCS, DCSP1, DCSP0, boarding rules), `metrics.py` (waiting-time measures)
- `buildings.py` the three buildings
- `PROTOCOL.md` test plan, fixed before the runs; `results/frozen_hashes.txt`
- `tests/` automatic checks: `python -m pytest tests`
- `validate_rtt.py` check against the classical round-trip time
- `run_campaign.py [workers]` 31,680 runs -> `results/runs.jsonl` (resumable; about
  3.5 CPU hours). The archived run-level results are in
  `results/runs.jsonl.gz`; `analyse.py` reads either form.
- `analyse.py` -> `results/*.csv`, `results/summary.json`
- `figures.py`, `pictorials.py` -> `figures/*.pdf`; `make_tables.py` -> LaTeX tables
- `results_v1/` superseded first campaign, kept as a record (see PROTOCOL.md)
- `paper/` LaTeX source of the manuscript

## Quick start
```
pip install numpy pandas matplotlib pytest
python -m pytest tests
python validate_rtt.py
python run_campaign.py 4
python analyse.py && python figures.py && python pictorials.py
```

Code: MIT licence. Data and results: CC BY 4.0.
