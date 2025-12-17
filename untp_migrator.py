#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

# Import your utility
from utilities.json_migration_utility import json_migr_util


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="untp_migrator.py",
        description="Apply JSON migration rules to an input JSON and write the transformed output JSON.",
    )
    parser.add_argument(
        "-m", "--mapping",
        required=True,
        help="Path to mapping rules JSON file (e.g., mapping_file_path/file.json).",
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to input JSON file (e.g., input_file_path/input.json).",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Path to output JSON file (e.g., output_file_path/out.json).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if a move source path is missing instead of skipping it.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    mapping_path = Path(args.mapping)
    input_path = Path(args.input)
    output_path = Path(args.output)

    # Basic validation
    if not mapping_path.is_file():
        print(f"ERROR: mapping file not found: {mapping_path}", file=sys.stderr)
        return 2
    if not input_path.is_file():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 2

    try:
        util = json_migr_util(strict=args.strict)
        util.migrate_json(str(mapping_path), str(input_path), str(output_path))
    except Exception as e:
        print(f"ERROR: migration failed: {e}", file=sys.stderr)
        return 1

    print(f"OK: wrote output to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
