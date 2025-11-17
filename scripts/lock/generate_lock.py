#!/usr/bin/env python3
"""Generate a deployment lock file for Shopifake services."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

if __package__ is None or __package__ == "":  # pragma: no cover - fallback for direct execution
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from scripts.lock import lib  # type: ignore
else:  # pragma: no cover
    from . import lib


def parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Generate deployment lock file")
    parser.add_argument(
        "--services",
        nargs="*",
        help="Optional list of service names to include (defaults to all submodules)",
    )
    parser.add_argument(
        "--image-metadata",
        type=Path,
        help="Path to JSON/YAML file providing image repository/tag/digest per service",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path. Defaults to locks/lock-<timestamp>.yml",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists",
    )
    parser.add_argument(
        "--default-tag-prefix",
        default=None,
        help="Optional tag prefix to prepend to the submodule SHA (e.g. main-). Leave unset for raw SHA.",
    )
    parser.add_argument(
        "--default-registry",
        default="ghcr.io/shopifake",
        help="Default image registry prefix when metadata is missing",
    )
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    """Entry point."""

    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[2]
    os.chdir(repo_root)

    timestamp = datetime.now(timezone.utc)
    image_metadata = lib.load_image_metadata(args.image_metadata)
    payload = lib.build_lock_payload(
        root=repo_root,
        services_filter=args.services,
        image_metadata=image_metadata,
        generator_id="generate_lock.py@v1",
        timestamp=timestamp,
        default_registry=args.default_registry.rstrip("/"),
        default_tag_prefix=(args.default_tag_prefix or None),
    )

    output_path = args.output or lib.default_output_path(timestamp)
    output_path = lib.dump_lock(payload, output_path, args.force)
    print(f"Lock written to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

