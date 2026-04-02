# Technology Stack

## Kiro Pants Power

**RECOMMENDED**: This project uses the `kiro-pants-power` for automated Pants build system and devcontainer management.

The power provides MCP tools that automatically handle:
- Container lifecycle (start, stop, rebuild)
- Pants commands (fix, lint, check, test, package)
- Workflow orchestration (full_quality_check for complete validation)

All power tools automatically ensure the devcontainer is running before execution. Manual scripts in `bin/` are available as fallback.

## Development Environment

**Dev Container** — Consistent development environment using Docker.

This project uses dev containers for reproducible development environments. All commands should be executed inside the dev container.

### Container Management Scripts

Located in `bin/` directory:

- `start-devcontainer.sh` — Start the dev container (idempotent, safe to run multiple times)
- `stop-devcontainer.sh` — Stop the dev container
- `build-container.sh` — Rebuild the container after configuration changes
- `exec-in-devcontainer.sh` — Execute a command in the running container
- `terminal.sh` — Open an interactive shell in the container

**CRITICAL**: Always run `./bin/start-devcontainer.sh` before executing any commands to ensure the container is running.

## Build System

**Pants Build System** (v2.29.0) — <https://www.pantsbuild.org>

Pants is used for all builds, testing, linting, and packaging in this monorepo.

## Language & Runtime

- **Python 3.12** (strict interpreter constraint: `==3.12.*`)
- Type checking with mypy
- Pydantic v2+ for data validation
- Dev container provides Python 3.12 pre-installed

## Key Dependencies

### Core Libraries

- `aws-lambda-powertools[aws-sdk]>=2.37.0` — Lambda logging, tracing, and utilities
- `boto3>=1.34.0` — AWS SDK (S3 presign, DynamoDB/SSM for client registry)
- `botocore>=1.34.0` — Low-level AWS SDK
- `pydantic>=2.7.1` — Data validation and configuration models

### Testing

- `pytest>=7.2.0` — Test framework

## Code Quality Tools

### Linting & Formatting

- **Ruff** — Fast Python linter and formatter
  - Line length: 88 characters
  - Indent: 4 spaces
  - Target version: Python 3.12
  - Selected rules: A, B, E, W, F, I, RUF, SIM, C90, PLW0406, COM818, SLF001

### Type Checking

- **mypy**

### Testing

- **pytest**

## Infrastructure

- **Terraform** — Infrastructure as Code for Lambda deployment
- **AWS Lambda** — Serverless compute (Python 3.12 runtime)
- **AWS API Gateway** — REST API with API key authentication
- **AWS S3** — Target buckets for pre-signed URL generation
- **AWS DynamoDB or SSM** — Client registry storage (decided during spec)

## Common Commands

### Using Kiro Pants Power (Recommended)

**PREFERRED METHOD**: Use the `kiro-pants-power` tools for all Pants and devcontainer operations.

#### Code Quality Workflow

```
# Complete quality check (fix → lint → check → test)
Use: full_quality_check tool

# Individual steps — all code
Use: pants_fix tool with scope="all"
Use: pants_lint tool with scope="all"
Use: pants_check tool with scope="all"
Use: pants_test tool with scope="all"

# Individual steps — specific directory
Use: pants_fix tool with scope="directory", path="lambda/s3_signed_url/src/python"
Use: pants_test tool with scope="directory", path="lambda/s3_signed_url/test/python"

# Individual steps — single file
Use: pants_check tool with scope="file", path="lambda/s3_signed_url/src/python/s3_signed_url_lambda/lambda_function.py"
```

#### Building

```
# Build all packages
Use: pants_package tool with scope="all"

# Build specific lambda
Use: pants_package tool with scope="directory", path="lambda/s3_signed_url/src/python/s3_signed_url_lambda"
```

#### Container Management

```
Use: container_start tool    # Start container
Use: container_stop tool     # Stop container
Use: container_rebuild tool  # Rebuild after config changes
```

### Using Manual Scripts (Fallback)

```bash
# Ensure container is running (always run this first)
./bin/start-devcontainer.sh

# Code quality
./bin/exec-in-devcontainer.sh pants fix ::
./bin/exec-in-devcontainer.sh pants lint ::
./bin/exec-in-devcontainer.sh pants check ::
./bin/exec-in-devcontainer.sh pants test ::

# Build
./bin/exec-in-devcontainer.sh pants package ::
```

## Python Interpreter Setup

The dev container provides Python 3.12 pre-installed. No manual Python installation needed.

For local development outside the container, Pants searches for Python interpreters in:
1. System PATH
2. pyenv installations
