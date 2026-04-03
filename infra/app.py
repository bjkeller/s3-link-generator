"""CDK application entry point for the S3 Pre-Sign Service."""

import aws_cdk as cdk

from stacks.presign_stack import PresignStack

app = cdk.App()
environment = app.node.try_get_context("environment") or "dev"

PresignStack(
    app,
    f"PresignStack-{environment}",
    environment=environment,
    env=cdk.Environment(account="090173369068", region="us-west-2"),
)

app.synth()
