python_sources(name="function")

python_aws_lambda_function(
    name="lambda",
    runtime="python3.12",
    handler="lambda_function.py:lambda_handler",
    include_requirements=False,
)

python_aws_lambda_layer(
    name="layer",
    runtime="python3.12",
    dependencies=[":function", "//:root#aws-lambda-powertools"],
    include_sources=False,
)