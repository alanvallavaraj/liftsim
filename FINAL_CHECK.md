# Final pre-submission corrections and checks

## Changes made
1. Abstract shortened from 277 to 245 words; all numbers unchanged and re-checked against
   results/aggregated_effects.csv.
2. Section 7.2: "cost confined to saturated periods" replaced by "costs concentrated in
   heavily loaded periods, generally small below the reference demand". Related wording
   ("no effect", "ineffective") changed to "no measurable effect" in Sections 1, 6.3, 7.1.
3. Han et al. (2024): related-work paragraph and Table 1 row rewritten from the article's
   published abstract (wheelchair users recognised by image analytics; priority weights by
   level of need; lower average waiting time for people with special needs reported). The
   full text was not available, so no claim is made about their controller type or data.
4. Plain-language summary and glossary moved from Appendix B to a one-page supplementary
   file (paper/supplementary.tex, .pdf). Appendix A is now the only appendix.
5. Table 5: column spacing reduced to remove a 2.5 pt overfull line.

## Checks performed
- LaTeX: compiled with latexmk; no undefined references or citations, no overfull boxes,
  no LaTeX warnings. 28 pages; every page inspected in the rendered PDF.
- Tests: `python -m pytest tests` -> 15 passed.
- Tables: regenerated with make_tables.py and compared byte-for-byte with paper/tables.
- Numbers in abstract and conclusions compared with result files (1.8 [1.3, 2.4];
  -9.3 [-10.7, -8.0]; 3.3 max cell; 30-43%; 0.6-4.1; 29.9 [26.6, 33.3]; 659 of 660).
- Run counts in the archives: 31,680 main; 8,730 supplementary. No experiment re-run.
- Results files post-date the FCFS boarding-order correction (PROTOCOL.md, Amendment 1).

## Not verified
- The journal's abstract word limit and review model (author guide not retrievable).
- Full text of Han et al. (2024), EN 81-70, ISO 8100-32, CIBSE Guide D.
- DOI of Kleinrock (1965): omitted because it could not be confirmed.
- The generative-AI declaration: the author must confirm the role of each tool.
