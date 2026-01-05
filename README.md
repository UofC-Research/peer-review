# Peer Review Project (v2)

## ELT Pipeline

Install dependencies:

```bash
pip install -e .
```

Tech stack:

- ELT pipeline: Python
- Analysis: R

Design patterns:

- Factory for extractor/storage/transformer selection
- Strategy via interface-based components

Development practice:

- Test-driven development (TDD): write tests before implementation changes

Local run (DuckDB + Parquet):

```bash
python -m peer_elt.cli --config configs/local.yml run
```

Production run (PostgreSQL + Slurm):

```bash
sbatch scripts/run_pipeline.slurm configs/prod.yml
```

Data model details: `docs/data_model.md`

Retry/backoff settings live in the `retry` block of each config file.

Run tests:

```bash
pytest
```

Note: pytest reads `pythonpath = ["src"]` from `pyproject.toml` so imports resolve without extra env setup.
