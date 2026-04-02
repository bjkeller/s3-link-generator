python_sources(name="function")

python_aws_lambda_function(
    name="lambda",
    runtime="python3.11",
    handler="lambda_function.py:lambda_handler",
    include_requirements=False,
)

python_aws_lambda_layer(
    name="layer",
    runtime="python3.11",
    dependencies=[
        ":function",
        "//common/src/python/database:lib",
        "//:root#aws-lambda-powertools",
        "//:root#sqlalchemy",
        "//:root#pydantic",
        "//:root#pymysql"
    ],
    include_sources=False,
)