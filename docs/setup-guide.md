# AWS Lambda Monorepo Setup Guide

This guide walks you through setting up a new AWS Lambda monorepo using Pants build system and Terraform.

## Prerequisites

Before starting, ensure you have:

- **Docker** - For dev container support
- **Node.js** - For devcontainer CLI installation
- **Git** - For version control
- **AWS CLI** - For AWS operations (can be installed in container)

## Step 1: Initialize Repository

```bash
# Create new repository
mkdir my-lambda-project
cd my-lambda-project
git init

# Copy template files
cp -r /path/to/lambda-monorepo-template/templates/* .
```

## Step 2: Install Dev Container CLI

```bash
npm install -g @devcontainers/cli
```

## Step 3: Customize Configuration Files

### 3.1 Update `pants.toml`

```toml
[GLOBAL]
pants_version = "2.27.0"
backend_packages.add = [
    "pants.backend.build_files.fmt.ruff",
    "pants.backend.awslambda.python",
    "pants.backend.python",
    "pants.backend.python.lint.docformatter",
    "pants.backend.experimental.python.lint.ruff.check",
    "pants.backend.experimental.python.lint.ruff.format",
    "pants.backend.python.typecheck.mypy"
]
pants_ignore = [
    '.devcontainer/**',
    '.vscode/**'
]

[source]
root_patterns = [
    "src/*", "test/*"
]

[python]
interpreter_constraints = ["==3.11.*"]
enable_resolves = true
resolves = { python-default = "python-default.lock"}

[python-bootstrap]
search_path = ["<PATH>", "<PYENV>"]

[python-infer]
use_rust_parser = true

[update-build-files]
formatter="ruff"
```

### 3.2 Update `requirements.txt`

**Basic Lambda Requirements:**
```
aws-lambda-powertools[aws-sdk]>=2.37.0
boto3>=1.34.0
boto3-stubs
botocore>=1.34.0
botocore-stubs
pydantic>=2.7.1
pytest>=7.2.0
```

**Add Database Support (if needed):**
```
# For MySQL/MariaDB
pymysql>=1.1.1
types-PyMySQL>=1.1.0
sqlalchemy>=2.0.23
sqlmodel>=0.0.18

# For Oracle
oracledb>=2.2.1

# For PostgreSQL
psycopg2-binary>=2.9.0
```

### 3.3 Update `.devcontainer/devcontainer.json`

```json
{
    "name": "My Lambda Project",
    "image": "mcr.microsoft.com/devcontainers/python:1-3.11-bullseye",
    "features": {
        "ghcr.io/devcontainers/features/aws-cli:1": {},
        "ghcr.io/devcontainers/features/docker-in-docker:2": {
            "version": "latest",
            "enableNonRootDocker": true,
            "moby": true
        },
        "ghcr.io/devcontainers/features/git:1": {},
        "ghcr.io/devcontainers/features/terraform:1": {
            "version": "latest",
            "tflint": "latest",
            "terragrunt": "latest"
        }
    },
    "postCreateCommand": "bash get-pants.sh",
    "customizations": {
        "vscode": {
            "settings": {
                "dev.containers.dockerCredentialHelper": false
            },
            "extensions": [
                "ms-python.python",
                "ms-python.vscode-pylance",
                "ms-azuretools.vscode-docker"
            ]
        }
    }
}
```

### 3.4 Create `ruff.toml`

```toml
line-length = 88
indent-width = 4
target-version = "py311"

[lint]
select = ["A", "B", "E", "W", "F", "I", "RUF", "SIM", "C90", "PLW0406", "COM818", "SLF001"]
```

## Step 4: Set Up Development Environment

### 4.1 Build and Start Container

```bash
# Build the dev container
./bin/build-container.sh

# Start the container
./bin/start-devcontainer.sh

# Open interactive shell
./bin/terminal.sh
```

### 4.2 Install Pants (inside container)

```bash
# Inside the container
bash get-pants.sh
```

### 4.3 Configure AWS (inside container)

```bash
# Configure AWS credentials
aws configure
```

## Step 5: Create Project Structure

### 5.1 Create Common Modules Directory

```bash
mkdir -p common/src/python
mkdir -p common/test/python
```

### 5.2 Create First Lambda

```bash
mkdir -p lambda/my_first_lambda/src/python/my_first_lambda_lambda
mkdir -p lambda/my_first_lambda/test/python
```

### 5.3 Create BUILD Files

**Root BUILD file:**
```python
python_requirements(
    name="root",
)
```

**Common BUILD file (`common/src/python/BUILD`):**
```python
python_sources(name="lib")
```

