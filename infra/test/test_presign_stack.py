"""CDK assertion tests for the PresignStack."""

from aws_cdk import assertions

# ---------------------------------------------------------------------------
# 8.2 — API Gateway configuration
# ---------------------------------------------------------------------------


def test_rest_api_exists_with_regional_endpoint(dev_template: assertions.Template):
    """Req 2.1, 2.2: REST API with regional endpoint."""
    dev_template.has_resource_properties(
        "AWS::ApiGateway::RestApi",
        {
            "EndpointConfiguration": {"Types": ["REGIONAL"]},
        },
    )


def test_get_method_with_proxy_integration(dev_template: assertions.Template):
    """Req 2.1, 2.5: GET method on /presign with Lambda proxy integration."""
    dev_template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "HttpMethod": "GET",
            "Integration": {
                "Type": "AWS_PROXY",
            },
        },
    )


def test_request_validator_validates_query_params(
    dev_template: assertions.Template,
):
    """Req 13.1: Request validator validates query string parameters."""
    dev_template.has_resource_properties(
        "AWS::ApiGateway::RequestValidator",
        {
            "ValidateRequestParameters": True,
        },
    )


def test_required_query_params(dev_template: assertions.Template):
    """Req 2.3, 2.4, 13.2, 13.3: bucket (required), key (required), expiration
    (optional)."""
    dev_template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "HttpMethod": "GET",
            "RequestParameters": {
                "method.request.querystring.bucket": True,
                "method.request.querystring.key": True,
                "method.request.querystring.expiration": False,
            },
        },
    )


def test_cors_configuration(dev_template: assertions.Template):
    """Req 3.1, 3.2, 3.3: CORS allows *, headers, and methods."""
    # CORS is implemented via an OPTIONS method on the /presign resource.
    dev_template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "HttpMethod": "OPTIONS",
            "Integration": {
                "IntegrationResponses": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "ResponseParameters": {
                                    (
                                        "method.response.header"
                                        ".Access-Control-Allow-Headers"
                                    ): "'Content-Type,x-api-key'",
                                    (
                                        "method.response.header"
                                        ".Access-Control-Allow-Origin"
                                    ): "'*'",
                                    (
                                        "method.response.header"
                                        ".Access-Control-Allow-Methods"
                                    ): assertions.Match.string_like_regexp("GET"),
                                },
                            }
                        )
                    ]
                ),
            },
        },
    )


def test_api_key_required_on_get_method(dev_template: assertions.Template):
    """Req 4.1: GET method requires API key."""
    dev_template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "HttpMethod": "GET",
            "ApiKeyRequired": True,
        },
    )


def test_api_key_resource_exists(dev_template: assertions.Template):
    """Req 4.2: At least one API key resource exists."""
    dev_template.resource_count_is("AWS::ApiGateway::ApiKey", 1)


def test_usage_plan_with_rate_limits_and_quota(dev_template: assertions.Template):
    """Req 4.3, 4.4: Usage plan with throttle and quota settings."""
    dev_template.has_resource_properties(
        "AWS::ApiGateway::UsagePlan",
        {
            "Throttle": {
                "RateLimit": 10,
                "BurstLimit": 20,
            },
            "Quota": {
                "Limit": 10000,
                "Period": "DAY",
            },
        },
    )


# ---------------------------------------------------------------------------
# 8.3 — VPC endpoint and resource policy
# ---------------------------------------------------------------------------


def test_vpc_endpoint_for_execute_api(dev_template: assertions.Template):
    """Req 5.1: VPC endpoint for execute-api service."""
    dev_template.has_resource_properties(
        "AWS::EC2::VPCEndpoint",
        {
            "ServiceName": "com.amazonaws.us-west-2.execute-api",
            "VpcEndpointType": "Interface",
        },
    )


def test_vpc_endpoint_in_private_subnets(dev_template: assertions.Template):
    """Req 5.2: VPC endpoint placed in private subnets."""
    dev_template.has_resource_properties(
        "AWS::EC2::VPCEndpoint",
        {
            "SubnetIds": [
                "subnet-0ad9370ddecc74240",
                "subnet-0ddaf0ed4e60d11cd",
            ],
        },
    )


def test_vpc_endpoint_private_dns_enabled(dev_template: assertions.Template):
    """Req 5.3: VPC endpoint has private DNS enabled."""
    dev_template.has_resource_properties(
        "AWS::EC2::VPCEndpoint",
        {
            "PrivateDnsEnabled": True,
        },
    )


