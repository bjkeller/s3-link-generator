# Project Structure Guide

This guide explains the recommended repository organization for AWS Lambda monorepos using Pants build system.

## Repository Layout

```
my-lambda-project/
├── .devcontainer/              # Dev container configuration
│   └── devcontainer.json      # Container setup and features
├── .github/                    # GitHub workflows (optional)
│   └── workflows/
├── .vscode/                    # VS Code settings (optional)
├── bin/                        # Development scripts
│   ├── build-container.sh      # Build dev container
│   ├── start-devcontainer.sh   # Start dev container
│   ├── stop-devcontainer.sh    # Stop dev container
│   ├── terminal.sh             # Open container shell
│   └── exec-in-devcontainer.sh # Execute commands in container
├── common/                     # Shared code across lambdas
│   ├── src/python/            # Shared source modules
│   │   ├── auth/              # Authentication utilities
│   │   ├── database/          # Database connections and models
│   │   ├── logging/           # Logging configuration
│   │   ├── models/            # Shared data models
│   │   ├── utils/             # Common utilities
│   │   └── validation/        # Input validation
│   └── test/python/           # Tests for shared modules
├── lambda/                     # Individual Lambda functions
│   ├── function_name/         # Each lambda in its own directory
│   │   ├── main.tf            # Terraform configuration
│   │   ├── variables.tf       # Terraform variables
│   │   ├── outputs.tf         # Terraform outputs
│   │   ├── src/python/        # Lambda-specific source code
│   │   │   └── function_name_lambda/
│   │   │       ├── BUILD      # Pants build configuration
│   │   │       └── lambda_function.py # Handler implementation
│   │   └── test/python/       # Lambda-specific tests
│   │       ├── BUILD          # Test build configuration
│   │       └── test_lambda_function.py
├── terraform/                  # Global infrastructure
│   ├── environments/          # Environment-specific configs
│   │   ├── dev/
│   │   ├── staging/
│   │   └── prod/
│   └── modules/               # Reusable Terraform modules
│       ├── iam/               # IAM roles and policies
│       ├── vpc/               # VPC configuration
│       └── monitoring/        # CloudWatch and alerting
├── scripts/                    # Utility scripts
├── docs/                       # Documentation
├── BUILD                       # Root build file
├── pants.toml                  # Pants configuration
├── requirements.txt            # Python dependencies
├── ruff.toml                   # Code formatting configuration
├── get-pants.sh               # Pants installation script
├── .gitignore                 # Git ignore patterns
└── README.md                  # Project documentation
```

## Directory Purposes

### Root Level Files

#### `pants.toml`
Central configuration for the Pants build system:
```toml
[GLOBAL]
pants_version = "2.27.0"
backend_packages.add = [
    "pants.backend.awslambda.python",
    "pants.backend.python",
    "pants.backend.python.typecheck.mypy"
]

[source]
root_patterns = ["src/*", "test/*"]

[python]
interpreter_constraints = ["==3.11.*"]
```

#### `BUILD`
Root build file for project-wide dependencies:
```python
python_requirements(name="root")
```

#### `requirements.txt`
Project dependencies:
```
aws-lambda-powertools[aws-sdk]>=2.37.0
boto3>=1.34.0
pydantic>=2.7.1
pytest>=7.2.0
```

### Common Directory

The `common/` directory contains shared code used across multiple lambdas.

#### Structure
```
common/
├── src/python/
│   ├── auth/                  # Authentication and authorization
│   │   ├── __init__.py
│   │   ├── jwt_handler.py
│   │   └── BUILD
│   ├── database/              # Database connections and ORM
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── BUILD
│   ├── models/                # Shared Pydantic models
│   │   ├── __init__.py
│   │   ├── request_models.py
│   │   ├── response_models.py
│   │   └── BUILD
│   └── utils/                 # Common utilities
│       ├── __init__.py
│       ├── logging.py
│       ├── validation.py
│       └── BUILD
└── test/python/               # Tests for shared modules
    ├── auth/
    ├── database/
    ├── models/
    └── utils/
```

#### Example BUILD Files

**`common/src/python/BUILD`:**
```python
python_sources(name="lib")
```

**`common/src/python/database/BUILD`:**
```python
python_sources(name="lib")
```

### Lambda Directory

Each lambda function has its own directory with a consistent structure.

#### Lambda Structure
```
lambda/user_management/
├── main.tf                    # Terraform configuration
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── src/python/
│   └── user_management_lambda/
│       ├── BUILD              # Build configuration
│       ├── lambda_function.py # Main handler
│       └── business_logic.py  # Business logic (optional)
└── test/python/
    ├── BUILD                  # Test build configuration
    ├── test_lambda_function.py
    └── test_business_logic.py
```

#### Lambda BUILD File Example

**`lambda/user_management/src/python/user_management_lambda/BUILD`:**
```python
python_sources(name="function")

python_aws_lambda_function(
    name="lambda",
    runtime="python3.11",
    handler="lambda_function.py:lambda_handler",
    include_requirements=False,
)

python_aws_lambda_layer(
    name="layer",
    runtime="python3.11",
    dependencies=[
        ":function",
        "//common/src/python/auth:lib",
        "//common/src/python/database:lib",
        "//common/src/python/models:lib",
        "//:root#boto3",
        "//:root#pydantic"
    ],
    include_sources=False,
)
```

