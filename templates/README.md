# AWS Lambda Monorepo

A serverless AWS Lambda implementation using Pants build system and Terraform for infrastructure management.

## Quick Start

1. **Install Prerequisites**
   ```bash
   npm install -g @devcontainers/cli
   ```

2. **Start Development Environment**
   ```bash
   ./bin/start-devcontainer.sh
   ./bin/terminal.sh
   ```

3. **Build and Test**
   ```bash
   pants fix lint check test ::
   ```

4. **Deploy Lambda**
   ```bash
   pants package lambda/my_lambda/src/python/my_lambda_lambda::
   cd lambda/my_lambda
   terraform init
   terraform apply
   ```

## Project Structure

```
.
├── common/                    # Shared code across lambdas
│   ├── src/python/           # Shared modules
│   └── test/python/          # Shared tests
├── lambda/                    # Individual Lambda functions
│   └── my_lambda/            # Lambda implementation
│       ├── src/python/       # Lambda source code
│       ├── test/python/      # Lambda tests
│       ├── main.tf           # Terraform configuration
│       └── variables.tf      # Terraform variables
├── bin/                       # Development scripts
├── .devcontainer/            # Dev container configuration
└── docs/                     # Documentation
```

## Development Workflow

### Daily Development
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

### Creating New Lambda
```bash
# Create directory structure
mkdir -p lambda/new_lambda/src/python/new_lambda_lambda
mkdir -p lambda/new_lambda/test/python

# Create BUILD files and implementation
# See docs/lambda-patterns.md for templates
```

### Deployment
```bash
# Build lambda
pants package lambda/my_lambda/src/python/my_lambda_lambda::

# Deploy with Terraform
cd lambda/my_lambda
terraform init
terraform plan
terraform apply
```

## Key Features

- **Pants Build System** - Modern Python monorepo management
- **Dev Containers** - Consistent development environment
- **Terraform Integration** - Infrastructure as Code
- **AWS Lambda Powertools** - Production-ready logging and tracing
- **Type Safety** - MyPy and Pydantic for robust code
- **Code Quality** - Automated formatting and linting

## Documentation

- [Setup Guide](docs/setup-guide.md) - Complete project initialization
- [Development Workflow](docs/development-workflow.md) - Daily development patterns
- [Project Structure](docs/project-structure.md) - Repository organization
- [Lambda Patterns](docs/lambda-patterns.md) - Implementation templates
- [Deployment Guide](docs/deployment-guide.md) - Terraform and AWS deployment

## Requirements

- Docker (for dev containers)
- Node.js (for devcontainer CLI)
- AWS CLI (configured in container)
- Terraform (available in container)

## Getting Help

1. Check the documentation in `docs/`
2. Review example implementations in `examples/`
3. Consult Pants documentation: https://www.pantsbuild.org/
4. AWS Lambda documentation: https://docs.aws.amazon.com/lambda/