"""Handler integration tests for the S3 pre-signed URL Lambda.

Tests cover the full lambda_handler flow using moto-mocked AWS services.
No live AWS calls are made.

Requirements: 1.1-1.6, 2.2, 3.2, 3.4, 4.2, 5.1, 6.3, 6.4, 7.1, 7.4,
              8.1, 11.1, 13.2-13.7
"""

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from conftest import make_apigw_event, register_client, store_signing_credentials
from s3_signed_url_lambda.lambda_function import lambda_handler

# ---------------------------------------------------------------------------
# 1. Valid request returns 200 with url and expires_in
#    (Req 13.2, 1.1, 7.1, 8.1)
# ---------------------------------------------------------------------------


def test_valid_request(
    lambda_context: Any,
    ssm_client: Any,
    secrets_client: Any,
) -> None:
    """A valid request with registered client returns 200."""
    register_client(ssm_client)
    store_signing_credentials(secrets_client)

    event = make_apigw_event()
    response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 200
    assert response["headers"]["Content-Type"] == "application/json"
    body = json.loads(response["body"])
    assert "url" in body
    assert isinstance(body["url"], str)
    assert len(body["url"]) > 0
    assert "expires_in" in body
    assert isinstance(body["expires_in"], int)


# ---------------------------------------------------------------------------
# 2. Missing bucket parameter returns 400 (Req 13.5, 1.2)
# ---------------------------------------------------------------------------


def test_missing_bucket(lambda_context: Any) -> None:
    """Request without bucket query param returns 400."""
    event = make_apigw_event(bucket=None)
    response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body
    assert "bucket" in body["error"].lower()


# ---------------------------------------------------------------------------
# 3. Missing key parameter returns 400 (Req 13.5, 1.3)
# ---------------------------------------------------------------------------


def test_missing_key(lambda_context: Any) -> None:
    """Request without key query param returns 400."""
    event = make_apigw_event(key=None)
    response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body
    assert "key" in body["error"].lower()


# ---------------------------------------------------------------------------
# 4. Empty bucket or key returns 400 (Req 1.4)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("bucket", "key"),
    [
        ("", "path/to/object.csv"),
        ("test-bucket", ""),
    ],
    ids=["empty-bucket", "empty-key"],
)
def test_empty_bucket_or_key(
    bucket: str,
    key: str,
    lambda_context: Any,
) -> None:
    """Request with empty bucket or key returns 400."""
    event = make_apigw_event(bucket=bucket, key=key)
    response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body


# ---------------------------------------------------------------------------
# 5. Invalid expiration returns 400 (Req 1.5)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expiration",
    ["abc", "3.14", "0", "-5"],
    ids=["non-integer", "float", "zero", "negative"],
)
def test_invalid_expiration(
    expiration: str,
    lambda_context: Any,
) -> None:
    """Request with non-positive-integer expiration returns 400."""
    event = make_apigw_event(expiration=expiration)
    response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body
    assert "expiration" in body["error"].lower()


# ---------------------------------------------------------------------------
# 6. Missing client identity returns 403 (Req 2.2)
# ---------------------------------------------------------------------------


def test_missing_client_identity(lambda_context: Any) -> None:
    """Request without apiKeyId in requestContext returns 403."""
    event = make_apigw_event(api_key_id=None)
    response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 403
    body = json.loads(response["body"])
    assert "error" in body


# ---------------------------------------------------------------------------
# 7. Unknown client_id returns 403 (Req 13.3, 3.2)
# ---------------------------------------------------------------------------


def test_unknown_client_id(
    lambda_context: Any,
    ssm_client: Any,
    secrets_client: Any,
) -> None:
    """Request with unregistered client_id returns 403."""
    register_client(ssm_client, client_id="other-client")
    store_signing_credentials(secrets_client)

    event = make_apigw_event(api_key_id="unknown-client")
    response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 403
    body = json.loads(response["body"])
    assert "error" in body


# ---------------------------------------------------------------------------
# 8. Unauthorized bucket returns 403 (Req 13.4, 4.2)
# ---------------------------------------------------------------------------


def test_unauthorized_bucket(
    lambda_context: Any,
    ssm_client: Any,
    secrets_client: Any,
) -> None:
    """Request for a bucket not in allowed_buckets returns 403."""
    register_client(ssm_client, allowed_buckets=["allowed-bucket"])
    store_signing_credentials(secrets_client)

    event = make_apigw_event(bucket="forbidden-bucket")
    response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 403
    body = json.loads(response["body"])
    assert "error" in body


