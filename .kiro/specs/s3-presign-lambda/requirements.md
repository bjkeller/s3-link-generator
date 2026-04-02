# Requirements Document

## Introduction

This spec covers the S3 Pre-Signed URL Lambda function. The Lambda generates time-limited pre-signed S3 GET URLs on behalf of authorized app clients. It validates the caller against a client registry, enforces per-client bucket allowlists, and returns a signed URL with configurable expiration.

The Lambda is designed to be generic and reusable — it has no knowledge of specific consumers. The first consumer is the NACC Quick Access Link web app, but any internal tool needing pre-signed S3 download URLs can be onboarded as a registered client.

API Gateway infrastructure is out of scope (covered by a separate spec). This spec assumes the Lambda receives its event from API Gateway with the client identity resolved from the `x-api-key` header via `requestContext`.

### Signing Credential Strategy

The Lambda uses long-term IAM user credentials (stored in a Secret_Store) to sign pre-signed URLs. This approach supports URL expirations up to 7 days (604,800 seconds), which is the S3 hard maximum for IAM user credentials.

Business context: A research team staffer requests a pre-signed URL and sends it to an external researcher who does not have access to the API or any UI. The researcher may not access the URL immediately, so short-lived URLs have caused problems in production. The 7-day maximum balances usability with the S3-imposed hard limit.

The Lambda execution role is used only for accessing the Secret_Store and SSM Parameter Store — not for signing URLs.

## Glossary

- **Lambda**: The AWS Lambda function that generates pre-signed S3 GET URLs
- **Client_Registry**: The SSM Parameter Store parameters that store app client configurations including allowed buckets and maximum expiration
- **App_Client**: A registered consumer of the Lambda, identified by an API key and mapped to a client configuration in the Client_Registry
- **Presigned_URL**: A time-limited URL granting temporary GET access to a specific S3 object without requiring AWS credentials
- **Request_Event**: The API Gateway proxy event received by the Lambda, containing query string parameters and request context
- **Client_Config**: A record in the Client_Registry containing client_id, allowed_buckets, max_expiration, and description
- **Expiration**: The duration in seconds for which a generated Presigned_URL remains valid
- **Handler**: The `lambda_handler` function that serves as the Lambda entry point
- **Validator**: The component responsible for validating request parameters and client authorization
- **URL_Generator**: The component that calls boto3 to generate the Presigned_URL
- **Signing_Credentials**: The long-term IAM user access key ID and secret access key stored in the Secret_Store, used to sign pre-signed URLs with up to 7-day expiration
- **Secret_Store**: The AWS service (Secrets Manager or SSM Parameter Store SecureString) that securely stores the Signing_Credentials

## Requirements

### Requirement 1: Parse and Validate Request Parameters

**User Story:** As an App_Client, I want the Lambda to validate my request parameters, so that I receive clear error messages when my request is malformed.

#### Acceptance Criteria

1. WHEN a Request_Event is received with both `bucket` and `key` query string parameters present, THE Validator SHALL accept the request parameters as valid
2. WHEN a Request_Event is received without a `bucket` query string parameter, THE Validator SHALL return a 400 response with an error message identifying the missing `bucket` parameter
3. WHEN a Request_Event is received without a `key` query string parameter, THE Validator SHALL return a 400 response with an error message identifying the missing `key` parameter
4. WHEN a Request_Event is received with an empty string for `bucket` or `key`, THE Validator SHALL return a 400 response with an error message identifying the invalid parameter
5. WHEN a Request_Event is received with an `expiration` query string parameter that is not a positive integer, THE Validator SHALL return a 400 response with an error message describing the invalid expiration value
6. WHEN a Request_Event is received without an `expiration` query string parameter, THE Validator SHALL use the default expiration value from the `DEFAULT_EXPIRATION` environment variable

### Requirement 2: Resolve App Client Identity

**User Story:** As an App_Client, I want the Lambda to identify me from the API Gateway request context, so that my request is processed with my specific permissions.

#### Acceptance Criteria

1. WHEN a Request_Event is received, THE Handler SHALL extract the App_Client identity from the API Gateway `requestContext.identity.apiKeyId` field
2. WHEN a Request_Event is received without a resolvable App_Client identity in the request context, THE Handler SHALL return a 403 response with an error message indicating the client could not be identified
3. THE Handler SHALL pass the resolved App_Client identity to the Client_Registry for configuration lookup

### Requirement 3: Look Up Client Configuration

**User Story:** As an App_Client, I want the Lambda to retrieve my configuration from the Client_Registry, so that my bucket permissions and expiration limits are enforced.

#### Acceptance Criteria

