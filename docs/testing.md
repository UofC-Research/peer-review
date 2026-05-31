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

## Test Inventory

This inventory summarizes what each pytest test currently protects. It is
intended as maintenance documentation: when a test is renamed, removed, or added,
update this section with the behavior the test is meant to lock down.

### Acquired Artifact Scoring

| Test                                                         | What it verifies                                                                                            |
|--------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| `test_acquired_xml_artifacts_are_parsed_and_scored`          | XML acquisition artifacts can be parsed into article documents and scored through the methodology workflow. |
| `test_acquired_html_artifact_parser_builds_article_document` | HTML acquisition artifacts can be parsed into the article-document shape used by scoring.                   |
| `test_artifact_registry_rejects_missing_parser`              | Artifact parsing fails clearly when no parser is registered for an artifact format.                         |
| `test_artifact_parser_rejects_failed_acquisition`            | Failed acquisition results are not silently parsed as successful artifacts.                                 |

### Article Parsing Pipeline

| Test                                                     | What it verifies                                                                           |
|----------------------------------------------------------|--------------------------------------------------------------------------------------------|
| `test_article_parsing_pipeline_scrapes_and_embeddings`   | The article parsing pipeline composes scraper, parser, embedding, and extraction services. |
| `test_simple_token_stats_processor_handles_article_text` | The token statistics processor produces basic token metrics from article text.             |

### CLI Pipeline

| Test                                                                | What it verifies                                                                         |
|---------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| `test_cli_run_prints_pipeline_result`                               | `peer-elt run` prints the pipeline result returned by the pipeline layer.                |
| `test_cli_transform_reads_raw_writes_outputs_and_prints_diff_rows`  | `peer-elt transform` reads raw data, writes transformed outputs, and reports row counts. |
| `test_cli_run_prints_error_json_and_returns_nonzero_on_exception`   | Runtime exceptions are reported as structured JSON and return a nonzero exit code.       |
| `test_cli_argparse_error_prints_json_including_usage_and_returns_2` | Argument parsing errors produce JSON including usage text and exit code `2`.             |
| `test_cli_argparse_error_with_verbose_errors_flag_includes_help`    | Verbose CLI errors include help text in the structured error payload.                    |

### Config And Pipeline

| Test                                                                    | What it verifies                                                                |
|-------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| `test_load_config_resolves_output_base_dir_relative_to_config_file`     | Relative output paths are resolved relative to the config file location.        |
| `test_load_config_raises_when_storage_env_var_unset`                    | Storage URLs that reference missing environment variables fail clearly.         |
| `test_load_config_allows_storage_env_var_when_set`                      | Storage URLs can be populated from environment variables.                       |
| `test_load_config_raises_when_retry_not_mapping`                        | Invalid `retry` blocks are rejected.                                            |
| `test_load_config_raises_when_transform_not_mapping`                    | Invalid `transform` blocks are rejected.                                        |
| `test_load_config_raises_clear_error_when_top_level_key_missing`        | Missing required top-level config keys produce clear errors.                    |
| `test_load_config_raises_clear_error_when_duckdb_storage_missing_path`  | DuckDB storage config requires a database path.                                 |
| `test_load_config_raises_clear_error_when_postgres_storage_missing_url` | Postgres storage config requires a URL.                                         |
| `test_load_config_allows_unknown_storage_backend_and_preserves_keys`    | Unknown storage backends are preserved for downstream extension.                |
| `test_load_config_raises_clear_error_when_source_missing_required_key`  | Source entries missing required fields fail clearly.                            |
| `test_load_config_raises_when_source_item_not_mapping`                  | Non-mapping source entries are rejected.                                        |
| `test_load_config_raises_on_empty_yaml`                                 | Empty YAML configs are rejected.                                                |
| `test_load_config_raises_on_non_mapping_payload`                        | YAML payloads that are not mappings are rejected.                               |
| `test_load_config_expands_env`                                          | Environment-variable expansion works in config values.                          |
| `test_load_config_raises_when_sources_not_list`                         | The `sources` config section must be a list.                                    |
| `test_load_config_raises_when_storage_not_mapping`                      | The `storage` config section must be a mapping.                                 |
| `test_load_config_raises_when_output_not_mapping`                       | The `output` config section must be a mapping.                                  |
| `test_extract_sources_combines_and_tags`                                | Extraction combines source data and tags rows with source metadata.             |
| `test_write_outputs_writes_files_and_calls_storage`                     | Output writing creates files and delegates persistence to storage.              |
| `test_run_pipeline_returns_zero_when_empty`                             | The pipeline reports zero rows without failing when extraction returns no data. |
| `test_cli_extract_prints_counts`                                        | The extract CLI path prints extraction counts.                                  |

