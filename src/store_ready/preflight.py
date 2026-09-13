"""Safe, real Strands/Bedrock preflight helpers.

This module never prints credentials. It only reports whether the standard AWS
credential chain can resolve an identity and leaves the actual live invocation
to the explicit preflight command.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class CredentialsRequired(RuntimeError):
    """Raised when the AWS credential chain has no usable credentials."""


@dataclass(frozen=True)
class PreflightConfig:
    """Non-secret configuration for a live preflight."""

    region: str
    model_id: str


def load_preflight_config() -> PreflightConfig:
    """Resolve non-secret settings and verify that credentials are available."""

    try:
        import boto3  # type: ignore[import-untyped]
    except ModuleNotFoundError as exc:
        raise CredentialsRequired("P0_RUNTIME_REQUIRED: install boto3 and strands-agents") from exc

    session = boto3.Session()
    credentials = session.get_credentials()
    if credentials is None:
        raise CredentialsRequired("P0_CREDENTIALS_REQUIRED")

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or session.region_name
    if not region:
        raise CredentialsRequired("P0_CREDENTIALS_REQUIRED: AWS_REGION_REQUIRED")

    model_id = os.getenv("STORE_READY_MODEL_ID", "amazon.nova-lite-v1:0")
    return PreflightConfig(region=region, model_id=model_id)