def test_resource_policy_allows_from_vpc_endpoint(
    dev_template: assertions.Template,
):
    """Req 5.4: Resource policy allows requests from VPC endpoint."""
    template_json = dev_template.to_json()
    rest_apis = {
        k: v
        for k, v in template_json["Resources"].items()
        if v["Type"] == "AWS::ApiGateway::RestApi"
    }
    assert len(rest_apis) == 1
    api_resource = next(iter(rest_apis.values()))
    policy = api_resource["Properties"]["Policy"]
    statements = policy["Statement"]

    allow_stmts = [s for s in statements if s["Effect"] == "Allow"]
    assert len(allow_stmts) >= 1
    allow_stmt = allow_stmts[0]
    assert allow_stmt["Action"] == "execute-api:Invoke"
    assert "aws:sourceVpce" in str(allow_stmt["Condition"])


def test_resource_policy_denies_non_vpc_endpoint(
    dev_template: assertions.Template,
):
    """Req 5.5: Resource policy denies requests not from VPC endpoint."""
    template_json = dev_template.to_json()
    rest_apis = {
        k: v
        for k, v in template_json["Resources"].items()
        if v["Type"] == "AWS::ApiGateway::RestApi"
    }
    api_resource = next(iter(rest_apis.values()))
    policy = api_resource["Properties"]["Policy"]
    statements = policy["Statement"]

    deny_stmts = [s for s in statements if s["Effect"] == "Deny"]
    assert len(deny_stmts) >= 1
    deny_stmt = deny_stmts[0]
    assert deny_stmt["Action"] == "execute-api:Invoke"
    condition = deny_stmt["Condition"]
    assert "StringNotEquals" in condition
    assert "aws:sourceVpce" in str(condition["StringNotEquals"])


# ---------------------------------------------------------------------------
# 8.4 — Lambda function and IAM role
# ---------------------------------------------------------------------------


def test_lambda_runtime_python312(dev_template: assertions.Template):
    """Req 6.1: Lambda uses python3.12 runtime."""
    dev_template.has_resource_properties(
        "AWS::Lambda::Function",
        {"Runtime": "python3.12"},
    )


def test_lambda_architecture_arm64(dev_template: assertions.Template):
    """Req 6.2: Lambda uses arm64 architecture."""
    dev_template.has_resource_properties(
        "AWS::Lambda::Function",
        {"Architectures": ["arm64"]},
    )


def test_lambda_memory_512mb(dev_template: assertions.Template):
    """Req 6.3: Lambda has 512 MB memory."""
    dev_template.has_resource_properties(
        "AWS::Lambda::Function",
        {"MemorySize": 512},
    )


def test_lambda_timeout_30s(dev_template: assertions.Template):
    """Req 6.4: Lambda timeout is 30 seconds."""
    dev_template.has_resource_properties(
        "AWS::Lambda::Function",
        {"Timeout": 30},
    )


def test_lambda_xray_active_tracing(dev_template: assertions.Template):
    """Req 6.5: Lambda has X-Ray active tracing enabled."""
    dev_template.has_resource_properties(
        "AWS::Lambda::Function",
        {"TracingConfig": {"Mode": "Active"}},
    )


def test_lambda_has_two_layers(dev_template: assertions.Template):
    """Req 6.7: Lambda has 2 layers (powertools + deps)."""
    template_json = dev_template.to_json()
    functions = [
        v
        for v in template_json["Resources"].values()
        if v["Type"] == "AWS::Lambda::Function"
    ]
    assert len(functions) == 1
    layers = functions[0]["Properties"]["Layers"]
    assert len(layers) == 2


def test_lambda_env_vars(dev_template: assertions.Template):
    """Req 7.1, 7.2, 7.3, 7.4: Lambda has all 4 environment variables."""
    dev_template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Environment": {
                "Variables": {
                    "CLIENT_REGISTRY_PREFIX": "/presign/dev/clients",
                    "SIGNING_CREDENTIALS_SECRET": "presign/dev/signing-credentials",
                    "DEFAULT_EXPIRATION": "604800",
                    "ENVIRONMENT": "dev",
                }
            }
        },
    )


def test_dedicated_iam_role_exists(dev_template: assertions.Template):
    """Req 8.1: A dedicated IAM role exists for the Lambda."""
    dev_template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Principal": {"Service": "lambda.amazonaws.com"},
                            }
                        )
                    ]
                ),
            },
        },
    )


def test_role_has_ssm_read_permissions(dev_template: assertions.Template):
    """Req 8.2: Execution role grants SSM read access."""
    dev_template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Action": [
                                    "ssm:GetParameter",
                                    "ssm:GetParametersByPath",
                                ],
                                "Effect": "Allow",
                            }
                        )
                    ]
                ),
            },
        },
    )


def test_role_has_secrets_manager_read(dev_template: assertions.Template):
    """Req 8.3: Execution role grants Secrets Manager read access."""
    dev_template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Action": "secretsmanager:GetSecretValue",
                                "Effect": "Allow",
                            }
                        )
                    ]
                ),
            },
        },
    )


