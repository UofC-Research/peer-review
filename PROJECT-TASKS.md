# Project Tasks

## Storyboard

| Panel | Status   | Story beat                               | Implemented                                                                                                                                                                                                                                                    | Left to do                                                                                                                |
|-------|----------|------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| 1     | Complete | Scope and study frame                    | Defined the Study 1 pipeline scope, project description, preregistration constraints, variables V1-V10, scoring rules, eligibility, and terminology for preprint/published manuscript pairing.                                                                 | Keep future analyses separated from the preregistered Study 1 scope.                                                      |
| 2     | Complete | Data acquisition foundation              | Implemented metadata extract/load for bioRxiv/medRxiv, deterministic acquisition requests, initial preprint version selection, published DOI carry-forward, and matched full-text download workflows, including eLife and PLOS publisher full-text candidates. | Add further publisher DOI templates as new matched-pair sources require them.                                             |
| 3     | Complete | Manuscript transformation and comparison | Built transform logic for version-to-version diff features and connected acquired full-text artifacts to parser strategies and methodology scoring.                                                                                                            | Implement complete parsing and format metadata capture across the access hierarchy, including PDF, HTML, and supplements. |
| 4     | Complete | Methodology scoring                      | Implemented V1-V10 scoring orchestration for matched manuscript pairs, raw statistical rigour computation, indicator deltas, PRES computation, evidence-row exports, and document-completeness flags.                                                          | Continue reliability checks through double-coding, adjudication, and IRR reporting.                                       |
| 5     | Complete | Persistence, CLI, and documentation      | Added CLI entry points, configs, DuckDB/PostgreSQL targets, persistent score output tables, NumPy-style Python docs, roxygen R docs, and basic project documentation.                                                                                          | Maintain documentation as the analysis/reporting workflow stabilizes.                                                     |
| 6     | Complete | R analysis layer                         | Implemented the TDD-covered R analysis layer and command-line wrapper for fixed pair-score descriptive PRES, indicator-delta, and raw-score summaries.                                                                                                         | Run preregistered descriptive analyses and heterogeneity summaries for context and journal practices.                     |
| 7     | Planned  | Reporting and audit package              | Current outputs support evidence rows, scoring records, and summary CSV generation.                                                                                                                                                                            | Generate manuscript-quality reporting artifacts, data-quality reporting, and exclusion audit logs.                        |
| 8     | Planned  | Deferred study extensions                | Deferred analysis topics are identified outside the current Study 1 implementation.                                                                                                                                                                            | Plan and preregister future analyses for funding, career stage, and institutional context.                                |

## TDD Module Implementation Audit

Audit date: 2026-05-29

Verification performed:

- `conda run -n peer_review_env python -m pytest` -> 85 passed, 3 live tests skipped, with one cache-permission warning
  for `.pytest_cache`
- `conda run -n peer_review_env python -m pytest --cov=peer_elt --cov-report=term-missing -q` -> 85 passed, 3 skipped,
  88% total
  Python coverage with branch coverage enabled
- `conda run -n peer_review_env Rscript tests/test_analysis_layer.R` -> passed with exit code 0
- `python -m compileall -q src tests` -> passed
- Placeholder scan across `src`, `tests`, and `scripts` found no TODO/FIXME markers. `NotImplementedError` appears only
  in abstract interfaces; one `pass` is defensive exception handling in metadata normalization.

### Python Modules

