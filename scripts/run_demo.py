#!/usr/bin/env python3
import os
import sys
from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from store_ready.web_app import serve  # noqa: E402

if __name__ == "__main__":
    serve(
        host=os.getenv("STORE_READY_HOST", "127.0.0.1"),
        port=int(os.getenv("STORE_READY_PORT", "8000")),
    )
