# Lambda Monorepo Template Usage Guide

This template provides everything you need to create a new AWS Lambda monorepo using Pants build system and Terraform for infrastructure.

## What's Included

### Documentation (`docs/`)
- **setup-guide.md** - Complete step-by-step setup instructions
- **development-workflow.md** - Daily development patterns and commands
- **project-structure.md** - Repository organization and naming conventions
- **lambda-patterns.md** - Implementation templates for common use cases
- **deployment-guide.md** - Terraform deployment and CI/CD integration

### Template Files (`templates/`)
- **config/** - Core configuration files (pants.toml, requirements.txt, etc.)
- **devcontainer/** - Dev container setup for consistent environments
- **scripts/** - Development helper scripts (container management)
- **lambda-example/** - Terraform templates for Lambda deployment
- **gitignore** - Comprehensive .gitignore for Python/AWS projects
- **README.md** - Project README template

### Example Implementations (`examples/`)
- **simple-lambda/** - Basic HTTP API Lambda without database
- **database-lambda/** - Lambda with database connectivity
- **common/** - Shared utilities and database connection patterns

## Quick Setup for New Project

### 1. Copy Template Files

```bash
# Create your new project directory
mkdir my-lambda-project
cd my-lambda-project

# Copy all template files
cp -r /path/to/lambda-monorepo-template/templates/config/* .
cp -r /path/to/lambda-monorepo-template/templates/devcontainer .devcontainer
cp -r /path/to/lambda-monorepo-template/templates/scripts bin
cp /path/to/lambda-monorepo-template/templates/gitignore .gitignore
cp /path/to/lambda-monorepo-template/templates/README.md .

# Copy documentation
cp -r /path/to/lambda-monorepo-template/docs .

# Copy examples for reference
cp -r /path/to/lambda-monorepo-template/examples .
```

### 2. Make Scripts Executable

```bash
chmod +x bin/*.sh
chmod +x get-pants.sh
```

### 3. Initialize Git Repository

```bash
git init
git add .
git commit -m "Initial commit with Lambda monorepo template"
```

### 4. Customize Configuration

Edit these files for your project:
- `.devcontainer/devcontainer.json` - Update project name
- `requirements.txt` - Add/remove dependencies as needed
- `README.md` - Update with your project details

### 5. Start Development

```bash
# Install devcontainer CLI
npm install -g @devcontainers/cli

# Build and start dev container
./bin/build-container.sh
./bin/start-devcontainer.sh

# Open shell and install Pants
./bin/terminal.sh
bash get-pants.sh
```

## Creating Your First Lambda

### 1. Create Directory Structure

```bash
mkdir -p lambda/my_first_lambda/src/python/my_first_lambda_lambda
mkdir -p lambda/my_first_lambda/test/python
```

### 2. Copy Example Implementation

Use the examples as starting points:
- Copy from `examples/simple-lambda/` for basic HTTP API
- Copy from `examples/database-lambda/` for database integration

### 3. Create BUILD Files

**Lambda BUILD file:**
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
    dependencies=[":function", "//:root#aws-lambda-powertools"],
    include_sources=False,
)
```

**Test BUILD file:**
```python
python_sources(name="tests")
python_tests(name="test")
```

### 4. Create Terraform Configuration

Copy from `templates/lambda-example/` and customize:
- `main.tf` - Lambda and layer resources
- `variables.tf` - Input variables
- `outputs.tf` - Output values

### 5. Test and Deploy

```bash
# Inside dev container
pants test lambda/my_first_lambda/test/python/::
pants package lambda/my_first_lambda/src/python/my_first_lambda_lambda::

# Deploy with Terraform
cd lambda/my_first_lambda
terraform init
terraform plan
terraform apply
```

## Customization Options

### Database Support

Uncomment database dependencies in `requirements.txt`:
```
# MySQL/MariaDB
pymysql>=1.1.1
sqlalchemy>=2.0.23

# PostgreSQL  
psycopg2-binary>=2.9.0

# Oracle
oracledb>=2.2.1
```

### Additional AWS Services

Add to `requirements.txt` as needed:
```
# S3 operations
boto3>=1.34.0

# DynamoDB
boto3-stubs[dynamodb]

# SQS/SNS
boto3-stubs[sqs,sns]
```

### Dev Container Features

Add to `.devcontainer/devcontainer.json`:
```json
"features": {
    "ghcr.io/devcontainers/features/node:1": {},
    "ghcr.io/devcontainers/features/java:1": {},
    "ghcr.io/devcontainers/features/go:1": {}
}
```

## Best Practices from Template

### Code Organization
- Keep lambdas focused and single-purpose
- Use `common/` directory for shared code
- Follow consistent naming conventions
- Separate source and test code

### Development Workflow
- Always use dev container for consistency
- Run quality checks before committing: `pants fix lint check test ::`
- Use meaningful commit messages
- Test locally before deploying

### Infrastructure
- Use Terraform workspaces for environments
- Keep infrastructure code with lambda code
- Use consistent variable naming
- Tag all resources appropriately

### Security
- Never commit AWS credentials
- Use IAM roles with minimal permissions
- Enable VPC configuration for database access
- Use environment variables for configuration

## Template Maintenance

### Updating Pants Version

Edit `pants.toml`:
```toml
[GLOBAL]
pants_version = "2.28.0"  # Update version
```

### Updating Python Version

Edit `pants.toml` and `.devcontainer/devcontainer.json`:
```toml
[python]
interpreter_constraints = ["==3.12.*"]  # Update version
```

```json
"image": "mcr.microsoft.com/devcontainers/python:1-3.12-bullseye"
```

### Adding New Backends

Edit `pants.toml`:
```toml
backend_packages.add = [
    "pants.backend.awslambda.python",
    "pants.backend.docker",  # Add new backend
    "pants.backend.shell"    # Add new backend
]
```

## Troubleshooting

### Container Issues
```bash
./bin/stop-devcontainer.sh
./bin/build-container.sh
./bin/start-devcontainer.sh
```

### Pants Issues
```bash
pants clean-all
pants generate-lockfiles
```

### AWS Issues
```bash
./bin/terminal.sh
aws configure
aws sts get-caller-identity
```

## Getting Help

1. **Documentation** - Check `docs/` directory for detailed guides
2. **Examples** - Review `examples/` for implementation patterns
3. **Pants Docs** - https://www.pantsbuild.org/docs
4. **AWS Lambda Docs** - https://docs.aws.amazon.com/lambda/
5. **Terraform Docs** - https://registry.terraform.io/providers/hashicorp/aws/

## Template Features Summary

✅ **Complete Development Environment**
- Dev containers with Python 3.11, AWS CLI, Terraform
- Pants build system pre-configured
- VS Code integration with extensions

✅ **Production-Ready Patterns**
- AWS Lambda Powertools for observability
- Proper error handling and logging
- Type safety with Pydantic and MyPy
- Comprehensive testing setup

✅ **Infrastructure as Code**
- Terraform templates for Lambda deployment
- Environment management with aliases
- VPC configuration support
- CloudWatch logging and monitoring

✅ **Code Quality**
- Automated formatting with Ruff
- Linting and type checking
- Pre-commit hooks ready
- Comprehensive test patterns

✅ **Scalable Architecture**
- Monorepo structure for multiple lambdas
- Shared code organization
- Consistent naming conventions
- Documentation templates

This template provides everything you need to start building production-ready AWS Lambda applications with modern development practices!