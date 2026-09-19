from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import compare_candidate_file_to_inventory, compare_file_to_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare Python functions by signature, AST, calls, literals, and text.")
    sub = parser.add_subparsers(dest="command", required=True)
    files = sub.add_parser("files")
    files.add_argument("file_a")
    files.add_argument("file_b")
    inventory = sub.add_parser("inventory")
    inventory.add_argument("candidate")
    inventory.add_argument("inventory")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.command == "files":
        result = compare_file_to_file(args.file_a, args.file_b)
    else:
        result = compare_candidate_file_to_inventory(args.candidate, args.inventory)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
