# Requirements Document

## Introduction

This spec covers the API Gateway layer and AWS CDK infrastructure for the S3 Pre-Signed URL Service. The CDK stack defines a REST API Gateway fronting the Lambda function (specified separately in `s3-presign-lambda`), along with all supporting infrastructure: IAM roles, API key authentication, usage plans, IP restriction, CloudWatch alarms, and stack outputs.

The stack is deployed via AWS CDK (Python) and references Pants-produced Lambda zip artifacts. It replaces the existing `quickaccessserverless` deployment in account `090173369068` / `us-west-2`.

### Key Decisions Aligned with Lambda Spec

- Client registry uses SSM Parameter Store (not DynamoDB) — no DynamoDB table is provisioned
- Lambda environment variables: `CLIENT_REGISTRY_PREFIX`, `SIGNING_CREDENTIALS_SECRET`, `DEFAULT_EXPIRATION`, `ENVIRONMENT`
- The Lambda execution role does NOT need `s3:GetObject` — signing uses dedicated IAM user credentials retrieved from Secrets Manager
- The execution role needs: SSM read, Secrets Manager read, CloudWatch Logs write, X-Ray write
- No VPC attachment for the Lambda — it only accesses public AWS endpoints (S3, SSM, Secrets Manager)
- API access is restricted to the NACC VPC (`NaccVPC1`, `vpc-089e3a35afb9d5b93`, CIDR `10.0.0.0/16`) via an interface VPC endpoint for `execute-api`

## Glossary

- **CDK_Stack**: The AWS CDK stack that defines all infrastructure resources for the pre-sign service
- **API_Gateway**: The AWS API Gateway REST API that exposes the `/presign` GET endpoint
- **Lambda_Function**: The AWS Lambda function resource defined in the CDK stack, referencing the Pants-produced zip artifact
- **Execution_Role**: The dedicated IAM role assumed by the Lambda_Function at runtime
- **API_Key**: An API Gateway API key assigned to an App_Client for authentication via the `x-api-key` header
- **Usage_Plan**: An API Gateway usage plan that associates API_Keys with the API stage and enforces rate limits and quotas
- **Resource_Policy**: An API Gateway resource policy that restricts access to requests originating from the NACC VPC endpoint
- **VPC_Endpoint**: An interface VPC endpoint for the `execute-api` service in the NACC VPC (`NaccVPC1`, `vpc-089e3a35afb9d5b93`, CIDR `10.0.0.0/16`), enabling private API Gateway access from within the VPC
- **Request_Validator**: An API Gateway request validator that enforces required query string parameters
- **Powertools_Layer**: A Lambda layer containing the `aws-lambda-powertools` package, built by Pants
- **Deps_Layer**: A Lambda layer containing the Lambda's Python dependencies (excluding powertools), built by Pants
- **Stack_Output**: A CloudFormation output exported from the CDK_Stack for cross-stack or consumer reference
- **App_Client**: A registered consumer of the API, identified by an API_Key
- **CloudWatch_Alarm**: A CloudWatch alarm that monitors API Gateway 5xx error rates

## Requirements

### Requirement 1: CDK Application Entry Point

**User Story:** As a DevOps engineer, I want a CDK application defined in `infra/` that accepts an `environment` context parameter, so that I can deploy the pre-sign stack to dev or prod environments.

#### Acceptance Criteria

1. THE CDK_Stack SHALL be defined in a CDK app located at `infra/app.py`
2. THE CDK_Stack SHALL read the `environment` context parameter (value `dev` or `prod`) from CDK context via `app.node.try_get_context("environment")`
3. WHEN the `environment` context parameter is not provided, THE CDK_Stack SHALL default to `dev`
4. THE CDK_Stack SHALL use the `environment` value to prefix or parameterize resource names for environment isolation

### Requirement 2: API Gateway REST API

**User Story:** As an App_Client, I want a regional REST API with a single GET `/presign` endpoint, so that I can request pre-signed S3 URLs over HTTPS.

#### Acceptance Criteria

1. THE API_Gateway SHALL expose a single GET method at the `/presign` resource path
2. THE API_Gateway SHALL use a regional endpoint configuration
3. THE API_Gateway SHALL require the `bucket` and `key` query string parameters via a Request_Validator
4. THE API_Gateway SHALL accept an optional `expiration` query string parameter
5. THE API_Gateway SHALL use Lambda proxy integration to forward requests to the Lambda_Function
6. THE API_Gateway SHALL deploy to a stage named after the `environment` value (e.g., `dev` or `prod`)

