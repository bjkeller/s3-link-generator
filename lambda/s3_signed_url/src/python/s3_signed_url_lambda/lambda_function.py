"""Lambda handler for S3 pre-signed URL generation.

Generates time-limited pre-signed S3 GET URLs for authorized app
clients. Uses long-term IAM user credentials from Secrets Manager for
signing, enabling URL expirations up to 7 days (604,800 seconds).
"""

import json
import os
from typing import Any

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from s3_signed_url_lambda.client_registry import ClientRegistry
from s3_signed_url_lambda.models import (
    AuthorizationError,
    ClientNotFoundError,
    PresignRequest,
    PresignResponse,
    RegistryError,
    ValidationError,
)

logger = Logger()

# --- Required environment variables (validated at import time) ---
_client_registry_prefix = os.environ.get("CLIENT_REGISTRY_PREFIX")
_signing_credentials_secret = os.environ.get("SIGNING_CREDENTIALS_SECRET")

if not _client_registry_prefix:
    logger.error("Missing required environment variable: CLIENT_REGISTRY_PREFIX")
    raise EnvironmentError(
        "Missing required environment variable: CLIENT_REGISTRY_PREFIX"
    )

if not _signing_credentials_secret:
    logger.error("Missing required environment variable: SIGNING_CREDENTIALS_SECRET")
    raise EnvironmentError(
        "Missing required environment variable: SIGNING_CREDENTIALS_SECRET"
    )

CLIENT_REGISTRY_PREFIX: str = _client_registry_prefix
SIGNING_CREDENTIALS_SECRET: str = _signing_credentials_secret

SYSTEM_MAX_EXPIRATION = 604800  # 7 days in seconds

# --- Module-level caching for warm-start reuse ---
_signing_credentials: dict[str, str] | None = None
_s3_signing_client: Any = None


def _init_signing_client() -> Any:
    """Retrieve signing credentials from Secrets Manager and create S3 client.

    Called once per cold start; the client is cached at module level for
    warm invocations.

    Returns:
        A boto3 S3 client configured with the IAM user signing credentials.

    Raises:
        RuntimeError: If the secret cannot be retrieved or is malformed.
    """
    global _signing_credentials, _s3_signing_client

    if _s3_signing_client is not None:
        return _s3_signing_client

    try:
        secrets_client = boto3.client("secretsmanager")
        response = secrets_client.get_secret_value(
            SecretId=SIGNING_CREDENTIALS_SECRET,
        )
        secret = json.loads(response["SecretString"])
    except (ClientError, json.JSONDecodeError, KeyError) as exc:
        logger.exception("Failed to retrieve signing credentials")
        raise RuntimeError("Failed to retrieve signing credentials") from exc

    access_key_id = secret.get("access_key_id")
    secret_access_key = secret.get("secret_access_key")

    if not access_key_id or not secret_access_key:
        logger.error("Signing credentials secret is missing required keys")
        raise RuntimeError("Signing credentials secret is missing required keys")

    _signing_credentials = {
        "access_key_id": access_key_id,
        "secret_access_key": secret_access_key,
    }
    _s3_signing_client = boto3.client(
        "s3",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    )
    return _s3_signing_client


def _parse_request(event: dict[str, Any]) -> PresignRequest:
    """Extract and validate query string parameters and client identity.

    Args:
        event: API Gateway proxy event.

    Returns:
        A validated PresignRequest.

    Raises:
        ValidationError: If required parameters are missing or invalid.
    """
    params = event.get("queryStringParameters") or {}

    bucket = params.get("bucket")
    if bucket is None:
        raise ValidationError("Missing required parameter: bucket")
    if not bucket:
        raise ValidationError("Invalid parameter: bucket must not be empty")

    key = params.get("key")
    if key is None:
        raise ValidationError("Missing required parameter: key")
    if not key:
        raise ValidationError("Invalid parameter: key must not be empty")

    expiration: int | None = None
    raw_expiration = params.get("expiration")
    if raw_expiration is not None:
        try:
            expiration = int(raw_expiration)
        except (ValueError, TypeError) as exc:
            raise ValidationError(
                "Invalid expiration: must be a positive integer"
            ) from exc
        if expiration <= 0:
            raise ValidationError("Invalid expiration: must be a positive integer")

    # Resolve client identity from API Gateway request context
    request_context = event.get("requestContext") or {}
    identity = request_context.get("identity") or {}
    client_id: str | None = identity.get("apiKeyId")

    if not client_id:
        raise AuthorizationError("Client identity could not be resolved")

    return PresignRequest(
        bucket=bucket,
        key=key,
        expiration=expiration,
        client_id=client_id,
    )


