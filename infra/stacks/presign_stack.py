"""CDK stack for the S3 Pre-Signed URL Service."""

import aws_cdk as cdk
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from constructs import Construct


class PresignStack(cdk.Stack):
    """CDK stack for the S3 Pre-Signed URL Service."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        environment: str,
        **kwargs,
    ) -> None:
        """Initialize the stack.

        Args:
            scope: CDK app scope.
            construct_id: Stack ID.
            environment: Deployment environment ('dev' or 'prod').
        """
        super().__init__(scope, construct_id, **kwargs)
        self.deploy_environment = environment

        # --- VPC import and VPC endpoint ---
        vpc = ec2.Vpc.from_vpc_attributes(
            self,
            "NaccVPC",
            vpc_id="vpc-089e3a35afb9d5b93",
            availability_zones=["us-west-2a", "us-west-2b"],
            private_subnet_ids=[
                "subnet-0ad9370ddecc74240",
                "subnet-0ddaf0ed4e60d11cd",
            ],
            vpc_cidr_block="10.0.0.0/16",
        )

        self.vpce = ec2.InterfaceVpcEndpoint(
            self,
            "ApiGatewayEndpoint",
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointAwsService.APIGATEWAY,
            subnets=ec2.SubnetSelection(
                subnets=[
                    ec2.Subnet.from_subnet_id(
                        self, "Private1", "subnet-0ad9370ddecc74240"
                    ),
                    ec2.Subnet.from_subnet_id(
                        self, "Private2", "subnet-0ddaf0ed4e60d11cd"
                    ),
                ]
            ),
            private_dns_enabled=True,
        )

        # --- Lambda execution role with least-privilege policies ---
        self.execution_role = iam.Role(
            self,
            "PresignLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Execution role for the presign Lambda function",
        )

        # SSM Parameter Store read access for client registry
        self.execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter", "ssm:GetParametersByPath"],
                resources=[
                    f"arn:aws:ssm:us-west-2:090173369068:parameter/presign/{environment}/clients/*"
                ],
            )
        )

        # Secrets Manager read access for signing credentials
        self.execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:us-west-2:090173369068:secret:presign/{environment}/signing-credentials*"
                ],
            )
        )

        # CloudWatch Logs write permissions scoped to the Lambda log group
        log_group_arn = (
            f"arn:aws:logs:us-west-2:090173369068:log-group:"
            f"/aws/lambda/{environment}-presign-handler:*"
        )
        self.execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[log_group_arn],
            )
        )

        # X-Ray write permissions
        self.execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                ],
                resources=["*"],
            )
        )

        # --- Lambda layers ---
        powertools_layer = lambda_.LayerVersion(
            self,
            "PowertoolsLayer",
            code=lambda_.Code.from_asset(
                "dist/lambda.s3_signed_url.src.python.s3_signed_url_lambda/powertools.zip"
            ),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            compatible_architectures=[lambda_.Architecture.ARM_64],
            description="aws-lambda-powertools layer",
        )

        deps_layer = lambda_.LayerVersion(
            self,
            "DepsLayer",
            code=lambda_.Code.from_asset(
                "dist/lambda.s3_signed_url.src.python.s3_signed_url_lambda/layer.zip"
            ),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            compatible_architectures=[lambda_.Architecture.ARM_64],
            description="Python dependencies layer",
        )

        # --- Lambda function ---
        self.handler = lambda_.Function(
            self,
            "PresignHandler",
            function_name=f"{environment}-presign-handler",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            handler="s3_signed_url_lambda.lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                "dist/lambda.s3_signed_url.src.python.s3_signed_url_lambda/lambda.zip"
            ),
            memory_size=512,
            timeout=cdk.Duration.seconds(30),
            tracing=lambda_.Tracing.ACTIVE,
            layers=[powertools_layer, deps_layer],
            role=self.execution_role,
            environment={
                "CLIENT_REGISTRY_PREFIX": f"/presign/{environment}/clients",
                "SIGNING_CREDENTIALS_SECRET": (
                    f"presign/{environment}/signing-credentials"
                ),
                "DEFAULT_EXPIRATION": "604800",
                "ENVIRONMENT": environment,
            },
        )

        # --- CloudWatch log group with 90-day retention ---
        self.log_group = logs.LogGroup(
            self,
            "PresignLogGroup",
            log_group_name=f"/aws/lambda/{environment}-presign-handler",
            retention=logs.RetentionDays.THREE_MONTHS,
            removal_policy=cdk.RemovalPolicy.DESTROY,
        )

        # --- API Gateway REST API with resource policy ---
        resource_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    principals=[iam.AnyPrincipal()],
                    actions=["execute-api:Invoke"],
                    resources=["execute-api:/*"],
                    conditions={
                        "StringEquals": {
                            "aws:sourceVpce": self.vpce.vpc_endpoint_id,
                        }
                    },
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.DENY,
                    principals=[iam.AnyPrincipal()],
                    actions=["execute-api:Invoke"],
                    resources=["execute-api:/*"],
                    conditions={
                        "StringNotEquals": {
                            "aws:sourceVpce": self.vpce.vpc_endpoint_id,
                        }
                    },
                ),
            ]
        )

        self.api = apigateway.RestApi(
            self,
            "PresignApi",
            rest_api_name=f"{environment}-presign-api",
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL],
            ),
            policy=resource_policy,
            deploy_options=apigateway.StageOptions(stage_name=environment),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=["GET", "OPTIONS"],
                allow_headers=["Content-Type", "x-api-key"],
            ),
        )

        # --- /presign resource with GET method and request validation ---
        validator = apigateway.RequestValidator(
            self,
            "QueryParamValidator",
            rest_api=self.api,
            validate_request_parameters=True,
        )

        presign_resource = self.api.root.add_resource("presign")
        presign_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.handler, proxy=True),
            api_key_required=True,
            request_parameters={
                "method.request.querystring.bucket": True,
                "method.request.querystring.key": True,
                "method.request.querystring.expiration": False,
            },
            request_validator=validator,
        )

        # --- API key and usage plan ---
        self.api_key = apigateway.ApiKey(
            self,
            "PresignApiKey",
            api_key_name=f"{environment}-presign-api-key",
            description=f"API key for {environment} presign service",
        )

        usage_plan = apigateway.UsagePlan(
            self,
            "PresignUsagePlan",
            name=f"{environment}-presign-usage-plan",
            throttle=apigateway.ThrottleSettings(
                rate_limit=10,
                burst_limit=20,
            ),
            quota=apigateway.QuotaSettings(
                limit=10000,
                period=apigateway.Period.DAY,
            ),
            api_stages=[
                apigateway.UsagePlanPerApiStage(
                    api=self.api,
                    stage=self.api.deployment_stage,
                )
            ],
        )

        usage_plan.add_api_key(self.api_key)

        # --- CloudWatch alarm on API Gateway 5xx errors ---
        cloudwatch.Alarm(
            self,
            "Api5xxAlarm",
            alarm_name=f"{environment}-presign-api-5xx-alarm",
            metric=self.api.metric_server_error(
                statistic="Sum",
                period=cdk.Duration.minutes(5),
            ),
            threshold=5,
            evaluation_periods=1,
            alarm_description=(
                f"Alarm when {environment} presign API 5xx errors exceed threshold"
            ),
        )

        # --- Stack outputs ---
        cdk.CfnOutput(
            self,
            "ApiUrl",
            value=self.api.url,
            description="API Gateway invoke URL",
            export_name=f"{environment}-presign-api-url",
        )

        cdk.CfnOutput(
            self,
            "ApiKeyId",
            value=self.api_key.key_id,
            description="API key ID",
            export_name=f"{environment}-presign-api-key-id",
        )