### Corpus Acquisition

| Test                                                                   | What it verifies                                                                         |
|------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| `test_build_pairs_selects_initial_preprint_version_and_published_doi`  | Matched-pair construction selects the initial preprint version and linked published DOI. |
| `test_query_preprint_servers_for_pairs_uses_configured_sources`        | Preprint-server querying follows configured source windows.                              |
| `test_build_acquisition_requests_uses_preprint_v1_and_doi_resolver`    | Acquisition requests target preprint version 1 and DOI-resolver published candidates.    |
| `test_build_acquisition_requests_resolves_elife_full_text_candidates`  | eLife DOIs map to expected full-text candidate URLs.                                     |
| `test_build_acquisition_requests_resolves_plos_full_text_candidates`   | PLOS DOIs map to expected full-text candidate URLs.                                      |
| `test_acquire_matched_pair_full_text_downloads_preprint_and_published` | Matched-pair acquisition attempts and records both preprint and published full text.     |

### Extractors And Factories

| Test                                                     | What it verifies                                                                 |
|----------------------------------------------------------|----------------------------------------------------------------------------------|
| `test_fetch_preprints_paginates_and_sets_fields`         | The bioRxiv/medRxiv metadata extractor paginates and normalizes expected fields. |
| `test_fetch_medrxiv_passes_server`                       | The medRxiv wrapper delegates with `server="medrxiv"`.                           |
| `test_registry_extractor_fetches_from_registered_client` | Registry-based extraction dispatches to the registered client.                   |
| `test_extractor_factory_supported_sources`               | Supported extractor factories are created for configured sources.                |
| `test_extractor_factory_rejects_unsupported_sources`     | Unsupported extractor source names fail clearly.                                 |
| `test_storage_factory_duckdb`                            | DuckDB storage instances can be created through the storage factory.             |
| `test_transformer_factory_diff`                          | Diff transformer instances can be created through the transformer factory.       |

### Full Text Acquisition

| Test                                                              | What it verifies                                                                      |
|-------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| `test_acquire_prefers_pdf_then_stops_on_success`                  | Acquisition tries PDF first and stops after the first successful download.            |
| `test_acquire_falls_back_pdf_to_xml`                              | Acquisition falls back from PDF to XML when PDF fails.                                |
| `test_acquire_falls_back_pdf_to_xml_to_html`                      | Acquisition falls back through PDF, XML, then HTML.                                   |
| `test_acquire_flags_for_human_when_all_fail`                      | Failed automated downloads are flagged for human review.                              |
| `test_acquire_flags_for_human_when_no_urls_exist`                 | Requests with no candidate URLs are flagged for human review.                         |
| `test_pair_acquisition_matches_html_when_published_only_has_html` | Pair acquisition can succeed when only the published-side HTML fallback is available. |

### HTTP Retry

| Test                                                        | What it verifies                                           |
|-------------------------------------------------------------|------------------------------------------------------------|
| `test_requests_http_get_retries_on_503_then_succeeds`       | HTTP 503 responses are retried and can eventually succeed. |
| `test_requests_http_get_does_not_retry_on_404`              | HTTP 404 responses are not retried.                        |
| `test_requests_http_get_retries_on_exception_then_succeeds` | Transient request exceptions are retried.                  |
| `test_requests_http_get_applies_backoff_delay_on_retries`   | Retry backoff waits are invoked between attempts.          |

### Live Integration

| Test                                                       | What it verifies                                                                              |
|------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| `test_live_preprint_sources_return_expected_metadata`      | Enabled live configs can query bioRxiv/medRxiv metadata windows and receive required columns. |
| `test_live_published_full_text_candidates_are_retrievable` | Configured published DOIs have at least one retrievable full-text candidate.                  |
| `test_live_matched_pairs_can_be_acquired`                  | Configured preprint/published pairs can be acquired through the live acquisition path.        |

### Methodology And Scoring

