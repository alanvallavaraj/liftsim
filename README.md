# liftsim

Seconds-based lift group simulator (`liftsim`) and the full study behind the paper
"Priority boarding in lift group control: a simulation study of its cost to other
passengers and of a priority-aware destination control rule".

## Contents
- `liftsim/` simulator: `model.py` (buildings, kinematics, round-trip formula),
  `traffic.py` (passenger streams), `sim.py` (cars, doors, controllers NC, ETA, ETD,
  ETDQ, DCS, DCSP1, DCSP0, DCSPA, boarding rules), `metrics.py` (waiting-time measures)
- `buildings.py` the three buildings
- `PROTOCOL.md` test plan of the main campaign (with Amendment 1); `SUPPLEMENT.md`
  supplementary experiments; `results/frozen_hashes.txt`
- `tests/` 15 automated tests: `python -m pytest tests`
- `validate_rtt.py` check against the classical round-trip time
- `run_campaign.py [workers]` main campaign, 31,680 runs -> `results/runs.jsonl`
  (resumable; about 3.5 CPU hours); archived as `results/runs.jsonl.gz`
- `run_supplement.py [workers]` supplementary experiments, 8,730 runs ->
  `results/supplement.jsonl` (archived as `.gz`)
- `analyse.py`, `analyse_ci.py`, `analyse_supplement.py` -> `results/*.csv`
- `figures.py`, `pictorials.py` -> `figures/*.pdf`; `make_tables.py` -> `paper/tables/`
- `results_v1/` superseded first campaign, kept as a record (see PROTOCOL.md)
- `paper/` LaTeX source of the manuscript

## Quick start
```
pip install numpy pandas matplotlib pytest
python -m pytest tests
python validate_rtt.py
python run_campaign.py 4          # or: gunzip -k results/*.gz to reuse archived runs
python run_supplement.py 4
python analyse.py && python analyse_ci.py && python analyse_supplement.py
python figures.py && python pictorials.py && python make_tables.py
cd paper && latexmk -pdf manuscript.tex
```

Code: MIT licence. Data and results: CC BY 4.0.
