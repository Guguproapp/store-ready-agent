from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from store_ready.evidence import sanitize_junit
from store_ready.preflight import CredentialsRequired, load_preflight_config


class EmptySession:
    region_name = None

    def get_credentials(self) -> None:
        return None


class PreflightTests(unittest.TestCase):
    def test_junit_sanitizer_removes_local_identity(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            report = Path(temporary_directory) / "pytest.xml"
            local_test_path = "/" + "Users" + "/person/project/test_example.py"
            report.write_text(
                '<?xml version="1.0"?><testsuite tests="1" '
                'hostname="personal-mac.local"><testcase '
                f'file="{local_test_path}" /></testsuite>',
                encoding="utf-8",
            )
            sanitize_junit(report)
            sanitized = report.read_text(encoding="utf-8")
            self.assertIn('tests="1"', sanitized)
            self.assertIn("[LOCAL_HOME]/project/test_example.py", sanitized)
            self.assertNotIn("hostname", sanitized)
            self.assertNotIn("/" + "Users" + "/", sanitized)

    def test_missing_aws_credentials_fails_closed(self) -> None:
        with patch("boto3.Session", return_value=EmptySession()):
            with self.assertRaisesRegex(CredentialsRequired, "P0_CREDENTIALS_REQUIRED"):
                load_preflight_config()