1. WHEN the Handler provides a valid client_id, THE Client_Registry SHALL return the corresponding Client_Config containing client_id, allowed_buckets, max_expiration, and description
2. WHEN the Handler provides a client_id that does not exist in the Client_Registry, THE Client_Registry SHALL raise an error that results in a 403 response with a message indicating the client is not registered
3. THE Client_Registry SHALL read from SSM Parameter Store using the prefix path identified by the `CLIENT_REGISTRY_PREFIX` environment variable (e.g., `/presign/clients/{client_id}`), where each client's configuration is stored as a JSON string parameter
4. IF SSM Parameter Store is unreachable or returns an error, THEN THE Client_Registry SHALL raise an error that results in a 500 response with a message indicating an internal error

### Requirement 4: Authorize Bucket Access

**User Story:** As a service operator, I want the Lambda to enforce per-client bucket allowlists, so that each App_Client can only generate URLs for buckets it is authorized to access.

#### Acceptance Criteria

1. WHEN the requested `bucket` is present in the App_Client's `allowed_buckets` list, THE Validator SHALL permit the request to proceed
2. WHEN the requested `bucket` is not present in the App_Client's `allowed_buckets` list, THE Validator SHALL return a 403 response with a message indicating the client is not authorized for the requested bucket
3. THE Validator SHALL perform an exact string match between the requested bucket name and the entries in `allowed_buckets`

### Requirement 5: Enforce Expiration Limits

**User Story:** As a service operator, I want the Lambda to enforce per-client maximum expiration, so that no client can generate URLs that outlive the IAM user credential signing limit.

#### Acceptance Criteria

1. WHEN the requested `expiration` exceeds the App_Client's `max_expiration` value, THE Validator SHALL cap the expiration to the App_Client's `max_expiration` value
2. WHEN the requested `expiration` is within the App_Client's `max_expiration` value, THE Validator SHALL use the requested expiration
3. WHEN no `expiration` is provided in the request, THE Validator SHALL use the default expiration from the `DEFAULT_EXPIRATION` environment variable
4. WHEN the default expiration from the environment variable exceeds the App_Client's `max_expiration`, THE Validator SHALL cap the expiration to the App_Client's `max_expiration` value
5. THE Lambda SHALL enforce a system-wide maximum expiration of 604,800 seconds (7 days) regardless of per-client configuration, to remain within the S3 hard limit for IAM user credential signatures

### Requirement 6: Retrieve Signing Credentials

**User Story:** As a service operator, I want the Lambda to securely retrieve long-term IAM user credentials from a managed secret store, so that pre-signed URLs can have up to 7-day expiration without embedding credentials in code or environment variables.

#### Acceptance Criteria

1. WHEN the Lambda initializes, THE Handler SHALL retrieve the Signing_Credentials (access key ID and secret access key) from the Secret_Store identified by the `SIGNING_CREDENTIALS_SECRET` environment variable
2. THE Handler SHALL cache the retrieved Signing_Credentials for the lifetime of the Lambda execution environment to avoid repeated Secret_Store calls on warm starts
3. IF the Secret_Store is unreachable or returns an error, THEN THE Handler SHALL return a 500 response with a message indicating an internal error
4. IF the retrieved secret does not contain both an access key ID and a secret access key, THEN THE Handler SHALL return a 500 response with a message indicating a configuration error
5. THE Handler SHALL log credential retrieval failures at ERROR level without exposing credential values in log output

### Requirement 7: Generate Pre-Signed URL

**User Story:** As an App_Client, I want the Lambda to generate a pre-signed S3 GET URL, so that I can provide time-limited download access to my users without exposing AWS credentials.

#### Acceptance Criteria

1. WHEN the request is validated and authorized, THE URL_Generator SHALL call boto3 `generate_presigned_url` with the `get_object` operation, the requested bucket, the requested key, and the resolved expiration
2. THE URL_Generator SHALL create a dedicated boto3 S3 client using the retrieved Signing_Credentials (IAM user access key ID and secret access key) for signing pre-signed URLs
3. THE URL_Generator SHALL NOT use the Lambda execution role credentials for signing pre-signed URLs
4. IF boto3 raises a client error during URL generation, THEN THE URL_Generator SHALL raise an error that results in a 500 response

### Requirement 8: Return Successful Response

**User Story:** As an App_Client, I want to receive the pre-signed URL in a structured JSON response, so that I can programmatically extract and use the URL.

#### Acceptance Criteria

1. WHEN a Presigned_URL is successfully generated, THE Handler SHALL return a 200 response with a JSON body containing `url` (the Presigned_URL string) and `expires_in` (the resolved expiration in seconds)
2. THE Handler SHALL set the `Content-Type` response header to `application/json`

### Requirement 9: Return Error Responses

