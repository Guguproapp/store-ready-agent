from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.build_public_submission import _scan


class PublicSubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.script = self.root / "scripts" / "build_public_submission.py"

    def test_builds_allowlisted_package_without_internal_evidence(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "store-ready-agent-public"
            completed = subprocess.run(
                [sys.executable, str(self.script), str(destination)],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("PUBLIC_SUBMISSION_READY", completed.stdout)
            for required in (
                "LICENSE",
                "README.md",
                "render.yaml",
                "docs/SBOM.md",
                "docs/THIRD_PARTY_NOTICES.md",
                "docs/architecture-diagram.svg",
                "docs/JUDGING_GUIDE.md",
                "docs/VIDEO_SCRIPT_EN.md",
                "src/store_ready/agents.py",
                "tests/test_agents.py",
                "PUBLIC_MANIFEST.txt",
            ):
                self.assertTrue((destination / required).is_file(), required)
            manifest = (destination / "PUBLIC_MANIFEST.txt").read_text(encoding="utf-8")
            self.assertNotIn("reports/", manifest)
            self.assertNotIn(".git/", manifest)
            self.assertNotIn(".env", manifest)
            public_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in destination.rglob("*")
                if path.is_file() and path.suffix in {"", ".md", ".py", ".toml", ".svg"}
            )
            self.assertNotIn(str(Path.home().resolve()) + "/", public_text)
            self.assertNotRegex(public_text, r"/(?:Users|home)/[A-Za-z0-9._-]+/")
            private_key_header = "-" * 5 + "BEGIN PRIVATE KEY" + "-" * 5
            self.assertNotIn(private_key_header, public_text)

    def test_refuses_existing_destination(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "already-exists"
            destination.mkdir()
            completed = subprocess.run(
                [sys.executable, str(self.script), str(destination)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("destination must not already exist", completed.stderr)

    def test_scan_rejects_generic_local_home_paths(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory)
            mac_home = "/" + "Users" + "/someone/private/file.txt"
            windows_home = "C:" + "\\" + "Users" + "\\person\\private.txt"
            (destination / "fixture.md").write_text(
                f"Do not publish {mac_home} or {windows_home}",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "local path found"):
                _scan(destination)


if __name__ == "__main__":
    unittest.main()