**Lambda BUILD file (`lambda/my_first_lambda/src/python/my_first_lambda_lambda/BUILD`):**
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
    dependencies=[":function", "//:root"],
    include_sources=False,
)
```

## Step 6: Create Your First Lambda

### 6.1 Lambda Function (`lambda/my_first_lambda/src/python/my_first_lambda_lambda/lambda_function.py`)

```python
"""My first Lambda function"""

import json
from typing import Any, Dict

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()


def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Lambda handler function.
    
    Args:
        event: The Lambda event
        context: The execution context
        
    Returns:
        Response object
    """
    logger.info("Processing request", extra={"event": event})
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": "Hello from Lambda!",
            "requestId": context.aws_request_id
        })
    }
```

### 6.2 Terraform Configuration (`lambda/my_first_lambda/main.tf`)

```hcl
terraform {
  required_version = ">= 1.0, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "local_file" "lambda_zip" {
  filename = var.lambda_file_path
}

resource "aws_lambda_function" "my_lambda" {
  filename         = data.local_file.lambda_zip.filename
  function_name    = var.lambda_function_name
  role            = var.role_arn
  handler         = var.lambda_handler
  source_code_hash = data.local_file.lambda_zip.content_base64sha256
  runtime         = var.runtime
  timeout         = 60
  
  layers = [aws_lambda_layer_version.lambda_layer.arn]
  
  environment {
    variables = {
      POWERTOOLS_SERVICE_NAME = var.lambda_function_name
    }
  }
  
  publish = true
}

data "local_file" "layer_zip" {
  filename = var.layer_file_path
}

resource "aws_lambda_layer_version" "lambda_layer" {
  filename            = data.local_file.layer_zip.filename
  source_code_hash    = data.local_file.layer_zip.content_base64sha256
  layer_name          = var.layer_name
  compatible_runtimes = [var.runtime]
}
```

### 6.3 Terraform Variables (`lambda/my_first_lambda/variables.tf`)

```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "my-first-lambda"
}

variable "lambda_handler" {
  description = "Lambda handler"
  type        = string
  default     = "lambda_function.lambda_handler"
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.11"
}

variable "role_arn" {
  description = "IAM role ARN for Lambda"
  type        = string
}

variable "lambda_file_path" {
  description = "Path to Lambda zip file"
  type        = string
}

variable "layer_file_path" {
  description = "Path to layer zip file"
  type        = string
}

variable "layer_name" {
  description = "Name of the Lambda layer"
  type        = string
  default     = "my-first-lambda-layer"
}
```

## Step 7: Test Your Setup

### 7.1 Build Lambda

```bash
# Inside container
pants package lambda/my_first_lambda/src/python/my_first_lambda_lambda::
```

### 7.2 Run Tests

```bash
# Inside container
pants test ::
```

### 7.3 Code Quality Checks

```bash
# Inside container
pants fix ::
pants lint ::
pants check ::
```

## Step 8: Create IAM Role (if needed)

Create `terraform/iam/main.tf`:

```hcl
resource "aws_iam_role" "lambda_role" {
  name = "lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

output "lambda_role_arn" {
  value = aws_iam_role.lambda_role.arn
}
```

## Step 9: Deploy Lambda

```bash
# Inside container, from lambda directory
cd lambda/my_first_lambda
terraform init
terraform plan
terraform apply
```

## Customization Checklist

- [ ] Update project name in `devcontainer.json`
- [ ] Customize `requirements.txt` for your needs
- [ ] Set up AWS credentials
- [ ] Create IAM roles and policies
- [ ] Configure VPC settings (if needed)
- [ ] Set up monitoring and logging
- [ ] Configure CI/CD pipeline

## Next Steps

1. Read the [Development Workflow](development-workflow.md) guide
2. Review [Lambda Patterns](lambda-patterns.md) for implementation examples
3. Check [Project Structure](project-structure.md) for organization best practices
4. Follow [Deployment Guide](deployment-guide.md) for production deployment

## Troubleshooting

### Container Issues
```bash
# Rebuild container
./bin/build-container.sh
./bin/start-devcontainer.sh
```

### Pants Issues
```bash
# Clear Pants cache
./bin/exec-in-devcontainer.sh pants clean-all
```

### AWS Issues
```bash
# Reconfigure AWS
./bin/terminal.sh
aws configure
```

## Support

- Check existing documentation in `docs/`
- Review example implementations in `examples/`
- Consult Pants documentation: https://www.pantsbuild.org/
- AWS Lambda documentation: https://docs.aws.amazon.com/lambda/