**User Story:** As an App_Client, I want to receive structured error responses with appropriate HTTP status codes, so that I can programmatically handle failures.

#### Acceptance Criteria

1. WHEN a request fails parameter validation, THE Handler SHALL return a 400 status code with a JSON body containing an `error` field describing the validation failure
2. WHEN a request fails client identification or bucket authorization, THE Handler SHALL return a 403 status code with a JSON body containing an `error` field describing the authorization failure
3. WHEN an unexpected error occurs during processing, THE Handler SHALL return a 500 status code with a JSON body containing a generic `error` message that does not expose internal details
4. THE Handler SHALL set the `Content-Type` response header to `application/json` for all error responses
5. THE Handler SHALL log the full error details (including stack trace for 500 errors) using structured logging before returning the error response

### Requirement 10: Structured Logging

**User Story:** As a service operator, I want the Lambda to produce structured logs, so that I can monitor, debug, and audit request processing.

#### Acceptance Criteria

1. THE Lambda SHALL use `aws-lambda-powertools` Logger for all log output
2. WHEN a request is received, THE Handler SHALL log the request parameters (bucket, key, expiration) and the resolved client_id at INFO level
3. WHEN a request completes successfully, THE Handler SHALL log the response status and resolved expiration at INFO level
4. WHEN a request fails, THE Handler SHALL log the error details and the corresponding HTTP status code at WARNING level for 400/403 errors and ERROR level for 500 errors
5. THE Lambda SHALL include the AWS request ID in all log entries

### Requirement 11: Configuration via Environment Variables

**User Story:** As a service operator, I want the Lambda to read its configuration from environment variables, so that I can change settings without modifying code.

#### Acceptance Criteria

1. THE Lambda SHALL read the `DEFAULT_EXPIRATION` environment variable as the default URL expiration in seconds, defaulting to 604800 (7 days) if not set
2. THE Lambda SHALL read the `CLIENT_REGISTRY_PREFIX` environment variable as the SSM Parameter Store prefix path for client configuration lookups
3. THE Lambda SHALL read the `ENVIRONMENT` environment variable to identify the deployment stage (dev or prod)
4. THE Lambda SHALL read the `SIGNING_CREDENTIALS_SECRET` environment variable as the Secrets Manager ARN or SSM Parameter Store path for retrieving the Signing_Credentials
5. IF a required environment variable (`CLIENT_REGISTRY_PREFIX` or `SIGNING_CREDENTIALS_SECRET`) is missing, THEN THE Lambda SHALL fail to initialize and log an error describing the missing variable

### Requirement 12: Pydantic Data Validation Models

**User Story:** As a developer, I want request, response, and configuration data modeled with Pydantic, so that data validation is consistent and type-safe.

#### Acceptance Criteria

1. THE Lambda SHALL define a Pydantic model for the parsed request containing bucket (str), key (str), expiration (optional int), and client_id (str)
2. THE Lambda SHALL define a Pydantic model for the Client_Config containing client_id (str), allowed_buckets (list of str), max_expiration (int), and description (str)
3. THE Lambda SHALL define a Pydantic model for the success response containing url (str) and expires_in (int)
4. THE Lambda SHALL use Pydantic model validation to enforce type constraints and required fields on all parsed data

### Requirement 13: Unit Testing with Mocked AWS Services

**User Story:** As a developer, I want comprehensive unit tests that mock all AWS service calls, so that I can validate Lambda behavior without live AWS resources.

#### Acceptance Criteria

1. THE test suite SHALL use `moto` to mock boto3 AWS service calls (S3, SSM Parameter Store, Secrets Manager)
2. THE test suite SHALL include a test case verifying a valid request returns a 200 response with a Presigned_URL and expires_in
3. THE test suite SHALL include a test case verifying an unknown client_id returns a 403 response
4. THE test suite SHALL include a test case verifying a request for an unauthorized bucket returns a 403 response
5. THE test suite SHALL include a test case verifying missing required parameters return a 400 response
6. THE test suite SHALL include a test case verifying a boto3 client error during URL generation returns a 500 response
7. THE test suite SHALL include a test case verifying a Secret_Store retrieval failure returns a 500 response
8. THE test suite SHALL NOT make any live AWS API calls

## Out of Scope

- API Gateway definition and CDK infrastructure (covered by a separate spec referencing `prompts/02-api.md`)
- Web UI or consumer applications
- CI/CD pipeline
- S3 object existence validation (the Presigned_URL will fail at download time if the object does not exist)
- IAM role and policy definition (handled by the CDK infrastructure spec)
- IAM user creation and access key rotation (operational concern managed outside this spec)
- Secret_Store resource provisioning (handled by the CDK infrastructure spec)
- VPC configuration
