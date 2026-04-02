# Development Workflow Guide

This guide covers the daily development workflow for AWS Lambda monorepos using Pants and dev containers.

## Daily Development Workflow

### 1. Start Development Session

```bash
# Always start with ensuring container is running
./bin/start-devcontainer.sh

# Open interactive shell for multiple commands
./bin/terminal.sh
```

### 2. Code Development Cycle

```bash
# Inside container - run these commands in sequence

# 1. Format code
pants fix ::

# 2. Run linting
pants lint ::

# 3. Type checking
pants check ::

# 4. Run tests
pants test ::
```

### 3. Building and Packaging

```bash
# Build specific lambda
pants package lambda/my_lambda/src/python/my_lambda_lambda::

# Build all lambdas
pants package ::

# Check build artifacts
ls -la dist/
```

## Container Management

### Starting Development

```bash
# Start container (idempotent - safe to run multiple times)
./bin/start-devcontainer.sh

# Verify container is running
docker ps | grep devcontainer
```

### Working in Container

**Option 1: Interactive Shell (Recommended for multiple commands)**
```bash
./bin/terminal.sh
# Now you're inside the container
pants fix ::
pants test ::
```

**Option 2: Single Commands**
```bash
./bin/exec-in-devcontainer.sh pants test lambda/my_lambda/test/python::
./bin/exec-in-devcontainer.sh pants package lambda/my_lambda/src/python::
```

### Stopping Development

```bash
# Stop container when switching projects or done for the day
./bin/stop-devcontainer.sh
```

## Code Quality Workflow

### Automated Formatting

```bash
# Fix all formatting issues
pants fix ::

# Fix specific directory
pants fix lambda/my_lambda/::
```

### Linting

```bash
# Run all linters
pants lint ::

# Lint specific files
pants lint lambda/my_lambda/src/python/my_lambda_lambda/lambda_function.py
```

### Type Checking

```bash
# Type check all code
pants check ::

# Type check specific module
pants check common/src/python/::
```

## Testing Workflow

### Running Tests

```bash
# Run all tests
pants test ::

# Run tests for specific lambda
pants test lambda/my_lambda/test/python/::

# Run specific test file
pants test lambda/my_lambda/test/python/test_lambda_function.py

# Run tests with coverage
pants test --coverage-py-report=html ::
```

### Test Development

```bash
# Create test file structure
mkdir -p lambda/my_lambda/test/python
touch lambda/my_lambda/test/python/test_lambda_function.py
```

**Example test file:**
```python
"""Tests for my_lambda function"""

import json
from unittest.mock import MagicMock

import pytest
from my_lambda_lambda.lambda_function import lambda_handler


def test_lambda_handler_success():
    """Test successful lambda execution"""
    event = {"test": "data"}
    context = MagicMock()
    context.aws_request_id = "test-request-id"
    
    response = lambda_handler(event, context)
    
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "message" in body
    assert body["requestId"] == "test-request-id"
```

## Lambda Development Patterns

### Creating New Lambda

```bash
# 1. Create directory structure
mkdir -p lambda/new_lambda/src/python/new_lambda_lambda
mkdir -p lambda/new_lambda/test/python

# 2. Create BUILD file
cat > lambda/new_lambda/src/python/new_lambda_lambda/BUILD << 'EOF'
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
EOF

# 3. Create lambda function
# (Copy from template or write new implementation)

# 4. Create test BUILD file
cat > lambda/new_lambda/test/python/BUILD << 'EOF'
python_sources(name="tests")
python_tests(name="test")
EOF

# 5. Test the new lambda
pants test lambda/new_lambda/test/python/::
pants package lambda/new_lambda/src/python/new_lambda_lambda::
```

### Working with Shared Code

```bash
# Create shared module
mkdir -p common/src/python/my_module
touch common/src/python/my_module/__init__.py
touch common/src/python/my_module/utils.py

# Create BUILD file for shared module
cat > common/src/python/my_module/BUILD << 'EOF'
python_sources(name="lib")
EOF

# Use in lambda by adding dependency
# In lambda BUILD file, add: "//common/src/python/my_module:lib"
```

## Debugging Workflow

### Local Testing

```bash
# Run lambda locally with test event
pants run lambda/my_lambda/src/python/my_lambda_lambda:lambda -- test_event.json
```

