from __future__ import annotations

"""Command-line interface for the ELT pipeline.

This module wires together configuration loading, factory-based component
construction, and pipeline execution behind a small set of subcommands.

The CLI prints **JSON** to stdout for easy scripting:

- ``extract`` prints ``{"raw_rows": <int>}``
- ``transform`` prints ``{"diff_rows": <int>}``
- ``run`` prints the dictionary returned by :func:`peer_elt.pipeline.run_pipeline`
"""

import argparse
import json

from peer_elt.config import load_config
from peer_elt.factories import ExtractorFactory, StorageFactory, TransformerFactory
from peer_elt.pipeline import extract_sources, load_raw, run_pipeline, transform, write_outputs


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the pipeline.

    Returns
    -------
    argparse.Namespace
        Parsed arguments. Includes:

        - ``config``: path to the pipeline YAML config
        - ``command``: one of ``"extract"``, ``"transform"``, or ``"run"``
    """
    parser = argparse.ArgumentParser(description="Peer review ELT pipeline")
    parser.add_argument("--config", required=True, help="Path to pipeline config YAML")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("extract", help="Extract preprint metadata only")
    subparsers.add_parser("transform", help="Transform raw into diff features (no extract)")
    subparsers.add_parser("run", help="Run extract, load, transform, and write outputs")

    return parser.parse_args()


def main() -> None:
    """Run the CLI entry point.

    The command is selected via a required subcommand:

    - ``extract``: extract raw metadata from configured sources and load it to storage
    - ``transform``: read raw data from storage, compute diff features, and write outputs
    - ``run``: run the full pipeline (extract + load + transform + write)

    Notes
    -----
    This function writes JSON status to stdout to support automation.

    Raises
    ------
    ValueError
        If an unknown command is encountered (should not happen with argparse).
    """
    args = _parse_args()
    config = load_config(args.config)
    extractor_factory = ExtractorFactory()
    storage_factory = StorageFactory()
    transformer_factory = TransformerFactory()
    storage = storage_factory.create(config.storage)
    transformer = transformer_factory.create(config)

    if args.command == "extract":
        raw_df = extract_sources(config.sources, extractor_factory, config.retry)
        load_raw(storage, raw_df)
        print(json.dumps({"raw_rows": int(raw_df.shape[0])}))
        return

    if args.command == "transform":
        raw_df = storage.read_raw()
        diff_df = transform(transformer, raw_df)
        write_outputs(storage, config, diff_df, "diff_features")
        print(json.dumps({"diff_rows": int(diff_df.shape[0])}))
        return

    if args.command == "run":
        result = run_pipeline(config)
        print(json.dumps(result))
        return

    raise ValueError(f"Unknown command {args.command}")


if __name__ == "__main__":
    main()
