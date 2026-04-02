"""Client registry backed by SSM Parameter Store."""

import json
from typing import Any

from botocore.exceptions import ClientError

from s3_signed_url_lambda.models import ClientConfig, ClientNotFoundError, RegistryError


class ClientRegistry:
    """Looks up client configurations from SSM Parameter Store."""

    def __init__(self, ssm_client: Any, prefix: str) -> None:
        """Initialize with an SSM client and the parameter prefix path."""
        self._ssm_client = ssm_client
        self._prefix = prefix

    def get_client_config(self, client_id: str) -> ClientConfig:
        """Fetch and parse client config from SSM.

        Raises ClientNotFoundError if parameter doesn't exist. Raises
        RegistryError if SSM is unreachable.
        """
        path = f"{self._prefix}/{client_id}"
        try:
            response = self._ssm_client.get_parameter(Name=path)
            value = response["Parameter"]["Value"]
            return ClientConfig.model_validate_json(value)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ParameterNotFound":
                raise ClientNotFoundError(
                    f"Client not registered: {client_id}"
                ) from exc
            raise RegistryError(
                f"SSM error looking up client {client_id}: {exc}"
            ) from exc
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            raise RegistryError(
                f"Invalid config for client {client_id}: {exc}"
            ) from exc
