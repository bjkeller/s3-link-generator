# Implementation Plan: S3 Pre-Sign API — CDK Infrastructure

## Overview

Implement the AWS CDK stack that provisions the API Gateway, Lambda function resource, VPC endpoint, IAM roles, CloudWatch monitoring, and all supporting infrastructure for the S3 Pre-Signed URL Service. The Lambda function code already exists at `lambda/s3_signed_url/`; this stack wires it up. All code is Python, using `aws-cdk-lib` constructs.

## Tasks

- [x] 1. Set up CDK project structure
  - [x] 1.1 Create `infra/` directory with `__init__.py`, `app.py`, `cdk.json`, and `requirements.txt`
    - Create `infra/app.py` as the CDK app entry point that reads `environment` from context (defaulting to `"dev"`) and instantiates `PresignStack`
    - Create `infra/cdk.json` with `"app": "python3 app.py"` and required CDK context flags
    - Create `infra/requirements.txt` listing `aws-cdk-lib>=2.150.0` and `constructs>=10.0.0`
    - _Requirements: 1.1, 1.2, 1.3, 12.1, 12.3, 12.4_

  - [x] 1.2 Create `infra/stacks/__init__.py` and `infra/stacks/presign_stack.py` with empty `PresignStack` class
    - Define `PresignStack(cdk.Stack)` with `environment: str` parameter
    - The constructor should accept `environment` and store it as an instance attribute
    - _Requirements: 1.4, 12.2_

- [x] 2. Implement VPC import and VPC endpoint
  - [x] 2.1 Import existing VPC and create interface VPC endpoint for `execute-api`
    - Use `ec2.Vpc.from_lookup()` with `vpc_id="vpc-089e3a35afb9d5b93"`
    - Create `ec2.InterfaceVpcEndpoint` for `APIGATEWAY` service in private subnets (`subnet-0ad9370ddecc74240`, `subnet-0ddaf0ed4e60d11cd`)
    - Enable private DNS on the endpoint
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 3. Implement Lambda execution role with least-privilege IAM policies
  - [x] 3.1 Create dedicated IAM role and attach policy statements
    - Create `iam.Role` with Lambda service principal
    - Grant `ssm:GetParameter` and `ssm:GetParametersByPath` scoped to `arn:aws:ssm:us-west-2:090173369068:parameter/presign/{env}/clients/*`
    - Grant `secretsmanager:GetSecretValue` scoped to `arn:aws:secretsmanager:us-west-2:090173369068:secret:presign/{env}/signing-credentials*`
    - Grant CloudWatch Logs write permissions (`logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`) scoped to the Lambda log group ARN
    - Grant X-Ray write permissions (`xray:PutTraceSegments`, `xray:PutTelemetryRecords`)
    - Do NOT grant any `s3:*` permissions
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 4. Implement Lambda function with layers and environment variables
  - [x] 4.1 Create Lambda layers and function resource
    - Create `lambda_.LayerVersion` for powertools and deps layers, each referencing Pants-produced zip artifacts via `Code.from_asset()`
    - Create `lambda_.Function` with: `python3.12` runtime, `arm64` architecture, 512 MB memory, 30s timeout, active X-Ray tracing
    - Attach both layers and the dedicated execution role
    - Set environment variables: `CLIENT_REGISTRY_PREFIX`, `SIGNING_CREDENTIALS_SECRET`, `DEFAULT_EXPIRATION`, `ENVIRONMENT`
    - Reference the Pants-produced function zip artifact via `Code.from_asset()`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.1, 7.2, 7.3, 7.4_

  - [x] 4.2 Create CloudWatch log group with 90-day retention
    - Create `logs.LogGroup` for the Lambda function with `retention_days=90`
    - _Requirements: 9.1, 9.2_

- [x] 5. Implement API Gateway with resource policy, CORS, request validation, and API key auth
  - [x] 5.1 Create REST API with resource policy restricting to VPC endpoint
    - Build `iam.PolicyDocument` with ALLOW from VPC endpoint + DENY from non-VPC-endpoint
    - Create `apigateway.RestApi` with regional endpoint, resource policy, and stage named after `environment`
    - Enable CORS: allow origins `*`, methods `GET, OPTIONS`, headers `Content-Type, x-api-key`
    - _Requirements: 2.2, 2.6, 3.1, 3.2, 3.3, 5.4, 5.5, 5.6_

  - [x] 5.2 Add `/presign` resource with GET method, request validator, and Lambda proxy integration
    - Create `apigateway.RequestValidator` with `validate_request_parameters=True`
    - Add `/presign` resource and GET method with `api_key_required=True`
    - Configure required query params: `bucket` (true), `key` (true), `expiration` (false)
    - Use `apigateway.LambdaIntegration` with `proxy=True`
    - _Requirements: 2.1, 2.3, 2.4, 2.5, 4.1, 13.1, 13.2, 13.3, 13.4_

  - [x] 5.3 Create API key and usage plan
    - Create `apigateway.ApiKey` for the initial app client
    - Create `apigateway.UsagePlan` with configurable rate limits and quota, associated with the API stage
    - Add the API key to the usage plan
    - _Requirements: 4.2, 4.3, 4.4_

