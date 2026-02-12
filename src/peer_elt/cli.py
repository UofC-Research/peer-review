from __future__ import annotations

"""peer_elt.cli

Command-line interface for the ELT pipeline.

This module is a thin orchestration layer that connects:

- YAML configuration loading (:func:`peer_elt.config.load_config`)
- factory-based component construction (:class:`peer_elt.factories.ExtractorFactory`,
  :class:`peer_elt.factories.StorageFactory`, :class:`peer_elt.factories.TransformerFactory`)
- pipeline stage functions (:func:`peer_elt.pipeline.extract_sources`,
  :func:`peer_elt.pipeline.load_raw`, :func:`peer_elt.pipeline.transform`,
  :func:`peer_elt.pipeline.write_outputs`, :func:`peer_elt.pipeline.run_pipeline`)

Subcommands
-----------
- ``extract``:
  Extract raw metadata from configured sources and persist it via storage.
  Prints JSON to stdout: ``{"raw_rows": <int>}``.

- ``transform``:
  Read raw data from storage, compute derived features, and write outputs.
  Prints JSON to stdout: ``{"diff_rows": <int>}``.

- ``run``:
  Execute the full pipeline end-to-end.
  Prints JSON to stdout: the dict returned by :func:`peer_elt.pipeline.run_pipeline`.

JSON + exit-code contract
-------------------------
On success:
- Exit code ``0``
- A JSON object is written to **stdout** (shape depends on subcommand; see above).

On errors:
- A JSON object is written to **stderr** with at least:
  ``{"ok": false, "error": {"type": <str>, "message": <str>}}``

Exit codes:
- ``2`` for usage/argument errors (raised as :class:`UsageError`).
  The JSON payload includes ``"usage"`` and, when ``--verbose-errors`` is set,
  also includes ``"help"`` (full formatted argparse help).
- ``1`` for unexpected runtime errors.
- ``130`` for keyboard interrupt (Ctrl+C).

Testing note
------------
:func:`main` accepts an optional ``argv`` sequence to make CLI behavior testable
without mutating ``sys.argv``.
"""

import argparse
import json
import sys
from typing import Any, Sequence

from peer_elt.config import load_config
from peer_elt.factories import ExtractorFactory, StorageFactory, TransformerFactory
from peer_elt.pipeline import extract_sources, load_raw, run_pipeline, transform, write_outputs


class UsageError(Exception):
    """Raised for CLI usage/argument errors (maps to exit code 2)."""

    def __init__(self, message: str, *, usage: str | None = None, help_text: str | None = None) -> None:
        super().__init__(message)
        self.usage = usage
        self.help_text = help_text


def _wants_verbose_errors(argv: Sequence[str] | None) -> bool:
    if argv is None:
        return "--verbose-errors" in sys.argv[1:]
    return "--verbose-errors" in argv


class JsonArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises UsageError instead of exiting.

    Parameters
    ----------
    include_help_in_errors:
        If True, include the full formatted help text in raised UsageError.
        (Useful for JSON error responses, but can be verbose.)
    """

    def __init__(self, *args: Any, include_help_in_errors: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._include_help_in_errors = include_help_in_errors

    def error(self, message: str) -> None:
        raise UsageError(
            message,
            usage=self.format_usage().strip(),
            help_text=self.format_help().strip() if self._include_help_in_errors else None,
        )

    def exit(self, status: int = 0, message: str | None = None) -> None:
        if status == 0:
            return
        raise UsageError(
            (message or "Argument parsing failed").strip(),
            usage=self.format_usage().strip(),
            help_text=self.format_help().strip() if self._include_help_in_errors else None,
        )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the pipeline."""
    include_help = _wants_verbose_errors(argv)

    parser = JsonArgumentParser(
        description="Peer review ELT pipeline",
        include_help_in_errors=include_help,
    )
    parser.add_argument("--config", required=True, help="Path to pipeline config YAML")
    parser.add_argument(
        "--verbose-errors",
        action="store_true",
        help="Include full CLI help text in JSON error responses (stderr).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("extract", help="Extract preprint metadata only")
    subparsers.add_parser("transform", help="Transform raw into diff features (no extract)")
    subparsers.add_parser("run", help="Run extract, load, transform, and write outputs")

    return parser.parse_args(argv)


def _print_json(payload: dict[str, Any], *, to_stderr: bool) -> None:
    stream = sys.stderr if to_stderr else sys.stdout
    print(json.dumps(payload), file=stream)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI entry point.

    Returns
    -------
    int
        Process exit code (0 for success; non-zero for errors).
    """
    try:
        args = _parse_args(argv)
        config = load_config(args.config)
        extractor_factory = ExtractorFactory()
        storage_factory = StorageFactory()
        transformer_factory = TransformerFactory()
        storage = storage_factory.create(config.storage)
        transformer = transformer_factory.create(config)

        if args.command == "extract":
            raw_df = extract_sources(config.sources, extractor_factory, config.retry)
            load_raw(storage, raw_df)
            _print_json({"raw_rows": int(raw_df.shape[0])}, to_stderr=False)
            return 0

        if args.command == "transform":
            raw_df = storage.read_raw()
            diff_df = transform(transformer, raw_df)
            write_outputs(storage, config, diff_df, "diff_features")
            _print_json({"diff_rows": int(diff_df.shape[0])}, to_stderr=False)
            return 0

        if args.command == "run":
            result = run_pipeline(config)
            _print_json(result, to_stderr=False)
            return 0

        raise ValueError(f"Unknown command {args.command}")

    except UsageError as exc:
        payload: dict[str, Any] = {
            "ok": False,
            "error": {"type": "UsageError", "message": str(exc)},
        }
        if exc.usage:
            payload["usage"] = exc.usage
        if exc.help_text:
            payload["help"] = exc.help_text
        _print_json(payload, to_stderr=True)
        return 2

    except KeyboardInterrupt:
        _print_json(
            {"ok": False, "error": {"type": "KeyboardInterrupt", "message": "Interrupted"}},
            to_stderr=True,
        )
        return 130
    except Exception as exc:
        _print_json(
            {"ok": False, "error": {"type": exc.__class__.__name__, "message": str(exc)}},
            to_stderr=True,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
