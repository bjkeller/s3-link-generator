# Coding Style Guidelines

## Python Import Organization

**CRITICAL**: All imports must be at the top of Python files, immediately after the module docstring (if present).

```python
# ✅ Correct
"""Module docstring."""

import json
from typing import Any

import boto3
from pydantic import BaseModel

def my_function():
    pass
```

```python
# ❌ Incorrect — imports scattered throughout file
def my_function():
    import os  # Don't do this
    pass

import boto3  # Don't do this after function definitions
```

## Lambda Architecture

### File Organization

Each lambda should follow this structure:
- `lambda_function.py` — Lambda handler entry point, parses event, calls business logic
- Additional modules as needed for business logic, models, client wrappers

### Handler Responsibilities

**Keep AWS Lambda context handling in the handler. Push business logic into separate functions or modules.**

```python
# lambda_function.py
"""Lambda handler for S3 pre-signed URL generation."""

import json
from typing import Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()


def lambda_handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda entry point — parse request, validate client, generate URL."""
    request = parse_request(event)
    client = lookup_client(request.client_id)
    validate_bucket_access(client, request.bucket)
    url = generate_presigned_url(request)
    return format_response(url, request.expiration)
```

### Separation of Concerns

- **Handler** (`lambda_function.py`): Event parsing, AWS context, response formatting
- **Business logic** (separate modules): Core operations, testable without Lambda context
- **Models** (`models.py`): Pydantic models for configuration and results
- **Client wrappers**: Encapsulate external API calls (S3, DynamoDB, SSM)

### Code Smells to Avoid

**❌ Don't put all logic in the handler**

```python
# Bad — handler does everything
def lambda_handler(event, context):
    s3 = boto3.client('s3')
    url = s3.generate_presigned_url(...)
    # 200 lines of validation and formatting...
```

**❌ Don't pass many simple type arguments**

```python
# Bad — too many simple arguments
def generate_url(bucket: str, key: str, expiration: int, client_id: str, max_exp: int):
    pass
```

**✅ Do use structured configuration**

```python
# Good — Pydantic model
from pydantic import BaseModel

class PresignRequest(BaseModel):
    bucket: str
    key: str
    expiration: int | None = None
    client_id: str

class ClientConfig(BaseModel):
    client_id: str
    allowed_buckets: list[str]
    max_expiration: int
    description: str

def generate_presigned_url(request: PresignRequest, client: ClientConfig) -> str:
    pass
```

## Design Principles

### Dependency Injection over Flag Parameters

Prefer dependency injection over boolean flags for configurable behavior.

### Type Safety

Use Pydantic models for:
- Lambda event / request parsing
- Client registry entries
- Structured response objects

### Credential Handling

- Use the Lambda execution role and default credential chain for S3 presigning
- Do NOT store or retrieve IAM access keys from SSM or environment variables
- Client registry stores app client metadata, not AWS credentials

## Key Principles

1. **Separation of Concerns**: Keep Lambda handler thin, push logic into testable modules
2. **Testability**: Business logic should be testable without Lambda context or live AWS services
3. **Type Safety**: Use Pydantic models over raw dicts for configuration and results
4. **Import Discipline**: All imports at the top, no scattered imports
5. **Dependency Injection**: Pass clients/dependencies in rather than constructing them deep in the call stack

## Testing Guidelines

### Test Against Public Interfaces

Tests should be robust to implementation changes within fixed interfaces.

- Test behavior, not implementation
- Test through public APIs
- Avoid testing internal state (private members prefixed with `_`)

### Mock Strategy

- Centralize mock factories in `conftest.py` or test utility modules
- Use pytest fixtures for reusable mock setup
- Provide sensible defaults, allow customization via kwargs
- Mock external services (S3, DynamoDB, SSM) — not internal logic

### Key Test Cases

- Valid request → pre-signed URL returned
- Unknown client → 403
- Client requests unauthorized bucket → 403
- Missing parameters → 400
- S3 client error → 500