def _resolve_expiration(requested: int | None, client_max: int) -> int:
    """Resolve the effective expiration, capping to client and system limits.

    Args:
        requested: The expiration requested by the caller, or None for default.
        client_max: The client's configured maximum expiration.

    Returns:
        The resolved expiration in seconds.
    """
    default_expiration = int(
        os.environ.get("DEFAULT_EXPIRATION", str(SYSTEM_MAX_EXPIRATION))
    )
    effective = requested if requested is not None else default_expiration
    return min(effective, client_max, SYSTEM_MAX_EXPIRATION)


def _build_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Format an API Gateway proxy response with JSON body.

    Args:
        status_code: HTTP status code.
        body: Response body as a dict (will be JSON-serialized).

    Returns:
        API Gateway proxy response dict.
    """
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _error_response(status_code: int, message: str) -> dict[str, Any]:
    """Format an error response.

    Args:
        status_code: HTTP status code.
        message: Human-readable error message.

    Returns:
        API Gateway proxy response dict with error body.
    """
    return _build_response(status_code, {"error": message})


@logger.inject_lambda_context
def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda entry point — parse request, validate client, generate URL.

    Args:
        event: API Gateway proxy event.
        context: Lambda context.

    Returns:
        API Gateway proxy response.
    """
    try:
        request = _parse_request(event)
    except AuthorizationError as exc:
        logger.warning("Client identity resolution failed", error=str(exc))
        return _error_response(403, str(exc))
    except ValidationError as exc:
        logger.warning("Request validation failed", error=str(exc))
        return _error_response(400, str(exc))

    logger.info(
        "Processing presign request",
        bucket=request.bucket,
        key=request.key,
        expiration=request.expiration,
        client_id=request.client_id,
    )

    # Initialize signing client (cached after first cold-start call)
    try:
        s3_client = _init_signing_client()
    except RuntimeError:
        return _error_response(500, "Internal server error")

    # Look up client configuration from SSM
    try:
        ssm_client = boto3.client("ssm")
        registry = ClientRegistry(ssm_client=ssm_client, prefix=CLIENT_REGISTRY_PREFIX)
        client_config = registry.get_client_config(request.client_id)
    except ClientNotFoundError:
        logger.warning(
            "Client not registered",
            client_id=request.client_id,
        )
        return _error_response(403, f"Client not registered: {request.client_id}")
    except RegistryError:
        logger.exception("Registry lookup failed")
        return _error_response(500, "Internal server error")

    # Authorize bucket access
    if request.bucket not in client_config.allowed_buckets:
        logger.warning(
            "Client not authorized for bucket",
            client_id=request.client_id,
            bucket=request.bucket,
        )
        return _error_response(
            403, f"Client not authorized for bucket: {request.bucket}"
        )

    # Resolve expiration
    expires_in = _resolve_expiration(request.expiration, client_config.max_expiration)

    # Generate pre-signed URL
    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": request.bucket, "Key": request.key},
            ExpiresIn=expires_in,
        )
    except ClientError:
        logger.exception("Failed to generate presigned URL")
        return _error_response(500, "Internal server error")

    logger.info(
        "Presign request completed",
        status=200,
        expires_in=expires_in,
    )

    response_body = PresignResponse(url=url, expires_in=expires_in)
    return _build_response(200, response_body.model_dump())
