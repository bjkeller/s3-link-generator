"""Shared fixtures for CDK assertion tests."""

import zipfile
from pathlib import Path

import aws_cdk as cdk
import pytest
from aws_cdk import assertions
from stacks.presign_stack import PresignStack

# Paths the stack expects for Code.from_asset() calls (relative to cwd).
_ASSET_DIR = "dist/lambda.s3_signed_url.src.python.s3_signed_url_lambda"
_ASSET_ZIPS = ["powertools.zip", "layer.zip", "lambda.zip"]


@pytest.fixture(scope="module", autouse=True)
def _dummy_assets() -> None:
    """Create minimal zip files in the cwd so CDK synthesis succeeds."""
    asset_path = Path(_ASSET_DIR)
    asset_path.mkdir(parents=True, exist_ok=True)
    for name in _ASSET_ZIPS:
        zip_path = asset_path / name
        if not zip_path.exists():
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("placeholder.txt", "")


def _synth_template(environment: str) -> assertions.Template:
    """Synthesize the stack for the given environment and return a Template."""
    app = cdk.App()
    stack = PresignStack(
        app,
        f"PresignStack-{environment}",
        environment=environment,
        env=cdk.Environment(account="090173369068", region="us-west-2"),
    )
    return assertions.Template.from_stack(stack)


@pytest.fixture(scope="module")
def dev_template() -> assertions.Template:
    """Synthesized CloudFormation template for the dev environment."""
    return _synth_template("dev")


@pytest.fixture(scope="module")
def prod_template() -> assertions.Template:
    """Synthesized CloudFormation template for the prod environment."""
    return _synth_template("prod")
