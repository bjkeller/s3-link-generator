# Implementation Plan: S3 Pre-Signed URL Lambda

## Overview

Implement the S3 pre-signed URL Lambda function that generates time-limited pre-signed S3 GET URLs for authorized app clients. The implementation replaces the existing placeholder handler with a production handler backed by SSM Parameter Store client registry, Secrets Manager signing credentials, Pydantic models, and comprehensive tests using moto and hypothesis.

## Tasks

- [-] 1. Add hypothesis dependency and regenerate Pants lockfile
  - Add `hypothesis>=6.100.0` to `requirements.txt` under the Testing section
  - Regenerate the Pants lockfile by running `pants generate-lockfiles` via kiro-pants-power or `./bin/exec-in-devcontainer.sh pants generate-lockfiles`
  - Verify the lockfile regenerated successfully
  - _Requirements: 13.1_

- [ ] 2. Implement Pydantic models and custom exceptions
  - [ ] 2.1 Create `lambda/s3_signed_url/src/python/s3_signed_url_lambda/models.py`
    - Define `PresignRequest` model with fields: `bucket` (str), `key` (str), `expiration` (int | None = None), `client_id` (str)
    - Define `ClientConfig` model with fields: `client_id` (str), `allowed_buckets` (list[str]), `max_expiration` (int), `description` (str)
    - Define `PresignResponse` model with fields: `url` (str), `expires_in` (int)
    - Define `ClientNotFoundError`, `RegistryError`, and `ValidationError` exception classes
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  - [ ]* 2.2 Write property test for Pydantic model serialization round-trip
    - Create `lambda/s3_signed_url/test/python/test_models.py`
    - Use hypothesis `@given` with `@settings(max_examples=100)` to generate random valid model instances
    - **Property 8: Pydantic model serialization round-trip** — For any valid `PresignRequest`, `ClientConfig`, or `PresignResponse`, serializing to dict and reconstructing produces an equivalent instance
    - **Validates: Requirements 12.1, 12.2, 12.3**
    - Run `pants_test` via kiro-pants-power on `lambda/s3_signed_url/test/python` to verify tests pass

- [ ] 3. Implement client registry
  - [ ] 3.1 Create `lambda/s3_signed_url/src/python/s3_signed_url_lambda/client_registry.py`
    - Implement `ClientRegistry` class with `__init__(self, ssm_client, prefix)` accepting an SSM client and prefix path
    - Implement `get_client_config(self, client_id) -> ClientConfig` that fetches and parses JSON from SSM at `{prefix}/{client_id}`
    - Raise `ClientNotFoundError` when the SSM parameter does not exist (catch `ParameterNotFound`)
    - Raise `RegistryError` when SSM is unreachable or returns other errors
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [ ] 3.2 Write property test for client config SSM round-trip
    - Create `lambda/s3_signed_url/test/python/test_client_registry.py`
    - Use hypothesis to generate random valid `ClientConfig` instances, store as JSON in moto-mocked SSM, retrieve via `ClientRegistry.get_client_config`, and assert equivalence
    - **Property 3: Client config round-trip through SSM** — For any valid ClientConfig, storing as JSON in SSM and retrieving via the registry produces an equivalent ClientConfig
    - **Validates: Requirements 3.1**
    - Include unit tests for: unknown client_id → `ClientNotFoundError`, SSM unreachable → `RegistryError`
    - Run `pants_test` via kiro-pants-power on `lambda/s3_signed_url/test/python` to verify tests pass

- [ ] 4. Implement Lambda handler
  - [ ] 4.1 Replace `lambda/s3_signed_url/src/python/s3_signed_url_lambda/lambda_function.py` with production handler
    - Implement module-level `_signing_credentials` and `_s3_signing_client` caching
    - Implement `_init_signing_client()` that retrieves IAM user creds from Secrets Manager (via `SIGNING_CREDENTIALS_SECRET` env var) and creates a dedicated S3 client
    - Implement `_parse_request(event)` that extracts `bucket`, `key`, `expiration` from `queryStringParameters` and `client_id` from `requestContext.identity.apiKeyId`, returning a `PresignRequest`
    - Implement `_resolve_expiration(requested, client_max)` that returns `min(requested_or_default, client_max, 604800)` using `DEFAULT_EXPIRATION` env var
    - Implement `_build_response(status_code, body)` and `_error_response(status_code, message)` helpers with `Content-Type: application/json` header
    - Implement `lambda_handler(event, context)` orchestrating: parse → resolve client → lookup config → authorize bucket → resolve expiration → sign → respond
    - Use `aws_lambda_powertools.Logger` for structured logging with request ID correlation
    - Handle all error cases: 400 for validation, 403 for auth, 500 for internal errors (generic message, no internal details exposed)
    - Validate required env vars `CLIENT_REGISTRY_PREFIX` and `SIGNING_CREDENTIALS_SECRET` at init time
    - _Requirements: 1.1–1.6, 2.1–2.3, 4.1–4.3, 5.1–5.5, 6.1–6.5, 7.1–7.4, 8.1–8.2, 9.1–9.5, 10.1–10.5, 11.1–11.5_
  - [ ] 4.2 Run code quality checks
    - Run `pants_fix` via kiro-pants-power on `lambda/s3_signed_url/src/python` to format code
    - Run `pants_check` via kiro-pants-power on `lambda/s3_signed_url/src/python` to verify type checking passes

