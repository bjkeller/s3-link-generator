# Spec Prompt: S3 Pre-Sign API

## Context

We are building a generic S3 pre-signed URL service. This prompt covers the API layer and infrastructure-as-code. The API fronts a Lambda that generates pre-signed S3 URLs for authorized app clients.

This replaces the existing `quickaccessserverless` deployment in account `090173369068` / `us-west-2`.

## Build & Deploy Strategy

- **Pants** builds the Lambda function zip and layer zip
- **AWS CDK (Python)** defines and deploys the full stack: API Gateway, Lambda, layers, DynamoDB, IAM, CloudWatch
- The CDK stack references the Pants-produced zip artifacts via `Code.from_asset()` / `LayerVersion`
- CDK app lives in an `infra/` directory at the repo root

## Requirements

### CDK Stack

Define a CDK app in `infra/` with a single stack containing:

#### API Gateway

- Single GET endpoint: `/presign`
- Required query parameters: `bucket`, `key`
- Optional query parameter: `expiration`
- Regional endpoint
- CORS enabled
- Request validation: validate that required query parameters are present

#### Authentication

Use API Gateway API keys + usage plans:

- Each app client gets an API key
- The API key is passed via the `x-api-key` header
- Usage plans can enforce rate limits and quotas per client
- The Lambda receives the API key identity and uses it to look up the client's bucket allowlist

Alternative: Cognito with client credentials grant. More complex but better if we need OAuth flows or token-based auth in the future. **Recommend starting with API keys for simplicity.**

#### IP Restriction

The current service restricts access to NACC office IPs (`128.208.132.0/24`, `192.42.144.0/25`). With the generalized design:

- IP restriction should be per-client or removed from the API level entirely
- If all current clients are internal, keep the resource policy IP restriction for now
- If external clients are added later, move IP restriction to WAF rules per client or remove it

**Recommend keeping the IP restriction at the API Gateway resource policy level for now**, since all known consumers are internal.

#### Lambda Function
- Runtime: `python3.12`
- Architecture: `arm64` (Graviton)
- Memory: 512 MB
- Timeout: 30s
- X-Ray tracing: Active
- Code: reference Pants-produced zip from `dist/` output
- Layers: separate powertools layer and deps layer (matching Pants BUILD targets)
- Environment variables:
  - `CLIENT_REGISTRY_TABLE` — DynamoDB table name (or SSM prefix, depending on registry choice)
  - `DEFAULT_EXPIRATION` — default pre-signed URL expiration in seconds
  - `ENVIRONMENT` — dev/prod

#### IAM (dedicated role)
- Create a dedicated execution role (do not reuse `LambdaUdsRead`)
- Policies:
  - `s3:GetObject` on buckets the service needs to sign for
  - DynamoDB read access (if using DynamoDB for client registry)
  - SSM read access (if using SSM for client registry)
  - CloudWatch Logs write
  - X-Ray write
  - VPC access (only if VPC attachment is retained — see open question)

#### Client Registry (if using DynamoDB)

- Table name: `{environment}-presign-clients`
- Partition key: `client_id` (String)
- Attributes: `allowed_buckets` (StringSet), `max_expiration` (Number), `description` (String)
- Billing: On-demand (PAY_PER_REQUEST) — this will have very low traffic

#### CloudWatch
- Log retention: 90 days
- Alarm on 5xx error rate

### CDK Context / Parameters

| Parameter | Type | Description |
|---|---|---|
| `environment` | String | `dev` or `prod` |

### Stack Outputs

Export the API endpoint URL and API key ID so they can be referenced by consumer deployments.

### CDK Project Structure

```
infra/
  app.py                    # CDK app entry point
  stacks/
    presign_stack.py        # Main stack definition
  cdk.json                  # CDK configuration
  requirements.txt          # CDK dependencies (aws-cdk-lib, constructs)
```

### Deploy Workflow

```bash
# 1. Build lambda artifacts with Pants
pants package lambda/s3_signed_url/src/python/s3_signed_url_lambda::

# 2. Deploy with CDK
cd infra
cdk deploy --context environment=dev
```

## Open Questions

1. **VPC attachment** — The current Lambda is in a VPC. This adds cold start latency. If the Lambda only needs S3 (public endpoint) and DynamoDB/SSM, VPC is unnecessary. **Recommend removing unless there's a specific reason.**

2. **Custom domain** — Should the API have a custom domain (e.g., `presign-api.nacc.org`)? Avoids hardcoding the API Gateway ID in consumers.

3. **API keys vs Cognito** — API keys are simpler. Cognito is more robust. For internal-only use with a few clients, API keys are fine. Revisit if external consumers are added.

4. **Bucket access scope** — The Lambda role needs `s3:GetObject` on all buckets any client might use. Options:
   - Wildcard on a prefix: `arn:aws:s3:::nacc*/*`
   - Explicit list maintained in the CDK stack
   - Separate policy per client (complex)
   
   **Recommend prefix-based wildcard if bucket naming is consistent.**

## Out of scope
- Lambda function code (see Lambda prompt)
- Web UI (see web-app prompt)
- CI/CD pipeline (GitHub Actions — separate effort)