### Debugging with VS Code

1. Open VS Code in dev container
2. Set breakpoints in Python code
3. Use F5 to start debugging
4. Configure `.vscode/launch.json` for lambda debugging

### Log Analysis

```bash
# Check lambda logs during development
pants run lambda/my_lambda/src/python/my_lambda_lambda:lambda -- --debug
```

## Dependency Management

### Adding New Dependencies

```bash
# 1. Add to requirements.txt
echo "requests>=2.28.0" >> requirements.txt

# 2. Update lock file
pants generate-lockfiles

# 3. Use in BUILD file
# Add "//:root#requests" to dependencies
```

### Managing Lambda Layers

```bash
# Build layer with specific dependencies
python_aws_lambda_layer(
    name="custom_layer",
    runtime="python3.11",
    dependencies=["//:root#requests", "//:root#boto3"],
    include_sources=False,
)
```

## Performance Optimization

### Build Performance

```bash
# Use Pants caching
export PANTS_CACHE_ENABLED=true

# Parallel execution
pants --process-execution-local-parallelism=4 test ::

# Remote caching (if configured)
pants --remote-cache-read --remote-cache-write test ::
```

### Lambda Performance

```bash
# Check package size
pants package lambda/my_lambda/src/python/my_lambda_lambda::
ls -lh dist/lambda.my_lambda.src.python.my_lambda_lambda/

# Optimize dependencies
# Use include_requirements=False and specific layer dependencies
```

## Git Workflow Integration

### Pre-commit Hooks

```bash
# Run quality checks before commit
pants fix lint check test ::

# Create git hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
./bin/start-devcontainer.sh
./bin/exec-in-devcontainer.sh pants fix lint check test ::
EOF
chmod +x .git/hooks/pre-commit
```

### Branch Development

```bash
# Start new feature
git checkout -b feature/new-lambda

# Develop and test
./bin/start-devcontainer.sh
./bin/terminal.sh
# ... development work ...

# Quality checks
pants fix lint check test ::

# Commit and push
git add .
git commit -m "Add new lambda function"
git push origin feature/new-lambda
```

## Deployment Workflow

### Local Deployment Testing

```bash
# Build lambda
pants package lambda/my_lambda/src/python/my_lambda_lambda::

# Deploy with Terraform
cd lambda/my_lambda
terraform plan
terraform apply
```

### Environment Management

```bash
# Deploy to different environments
cd lambda/my_lambda

# Development
terraform workspace select dev
terraform apply

# Production
terraform workspace select prod
terraform apply
```

## Troubleshooting Common Issues

### Container Issues

```bash
# Container won't start
./bin/stop-devcontainer.sh
./bin/build-container.sh
./bin/start-devcontainer.sh

# Permission issues
docker system prune
./bin/build-container.sh
```

### Pants Issues

```bash
# Clear cache
pants clean-all

# Regenerate BUILD files
pants tailor ::

# Update dependencies
pants generate-lockfiles
```

### Import Issues

```bash
# Check source roots
pants roots

# Verify BUILD files
pants dependencies lambda/my_lambda/src/python/my_lambda_lambda:function
```

### AWS Issues

```bash
# Reconfigure credentials
./bin/terminal.sh
aws configure

# Test AWS access
aws sts get-caller-identity
```

## Best Practices

### Code Organization

- Keep lambdas focused and single-purpose
- Use shared modules for common functionality
- Follow consistent naming conventions
- Write comprehensive tests

### Development Habits

- Always run quality checks before committing
- Use meaningful commit messages
- Test locally before deploying
- Keep dependencies minimal and up-to-date

### Performance

- Monitor lambda cold starts
- Optimize package sizes
- Use appropriate memory settings
- Implement proper error handling

### Security

- Never commit AWS credentials
- Use IAM roles with minimal permissions
- Validate all inputs
- Log security-relevant events

## Quick Reference Commands

```bash
# Essential daily commands
./bin/start-devcontainer.sh          # Start development
./bin/terminal.sh                    # Open shell
pants fix lint check test ::        # Quality pipeline
pants package lambda/name/src/::    # Build lambda
./bin/stop-devcontainer.sh          # End session

# Debugging commands
pants dependencies target           # Check dependencies
pants peek target                   # Inspect target
pants roots                        # List source roots
docker ps                          # Check containers
```