# ---------------------------------------------------------------------------
# 9. SSM unreachable returns 500 (Req 3.4)
# ---------------------------------------------------------------------------


def test_ssm_unreachable(
    lambda_context: Any,
    ssm_client: Any,
    secrets_client: Any,
) -> None:
    """When SSM raises a non-ParameterNotFound error, returns 500."""
    store_signing_credentials(secrets_client)

    event = make_apigw_event()

    ssm_error = ClientError(
        {
            "Error": {
                "Code": "InternalError",
                "Message": "Service unavailable",
            }
        },
        "GetParameter",
    )
    mock_ssm = MagicMock()
    mock_ssm.get_parameter.side_effect = ssm_error

    with patch(
        "s3_signed_url_lambda.lambda_function.boto3.client",
        side_effect=lambda svc, **kw: mock_ssm if svc == "ssm" else secrets_client,
    ):
        response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "error" in body


# ---------------------------------------------------------------------------
# 10. Secrets Manager unreachable returns 500 (Req 13.7, 6.3)
# ---------------------------------------------------------------------------


def test_secrets_manager_unreachable(
    lambda_context: Any,
    aws_mock: None,
) -> None:
    """When Secrets Manager is unreachable, handler returns 500."""
    event = make_apigw_event()

    sm_error = ClientError(
        {
            "Error": {
                "Code": "InternalError",
                "Message": "Service unavailable",
            }
        },
        "GetSecretValue",
    )
    mock_sm = MagicMock()
    mock_sm.get_secret_value.side_effect = sm_error

    with patch(
        "s3_signed_url_lambda.lambda_function.boto3.client",
        return_value=mock_sm,
    ):
        response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "error" in body


# ---------------------------------------------------------------------------
# 11. Malformed signing credentials returns 500 (Req 6.4)
# ---------------------------------------------------------------------------


def test_malformed_signing_credentials(
    lambda_context: Any,
    secrets_client: Any,
    ssm_client: Any,
) -> None:
    """Signing credentials missing required keys returns 500."""
    register_client(ssm_client)
    secrets_client.create_secret(
        Name="test/signing-creds",
        SecretString=json.dumps({"wrong_key": "value"}),
    )

    event = make_apigw_event()
    response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "error" in body


# ---------------------------------------------------------------------------
# 12. boto3 client error during signing returns 500 (Req 13.6, 7.4)
# ---------------------------------------------------------------------------


def test_signing_client_error(
    lambda_context: Any,
    ssm_client: Any,
    secrets_client: Any,
) -> None:
    """When generate_presigned_url raises ClientError, returns 500."""
    register_client(ssm_client)
    store_signing_credentials(secrets_client)

    event = make_apigw_event()

    s3_error = ClientError(
        {
            "Error": {
                "Code": "NoSuchBucket",
                "Message": "Bucket not found",
            }
        },
        "GeneratePresignedUrl",
    )
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.side_effect = s3_error

    with patch(
        "s3_signed_url_lambda.lambda_function._init_signing_client",
        return_value=mock_s3,
    ):
        response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "error" in body


# ---------------------------------------------------------------------------
# 13. Default expiration used when not provided (Req 1.6, 11.1)
# ---------------------------------------------------------------------------


def test_default_expiration(
    lambda_context: Any,
    ssm_client: Any,
    secrets_client: Any,
) -> None:
    """When no expiration is provided, the default from env var is used."""
    register_client(ssm_client, max_expiration=604800)
    store_signing_credentials(secrets_client)

    event = make_apigw_event(expiration=None)
    response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["expires_in"] == 604800


# ---------------------------------------------------------------------------
# 14. Expiration capped to client max (Req 5.1)
# ---------------------------------------------------------------------------


def test_expiration_capped_to_client_max(
    lambda_context: Any,
    ssm_client: Any,
    secrets_client: Any,
) -> None:
    """When requested expiration exceeds client max, it is capped."""
    client_max = 3600
    register_client(ssm_client, max_expiration=client_max)
    store_signing_credentials(secrets_client)

    event = make_apigw_event(expiration="86400")
    response = lambda_handler(event, lambda_context)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["expires_in"] == client_max
