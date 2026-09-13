#!/usr/bin/env python3
"""Remove local machine identity from a generated JUnit XML artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from store_ready.evidence import sanitize_junit  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    sanitize_junit(args.path)


if __name__ == "__main__":
    main()
