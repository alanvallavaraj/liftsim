# Pre-submission audit: what was checked, changed and left open

## Corrections that changed results
1. FCFS boarding under destination control used allocation order instead of arrival order
   (differs only for passengers re-allocated after being left behind). Corrected; 2,640
   main-campaign runs and 1,170 supplementary runs re-executed on the same streams.
   Effect: destination-control results at x >= 1.15 changed (e.g. DCS-P0 at x = 1.3:
   others +46.8 s, priority -67.3 s, all passengers +29.9 s; previously +59.5, -55.3).
   Results at x <= 1 and all landing-call results are unchanged.
2. (Earlier, before the version-2 campaign) car direction rule at the reversal floor.

## Additions
- Aggregated effects with paired-bootstrap intervals (analyse_ci.py).
- Supplementary experiments S1 (distribution, overload, adaptive variant DCS-PA) and
  S2 (priority share; space vs time), 8,730 runs (SUPPLEMENT.md).
- Nine new unit tests (tests/test_model.py); 15 tests in total, all passing.
- Algorithm 1 and Eq. (3)-(4): DCS-P specified from the source code.

## Checks performed
- pytest: 15 passed.
- Round-trip time: -0.2% to +1.9% against the classical formula (6 configurations).
- 56 configurations: campaign controllers give identical outcomes before and after the
  supplementary additions (before the FCFS correction).
- Run counts: 66 x 20 x (5 x 4 + 2 x 2) = 31,680 main; 8,730 supplementary.
- Every number in the manuscript text was taken from results/*.csv after the final rerun.
- 17 of 24 references checked against Crossref records or publisher pages in this audit;
  the others (books, standards, Elevator World article, Kleinrock 1965) were checked by
  web search earlier. The DOI of Kleinrock (1965) could not be confirmed and was removed.
- Repository https://github.com/alanvallavaraj/liftsim is public.

## Not done / open
- No empirical validation (no measured building data, no independent benchmark with
  reference results was available).
- The journal's abstract word limit and review model could not be confirmed.
- EN 81-70, ISO 8100-32, CIBSE Guide D and the Elevator Traffic Handbook were not read in
  full; they are cited only for their scope.
- Han et al. (2024) is characterised from its title and bibliographic record only.
- The AI declaration must be confirmed by the author (actual role of each tool).
- No archived release with a DOI (e.g. Zenodo) exists yet.
