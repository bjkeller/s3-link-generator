# S3 Pre-Signed URL Service

A generic AWS Lambda service that generates pre-signed S3 download URLs for authorized app clients. Built with Pants build system and Terraform for infrastructure management.

## Overview

This service provides a single API endpoint (`GET /presign`) that:
1. Authenticates the caller via API key
2. Validates the client is authorized for the requested S3 bucket
3. Returns a time-limited pre-signed download URL

The first consumer is the NACC Quick Access Link web app, but the service is designed to be reusable by any internal tool that needs pre-signed S3 URLs.

## Quick Start

1. Install prerequisites
   ```bash
   npm install -g @devcontainers/cli
   ```

2. Start development environment
   ```bash
   ./bin/build-container.sh
   ./bin/start-devcontainer.sh
   ./bin/terminal.sh
   ```

3. Build and test
   ```bash
   pants fix lint check test ::
   ```

4. Deploy
   ```bash
   pants package lambda/s3_signed_url/src/python/s3_signed_url_lambda::
   cd lambda/s3_signed_url
   terraform init
   terraform apply
   ```

## Project Structure

```
.
├── lambda/s3_signed_url/      # Pre-sign Lambda function
│   ├── src/python/            # Lambda source code
│   ├── test/python/           # Lambda tests
│   ├── main.tf                # Terraform configuration
│   ├── variables.tf           # Terraform variables
│   └── outputs.tf             # Terraform outputs
├── prompts/                   # Spec prompts for agent-driven development
│   ├── 01-lambda.md           # Lambda implementation spec
│   ├── 02-api.md              # API Gateway / SAM spec
│   └── 03-web-app.md          # Quick Access Link web app spec
├── examples/                  # Reference lambda implementations
├── bin/                       # Development scripts
├── .devcontainer/             # Dev container configuration
└── docs/                      # Documentation
```

## Development Workflow

```bash
# Start container
./bin/start-devcontainer.sh

# Open shell
./bin/terminal.sh

# Code quality pipeline
pants fix ::
pants lint ::
pants check ::
pants test ::
```

## Documentation

- [Setup Guide](docs/setup-guide.md)
- [Development Workflow](docs/development-workflow.md)
- [Project Structure](docs/project-structure.md)
- [Lambda Patterns](docs/lambda-patterns.md)
- [Deployment Guide](docs/deployment-guide.md)

## Requirements

- Docker (for dev containers)
- Node.js (for devcontainer CLI)
- AWS CLI (configured in container)
- Terraform (available in container)