| Module                           | TDD status                                                        | Implementation status                                                                                  | Remaining work                                                                              |
|----------------------------------|-------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| `peer_elt.__init__`              | Package export marker                                             | Complete                                                                                               | None                                                                                        |
| `peer_elt.cli`                   | Covered by CLI tests                                              | Complete                                                                                               | None                                                                                        |
| `peer_elt.config`                | Covered by config and pipeline tests                              | Complete                                                                                               | None                                                                                        |
| `peer_elt.factories`             | Covered by factory tests                                          | Complete                                                                                               | None                                                                                        |
| `peer_elt.interfaces`            | Abstract contract covered through concrete test doubles           | Complete as interface-only module                                                                      | None                                                                                        |
| `peer_elt.pipeline`              | Covered by pipeline orchestration tests                           | Complete                                                                                               | None                                                                                        |
| `peer_elt.acquire.__init__`      | Package export marker                                             | Complete                                                                                               | None                                                                                        |
| `peer_elt.acquire.corpus`        | Covered by corpus acquisition and acquired-artifact scoring tests | Complete for current Study 1 acquisition workflow, including eLife/PLOS published full-text candidates | Add further publisher DOI templates as needed                                               |
| `peer_elt.acquire.full_text`     | Covered by full-text acquisition tests                            | Complete for configured PDF/XML/HTML fallback requests                                                 | None                                                                                        |
| `peer_elt.acquire.http`          | Covered by retry tests                                            | Complete                                                                                               | None                                                                                        |
| `peer_elt.acquire.tdm`           | Covered by TDM acquisition tests                                  | Complete for injectable bioRxiv/medRxiv TDM archive sync and published-link metadata download helpers  | Wire into production acquisition jobs if bulk TDM retrieval is selected                     |
| `peer_elt.extract.__init__`      | Package export marker                                             | Complete                                                                                               | None                                                                                        |
| `peer_elt.extract.biorxiv`       | Covered by extractor tests                                        | Complete                                                                                               | None                                                                                        |
| `peer_elt.extract.medrxiv`       | Covered through extractor tests and bioRxiv-compatible wrapper    | Complete                                                                                               | None                                                                                        |
| `peer_elt.extract.registry`      | Covered by extractor and factory tests                            | Complete                                                                                               | None                                                                                        |
| `peer_elt.load.__init__`         | Package export marker                                             | Complete                                                                                               | None                                                                                        |
| `peer_elt.load.duckdb`           | Covered by transformer/storage tests                              | Complete                                                                                               | None                                                                                        |
| `peer_elt.load.postgres`         | Covered by PostgreSQL storage tests using mocked SQL paths        | Complete                                                                                               | Validate against a live PostgreSQL service before production use                            |
| `peer_elt.parse.__init__`        | Package export marker                                             | Complete                                                                                               | None                                                                                        |
| `peer_elt.parse.interfaces`      | Protocol contract used by parser pipeline tests                   | Complete as interface-only module                                                                      | None                                                                                        |
| `peer_elt.parse.models`          | Covered by parser pipeline tests                                  | Complete                                                                                               | None                                                                                        |
| `peer_elt.parse.pipeline`        | Covered by PDF and article parsing pipeline tests                 | Complete for injected parser/scraper services                                                          | Integrate real parser services when selected for production                                 |
| `peer_elt.parse.processors`      | Covered by parser and scoring workflow tests                      | Complete                                                                                               | None                                                                                        |
| `peer_elt.parse.xml_reader`      | Covered by XML reader and acquired-artifact tests                 | Complete                                                                                               | None                                                                                        |
| `peer_elt.transform.__init__`    | Package export marker                                             | Complete                                                                                               | None                                                                                        |
| `peer_elt.transform.adapters`    | Covered by methodology integration tests                          | Complete                                                                                               | None                                                                                        |
| `peer_elt.transform.artifacts`   | Covered by acquired-artifact scoring tests                        | Complete for parsed PDF/XML/HTML artifact strategies                                                   | Expand format metadata capture across the full access hierarchy                             |
| `peer_elt.transform.diff`        | Covered by transformer/storage and factory tests                  | Complete                                                                                               | None                                                                                        |
| `peer_elt.transform.methodology` | Covered by methodology and integration tests                      | Complete                                                                                               | Continue double-coding, adjudication, and IRR reliability checks                            |
| `peer_elt.transform.outputs`     | Covered by methodology integration tests                          | Complete                                                                                               | None                                                                                        |
| `peer_elt.transform.scoring`     | Covered by scoring and methodology tests                          | Complete for rule/model hybrid scoring framework                                                       | Keep scoring rules frozen for preregistered Study 1; defer new indicators to future studies |

