"""Pydantic models and custom exceptions for the S3 pre-signed URL Lambda."""

from pydantic import BaseModel


class PresignRequest(BaseModel):
    """Parsed and validated request parameters."""

    bucket: str
    key: str
    expiration: int | None = None
    client_id: str


class ClientConfig(BaseModel):
    """Client configuration from the registry."""

    client_id: str
    allowed_buckets: list[str]
    max_expiration: int
    description: str


class PresignResponse(BaseModel):
    """Successful response payload."""

    url: str
    expires_in: int


class ClientNotFoundError(Exception):
    """Raised when client_id is not found in the registry."""


class RegistryError(Exception):
    """Raised when SSM Parameter Store is unreachable or returns an error."""


class ValidationError(Exception):
    """Raised when request parameters fail validation."""


class AuthorizationError(Exception):
    """Raised when client identity cannot be resolved."""
