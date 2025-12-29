# Project Tasks

## Completed
- Defined pipeline scope, config, and data model for preprints and comparisons
- Implemented extract/load layer for bioRxiv/medRxiv metadata with DuckDB/PostgreSQL targets
- Implemented transform layer to compute version-to-version diff features
- Added CLI entry points, configs, and basic docs
- Created the project description file

## In Progress
- TBD

## Planned
- Add arXiv extraction and unify schema across sources
- Build DOI to published-article linkage (Crossref/OpenAlex) and persist mappings
- Ingest published full text and metadata (journal, publisher, acceptance dates)
- Add PDF/structured-text diffing between preprint and published versions
- Define discipline taxonomy and map sources to Math/Stats/CS/Physics/Chemistry/Biology/Medicine
- Add author/institution disambiguation and region mapping (US/EU/Asia)
- Collect funding signals (grants acknowledged, funder registry IDs) to infer soft vs hard funding
- Add career-stage features (author rank/years since PhD via ORCID/OpenAlex)
- Build analytical datasets for regression and causal analysis
- Implement evaluation metrics for “rigor vs suppression” (e.g., methods expansion vs novelty loss)
- Add validation checks, data quality reports, and sampling for manual review
