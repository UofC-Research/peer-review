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

Local run (DuckDB + Parquet):

```bash
python -m peer_elt.cli --config configs/local.yml run
```

Production run (PostgreSQL + Slurm):

```bash
sbatch scripts/run_pipeline.slurm configs/prod.yml
```

Data model details: `docs/data_model.md`

Run tests:

```bash
pytest
```