- [x] 6. Implement CloudWatch alarm and stack outputs
  - [x] 6.1 Create CloudWatch alarm on API Gateway 5xx errors
    - Create `cloudwatch.Alarm` monitoring the `5XXError` metric with `Sum` statistic, 5-minute period
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 6.2 Add stack outputs for API URL and API key ID
    - Export API Gateway invoke URL with environment-prefixed export name
    - Export API key ID with environment-prefixed export name
    - _Requirements: 11.1, 11.2, 11.3_

- [x] 7. Checkpoint — Verify stack synthesizes
  - Ensure the stack synthesizes without errors (`cdk synth`), ask the user if questions arise.

- [x] 8. Implement CDK assertion tests
  - [x] 8.1 Create test scaffolding: `infra/tests/__init__.py`, `infra/tests/conftest.py`
    - Create `dev_template` and `prod_template` pytest fixtures that synthesize the stack and return `assertions.Template` objects
    - _Requirements: 12.1, 12.2_

  - [x] 8.2 Write CDK assertion tests for API Gateway configuration
    - Test REST API exists with regional endpoint (Req 2.1, 2.2)
    - Test GET method on `/presign` with proxy integration (Req 2.1, 2.5)
    - Test request validator validates query params (Req 13.1)
    - Test required params: bucket (true), key (true), expiration (false) (Req 2.3, 2.4, 13.2, 13.3)
    - Test CORS: allow origins `*`, headers, methods (Req 3.1, 3.2, 3.3)
    - Test API key required on GET method (Req 4.1)
    - Test API key resource exists (Req 4.2)
    - Test usage plan with rate limits and quota (Req 4.3, 4.4)

  - [x] 8.3 Write CDK assertion tests for VPC endpoint and resource policy
    - Test VPC endpoint for execute-api service (Req 5.1)
    - Test VPC endpoint in private subnets (Req 5.2)
    - Test VPC endpoint private DNS enabled (Req 5.3)
    - Test resource policy allows from VPC endpoint (Req 5.4)
    - Test resource policy denies non-VPC-endpoint (Req 5.5)

  - [x] 8.4 Write CDK assertion tests for Lambda function and IAM role
    - Test Lambda runtime python3.12 (Req 6.1)
    - Test Lambda architecture arm64 (Req 6.2)
    - Test Lambda memory 512 MB (Req 6.3)
    - Test Lambda timeout 30s (Req 6.4)
    - Test Lambda X-Ray active tracing (Req 6.5)
    - Test Lambda has 2 layers (Req 6.7)
    - Test Lambda env vars: all 4 present (Req 7.1, 7.2, 7.3, 7.4)
    - Test dedicated IAM role exists (Req 8.1)
    - Test role has SSM read permissions (Req 8.2)
    - Test role has Secrets Manager read (Req 8.3)
    - Test role has CloudWatch Logs write (Req 8.4)
    - Test role has X-Ray write (Req 8.5)
    - **Property 2: No S3 data-plane permissions on execution role** — assert no IAM policy statement contains `s3:*` actions (Req 8.6)

  - [x] 8.5 Write CDK assertion tests for CloudWatch, outputs, and environment parameterization
    - Test log group with 90-day retention (Req 9.1, 9.2)
    - Test CloudWatch alarm on 5XXError metric with Sum statistic and 300s period (Req 10.1, 10.2, 10.3)
    - Test stack output: API URL (Req 11.1)
    - Test stack output: API key ID (Req 11.2)
    - **Property 1: Environment parameterization** — compare dev vs prod templates to verify Lambda ENVIRONMENT env var, stage name, and output export names differ (Req 1.2, 2.6, 7.4, 11.3)



## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The Lambda function code already exists at `lambda/s3_signed_url/` — this spec only creates CDK infrastructure
- Lambda artifacts come from Pants build output — the CDK stack references them via `Code.from_asset()`
- Tests use `aws_cdk.assertions` for deterministic template assertions (no property-based testing with hypothesis)
- Property 1 (environment parameterization) and Property 2 (no S3 permissions) from the design are covered in test tasks 8.5 and 8.4 respectively
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