### Requirement 3: CORS Configuration

**User Story:** As a web application developer, I want CORS enabled on the API, so that browser-based consumers (such as the Quick Access Link web app) can call the API cross-origin.

#### Acceptance Criteria

1. THE API_Gateway SHALL return CORS headers allowing cross-origin requests from any origin (`*`)
2. THE API_Gateway SHALL include `Content-Type` and `x-api-key` in the `Access-Control-Allow-Headers` response
3. THE API_Gateway SHALL include `GET` and `OPTIONS` in the `Access-Control-Allow-Methods` response

### Requirement 4: API Key Authentication

**User Story:** As a service operator, I want API key authentication on the `/presign` endpoint, so that only registered App_Clients can access the API.

#### Acceptance Criteria

1. THE API_Gateway GET method SHALL require an API key via the `x-api-key` header (`api_key_required=True`)
2. THE CDK_Stack SHALL create at least one API_Key resource for the initial App_Client
3. THE CDK_Stack SHALL create a Usage_Plan that associates the API_Key with the API_Gateway stage
4. THE Usage_Plan SHALL support configurable rate limits (requests per second) and quota (requests per day) per plan

### Requirement 5: VPC-Based Access Restriction

**User Story:** As a security engineer, I want the API restricted to requests originating from the NACC VPC, so that only internal systems within the VPC can reach the endpoint.

#### Acceptance Criteria

1. THE CDK_Stack SHALL create an interface VPC_Endpoint for the `com.amazonaws.us-west-2.execute-api` service in the NACC VPC (`NaccVPC1`, `vpc-089e3a35afb9d5b93`)
2. THE VPC_Endpoint SHALL be placed in the private subnets of the NACC VPC (`NaccPrivate1`, `NaccPrivate2`)
3. THE VPC_Endpoint SHALL have private DNS enabled so that API Gateway requests from within the VPC resolve to the endpoint automatically
4. THE API_Gateway SHALL attach a Resource_Policy that allows requests only from the VPC_Endpoint
5. THE Resource_Policy SHALL deny all requests that do not originate from the VPC_Endpoint
6. THE Resource_Policy SHALL apply to all methods and resources on the API_Gateway

### Requirement 6: Lambda Function Resource

**User Story:** As a DevOps engineer, I want the Lambda function defined in the CDK stack with the correct runtime, architecture, and configuration, so that it runs efficiently on Graviton with the expected settings.

#### Acceptance Criteria

1. THE Lambda_Function SHALL use the `python3.12` runtime
2. THE Lambda_Function SHALL use the `arm64` (Graviton) architecture
3. THE Lambda_Function SHALL have a memory allocation of 512 MB
4. THE Lambda_Function SHALL have a timeout of 30 seconds
5. THE Lambda_Function SHALL have X-Ray active tracing enabled
6. THE Lambda_Function SHALL reference the Pants-produced function zip artifact via `Code.from_asset()` pointing to the `dist/` output path
7. THE Lambda_Function SHALL attach the Powertools_Layer and the Deps_Layer as separate Lambda layers, each referencing a Pants-produced layer zip artifact

### Requirement 7: Lambda Environment Variables

**User Story:** As a service operator, I want the Lambda configured with the correct environment variables, so that it can locate the client registry, signing credentials, and deployment settings at runtime.

#### Acceptance Criteria

1. THE Lambda_Function SHALL have the `CLIENT_REGISTRY_PREFIX` environment variable set to the SSM Parameter Store prefix path for client configurations
2. THE Lambda_Function SHALL have the `SIGNING_CREDENTIALS_SECRET` environment variable set to the Secrets Manager ARN or SSM path for the IAM user signing credentials
3. THE Lambda_Function SHALL have the `DEFAULT_EXPIRATION` environment variable set to the default URL expiration in seconds
4. THE Lambda_Function SHALL have the `ENVIRONMENT` environment variable set to the `environment` context value (`dev` or `prod`)

### Requirement 8: IAM Execution Role

**User Story:** As a security engineer, I want a dedicated least-privilege IAM execution role for the Lambda, so that it has only the permissions it needs and does not reuse a shared role.

