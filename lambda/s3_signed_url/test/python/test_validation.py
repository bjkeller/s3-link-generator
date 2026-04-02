"""Property-based tests for request validation and authorization."""

import json
import os
from typing import Any
from unittest.mock import MagicMock

import boto3
from conftest import (
    make_apigw_event,
    register_client,
    store_signing_credentials,
)
from hypothesis import given, settings
from hypothesis.strategies import (
    characters,
    composite,
    integers,
    lists,
    none,
    one_of,
    sampled_from,
    text,
)
from moto import mock_aws
from s3_signed_url_lambda.lambda_function import lambda_handler

SYSTEM_MAX_EXPIRATION = 604_800

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_bucket_alphabet = characters(whitelist_categories=("L", "N"))

bucket_names = text(min_size=1, max_size=63, alphabet=_bucket_alphabet)

allowed_buckets_lists = lists(
    text(min_size=1, max_size=63, alphabet=_bucket_alphabet),
    min_size=1,
    max_size=10,
)


@composite
def bucket_in_allowlist(draw):
    """Generate an allowed_buckets list and a bucket in it."""
    buckets = draw(allowed_buckets_lists)
    bucket = draw(sampled_from(buckets))
    return buckets, bucket


# Feature: s3-presign-lambda, Property 4:
# Bucket authorization matches allowlist membership
class TestBucketAuthorizationMatchesAllowlist:
    """Property 4: Bucket authorization matches allowlist.

    **Validates: Requirements 4.1, 4.2, 4.3**
    """

    @given(data=bucket_in_allowlist())
    @settings(max_examples=100)
    def test_bucket_in_allowlist_is_authorized(
        self, data: tuple[list[str], str]
    ) -> None:
        """A bucket drawn from allowed_buckets is authorized."""
        allowed_buckets, bucket = data
        assert bucket in allowed_buckets

    @given(
        allowed_buckets=allowed_buckets_lists,
        bucket=bucket_names,
    )
    @settings(max_examples=100)
    def test_authorization_iff_in_allowlist(
        self, allowed_buckets: list[str], bucket: str
    ) -> None:
        """Authorized iff bucket in list."""
        authorized = bucket in allowed_buckets
        denied = bucket not in allowed_buckets
        assert authorized != denied
        assert authorized == (bucket in allowed_buckets)


# Feature: s3-presign-lambda, Property 5:
# Expiration resolution is capped correctly
class TestExpirationResolutionCapping:
    """Property 5: Resolved expiration equals
    min(requested_or_default, client_max, 604800).

    Tests through the public lambda_handler interface by
    observing the ``expires_in`` field in the 200 response.

    **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 1.6**
    """

    @given(
        requested=one_of(
            none(),
            integers(min_value=1, max_value=1_000_000),
        ),
        client_max=integers(
            min_value=1, max_value=1_000_000,
        ),
        default_exp=integers(
            min_value=1, max_value=1_000_000,
        ),
    )
    @settings(max_examples=100, deadline=None)
    def test_expires_in_equals_min(
        self,
        requested: int | None,
        client_max: int,
        default_exp: int,
    ) -> None:
        """expires_in == min(req_or_default, client_max, 604800)."""
        import s3_signed_url_lambda.lambda_function as mod

        mod._signing_credentials = None  # noqa: SLF001
        mod._s3_signing_client = None  # noqa: SLF001

        ctx = MagicMock()
        ctx.aws_request_id = "test-request-id"
        ctx.function_name = "test"

        os.environ["DEFAULT_EXPIRATION"] = str(default_exp)
        try:
            with mock_aws():
                ssm = boto3.client(
                    "ssm", region_name="us-east-1",
                )
                sm = boto3.client(
                    "secretsmanager",
                    region_name="us-east-1",
                )
                register_client(
                    ssm, max_expiration=client_max,
                )
                store_signing_credentials(sm)

                exp_str = (
                    str(requested) if requested is not None
                    else None
                )
                event = make_apigw_event(expiration=exp_str)
                resp = lambda_handler(event, ctx)

            assert resp["statusCode"] == 200
            body = json.loads(resp["body"])

            effective = (
                requested if requested is not None
                else default_exp
            )
            expected = min(
                effective,
                client_max,
                SYSTEM_MAX_EXPIRATION,
            )
            assert body["expires_in"] == expected
        finally:
            os.environ.pop("DEFAULT_EXPIRATION", None)
            mod._signing_credentials = None  # noqa: SLF001
            mod._s3_signing_client = None  # noqa: SLF001
