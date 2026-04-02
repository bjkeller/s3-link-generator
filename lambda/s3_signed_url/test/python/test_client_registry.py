"""Tests for ClientRegistry — property-based and unit tests.

# Feature: s3-presign-lambda, Property 3: Client config round-trip
through SSM
"""

from unittest.mock import MagicMock

import boto3
import pytest
from botocore.exceptions import ClientError
from hypothesis import given, settings
from hypothesis.strategies import (
    characters,
    composite,
    integers,
    lists,
    text,
)
from moto import mock_aws
from s3_signed_url_lambda.client_registry import ClientRegistry
from s3_signed_url_lambda.models import ClientConfig, ClientNotFoundError, RegistryError

SSM_PREFIX = "/presign/clients"


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_id_alphabet = characters(whitelist_categories=("L", "N"))

client_ids = text(min_size=1, max_size=50, alphabet=_id_alphabet)

bucket_names = text(
    min_size=1,
    max_size=63,
    alphabet=characters(whitelist_categories=("L", "N")),
)

descriptions = text(min_size=1, max_size=200)


@composite
def client_configs(draw):
    """Generate a random valid ClientConfig."""
    cid = draw(client_ids)
    buckets = draw(lists(bucket_names, min_size=1, max_size=5))
    max_exp = draw(integers(min_value=1, max_value=604800))
    desc = draw(descriptions)
    return ClientConfig(
        client_id=cid,
        allowed_buckets=buckets,
        max_expiration=max_exp,
        description=desc,
    )


# ---------------------------------------------------------------------------
# Property-based test
# ---------------------------------------------------------------------------


class TestClientConfigRoundTrip:
    """Property 3: Client config round-trip through SSM.

    **Validates: Requirements 3.1**
    """

    @given(config=client_configs())
    @settings(max_examples=100, deadline=None)
    def test_round_trip(self, config: ClientConfig) -> None:
        """For any valid ClientConfig, storing as JSON in SSM and retrieving
        via the registry produces an equivalent ClientConfig."""
        with mock_aws():
            ssm = boto3.client("ssm", region_name="us-east-1")
            registry = ClientRegistry(ssm_client=ssm, prefix=SSM_PREFIX)

            # Store config as JSON parameter
            param_path = f"{SSM_PREFIX}/{config.client_id}"
            ssm.put_parameter(
                Name=param_path,
                Value=config.model_dump_json(),
                Type="String",
            )

            # Retrieve via registry
            result = registry.get_client_config(config.client_id)

            assert result == config


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestClientRegistryUnit:
    """Unit tests for ClientRegistry edge cases."""

    def test_unknown_client_raises_client_not_found(self) -> None:
        """Unknown client_id raises ClientNotFoundError."""
        with mock_aws():
            ssm = boto3.client("ssm", region_name="us-east-1")
            registry = ClientRegistry(ssm_client=ssm, prefix=SSM_PREFIX)

            with pytest.raises(ClientNotFoundError):
                registry.get_client_config("nonexistent-client")

    def test_ssm_unreachable_raises_registry_error(self) -> None:
        """SSM client error (non-ParameterNotFound) raises RegistryError."""
        ssm = MagicMock()
        ssm.get_parameter.side_effect = ClientError(
            error_response={
                "Error": {
                    "Code": "InternalError",
                    "Message": "Service unavailable",
                }
            },
            operation_name="GetParameter",
        )
        registry = ClientRegistry(ssm_client=ssm, prefix=SSM_PREFIX)

        with pytest.raises(RegistryError):
            registry.get_client_config("some-client")