### R Modules

| Module                           | TDD status                                                       | Implementation status                               | Remaining work                                                            |
|----------------------------------|------------------------------------------------------------------|-----------------------------------------------------|---------------------------------------------------------------------------|
| `src/analysis/study1_analysis.R` | Covered by six `testthat` cases in `tests/test_analysis_layer.R` | Complete for fixed pair-score descriptive summaries | Generate manuscript-quality reporting artifacts from summary tables       |
| `scripts/run_study1_analysis.R`  | Core behavior covered through `run_study1_analysis()` tests      | Implemented command-line wrapper                    | Add a direct wrapper smoke test for argument handling and output messages |
| `src/analysis/init_r.R`          | Not a product module; environment bootstrap helper only          | Complete as setup helper                            | Keep in sync with `environment.yml` if R dependencies change              |
| `tests/test_analysis_layer.R`    | R test module                                                    | Complete                                            | Extend when reporting artifacts are implemented                           |

## Completed
- Defined pipeline scope, config, and data model for preprints and comparisons
- Implemented extract/load layer for bioRxiv/medRxiv metadata with DuckDB/PostgreSQL targets
- Implemented transform layer to compute version-to-version diff features
- Added CLI entry points, configs, and basic docs
- Created the project description file
- Documented tool split: Python for ELT, R for analysis
- Locked preregistration planning document for Study 1 (variables V1-V10, scoring rules, eligibility, and analysis constraints)
- Defined document access rules, preprint version selection, and workflow for within-manuscript comparisons
- Authored public summary, reader map, and project description to align with preregistered scope
- Documented data model and terminology for preprint/published manuscript pairing
- Implemented methodology-level V1-V10 scoring orchestration for matched manuscript pairs
- Added explicit raw statistical rigour, indicator delta, and PRES computation in Python
- Added audit-ready evidence-row exports and document-completeness review flags for zero scores
- Added TDD coverage for the methodology workflow and retained full-suite passing status
- Implemented TDD-covered framework to query preprint sources, select initial preprint versions, carry published DOIs
  forward, and download matched full text
- Added deterministic acquisition-request construction for initial preprint and published DOI resolver workflows
- Implemented TDD-covered R analysis layer for descriptive PRES, indicator-delta, and raw-score summaries
- Added R command-line wrapper for generating Study 1 summary CSV files from fixed pair-score records
- Refactored factory, adapter, workflow, and repository boundaries using design-pattern-oriented components
- Integrated parsed full-text section adapters with the methodology scoring workflow
- Connected Python methodology score records to persistent output tables for the R analysis runner
- Updated Python documentation to use NumPy-style docstrings and R documentation to use roxygen comments
- Connected acquired full-text artifacts to parsing and methodology scoring through artifact parser strategies
- Completed TDD module implementation audit for Python and R modules
- Enabled pytest-cov verification and recorded 88% branch-aware total Python coverage
- Extended published-article full-text resolution for eLife and PLOS DOI patterns using TDD
- Added config-driven opt-in live integration tests for preprint APIs, published full-text retrieval, and matched-pair
  acquisition
- Added TDD-covered optional TDM acquisition helpers for bioRxiv/medRxiv requester-pays preprint archive sync and
  bioRxiv API published-link metadata download

## In Progress

- None currently

## Planned

- Add direct smoke test coverage for the R command-line wrapper
- Run live integration tests periodically with a maintained local live-test config
- Implement end-to-end parsing and format metadata capture per access hierarchy (PDF/HTML/supplements)
- Generate manuscript-quality reporting artifacts from fixed R summary tables
- Run preregistered descriptive analyses and heterogeneity summaries (context, journal practices)
- Conduct reliability checks (double-coding, adjudication, IRR reporting)
- Prepare Study 1 data-quality reporting and exclusion audit logs
- Plan and preregister deferred analyses (funding, career stage, institutional context) for future studies
