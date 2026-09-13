#!/usr/bin/env python3
"""Build a clean public-source package without internal governance evidence."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ENTRIES = (
    "LICENSE",
    "README.md",
    "pyproject.toml",
    "requirements-dev.lock",
    "render.yaml",
    "src/store_ready",
    "tests",
    "scripts/__init__.py",
    "scripts/build_public_submission.py",
    "scripts/preflight_live.py",
    "scripts/run_demo.py",
    "scripts/sanitize_junit.py",
    "docs/ARCHITECTURE.md",
    "docs/DEVPOST_DRAFT.md",
    "docs/JUDGING_GUIDE.md",
    "docs/LIVE_EVIDENCE.md",
    "docs/PUBLIC_REPO_READINESS.md",
    "docs/SBOM.md",
    "docs/THIRD_PARTY_NOTICES.md",
    "docs/VIDEO_SCRIPT_EN.md",
    "docs/architecture-diagram.svg",
)
TEXT_SUFFIXES = {"", ".css", ".html", ".js", ".json", ".md", ".py", ".svg", ".toml", ".txt"}
SECRET_PATTERNS = (
    re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"aws_secret_access_key\s*[:=]\s*[A-Za-z0-9/+]{20,}", re.IGNORECASE),
    re.compile(r"aws_session_token\s*[:=]\s*[A-Za-z0-9/+=]{40,}", re.IGNORECASE),
)
LOCAL_PATH_PATTERNS = (
    re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\"),
)


def _inside_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return False
    return True


def _copy_entry(relative: str, destination: Path) -> None:
    source = ROOT / relative
    target = destination / relative
    if not source.exists():
        raise FileNotFoundError(f"required public file is missing: {relative}")
    if source.is_dir():
        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "*.db", "*.sqlite*"),
        )
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _scan(destination: Path) -> list[str]:
    manifest: list[str] = []
    for path in sorted(item for item in destination.rglob("*") if item.is_file()):
        relative = path.relative_to(destination).as_posix()
        manifest.append(relative)
        if path.name == ".env" or path.suffix == ".pem":
            raise ValueError(f"forbidden public file: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        content = path.read_text(encoding="utf-8")
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            raise ValueError(f"secret pattern found in public file: {relative}")
        if any(pattern.search(content) for pattern in LOCAL_PATH_PATTERNS):
            raise ValueError(f"local path found in public file: {relative}")
    return manifest


def build_public_submission(destination: Path) -> list[str]:
    """Copy the public allowlist to a new destination and return its manifest."""

    if destination.exists():
        raise FileExistsError("destination must not already exist")
    if _inside_root(destination):
        raise ValueError("destination must be outside the repository")
    destination.mkdir(parents=True)
    for entry in PUBLIC_ENTRIES:
        _copy_entry(entry, destination)
    manifest = _scan(destination)
    (destination / "PUBLIC_MANIFEST.txt").write_text(
        "\n".join((*manifest, "PUBLIC_MANIFEST.txt")) + "\n",
        encoding="utf-8",
    )
    return [*manifest, "PUBLIC_MANIFEST.txt"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        manifest = build_public_submission(args.destination)
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    print(f"PUBLIC_SUBMISSION_READY files={len(manifest)} destination={args.destination}")


if __name__ == "__main__":
    main()
