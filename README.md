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
    F --> G[Transform first vs latest versions]
    G --> H[Write diff_features to storage and files]
    H --> I[Score V1-V10 for matched manuscript pairs]
    I --> J[Compute indicator deltas and PRES]
    J --> K[Downstream R analysis and documentation]
```

At runtime the pipeline does four things:

1. Loads a YAML config and validates source, storage, output, transform, and
   retry settings.
2. Extracts preprint metadata from configured preprint servers.
3. Appends raw rows to `raw_preprints` in the configured storage backend.
4. Builds `diff_features` and writes Parquet output, optional CSV output, and a
   storage table.
5. Supports the preregistered V1-V10 methodology workflow for matched
   preprint-published pairs through `peer_elt.transform.methodology`.

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
python -m pip install -e ".[dev]"
```

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
  `data/processed/peer_review.duckdb`, CSV output enabled, PDF diff disabled.
- `configs/prod.yml`: bioRxiv and medRxiv metadata for 2020-2025, PostgreSQL
  storage from `${POSTGRES_URL}`, CSV output disabled, PDF diff enabled.

Important config sections:

- `sources`: preprint servers and inclusive date windows.
- `storage`: backend settings for `duckdb` or `postgres`.
- `output`: output directory and CSV toggle.
- `transform`: optional PDF-diff settings.
- `retry`: retry and exponential backoff settings for external calls.

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

## Analysis Layer

Python owns the ELT pipeline. R is reserved for downstream analysis and reporting
work tied to the preregistered Study 1 analysis plan. The starter R setup script
is:

```bash
Rscript src/analysis/init_r.R
```

## Tests

Run the test suite from the repository root:

```bash
pytest
```

Pytest reads `pythonpath = ["src"]` from `pyproject.toml`, so tests can import
the package without extra path setup.

## Key Files

- `environment.yml`: Conda environment definition.
- `pyproject.toml`: package metadata, CLI entry point, and test settings.
- `src/peer_elt/cli.py`: command-line entry point.
- `src/peer_elt/pipeline.py`: extract, load, transform, and write orchestration.
- `src/peer_elt/config.py`: YAML config schema and loader.
- `src/peer_elt/factories.py`: extractor, storage, and transformer selection.
- `src/peer_elt/transform/methodology.py`: V1-V10 pair scoring, deltas, PRES,
  and audit exports.
- `src/peer_elt/transform/scoring.py`: rule-based and hybrid indicator scoring.
- `docs/peer_review_planning_document.md`: controlling preregistration document.
- `docs/data_model.md`: raw and derived table definitions.
