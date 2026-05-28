# Project Tasks

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

## In Progress

- Integrating full-text parsing outputs with the methodology scoring workflow
- Connecting acquired full-text artifacts to parsing and methodology scoring

## Planned

- Connect methodology score records to persistent storage/output tables
- Extend published-article full-text resolution beyond DOI landing pages for publisher-specific PDF/XML/HTML sources
- Implement end-to-end parsing and format metadata capture per access hierarchy (PDF/HTML/supplements)
- Generate descriptive summaries from fixed V1-V10 score records (PRES and indicator-level change distributions)
- Run preregistered descriptive analyses and heterogeneity summaries (context, journal practices)
- Conduct reliability checks (double-coding, adjudication, IRR reporting)
- Prepare Study 1 data-quality reporting and exclusion audit logs
- Plan and preregister deferred analyses (funding, career stage, institutional context) for future studies