def test_role_has_cloudwatch_logs_write(dev_template: assertions.Template):
    """Req 8.4: Execution role grants CloudWatch Logs write permissions."""
    dev_template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Action": [
                                    "logs:CreateLogGroup",
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents",
                                ],
                                "Effect": "Allow",
                            }
                        )
                    ]
                ),
            },
        },
    )


def test_role_has_xray_write(dev_template: assertions.Template):
    """Req 8.5: Execution role grants X-Ray write permissions."""
    dev_template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Action": [
                                    "xray:PutTraceSegments",
                                    "xray:PutTelemetryRecords",
                                ],
                                "Effect": "Allow",
                            }
                        )
                    ]
                ),
            },
        },
    )


def test_no_s3_permissions_on_execution_role(dev_template: assertions.Template):
    """Property 2 / Req 8.6: Execution role must NOT grant any s3:* actions."""
    template_json = dev_template.to_json()
    policies = [
        v
        for v in template_json["Resources"].values()
        if v["Type"] == "AWS::IAM::Policy"
    ]
    for policy in policies:
        statements = policy["Properties"]["PolicyDocument"]["Statement"]
        for stmt in statements:
            actions = stmt.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]
            for action in actions:
                assert not action.lower().startswith("s3:"), (
                    f"Execution role must not have S3 permissions, found: {action}"
                )


# ---------------------------------------------------------------------------
# 8.5 — CloudWatch, outputs, and environment parameterization
# ---------------------------------------------------------------------------


def test_log_group_with_90_day_retention(dev_template: assertions.Template):
    """Req 9.1, 9.2: Log group with 90-day retention."""
    dev_template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {"RetentionInDays": 90},
    )


def test_cloudwatch_alarm_on_5xx_errors(dev_template: assertions.Template):
    """Req 10.1, 10.2, 10.3: Alarm on 5XXError with Sum statistic and 300s
    period."""
    dev_template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "MetricName": "5XXError",
            "Statistic": "Sum",
            "Period": 300,
        },
    )


def test_stack_output_api_url(dev_template: assertions.Template):
    """Req 11.1: Stack exports API Gateway invoke URL."""
    template_json = dev_template.to_json()
    outputs = template_json.get("Outputs", {})
    api_url_outputs = [
        v
        for v in outputs.values()
        if v.get("Export", {}).get("Name") == "dev-presign-api-url"
    ]
    assert len(api_url_outputs) == 1, "Expected one API URL output with dev export name"


def test_stack_output_api_key_id(dev_template: assertions.Template):
    """Req 11.2: Stack exports API key ID."""
    template_json = dev_template.to_json()
    outputs = template_json.get("Outputs", {})
    api_key_outputs = [
        v
        for v in outputs.values()
        if v.get("Export", {}).get("Name") == "dev-presign-api-key-id"
    ]
    assert len(api_key_outputs) == 1, (
        "Expected one API key ID output with dev export name"
    )


def test_environment_parameterization_lambda_env_var(
    dev_template: assertions.Template,
    prod_template: assertions.Template,
):
    """Property 1: Lambda ENVIRONMENT env var matches the environment value."""
    dev_template.has_resource_properties(
        "AWS::Lambda::Function",
        {"Environment": {"Variables": {"ENVIRONMENT": "dev"}}},
    )
    prod_template.has_resource_properties(
        "AWS::Lambda::Function",
        {"Environment": {"Variables": {"ENVIRONMENT": "prod"}}},
    )


def test_environment_parameterization_stage_name(
    dev_template: assertions.Template,
    prod_template: assertions.Template,
):
    """Property 1: API Gateway stage name matches the environment value."""
    dev_template.has_resource_properties(
        "AWS::ApiGateway::Stage",
        {"StageName": "dev"},
    )
    prod_template.has_resource_properties(
        "AWS::ApiGateway::Stage",
        {"StageName": "prod"},
    )


def test_environment_parameterization_output_export_names(
    dev_template: assertions.Template,
    prod_template: assertions.Template,
):
    """Property 1: Stack output export names contain the environment value."""
    dev_json = dev_template.to_json()
    prod_json = prod_template.to_json()

    dev_exports = {
        v.get("Export", {}).get("Name")
        for v in dev_json.get("Outputs", {}).values()
        if v.get("Export")
    }
    prod_exports = {
        v.get("Export", {}).get("Name")
        for v in prod_json.get("Outputs", {}).values()
        if v.get("Export")
    }

    # Dev exports should contain "dev", prod exports should contain "prod"
    assert all("dev" in name for name in dev_exports), f"Dev exports: {dev_exports}"
    assert all("prod" in name for name in prod_exports), f"Prod exports: {prod_exports}"

    # They should be different
    assert dev_exports != prod_exports, "Dev and prod export names must differ"
