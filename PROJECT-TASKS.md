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

## In Progress
None (planning locked; no data accessed or analyses performed)

## Planned
- Build corpus assembly for matched preprint-published manuscript pairs (server metadata, DOI linkage, eligibility filters)
- Implement full-text acquisition and format metadata capture per access hierarchy (PDF/HTML/supplements)
- Implement V1-V10 scoring workflow with evidence logging and audit trail
- Compute within-manuscript deltas and descriptive summaries (PRES and indicator-level changes)
- Run preregistered descriptive analyses and heterogeneity summaries (context, journal practices)
- Conduct reliability checks (double-coding, adjudication, IRR reporting)
- Prepare Study 1 data-quality reporting and exclusion audit logs
- Plan and preregister deferred analyses (funding, career stage, institutional context) for future studies
