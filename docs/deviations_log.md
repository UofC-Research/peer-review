**Entry Title:** Pre‑lock framing refinement following literature review  
**Date:** [prior to Jan 28, 2026]  
**Status:** Pre‑lock clarification (no data accessed)

**Note:**  
During early project ideation **prior to OSF preregistration**, the study framing was less formalized and exploratory in nature. Following an initial literature review and clarification of the study’s scope, the framing was refined to emphasize a **non-causal, preregistered, within-manuscript comparison of statistical rigor (V1–V10)**.

This refinement occurred **prior to the planning lock** and **before any data access, variable operationalization, scoring, or analysis** described in the peer-review planning document. The current preregistration document constitutes the finalized, binding specification for Study 1. **No variables, scoring rules, eligibility criteria, or analytic constraints were modified after the planning lock.**

---

## Post-Lock Deviation Assessment

**Assessment date:** 2026-05-29  
**Reference document:** `docs/peer_review_planning_document.md`  
**Registered scope checked:** Study 1 preregistered variables V1-V10, scoring
rules, matched preprint-published unit of analysis, document access rules,
version selection rules, composite scores, descriptive analysis constraints,
and non-causal interpretation framework.

### Summary Determination

No substantive deviation from the preregistered Study 1 design was identified
in the current local project state.

The following core preregistered commitments remain unchanged:

- The unit of analysis remains the matched preprint-published manuscript pair.
- The baseline comparator remains the first publicly posted preprint version.
- The evaluated outcomes remain V1-V10 statistical rigour indicators.
- V1-V10 scoring rules, ordinal thresholds, and evidence requirements remain
  unchanged.
- Raw Statistical Rigour Score and PRES definitions remain unchanged.
- Analyses remain descriptive and non-causal.
- Deferred analyses involving funding, career stage, institutional context, and
  related contextual variables remain deferred.

The items below are post-lock implementation clarifications or engineering
changes. They do not alter the registered variables, scoring criteria,
eligibility criteria, or analysis plan, but they are logged for auditability.

---

### Entry: Publisher-specific full-text resolution added

**Date:** 2026-05-29  
**Status:** Post-lock implementation clarification  
**Data accessed:** No study outcome data accessed  
**Analyses conducted:** No

**Description:**  
The acquisition code was extended to resolve published-article full-text URL
candidates for known publisher DOI families. Specifically, eLife and PLOS DOI
patterns now produce publisher-specific PDF, XML, and HTML candidate URLs before
falling back to the generic DOI resolver.

**Relationship to preregistration:**  
This is consistent with Section 11.1 of the preregistration, which states that
manuscripts are evaluated using the most complete and stable full-text
representation available and lists publisher-provided PDF, HTML, and XML as
acceptable representations.

**Impact on registered design:**  
None. This change affects document retrieval mechanics only. It does not alter
which manuscripts are eligible, which preprint version is selected, which
published version is paired, how V1-V10 are scored, or how PRES is computed.

**Risk controlled:**  
The change reduces the chance that a published article is treated as
HTML-only or inaccessible merely because the DOI resolver landing page does not
directly expose machine-readable full text.

**Tests added:**  
TDD tests were added for eLife and PLOS DOI patterns in
`tests/test_corpus_acquisition.py`.

---

### Entry: Automated test coverage audit added to planning document

**Date:** 2026-05-29  
**Status:** Post-lock transparency documentation  
**Data accessed:** No study outcome data accessed  
**Analyses conducted:** No

**Description:**  
A test coverage audit section was added to the planning document to document
what each Python and R test verifies and which tests remain potentially
missing.

**Relationship to preregistration:**  
This is a transparency and software-quality record. It does not modify the
registered study design, codebook, eligibility criteria, document access rules,
or analytic plan.

**Impact on registered design:**  
None.

**Current executable status recorded:**  
Python tests pass with 80 tests; branch-aware Python coverage is 88%; the R
analysis-layer test file passes.

---

### Entry: Test and coverage tooling made reproducible

**Date:** 2026-05-29  
**Status:** Post-lock engineering maintenance  
**Data accessed:** No study outcome data accessed  
**Analyses conducted:** No

**Description:**  
`pytest-cov` coverage configuration was added to project metadata so coverage
commands are repeatable. Generated coverage artifacts were identified as
non-source test outputs and excluded from Git tracking.

**Relationship to preregistration:**  
This is engineering infrastructure for reproducibility and does not alter any
registered scientific decision.

**Impact on registered design:**  
None.

---

### Entry: R descriptive analysis implementation added

**Date:** 2026-05-29  
**Status:** Post-lock implementation of preregistered descriptive summaries  
**Data accessed:** No study outcome data accessed  
**Analyses conducted:** No study analysis conducted

**Description:**  
The R analysis layer was implemented to read fixed methodology pair-score
records and generate descriptive PRES, indicator-delta, and raw-score summary
tables.

**Relationship to preregistration:**  
This implements the preregistered descriptive analysis approach. It does not
introduce inferential testing, causal estimation, new outcome variables, or
post-hoc score weighting.

**Impact on registered design:**  
None, provided the R layer remains restricted to fixed pair-score records and
descriptive summaries as documented.

---

### Entry: Pytest live-data and dummy-data workflows documented

**Date:** 2026-05-30  
**Status:** Post-lock transparency documentation  
**Data accessed:** No study outcome data accessed  
**Analyses conducted:** No

**Description:**  
Testing documentation was clarified to distinguish deterministic dummy-data
pytest runs from opt-in live-data integration tests. The README now summarizes
the default offline workflow, live-test commands, and the local live-config
workflow. A dedicated `docs/testing.md` file was added, the planning document's
test coverage audit was cross-referenced to that workflow, and
`configs/live_tests.example.yml` comments were expanded to explain how to copy
and modify `configs/live_tests.local.yml`.

**Relationship to preregistration:**  
This is a software reproducibility and auditability clarification. It documents
how automated tests are run and how live integration checks are enabled. It does
not modify the preregistered study design, variables, scoring rules, document
access hierarchy, eligibility criteria, version-selection rules, or analytic
plan.

**Impact on registered design:**  
None. Dummy-data and live-data pytest modes validate implementation behavior
only. The live-test configuration controls external integration checks; it does
not define the study corpus or alter Study 1 measurement decisions.

**Files updated:**  
`README.md`, `docs/testing.md`, `docs/peer_review_planning_document.md`, and
`configs/live_tests.example.yml`.