#### Lambda Function Example

**`lambda/user_management/src/python/user_management_lambda/lambda_function.py`:**
```python
"""User management Lambda function"""

import json
from typing import Any, Dict

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from models.request_models import UserRequest
from models.response_models import UserResponse
from database.connection import get_database_connection

logger = Logger()


def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Handle user management requests.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
    """
    try:
        # Parse and validate request
        request = UserRequest.model_validate(json.loads(event.get("body", "{}")))
        
        # Process request
        result = process_user_request(request)
        
        # Return response
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": result.model_dump_json()
        }
        
    except Exception as e:
        logger.error("Error processing request", extra={"error": str(e)})
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error"})
        }


def process_user_request(request: UserRequest) -> UserResponse:
    """Process user management business logic.
    
    Args:
        request: Validated user request
        
    Returns:
        User response
    """
    # Business logic implementation
    pass
```

### Terraform Directory

Infrastructure as Code organization for different environments and reusable modules.

#### Structure
```
terraform/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── prod/
│       ├── main.tf
│       ├── variables.tf
│       └── terraform.tfvars
└── modules/
    ├── iam/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    ├── vpc/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── outputs.tf
    └── lambda/
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

## Naming Conventions

### Directory Names
- **Lambda directories**: `snake_case` (e.g., `user_management`, `data_processor`)
- **Common modules**: `snake_case` (e.g., `database`, `auth`, `utils`)
- **Terraform modules**: `snake_case` (e.g., `iam`, `vpc`, `monitoring`)

### File Names
- **Python files**: `snake_case.py` (e.g., `lambda_function.py`, `user_service.py`)
- **Terraform files**: Standard names (`main.tf`, `variables.tf`, `outputs.tf`)
- **BUILD files**: Always named `BUILD`

### Python Naming
- **Modules**: `snake_case`
- **Classes**: `PascalCase`
- **Functions**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`

### AWS Resource Names
- **Lambda functions**: `kebab-case` (e.g., `user-management-lambda`)
- **IAM roles**: `kebab-case` (e.g., `lambda-execution-role`)
- **S3 buckets**: `kebab-case` (e.g., `my-project-artifacts`)

## Build Configuration Patterns

### Source Roots
Pants recognizes these patterns as source roots:
- `src/*` - Source code directories
- `test/*` - Test directories

This allows imports like:
```python
from database.connection import get_connection
from models.user_models import User
```

### Dependency Management

#### Internal Dependencies
```python
# In lambda BUILD file
dependencies=[
    "//common/src/python/database:lib",
    "//common/src/python/models:lib",
]
```

#### External Dependencies
```python
# In lambda BUILD file
dependencies=[
    "//:root#boto3",
    "//:root#pydantic",
]
```

### Layer Configuration

#### Basic Layer
```python
python_aws_lambda_layer(
    name="layer",
    runtime="python3.11",
    dependencies=[":function", "//:root"],
    include_sources=False,
)
```

#### Optimized Layer (separate dependencies)
```python
python_aws_lambda_layer(
    name="layer",
    runtime="python3.11",
    dependencies=[
        ":function",
        "//common/src/python/database:lib",
        "//:root#boto3"
    ],
    include_sources=False,
)
```

## Testing Structure

### Test Organization
```
test/python/
├── unit/                      # Unit tests
│   ├── test_lambda_function.py
│   └── test_business_logic.py
├── integration/               # Integration tests
│   ├── test_database_integration.py
│   └── test_api_integration.py
└── fixtures/                  # Test fixtures and data
    ├── sample_events.json
    └── mock_responses.json
```

### Test BUILD Configuration
```python
python_sources(name="tests")

python_tests(
    name="unit_tests",
    sources=["unit/**/*.py"],
)

python_tests(
    name="integration_tests",
    sources=["integration/**/*.py"],
)
```

## Environment Configuration

### Development Environment
- Local development in dev container
- Isolated AWS resources
- Debug logging enabled
- Relaxed security for testing

### Staging Environment
- Production-like configuration
- Integration testing
- Performance testing
- Security validation

### Production Environment
- Optimized performance settings
- Enhanced monitoring
- Strict security policies
- Backup and disaster recovery

## Best Practices

### Code Organization
1. **Single Responsibility**: Each lambda should have a focused purpose
2. **Shared Code**: Extract common functionality to `common/` directory
3. **Layered Architecture**: Separate business logic from lambda handlers
4. **Configuration**: Use environment variables and Terraform variables

### Build Configuration
1. **Minimal Dependencies**: Only include necessary dependencies in layers
2. **Source Separation**: Keep source and test code separate
3. **Consistent Naming**: Follow established naming conventions
4. **Documentation**: Include BUILD file comments for complex configurations

### Infrastructure
1. **Environment Separation**: Use separate Terraform workspaces/directories
2. **Module Reuse**: Create reusable Terraform modules
3. **State Management**: Use remote state storage
4. **Security**: Follow least privilege principle for IAM roles

### Testing
1. **Comprehensive Coverage**: Test both unit and integration scenarios
2. **Mock External Dependencies**: Use mocks for AWS services in unit tests
3. **Test Data**: Use fixtures for consistent test data
4. **Continuous Testing**: Run tests in CI/CD pipeline

This structure provides a scalable foundation for AWS Lambda monorepos that can grow from simple single-function projects to complex multi-service applications.