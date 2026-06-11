# Peer Review Project

ELT and analysis support for Study 1 of the peer-review manuscript-change
project. The current pipeline collects bioRxiv and medRxiv preprint metadata,
stores raw records, derives first-version versus latest-version change features,
and writes analysis-ready outputs for downstream review.

The preregistered study scope, measurement rules, and interpretation constraints
live in `docs/peer_review_planning_document.md`. The code in this repository is
the implementation layer for that workflow.

## Project Flow

```mermaid
flowchart TD
    A[environment.yml] --> B[Conda environment: peer_review_env]
    C[configs/local.yml or configs/prod.yml] --> D[peer_elt CLI]
    D --> E[Extract metadata from bioRxiv and medRxiv]
    E --> F[Load raw_preprints into DuckDB or PostgreSQL]
    F --> G[Select initial preprint version and published DOI]
    G --> H[Download initial preprint and published article full text]
    H --> I[Transform first vs latest metadata versions]
    I --> J[Write diff_features to storage and files]
    J --> K[Score V1-V10 for matched manuscript pairs]
    K --> L[Compute indicator deltas and PRES]
    L --> M[Downstream R analysis and documentation]
```

At runtime the pipeline does four things:

1. Loads a YAML config and validates source, storage, output, transform, and
   retry settings.
2. Extracts preprint metadata from configured preprint servers.
3. Appends raw rows to `raw_preprints` in the configured storage backend.
4. Builds matched manuscript pairs by selecting the initial preprint version and
   carrying forward the corresponding published DOI.
5. Builds deterministic full-text acquisition requests and downloads the
   initial preprint and published article using PDF/XML/HTML fallback.
6. Builds `diff_features` and writes Parquet output, optional CSV output, and a
   storage table.
7. Parses acquired local full-text artifacts through format-specific parser
   strategies in `peer_elt.transform.artifacts`.
8. Normalizes parsed full-text outputs into canonical `methods`, `results`, and
   `statements` sections through `peer_elt.transform.adapters`.
9. Scores matched preprint-published pairs through
   `peer_elt.transform.methodology.MethodologyScoringWorkflow`.
10. Writes fixed `methodology_pair_scores` and `methodology_evidence_rows`
   outputs through `peer_elt.transform.outputs` for downstream R analysis.

## Environment Setup

The project environment is defined in `environment.yml`. It creates the Conda
environment `peer_review_env` and includes the Python, R, Jupyter, ELT, storage,
and test dependencies used by the project.

Create the environment:

```bash
conda env create -f environment.yml
conda activate peer_review_env
```

Update an existing environment after `environment.yml` changes:

```bash
conda env update -f environment.yml --prune
conda activate peer_review_env
```

Install the local package in editable mode so the `peer-elt` command and
`peer_elt` imports resolve from `src/`:

```bash
python -m pip install -e .[dev]
```

The package declares `requires-python = ">=3.13"` in `pyproject.toml`, so the
recommended setup is a Python 3.13 virtual environment before installation.

If you must install in an older interpreter temporarily, use
`--ignore-requires-python` only as a workaround.

Local secrets and machine-specific environment variables belong in `.env`.
Start from the committed template and keep the real file private:

```bash
cp configs/.env.example .env
```

## Development Setup (Python 3.13)

For a minimal, reproducible local setup:

```bash
python3.13 -m venv .venv
. .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

If `python3.13` is not available on your PATH, create the same environment from an
existing 3.13 interpreter (`py -3.13` on Windows) and then run the `pip` command in
that environment.

Use `.env` for values such as `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, optional `AWS_SESSION_TOKEN`, `AWS_DEFAULT_REGION`,
and `PEER_REVIEW_LIVE_CONFIG`. Use YAML files in `configs/` for structured
pipeline and live-test settings such as sources, date windows, storage, output
paths, TDM buckets, and retry settings.

## Run the Pipeline

Local development uses DuckDB and writes CSV output as well as Parquet:

```bash
peer-elt --config configs/local.yml run
```

Equivalent module form:

```bash
python -m peer_elt.cli --config configs/local.yml run
```

Production is configured for PostgreSQL and Slurm:

```bash
export POSTGRES_URL="postgresql+psycopg2://user:password@host:5432/database"
sbatch scripts/run_pipeline.slurm configs/prod.yml
```

The CLI also supports running stages separately:

```bash
peer-elt --config configs/local.yml extract
peer-elt --config configs/local.yml transform
```

Successful commands print JSON summaries to stdout. Usage and runtime errors are
reported as JSON on stderr.

## Configuration

Config files live in `configs/`.

- `configs/local.yml`: bioRxiv and medRxiv metadata for 2023, DuckDB storage at
  `data/processed/peer_review.duckdb`, CSV output enabled, PDF diff disabled,
  and optional AWS/TDM settings disabled by default.
- `configs/prod.yml`: bioRxiv and medRxiv metadata for 2020-2025, PostgreSQL
  storage from `${POSTGRES_URL}`, CSV output disabled, PDF diff enabled, and
  optional AWS/TDM settings disabled by default.

Important config sections:

- `sources`: preprint servers and inclusive date windows.
- `storage`: backend settings for `duckdb` or `postgres`.
- `output`: output directory and CSV toggle.
- `transform`: optional PDF-diff settings.
- `retry`: retry and exponential backoff settings for external calls.
- `tdm_repository`: optional bioRxiv/medRxiv requester-pays S3 acquisition
  settings for TDM preprint archives. Keep `enabled` and
  `live_aws_tests_enabled` false unless explicitly running local TDM acquisition
  or opt-in live AWS probes.

## Outputs

The main tables are documented in `docs/data_model.md`.

- `raw_preprints`: raw metadata rows from the preprint APIs.
- `diff_features`: per-DOI comparison features between the first observed
  preprint version and the latest observed version.
- `methodology_pair_scores`: table-ready V1-V10 preprint scores, published
  scores, deltas, raw version scores, PRES, document formats, and review flags.
- `methodology_evidence_rows`: audit-ready evidence snippets supporting
  indicator scores.

`diff_features` is always written as Parquet. CSV is written when
`output.write_csv` is `true`.

## Corpus and Full-Text Acquisition

The acquisition framework is implemented in `peer_elt.acquire.corpus` and
`peer_elt.acquire.full_text`.

- `query_preprint_servers_for_pairs(...)` queries configured preprint sources
  through the extractor interface and returns matched manuscript pairs.
- `build_matched_manuscript_pairs(...)` selects the initial preprint version
  for each preprint DOI and requires a corresponding published DOI.
- `build_acquisition_requests(...)` creates URL candidates for the initial
  preprint version plus publisher-specific published article candidates for
  supported DOI families, with DOI resolver fallback.
- `acquire_matched_pair_full_text(...)` downloads both sides using the existing
  PDF/XML/HTML fallback downloader and injected HTTP client.

For bulk preprint full-text acquisition, local or production runs may also use
the official bioRxiv/medRxiv Text and Data Mining (TDM) repositories. This is
documented as an optional disabled `tdm_repository` block in
`configs/local.yml`, `configs/prod.yml`, and `configs/live_tests.example.yml`.
The TDM repositories provide requester-pays S3 access to bioRxiv/medRxiv
preprint full-text packages. The helper module `peer_elt.acquire.tdm` parses
that config and can automate requester-pays TDM archive sync, bioRxiv API
published-link metadata download, and published-article full-text retrieval.
The built-in AWS CLI TDM client reads repo-root `.env` credentials when present
and recognizes uppercase AWS CLI variable names as well as lowercase aliases
such as `aws_access_key_id` and `aws_secret_access_key`.
When TDM is selected, the preferred processing order is XML, then PDF, then HTML
for both preprint and published article files. Published-article full text still
comes from publisher, DOI-resolver, PMC, or other permitted article-level
sources.

Default tests use fake HTTP/AWS clients, so acquisition behavior is covered
without live network access. Opt-in live tests can also probe AWS requester-pays
TDM bucket access without syncing or downloading archives.

## Analysis Layer

Python owns the ELT pipeline. R is reserved for downstream analysis and reporting
work tied to the preregistered Study 1 analysis plan.

The Python scoring workflow separates three responsibilities:

- `peer_elt.transform.artifacts` dispatches acquired local full-text artifacts
  (`pdf`, `xml`, `html`) to parser strategies and scores parsed pairs through a
  facade workflow.
- `peer_elt.transform.adapters` converts parsed PDF/XML/article outputs or
  section mappings into canonical methodology sections.
- `peer_elt.transform.methodology` applies the fixed V1-V10 scoring workflow and
  computes raw scores, deltas, PRES, and evidence rows.
