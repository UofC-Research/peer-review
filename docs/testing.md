# Testing Workflows

This project has two pytest modes:

- Dummy-data/offline tests: deterministic tests that use fixtures, temporary
  directories, and fake HTTP clients. These are the default and are suitable for
  routine development and CI.
- Live-data tests: opt-in integration tests marked `live` that call external
  bioRxiv/medRxiv APIs and publisher or DOI-resolver endpoints.

## Dummy-Data Pytest Runs

Run the default Python test suite from the repository root:

```bash
pytest
```

Live tests are collected but skipped unless a live config path is supplied. To
exclude live tests entirely, run:

```bash
pytest -m "not live"
```

No local data files or live credentials are needed for dummy-data runs.

Files involved:

- `pyproject.toml`: pytest configuration, including `pythonpath = ["src"]`,
  test discovery under `tests`, default `addopts`, and the `live` marker.
- `tests/conftest.py`: adds the `--live-config` option and skips live tests
  when no enabled config is supplied.
- `tests/test_*.py`: regular unit and integration tests that use dummy data,
  injected clients, and temporary files.
- `tests/test_live_integration.py`: live tests; skipped during dummy-data runs
  unless explicitly enabled.

## Live-Data Pytest Runs

Create a local live-test config from the committed example:

```bash
cp configs/live_tests.example.yml configs/live_tests.local.yml
```

Edit `configs/live_tests.local.yml` before running live tests:

- Set `enabled: true`.
- Replace placeholder `preprint_sources` date windows with stable historical
  bioRxiv or medRxiv windows.
- Replace placeholder `published_full_text` DOIs with stable, accessible
  published articles.
- Replace placeholder `matched_pairs` preprint/published DOI pairs with stable
  examples.
- Adjust `timeout_seconds` and `retry` only when the external services need
  more conservative timing.

Run only the live tests:

```bash
pytest -m live --live-config configs/live_tests.local.yml
```

Run the full Python suite with live tests included:

```bash
pytest --live-config configs/live_tests.local.yml
```

The same config can be supplied by environment variable:

```bash
PEER_REVIEW_LIVE_CONFIG=configs/live_tests.local.yml pytest -m live
```

Live tests may fail because of upstream changes, rate limiting, network
availability, DOI-resolution changes, or publisher access changes. Treat those
failures as integration-health signals before treating them as code regressions.

Files involved:

- `configs/live_tests.example.yml`: committed template and schema. Keep this
  disabled with `enabled: false`.
- `configs/live_tests.local.yml`: local file to create and modify for live
  runs. It is ignored by Git.
- `.gitignore`: keeps `configs/live_tests.local.yml` out of version control.
- `tests/conftest.py`: reads `--live-config` or `PEER_REVIEW_LIVE_CONFIG`,
  validates the YAML mapping, and requires `enabled: true`.
- `tests/test_live_integration.py`: consumes `preprint_sources`,
  `published_full_text`, `matched_pairs`, `timeout_seconds`, and `retry`.

## R Tests

Run the R analysis tests from the repository root:

```bash
Rscript tests/test_analysis_layer.R
```

These tests use deterministic analysis inputs and do not require live data.
