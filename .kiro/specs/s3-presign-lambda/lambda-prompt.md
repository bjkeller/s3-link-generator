# Spec Prompt: S3 Pre-Sign Lambda

## Context

We are building a generic S3 pre-signed URL service. The Lambda generates pre-signed URLs for S3 objects on behalf of authorized app clients. It has no knowledge of specific use cases — it just validates the caller is allowed to access the requested bucket and returns a signed URL.

The first consumer will be the NACC Quick Access Link web app, but the service is designed to be reusable by any internal tool that needs pre-signed S3 download URLs.

## Behavior

1. Receive a request with an app client identifier, S3 bucket name, and object key
2. Look up the app client in the client registry
3. Verify the requested bucket is in the client's allowlist
4. Generate a pre-signed GET URL for the S3 object with a configurable expiration
5. Return the pre-signed URL

### Request parameters

| Parameter | Required | Description |
|---|---|---|
| `bucket` | Yes | S3 bucket name |
| `key` | Yes | S3 object key |
| `expiration` | No | URL expiration in seconds (default: 1209600 / 2 weeks, max: configurable per client) |

The app client identity comes from the authentication mechanism (API key header or Cognito token), not as a query parameter.

### Responses

| Status | Condition |
|---|---|
| 200 | Success — returns `{ "url": "<presigned_url>", "expires_in": <seconds> }` |
| 400 | Missing or invalid parameters |
| 403 | App client not authorized for the requested bucket |
| 404 | (Optional) S3 object does not exist — or skip this check and let the pre-signed URL fail on download |
| 500 | Unexpected error |

## App Client Registry

A mapping of app client identifiers to their configuration:

```json
{
  "client_id": "quickaccess-web",
  "allowed_buckets": ["naccquickaccess"],
  "max_expiration": 1209600,
  "description": "NACC Quick Access Link web app"
}
```

### Storage options (pick one during spec)

- **DynamoDB table** — most flexible, supports many clients, no redeploy to add/modify clients
- **SSM Parameter Store** — simpler, fine for a handful of clients
- **Lambda environment variable (JSON)** — simplest, but requires redeploy to change

Recommend DynamoDB if we expect more than 2-3 clients. SSM is fine if this stays small.

## Requirements

### Runtime & tooling
- Python 3.12+ (Pants build system with `requirements.txt` for dependency management)
- `aws-lambda-powertools` for structured logging, typing, and event handling
- `boto3` with the default credential chain (no stored IAM user keys)
- `pydantic` for data validation and configuration models

### Credential handling
- The Lambda execution role must have `s3:GetObject` on the buckets it needs to sign for
- Since this is generic, the role needs access to all buckets that any registered client might use
- Consider a resource policy pattern: `arn:aws:s3:::nacc*/*` if all NACC buckets share a prefix, or maintain an explicit list
- Do NOT store or retrieve IAM access keys from SSM Parameter Store

### Configuration
- Default URL expiration: environment variable
- Client registry location (DynamoDB table name, SSM prefix, etc.): environment variable
- Environment name (dev/prod): environment variable

### Testing
- Unit tests with mocking (`moto` or `unittest.mock`) — no live AWS calls
- Test cases:
  - Valid request → pre-signed URL returned
  - Unknown client → 403
  - Client requests unauthorized bucket → 403
  - Missing parameters → 400
  - S3 client error → 500

### Code structure (Pants monorepo layout)
```
lambda/s3_signed_url/
  src/python/s3_signed_url_lambda/
    BUILD
    lambda_function.py        # Handler entry point
    client_registry.py        # App client lookup and validation
    models.py                 # Pydantic models for request/response/config
  test/python/
    BUILD
    test_lambda_function.py
    test_client_registry.py
```

Infrastructure is defined separately via CDK (see API prompt).

## Out of scope
- API Gateway definition (see API prompt)
- Web UI (see web-app prompt)
- CI/CD pipeline
- Object existence validation (let the pre-signed URL fail at download time)
