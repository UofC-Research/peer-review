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
Python tests passed with 80 tests at the time of this entry; branch-aware Python
coverage was 88%; the R analysis-layer test file passed. Later TDM acquisition
tests increased the Python suite to 87 passing tests without changing total
coverage.

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

---

### Entry: Optional bioRxiv/medRxiv TDM acquisition helpers added

**Date:** 2026-05-30  
**Status:** Post-lock implementation clarification  
**Data accessed:** No study outcome data accessed  
**Analyses conducted:** No

**Description:**  
An optional Text and Data Mining (TDM) acquisition path was added for
bioRxiv/medRxiv preprint full-text archives. The implementation adds
`peer_elt.acquire.tdm`, which parses a local `tdm_repository` configuration
block, delegates requester-pays S3 archive sync to an injected client or AWS CLI
wrapper, downloads linked published-article metadata from the bioRxiv API
`pubs` endpoint for bioRxiv or medRxiv, and retrieves linked published article
full text in XML, PDF, then HTML order. The example live-test config documents
the disabled local TDM option and records XML, PDF, then HTML as the preferred
processing order when TDM is selected.

**Relationship to preregistration:**  
This is an access-route clarification and software implementation detail. The
TDM path provides an alternate way to retrieve the same preprint-side full text
that is otherwise accessible through bioRxiv/medRxiv pages or URLs. It does not
modify the preregistered corpus definition, first-version selection rule,
published DOI matching rule, V1-V10 scoring criteria, document-completeness
requirements, or descriptive analysis plan.

**Impact on registered design:**  
None. TDM acquisition is optional and limited to retrieval mechanics. Published
article full text remains governed by the existing publisher, DOI-resolver, PMC,
or equivalent article-level access route.

**Tests added:**  
TDD tests were added in `tests/test_tdm_acquisition.py` for TDM config parsing,
unsupported-server rejection, requester-pays archive-sync delegation for both
bioRxiv and medRxiv, AWS CLI requester-pays command construction, published
metadata URL construction, published metadata payload persistence, and automated
TDM preprint/published acquisition orchestration.

**Files updated:**  
`src/peer_elt/acquire/tdm.py`, `tests/test_tdm_acquisition.py`,
`configs/live_tests.example.yml`, `README.md`, `docs/testing.md`,
`docs/peer_review_planning_document.md`, `docs/use_cases.md`,
`docs/methods_and_results_generation.md`, and `PROJECT-TASKS.md`.

---

### Entry: Local AWS credential wiring and test inventory documented

**Date:** 2026-05-31  
**Status:** Post-lock engineering maintenance and transparency documentation  
**Data accessed:** No study outcome data accessed  
**Analyses conducted:** No

**Description:**  
The optional AWS CLI TDM client was updated to read repo-local `.env`
credentials when present and pass recognized AWS credential variables to the
S3 sync subprocess. A committed `.env.example` file documents local environment
variables, while `.env` remains ignored by Git. Documentation was updated to
distinguish `.env` secrets/process-level switches from YAML run configuration,
and `docs/testing.md` now includes a test-by-test inventory plus known deferred
coverage areas.

**Relationship to preregistration:**  
This is a software reproducibility and credential-handling clarification. It
does not modify the preregistered corpus definition, eligibility criteria,
document hierarchy, V1-V10 scoring rules, composite-score definitions, or
descriptive analysis plan.

**Impact on registered design:**  
None. The change affects only local credential propagation for an optional
preprint full-text acquisition route and documentation of test coverage.

**Tests added:**  
TDD tests were added in `tests/test_tdm_acquisition.py` to verify that
lowercase `.env` AWS aliases are translated to AWS CLI environment variables
and that the AWS CLI TDM client passes `.env` credentials to the subprocess.

**Current executable status recorded:**  
The Python suite passed with 89 tests and 3 skipped live tests in
`peer_review_env`. The skipped tests are opt-in live integration tests that
require `--live-config` or `PEER_REVIEW_LIVE_CONFIG`.

**Files updated:**  
`.gitignore`, `.env.example`, `src/peer_elt/acquire/tdm.py`,
`tests/test_tdm_acquisition.py`, `configs/live_tests.example.yml`, `README.md`,
`docs/testing.md`, `docs/peer_review_planning_document.md`, and
`docs/deviations_log.md`.

---

### Entry: Opt-in live AWS TDM bucket probes added

**Date:** 2026-06-01  
**Status:** Post-lock engineering maintenance and transparency documentation  
**Data accessed:** No study outcome data accessed  
**Analyses conducted:** No

**Description:**  
Opt-in live pytest coverage was added for AWS requester-pays TDM bucket access.
The live test consumes `tdm_repository` only when both `enabled` and
`live_aws_tests_enabled` are true, then uses AWS CLI
`s3api list-objects-v2 --max-items 1` to probe each configured bucket without
syncing or downloading archives. The local and production configs now record
the official bioRxiv/medRxiv TDM bucket settings with live AWS tests disabled by
default.

**Relationship to preregistration:**  
This is a software integration-health check for an optional access route. It
does not modify the preregistered corpus definition, eligibility criteria,
published DOI matching rule, V1-V10 scoring rules, or descriptive analysis
plan.

**Impact on registered design:**  
None. The change validates AWS/TDM access configuration only. Full archive sync
remains a manual/local acquisition action because it can download large
requester-pays data.

**Tests added:**  
TDD tests were added in `tests/test_tdm_acquisition.py` for lightweight AWS CLI
probe command construction, non-S3 URI rejection, and local/production config
TDM bucket defaults. An opt-in live test was added in
`tests/test_live_integration.py` for real requester-pays AWS bucket access
probes.

**Files updated:**  
`src/peer_elt/acquire/tdm.py`, `tests/test_tdm_acquisition.py`,
`tests/test_live_integration.py`, `configs/prod.yml`,
`configs/local.yml`, `configs/live_tests.example.yml`, `README.md`,
`docs/testing.md`, `docs/peer_review_planning_document.md`, and
`docs/deviations_log.md`.
