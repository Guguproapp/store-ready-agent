#!/usr/bin/env python3
"""Run the live Bedrock credential gate without exposing secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from store_ready.agents import (  # noqa: E402
    LivePreflightFailed,
    evidence_document,
    run_live_preflight,
)
from store_ready.preflight import CredentialsRequired, load_preflight_config  # noqa: E402


def main() -> int:
    try:
        config = load_preflight_config()
    except CredentialsRequired as exc:
        print(str(exc))
        return 2

    print(f"CREDENTIAL_CHAIN_RESOLVED region={config.region} model={config.model_id}")
    try:
        evidence = run_live_preflight(config)
    except LivePreflightFailed as exc:
        print(str(exc))
        return 3

    output = Path("reports/live-agent-evidence/preflight.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence_document(evidence), ensure_ascii=False, indent=2) + "\n")
    print(f"LIVE_PREFLIGHT_PASS evidence={output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