- `peer_elt.transform.outputs` persists pair-score and evidence outputs under
  stable table/file names.

The implemented R layer consumes `methodology_pair_scores` records after V1-V10
scores are fixed. R source files use roxygen-style documentation and produce
descriptive, non-inferential Study 1 summaries:

- `pres_summary.csv`
- `indicator_delta_summary.csv`
- `raw_score_summary.csv`

Run it from a pair-score CSV:

```bash
Rscript scripts/run_study1_analysis.R data/processed/methodology_pair_scores.csv data/analysis
```

The starter R setup script is:

```bash
Rscript src/analysis/init_r.R
```

## Tests

Run the default test suite from the repository root:

```bash
pytest
```

This is the dummy-data/offline mode. The regular suite uses fixtures, temporary
files, and fake HTTP clients for acquisition tests, so it does not require
network access or real DOI retrieval. The opt-in tests marked `live` are
collected but skipped unless a live config is supplied.

To run only the deterministic dummy-data tests and exclude live tests entirely:

```bash
pytest -m "not live"
```

Pytest settings live in `pyproject.toml`. In particular,
`pythonpath = ["src"]` lets tests import the package without extra path setup,
and the `live` marker identifies tests that may call external services.

Run the R analysis tests:

```bash
Rscript tests/test_analysis_layer.R
```

Live integration tests are opt-in and are driven by a YAML config. To run them
against real bioRxiv/medRxiv and publisher endpoints:

```bash
cp configs/live_tests.example.yml configs/live_tests.local.yml
# edit configs/live_tests.local.yml:
#   - set enabled: true
#   - replace placeholder DOI/date-window cases with stable live examples
#   - optionally set tdm_repository.enabled/live_aws_tests_enabled: true
#     to probe AWS requester-pays TDM bucket access without archive downloads
pytest -m live --live-config configs/live_tests.local.yml
```

To run the full Python suite with live tests included, omit the marker filter:

```bash
pytest --live-config configs/live_tests.local.yml
```

The same config can be supplied with `PEER_REVIEW_LIVE_CONFIG`. Keep local live
configs and secrets out of version control; `configs/live_tests.local.yml` and
`.env` are ignored. More detail, including which files to modify for each mode
and what each test covers, is in `docs/testing.md`.

## Key Files

- `environment.yml`: Conda environment definition.
- `pyproject.toml`: package metadata, CLI entry point, and test settings.
- `src/peer_elt/cli.py`: command-line entry point.
- `src/peer_elt/pipeline.py`: extract, load, transform, and write orchestration.
- `src/peer_elt/config.py`: YAML config schema and loader.
- `src/peer_elt/factories.py`: extractor, storage, and transformer selection.
- `src/peer_elt/acquire/corpus.py`: query-to-pair selection and matched
  preprint/published full-text acquisition.
- `src/peer_elt/acquire/full_text.py`: PDF/XML/HTML fallback downloader.
- `src/peer_elt/acquire/tdm.py`: optional bioRxiv/medRxiv TDM archive and
  published-link metadata acquisition helpers.
- `src/peer_elt/transform/artifacts.py`: parser-strategy registry and facade
  for connecting acquired artifacts to methodology scoring.
- `src/peer_elt/transform/adapters.py`: adapter strategies that canonicalize
  parsed document outputs for methodology scoring.
- `src/peer_elt/transform/methodology.py`: V1-V10 pair scoring, deltas, PRES,
  and audit exports.
- `src/peer_elt/transform/outputs.py`: repository-style persistence for
  methodology pair-score and evidence tables.
- `src/peer_elt/transform/scoring.py`: rule-based and hybrid indicator scoring.
- `src/analysis/study1_analysis.R`: R summaries for PRES, indicator deltas, and
  raw version scores.
- `scripts/run_study1_analysis.R`: command-line wrapper for the R analysis
  layer.
- `docs/peer_review_planning_document.md`: controlling preregistration document.
- `docs/data_model.md`: raw and derived table definitions.
- `docs/deviations_log.md`: post-lock deviation and implementation
  clarification audit trail.
- `docs/testing.md`: pytest dummy-data and live-data test workflows.
- `configs/live_tests.example.yml`: template and schema for opt-in live tests.
- `configs/.env.example`: template for local environment variables and AWS
  requester-pays S3 credentials.