- [ ] 5. Implement test fixtures and handler tests
  - [ ] 5.1 Create `lambda/s3_signed_url/test/python/conftest.py` with shared fixtures
    - Create moto-mocked SSM, S3, and Secrets Manager client fixtures using `@pytest.fixture`
    - Create factory functions for building API Gateway proxy events with customizable `bucket`, `key`, `expiration`, and `apiKeyId`
    - Create factory functions for registering client configs in mocked SSM
    - Create factory functions for storing signing credentials in mocked Secrets Manager
    - Provide fixture that resets module-level `_signing_credentials` and `_s3_signing_client` state between tests
    - Set required environment variables (`CLIENT_REGISTRY_PREFIX`, `SIGNING_CREDENTIALS_SECRET`, `DEFAULT_EXPIRATION`) in fixtures
    - _Requirements: 13.1, 13.8_
  - [ ] 5.2 Replace `lambda/s3_signed_url/test/python/test_lambda_function.py` with production handler tests
    - Test valid request returns 200 with `url` and `expires_in` in JSON body (_Requirements: 13.2, 1.1, 7.1, 8.1_)
    - Test missing `bucket` parameter returns 400 (_Requirements: 13.5, 1.2_)
    - Test missing `key` parameter returns 400 (_Requirements: 13.5, 1.3_)
    - Test empty `bucket` or `key` returns 400 (_Requirements: 1.4_)
    - Test invalid expiration (non-integer, zero, negative) returns 400 (_Requirements: 1.5_)
    - Test missing client identity returns 403 (_Requirements: 2.2_)
    - Test unknown client_id returns 403 (_Requirements: 13.3, 3.2_)
    - Test unauthorized bucket returns 403 (_Requirements: 13.4, 4.2_)
    - Test SSM unreachable returns 500 (_Requirements: 3.4_)
    - Test Secrets Manager unreachable returns 500 (_Requirements: 13.7, 6.3_)
    - Test malformed signing credentials returns 500 (_Requirements: 6.4_)
    - Test boto3 client error during signing returns 500 (_Requirements: 13.6, 7.4_)
    - Test default expiration used when not provided (_Requirements: 1.6, 11.1_)
    - Test expiration capped to client max (_Requirements: 5.1_)
    - All tests use moto mocks, no live AWS calls (_Requirements: 13.8_)
    - Run `pants_test` via kiro-pants-power on `lambda/s3_signed_url/test/python` to verify all tests pass

- [ ] 6. Implement property-based validation tests
  - [ ]* 6.1 Write property test for invalid expiration rejection
    - Create `lambda/s3_signed_url/test/python/test_validation.py`
    - **Property 2: Invalid expiration values are rejected** — For any string that is not a positive integer, the handler returns 400 with an `error` field
    - **Validates: Requirements 1.5**
    - Use hypothesis to generate non-positive-integer strings (negative, zero, floats, non-numeric)
  - [ ] 6.2 Write property test for bucket authorization matching allowlist
    - Add to `test_validation.py`
    - **Property 4: Bucket authorization matches allowlist membership** — For any client config and bucket name, authorization permits iff bucket is in `allowed_buckets`
    - **Validates: Requirements 4.1, 4.2, 4.3**
  - [ ] 6.3 Write property test for expiration resolution capping
    - Add to `test_validation.py`
    - **Property 5: Expiration resolution is capped correctly** — Resolved expiration equals `min(requested_or_default, client_max, 604800)`
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 1.6**
  - [ ]* 6.4 Write property test for valid request producing presigned URL
    - Add to `test_lambda_function.py` or `test_validation.py`
    - **Property 1: Valid request produces a presigned URL response** — For any valid request with authorized bucket and registered client, handler returns 200 with `url` and `expires_in`
    - **Validates: Requirements 1.1, 7.1, 8.1**
  - [ ]* 6.5 Write property test for Content-Type header on all responses
    - **Property 6: All responses include Content-Type application/json** — For any request, the response includes `Content-Type: application/json`
    - **Validates: Requirements 8.2, 9.4**
  - [ ]* 6.6 Write property test for error response structure
    - **Property 7: Error responses contain structured error field** — For any failing request, the response has the appropriate status code and a JSON body with a non-empty `error` string
    - **Validates: Requirements 9.1, 9.2**
  - [ ]* 6.7 Run all property tests
    - Run `pants_test` via kiro-pants-power on `lambda/s3_signed_url/test/python` to verify all property-based tests pass
    - Each property test must use `@settings(max_examples=100)`

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All Pants commands should be run via kiro-pants-power MCP tools
- Do NOT modify any existing hooks in `.kiro/hooks/`
