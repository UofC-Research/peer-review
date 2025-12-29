from __future__ import annotations

import argparse
import json

from peer_elt.config import load_config
from peer_elt.factories import ExtractorFactory, StorageFactory, TransformerFactory
from peer_elt.pipeline import extract_sources, load_raw, run_pipeline, transform, write_outputs


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Peer review ELT pipeline")
    parser.add_argument("--config", required=True, help="Path to pipeline config YAML")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("extract", help="Extract preprint metadata only")
    subparsers.add_parser("transform", help="Transform raw into diff features (no extract)")
    subparsers.add_parser("run", help="Run extract, load, transform, and write outputs")

    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = load_config(args.config)
    extractor_factory = ExtractorFactory()
    storage_factory = StorageFactory()
    transformer_factory = TransformerFactory()
    storage = storage_factory.create(config.storage)
    transformer = transformer_factory.create(config)

    if args.command == "extract":
        raw_df = extract_sources(config.sources, extractor_factory)
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
