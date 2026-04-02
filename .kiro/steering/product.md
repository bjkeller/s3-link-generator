# Product Overview

S3 Presigned URL Service is a Pants-managed monorepo containing an AWS Lambda function that generates pre-signed S3 download URLs for authorized app clients.

## Core Functionality

- **Pre-signed URL Generation**: Generates time-limited S3 GET URLs on behalf of registered app clients
- **App Client Authorization**: Validates the calling client against a registry and enforces per-client bucket allowlists
- **Configurable Expiration**: Default and per-client maximum expiration times; clients may request shorter durations
- **API Gateway Frontend**: Single `GET /presign` endpoint authenticated via API key (`x-api-key` header)

## Key Components

- **Lambda Function**: `lambda/s3_signed_url/` — source, tests, and Terraform for the presign lambda
- **Client Registry**: Maps app client identifiers to allowed buckets and max expiration (DynamoDB or SSM — decided during spec)
- **API Layer**: API Gateway with API key auth, IP restriction, request validation, and usage plans

## Request / Response

### Request parameters

| Parameter | Required | Description |
|---|---|---|
| `bucket` | Yes | S3 bucket name |
| `key` | Yes | S3 object key |
| `expiration` | No | URL expiration in seconds (default: env var, max: per-client config) |

App client identity comes from the `x-api-key` header — not a query parameter.

### Responses

| Status | Condition |
|---|---|
| 200 | `{ "url": "<presigned_url>", "expires_in": <seconds> }` |
| 400 | Missing or invalid parameters |
| 403 | Client not authorized for the requested bucket |
| 500 | Unexpected error |

## Known Consumers

- **NACC Quick Access Link web app** — static S3/CloudFront site that constructs S3 keys for NACC dataset files and calls this API to generate download links

## Key Dependencies

- `boto3` — AWS SDK (S3 presign, DynamoDB/SSM client registry)
- `pydantic` — Data validation and configuration models
- `aws-lambda-powertools` — Logging, tracing, and Lambda utilities

## Target Users

NACC internal teams and tools that need pre-signed S3 download URLs without direct AWS access.