| Test                                                                    | What it verifies                                                                 |
|-------------------------------------------------------------------------|----------------------------------------------------------------------------------|
| `test_version_scorecard_materializes_all_preregistered_indicators`      | Version scorecards include all preregistered indicators.                         |
| `test_pair_scorecard_computes_deltas_and_pres_independently`            | Pair scorecards compute deltas and peer-review effect size independently.        |
| `test_pair_scorecard_exports_flat_record_and_evidence_rows`             | Pair scorecards export flat records and evidence rows.                           |
| `test_section_adapter_normalizes_parsed_document_sections`              | Parsed document sections are normalized for methodology scoring.                 |
| `test_article_adapter_extracts_headed_sections_for_scoring`             | Article adapters extract headed sections for scoring.                            |
| `test_methodology_workflow_scores_parsed_pair_through_adapter_strategy` | Parsed preprint/published pairs can be scored through the adapter strategy.      |
| `test_methodology_output_repository_writes_r_ready_tables`              | Methodology outputs are written in R-ready table form.                           |
| `test_methodology_output_frames_have_stable_empty_schema`               | Empty methodology output frames keep a stable schema.                            |
| `test_rule_based_scoring_hits_all_indicators`                           | Rule-based scoring can produce all indicator outputs.                            |
| `test_hybrid_scoring_prefers_lower_score_when_low_confidence`           | Hybrid scoring keeps lower rule-based scores when model confidence is low.       |
| `test_hybrid_scoring_allows_high_confidence_override`                   | Hybrid scoring allows high-confidence model predictions to override rule scores. |
| `test_model_scorer_builds_indicator_scores_from_predictions`            | Model predictions are converted into indicator score records.                    |

### Parsing Pipelines

| Test                                                            | What it verifies                                                                      |
|-----------------------------------------------------------------|---------------------------------------------------------------------------------------|
| `test_pdf_parsing_pipeline_composes_services`                   | PDF parsing composes loader, extractor, cleaner, and processor services.              |
| `test_simple_token_stats_processor_counts`                      | Token statistics count expected tokens and sentences across parameterized text cases. |
| `test_section_tag_reader_extracts_named_sections`               | Section-tag XML reader extracts named sections.                                       |
| `test_tei_reader_prefers_type_attribute_and_falls_back_to_head` | TEI XML reader prefers section `type` attributes and falls back to headings.          |
| `test_reader_factory_handles_formats_and_rejects_unknown`       | XML reader factory handles supported formats and rejects unknown formats.             |
| `test_reader_raises_on_invalid_xml`                             | Invalid XML raises a parse error.                                                     |

### Storage

| Test                                    | What it verifies                                                             |
|-----------------------------------------|------------------------------------------------------------------------------|
| `test_engine_requires_url`              | Postgres engine construction requires a database URL.                        |
| `test_load_raw_postgres_skips_empty`    | Empty raw-data loads are skipped for Postgres storage.                       |
| `test_write_table_postgres_skips_empty` | Empty table writes are skipped for Postgres storage.                         |
| `test_diff_transformer_basic`           | Diff transformation computes basic change metrics between preprint versions. |
| `test_duckdb_storage_round_trip`        | DuckDB storage can write and read a table round trip.                        |

### TDM Acquisition

| Test                                                                       | What it verifies                                                                                        |
|----------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| `test_tdm_config_accepts_biorxiv_and_medrxiv_servers`                      | TDM config parsing accepts official bioRxiv and medRxiv S3 resources.                                   |
| `test_tdm_config_from_mapping_rejects_unknown_server`                      | Unsupported TDM server names fail clearly.                                                              |
| `test_download_tdm_preprint_archive_uses_requester_pays_s3_settings`       | Archive sync delegates bucket, destination, region, and requester-pays settings to the client.          |
| `test_aws_cli_tdm_archive_client_uses_requester_payer_flag`                | AWS CLI sync commands include `--request-payer requester` when needed.                                  |
| `test_aws_cli_environment_from_dotenv_recognizes_lowercase_aws_keys`       | `.env` lowercase AWS aliases are translated to AWS CLI environment variables.                           |
| `test_aws_cli_tdm_archive_client_loads_dotenv_credentials_for_subprocess`  | The AWS CLI TDM client passes `.env` credentials to the subprocess environment.                         |
| `test_acquire_tdm_preprints_and_published_articles_automates_tdm_workflow` | Automated TDM workflow syncs archives, downloads published metadata, and retrieves published full text. |
| `test_build_published_metadata_url_supports_biorxiv_and_medrxiv`           | Published-metadata API URLs are built for both bioRxiv and medRxiv.                                     |
| `test_download_published_metadata_writes_api_payload`                      | Published-metadata downloads write the API payload to disk.                                             |