#### Acceptance Criteria

1. THE CDK_Stack SHALL create a dedicated Execution_Role for the Lambda_Function (not reuse an existing shared role)
2. THE Execution_Role SHALL grant `ssm:GetParameter` and `ssm:GetParametersByPath` on the SSM prefix path used by the client registry
3. THE Execution_Role SHALL grant `secretsmanager:GetSecretValue` on the Secrets Manager resource storing the signing credentials
4. THE Execution_Role SHALL grant CloudWatch Logs write permissions (`logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`)
5. THE Execution_Role SHALL grant X-Ray write permissions (`xray:PutTraceSegments`, `xray:PutTelemetryRecords`)
6. THE Execution_Role SHALL NOT grant `s3:GetObject` or any S3 data-plane permissions (signing uses dedicated IAM user credentials, not the execution role)

### Requirement 9: CloudWatch Log Group and Retention

**User Story:** As a service operator, I want Lambda logs retained for 90 days with a dedicated log group, so that I can investigate issues within a reasonable window without unbounded log storage costs.

#### Acceptance Criteria

1. THE CDK_Stack SHALL create a CloudWatch Logs log group for the Lambda_Function
2. THE log group SHALL have a retention period of 90 days

### Requirement 10: CloudWatch Alarm on 5xx Errors

**User Story:** As a service operator, I want an alarm on API Gateway 5xx error rates, so that I am notified when the service is experiencing server-side failures.

#### Acceptance Criteria

1. THE CDK_Stack SHALL create a CloudWatch_Alarm that monitors the API_Gateway `5XXError` metric
2. THE CloudWatch_Alarm SHALL trigger when the 5xx error count exceeds a threshold within a 5-minute evaluation period
3. THE CloudWatch_Alarm SHALL use the `Sum` statistic for the `5XXError` metric

### Requirement 11: Stack Outputs

**User Story:** As a consumer deployment engineer, I want the API endpoint URL and API key ID exported as stack outputs, so that consumer stacks and configuration files can reference them.

#### Acceptance Criteria

1. THE CDK_Stack SHALL export the API_Gateway invoke URL as a Stack_Output
2. THE CDK_Stack SHALL export the API_Key ID as a Stack_Output
3. THE Stack_Outputs SHALL use descriptive export names that include the environment value for uniqueness

### Requirement 12: CDK Project Structure

**User Story:** As a developer, I want the CDK project organized with a clear directory structure, so that the infrastructure code is maintainable and follows CDK conventions.

#### Acceptance Criteria

1. THE CDK project SHALL have an entry point at `infra/app.py`
2. THE CDK project SHALL define the stack in `infra/stacks/presign_stack.py`
3. THE CDK project SHALL include a `infra/cdk.json` configuration file
4. THE CDK project SHALL include a `infra/requirements.txt` listing `aws-cdk-lib` and `constructs` as dependencies

### Requirement 13: Request Validation

**User Story:** As a service operator, I want API Gateway to validate that required query parameters are present before invoking the Lambda, so that obviously malformed requests are rejected at the gateway level without consuming Lambda invocations.

#### Acceptance Criteria

1. THE API_Gateway SHALL configure a Request_Validator that validates query string parameters
2. THE Request_Validator SHALL enforce that the `bucket` query string parameter is present in the request
3. THE Request_Validator SHALL enforce that the `key` query string parameter is present in the request
4. WHEN a request is missing a required query string parameter, THE API_Gateway SHALL return a 400 response without invoking the Lambda_Function

## Out of Scope

- Lambda function code (covered by `s3-presign-lambda` spec)
- Web UI / Quick Access Link web app (covered by a separate spec referencing `prompts/03-web-app.md`)
- CI/CD pipeline (GitHub Actions — separate effort)
- DynamoDB client registry table (Lambda spec decided on SSM Parameter Store)
- VPC configuration for the Lambda function (Lambda only accesses public AWS endpoints; the VPC endpoint is for API Gateway access restriction only)
- Custom domain name (open question — can be added later without changing the stack structure)
- IAM user creation and access key rotation for signing credentials (operational concern)
- Secrets Manager secret provisioning for signing credentials (one-time manual setup)
- WAF rules (not needed while all consumers are internal; revisit if external clients are added)
