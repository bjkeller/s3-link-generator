"""Shared test fixtures for the S3 pre-signed URL Lambda test suite.

Provides moto-mocked AWS clients, factory functions for building API Gateway
proxy events, registering client configs in SSM, and storing signing
credentials in Secrets Manager. Also resets module-level handler state
between tests.

Requirements: 13.1, 13.8
"""

import json
import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import boto3
import pytest
from moto import mock_aws

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_REGION = "us-east-1"
TEST_CLIENT_REGISTRY_PREFIX = "/presign/clients"
TEST_SIGNING_CREDENTIALS_SECRET = "test/signing-creds"
TEST_DEFAULT_EXPIRATION = "604800"
TEST_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
TEST_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


# ---------------------------------------------------------------------------
# Environment variables — set BEFORE any handler import
# ---------------------------------------------------------------------------

os.environ["CLIENT_REGISTRY_PREFIX"] = TEST_CLIENT_REGISTRY_PREFIX
os.environ["SIGNING_CREDENTIALS_SECRET"] = TEST_SIGNING_CREDENTIALS_SECRET
os.environ["DEFAULT_EXPIRATION"] = TEST_DEFAULT_EXPIRATION
os.environ["AWS_DEFAULT_REGION"] = TEST_REGION
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["POWERTOOLS_LOG_LEVEL"] = "DEBUG"


# ---------------------------------------------------------------------------
# Module-level state reset
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_handler_state() -> Generator[None, None, None]:
    """Reset module-level cached state between tests.

    The handler caches ``_signing_credentials`` and
    ``_s3_signing_client`` at module level for warm-start reuse. Tests
    must start with a clean slate so each test controls its own mock
    environment.
    """
    import s3_signed_url_lambda.lambda_function as handler_mod

    handler_mod._signing_credentials = None  # noqa: SLF001
    handler_mod._s3_signing_client = None  # noqa: SLF001
    yield
    handler_mod._signing_credentials = None  # noqa: SLF001
    handler_mod._s3_signing_client = None  # noqa: SLF001


# ---------------------------------------------------------------------------
# Mock Lambda context
# ---------------------------------------------------------------------------


@pytest.fixture
def lambda_context() -> MagicMock:
    """Provide a minimal mock Lambda context."""
    ctx = MagicMock()
    ctx.aws_request_id = "test-request-id"
    ctx.function_name = "s3-presign-lambda"
    ctx.memory_limit_in_mb = 128
    ctx.remaining_time_in_millis = 30000
    return ctx


# ---------------------------------------------------------------------------
# Moto-mocked AWS client fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def aws_mock() -> Generator[None, None, None]:
    """Activate moto ``mock_aws`` for the duration of a test."""
    with mock_aws():
        yield


@pytest.fixture
def ssm_client(aws_mock: None) -> Any:
    """Return a moto-mocked SSM client."""
    return boto3.client("ssm", region_name=TEST_REGION)


@pytest.fixture
def s3_client(aws_mock: None) -> Any:
    """Return a moto-mocked S3 client."""
    return boto3.client("s3", region_name=TEST_REGION)


@pytest.fixture
def secrets_client(aws_mock: None) -> Any:
    """Return a moto-mocked Secrets Manager client."""
    return boto3.client("secretsmanager", region_name=TEST_REGION)


# ---------------------------------------------------------------------------
# Factory: API Gateway proxy events
# ---------------------------------------------------------------------------


def make_apigw_event(
    bucket: str | None = "test-bucket",
    key: str | None = "path/to/object.csv",
    expiration: str | None = None,
    api_key_id: str | None = "test-client",
) -> dict[str, Any]:
    """Build an API Gateway proxy event dict.

    Usage::

        event = make_apigw_event("my-bucket", "obj.csv")
        event = make_apigw_event(expiration="7200", api_key_id="client-1")
        event = make_apigw_event()  # uses sensible defaults
    """
    params: dict[str, str] = {}
    if bucket is not None:
        params["bucket"] = bucket
    if key is not None:
        params["key"] = key
    if expiration is not None:
        params["expiration"] = expiration

    identity: dict[str, Any] = {}
    if api_key_id is not None:
        identity["apiKeyId"] = api_key_id

    return {
        "queryStringParameters": params or None,
        "requestContext": {
            "identity": identity,
        },
    }


# ---------------------------------------------------------------------------
# Factory: register client config in mocked SSM
# ---------------------------------------------------------------------------


def register_client(
    ssm_client: Any,
    client_id: str = "test-client",
    allowed_buckets: list[str] | None = None,
    max_expiration: int = 604800,
    description: str = "test client",
    prefix: str = "/presign/clients",
) -> dict[str, Any]:
    """Store a client config in moto-mocked SSM.

    Usage::

        config = register_client(ssm_client)
        config = register_client(
            ssm_client,
            client_id="custom",
            allowed_buckets=["bucket-a", "bucket-b"],
            max_expiration=86400,
        )

    Returns the raw config dict that was stored.
    """
    if allowed_buckets is None:
        allowed_buckets = ["test-bucket"]

    config: dict[str, Any] = {
        "client_id": client_id,
        "allowed_buckets": allowed_buckets,
        "max_expiration": max_expiration,
        "description": description,
    }
    param_path = f"{prefix}/{client_id}"
    ssm_client.put_parameter(
        Name=param_path,
        Value=json.dumps(config),
        Type="String",
    )
    return config


# ---------------------------------------------------------------------------
# Factory: store signing credentials in mocked Secrets Manager
# ---------------------------------------------------------------------------


def store_signing_credentials(
    secretsmanager_client: Any,
    secret_id: str = TEST_SIGNING_CREDENTIALS_SECRET,
    access_key_id: str = TEST_ACCESS_KEY_ID,
    secret_access_key: str = TEST_SECRET_ACCESS_KEY,
) -> dict[str, str]:
    """Store signing credentials in moto-mocked Secrets Manager.

    Usage::

        creds = store_signing_credentials(secrets_client)
        creds = store_signing_credentials(
            secrets_client,
            access_key_id="AKIA...",
            secret_access_key="...",
        )

    Returns the raw credentials dict that was stored.
    """
    creds = {
        "access_key_id": access_key_id,
        "secret_access_key": secret_access_key,
    }
    secretsmanager_client.create_secret(
        Name=secret_id,
        SecretString=json.dumps(creds),
    )
    return creds