## Potential Missing Tests

These are known gaps or deferred tests. They are not necessarily bugs, but they
are useful candidates when hardening the project.

| Area                         | Missing or deferred coverage                                                                                                                                                                                                                                  |
|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Real AWS/TDM S3 access       | No automated test performs a real requester-pays S3 sync against `biorxiv-src-monthly` or `medrxiv-src-monthly`; this is intentionally avoided in default tests because it requires credentials, network access, AWS CLI, permissions, and charge acceptance. |
| `.env` parsing edge cases    | Current tests cover uppercase keys, lowercase aliases, simple quotes, session token, and region. They do not cover escaped quotes, multiline values, duplicate keys, or malformed credential values.                                                          |
| Live TDM config consumption  | `tests/test_live_integration.py` does not consume the `tdm_repository` block; live tests currently cover API/full-text routes rather than S3 archive sync.                                                                                                    |
| AWS CLI not installed        | The AWS CLI client command shape is tested with an injected runner, but there is no test for the user-facing failure message when the `aws` executable is missing.                                                                                            |
| Real Postgres integration    | Postgres tests use mocked behavior and empty-frame skips; they do not connect to a real Postgres server or validate SQL schema creation end to end.                                                                                                           |
| Real publisher variability   | Live tests can check configured DOI examples, but offline tests do not exhaustively cover publisher-specific URL patterns beyond the implemented DOI families.                                                                                                |
| PDF extraction quality       | PDF parsing tests verify pipeline composition and basic token counts; they do not benchmark extraction quality across noisy publisher PDFs.                                                                                                                   |
| CLI entry point packaging    | CLI behavior is tested through Python call paths; installation-level console-script wiring is not separately exercised.                                                                                                                                       |
| R test in pytest/CI          | `tests/test_analysis_layer.R` is documented separately and is not executed by the Python pytest suite.                                                                                                                                                        |
| Performance/regression scale | Tests use small fixtures and fakes; there is no large-window acquisition or storage performance regression test.                                                                                                                                              |

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
- Optionally document a local `tdm_repository` plan if bulk bioRxiv/medRxiv
  preprint full-text acquisition will use the official Text and Data Mining
  requester-pays S3 repositories.
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

## Optional TDM Repository Use

bioRxiv and medRxiv provide Text and Data Mining repositories for bulk access to
preprint full-text packages. The example live config includes a disabled
`tdm_repository` block so local configs can record this acquisition route.

Current pytest live tests do not consume `tdm_repository` and do not sync S3
buckets directly. The TDD-covered `peer_elt.acquire.tdm` workflow parses the
block, delegates archive sync to an injected requester-pays S3 client, downloads
linked published-article metadata from the bioRxiv API, and retrieves published
article full text in XML, PDF, then HTML order.

Scope boundaries:

- TDM is an optional bulk source for bioRxiv/medRxiv preprint full text.
- When TDM is selected, process matched preprint and published article files in
  XML, PDF, then HTML order. XML is preferred for efficient structured
  comparison; PDF and HTML are automated fallbacks.
- Linked published-article metadata should still be taken from the bioRxiv API
  `published` or `pubs` fields.
- Published-article full text should still be retrieved from publisher-specific,
  DOI-resolver, PMC, or other permitted article-level sources. The
  bioRxiv/medRxiv TDM repositories do not replace that published-side
  acquisition path.

This testing workflow documentation is a post-lock transparency clarification,
not a study-design change. The audit-trail entry is recorded in
`docs/deviations_log.md`.

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
  It does not currently consume `tdm_repository`.
- `tests/test_tdm_acquisition.py`: verifies TDM config parsing, AWS CLI
  requester-pays archive-sync command construction, archive-sync delegation for
  bioRxiv and medRxiv, published-link metadata downloads from the bioRxiv API,
  and automated XML-first published article full-text retrieval.

## R Tests

Run the R analysis tests from the repository root:

```bash
Rscript tests/test_analysis_layer.R
```

These tests use deterministic analysis inputs and do not require live data.
