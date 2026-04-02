# Deployment Guide

This guide covers deploying AWS Lambda functions using Terraform in a Pants monorepo environment.

## Overview

The deployment process involves:
1. Building Lambda packages with Pants
2. Deploying infrastructure with Terraform
3. Managing multiple environments
4. Monitoring and rollback procedures

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform installed (available in dev container)
- Pants build system set up
- IAM permissions for Lambda, IAM, VPC, and other required services

## Build Process

### Building Lambda Packages

```bash
# Ensure dev container is running
./bin/start-devcontainer.sh

# Build specific lambda
./bin/exec-in-devcontainer.sh pants package lambda/my_lambda/src/python/my_lambda_lambda::

# Build all lambdas
./bin/exec-in-devcontainer.sh pants package ::

# Check build artifacts
ls -la dist/
```

### Build Artifacts Structure

```
dist/
└── lambda.my_lambda.src.python.my_lambda_lambda/
    ├── lambda.zip      # Lambda function code
    ├── layer.zip       # Dependencies layer
    └── powertools.zip  # Powertools layer (if configured)
```

## Terraform Configuration

### Basic Lambda Terraform Structure

**File: `lambda/my_lambda/main.tf`**

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

# Lambda function
resource "aws_lambda_function" "main" {
  filename         = var.lambda_file_path
  function_name    = var.lambda_function_name
  role            = var.role_arn
  handler         = var.lambda_handler
  source_code_hash = filebase64sha256(var.lambda_file_path)
  runtime         = var.runtime
  timeout         = var.timeout
  memory_size     = var.memory_size
  
  layers = [
    aws_lambda_layer_version.dependencies.arn
  ]
  
  # VPC configuration (if needed)
  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [var.vpc_config] : []
    content {
      subnet_ids         = vpc_config.value.subnet_ids
      security_group_ids = vpc_config.value.security_group_ids
    }
  }
  
  environment {
    variables = var.environment_variables
  }
  
  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }
  
  publish = true
  
  tags = var.tags
}

# Lambda layer for dependencies
resource "aws_lambda_layer_version" "dependencies" {
  filename            = var.layer_file_path
  layer_name          = var.layer_name
  source_code_hash    = filebase64sha256(var.layer_file_path)
  compatible_runtimes = [var.runtime]
  
  description = "Dependencies layer for ${var.lambda_function_name}"
}

# Lambda aliases for environment management
resource "aws_lambda_alias" "dev" {
  name             = "dev"
  description      = "Development alias"
  function_name    = aws_lambda_function.main.function_name
  function_version = "$LATEST"
}

resource "aws_lambda_alias" "prod" {
  name             = "prod"
  description      = "Production alias"
  function_name    = aws_lambda_function.main.function_name
  function_version = var.prod_function_version
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.lambda_function_name}"
  retention_in_days = var.log_retention_days
  
  tags = var.tags
}

# Provisioned concurrency for production (optional)
resource "aws_lambda_provisioned_concurrency_config" "prod" {
  count = var.provisioned_concurrency > 0 ? 1 : 0
  
  function_name                     = aws_lambda_function.main.function_name
  provisioned_concurrent_executions = var.provisioned_concurrency
  qualifier                         = aws_lambda_alias.prod.name
  
  depends_on = [aws_lambda_alias.prod]
}
```

**File: `lambda/my_lambda/variables.tf`**

```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
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

variable "timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 60
}

variable "memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 128
}

variable "role_arn" {
  description = "IAM role ARN for Lambda execution"
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
}

variable "environment_variables" {
  description = "Environment variables for Lambda"
  type        = map(string)
  default     = {}
}

variable "vpc_config" {
  description = "VPC configuration for Lambda"
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}

variable "prod_function_version" {
  description = "Function version for production alias"
  type        = string
  default     = "1"
}

variable "provisioned_concurrency" {
  description = "Provisioned concurrency for production"
  type        = number
  default     = 0
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
```

**File: `lambda/my_lambda/outputs.tf`**

```hcl
output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.main.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.main.function_name
}

output "lambda_invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  value       = aws_lambda_function.main.invoke_arn
}

output "dev_alias_arn" {
  description = "ARN of the dev alias"
  value       = aws_lambda_alias.dev.arn
}

output "prod_alias_arn" {
  description = "ARN of the prod alias"
  value       = aws_lambda_alias.prod.arn
}

output "layer_arn" {
  description = "ARN of the Lambda layer"
  value       = aws_lambda_layer_version.dependencies.arn
}
```

## IAM Configuration

### Lambda Execution Role

**File: `terraform/modules/iam/lambda-role.tf`**

```hcl
# Basic Lambda execution role
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-execution-role"

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

  tags = var.tags
}

# Basic execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_execution.name
}

# VPC execution policy (if using VPC)
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  count      = var.enable_vpc ? 1 : 0
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
  role       = aws_iam_role.lambda_execution.name
}

# X-Ray tracing policy
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
  role       = aws_iam_role.lambda_execution.name
}

# Custom policy for additional permissions
resource "aws_iam_role_policy" "lambda_custom" {
  count = length(var.custom_policies) > 0 ? 1 : 0
  name  = "${var.project_name}-lambda-custom-policy"
  role  = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = var.custom_policies
  })
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}
```

## Deployment Workflows

### Single Lambda Deployment

```bash
# 1. Start dev container
./bin/start-devcontainer.sh

# 2. Build the lambda
./bin/exec-in-devcontainer.sh pants package lambda/my_lambda/src/python/my_lambda_lambda::

# 3. Navigate to lambda directory
cd lambda/my_lambda

# 4. Initialize Terraform (first time only)
terraform init

# 5. Plan deployment
terraform plan \
  -var="lambda_file_path=../../dist/lambda.my_lambda.src.python.my_lambda_lambda/lambda.zip" \
  -var="layer_file_path=../../dist/lambda.my_lambda.src.python.my_lambda_lambda/layer.zip" \
  -var="lambda_function_name=my-lambda-function" \
  -var="layer_name=my-lambda-layer" \
  -var="role_arn=arn:aws:iam::123456789012:role/lambda-execution-role"

# 6. Apply deployment
terraform apply \
  -var="lambda_file_path=../../dist/lambda.my_lambda.src.python.my_lambda_lambda/lambda.zip" \
  -var="layer_file_path=../../dist/lambda.my_lambda.src.python.my_lambda_lambda/layer.zip" \
  -var="lambda_function_name=my-lambda-function" \
  -var="layer_name=my-lambda-layer" \
  -var="role_arn=arn:aws:iam::123456789012:role/lambda-execution-role"
```

### Using Terraform Variables File

**File: `lambda/my_lambda/terraform.tfvars`**

```hcl
# Lambda configuration
lambda_function_name = "my-lambda-function"
layer_name          = "my-lambda-layer"
timeout             = 30
memory_size         = 256

# File paths (updated by deployment script)
lambda_file_path = "../../dist/lambda.my_lambda.src.python.my_lambda_lambda/lambda.zip"
layer_file_path  = "../../dist/lambda.my_lambda.src.python.my_lambda_lambda/layer.zip"

# IAM role
role_arn = "arn:aws:iam::123456789012:role/lambda-execution-role"

# Environment variables
environment_variables = {
  ENVIRONMENT = "dev"
  LOG_LEVEL   = "INFO"
}

# VPC configuration (if needed)
vpc_config = {
  subnet_ids         = ["subnet-12345", "subnet-67890"]
  security_group_ids = ["sg-abcdef"]
}

# Tags
tags = {
  Environment = "dev"
  Project     = "my-project"
  Owner       = "team-name"
}
```

### Deployment Script

**File: `scripts/deploy-lambda.sh`**

```bash
#!/bin/bash

set -euo pipefail

# Configuration
LAMBDA_NAME=${1:-""}
ENVIRONMENT=${2:-"dev"}

if [ -z "$LAMBDA_NAME" ]; then
    echo "Usage: $0 <lambda_name> [environment]"
    echo "Example: $0 my_lambda dev"
    exit 1
fi

LAMBDA_DIR="lambda/${LAMBDA_NAME}"
DIST_DIR="dist/lambda.${LAMBDA_NAME}.src.python.${LAMBDA_NAME}_lambda"

echo "Deploying Lambda: $LAMBDA_NAME to environment: $ENVIRONMENT"

# Ensure dev container is running
./bin/start-devcontainer.sh

# Build the lambda
echo "Building Lambda package..."
./bin/exec-in-devcontainer.sh pants package "lambda/${LAMBDA_NAME}/src/python/${LAMBDA_NAME}_lambda::"

# Check if build artifacts exist
if [ ! -f "${DIST_DIR}/lambda.zip" ]; then
    echo "Error: Lambda zip file not found at ${DIST_DIR}/lambda.zip"
    exit 1
fi

if [ ! -f "${DIST_DIR}/layer.zip" ]; then
    echo "Error: Layer zip file not found at ${DIST_DIR}/layer.zip"
    exit 1
fi

# Navigate to lambda directory
cd "$LAMBDA_DIR"

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    echo "Initializing Terraform..."
    terraform init
fi

# Select workspace for environment
echo "Selecting Terraform workspace: $ENVIRONMENT"
terraform workspace select "$ENVIRONMENT" || terraform workspace new "$ENVIRONMENT"

# Plan deployment
echo "Planning deployment..."
terraform plan \
    -var="lambda_file_path=../../${DIST_DIR}/lambda.zip" \
    -var="layer_file_path=../../${DIST_DIR}/layer.zip" \
    -var-file="${ENVIRONMENT}.tfvars"

# Confirm deployment
read -p "Do you want to apply these changes? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Applying deployment..."
    terraform apply \
        -var="lambda_file_path=../../${DIST_DIR}/lambda.zip" \
        -var="layer_file_path=../../${DIST_DIR}/layer.zip" \
        -var-file="${ENVIRONMENT}.tfvars"
    
    echo "Deployment completed successfully!"
else
    echo "Deployment cancelled."
fi
```

## Environment Management

### Environment-Specific Configuration

**Development (`dev.tfvars`):**
```hcl
# Development environment
lambda_function_name = "my-lambda-dev"
memory_size         = 128
timeout             = 30
log_retention_days  = 7
provisioned_concurrency = 0

environment_variables = {
  ENVIRONMENT = "dev"
  LOG_LEVEL   = "DEBUG"
  DEBUG_MODE  = "true"
}

tags = {
  Environment = "dev"
  Project     = "my-project"
}
```

**Production (`prod.tfvars`):**
```hcl
# Production environment
lambda_function_name = "my-lambda-prod"
memory_size         = 512
timeout             = 60
log_retention_days  = 30
provisioned_concurrency = 5

environment_variables = {
  ENVIRONMENT = "prod"
  LOG_LEVEL   = "INFO"
  DEBUG_MODE  = "false"
}

tags = {
  Environment = "prod"
  Project     = "my-project"
  CostCenter  = "engineering"
}
```

### Multi-Environment Deployment

```bash
# Deploy to development
./scripts/deploy-lambda.sh my_lambda dev

# Deploy to staging
./scripts/deploy-lambda.sh my_lambda staging

# Deploy to production
./scripts/deploy-lambda.sh my_lambda prod
```

## Version Management

### Lambda Versioning Strategy

```hcl
# Create new version on each deployment
resource "aws_lambda_function" "main" {
  # ... other configuration ...
  
  publish = true  # Creates new version on each update
}

# Production alias points to specific version
resource "aws_lambda_alias" "prod" {
  name             = "prod"
  function_name    = aws_lambda_function.main.function_name
  function_version = var.prod_function_version  # Controlled version
}

# Development alias points to latest
resource "aws_lambda_alias" "dev" {
  name             = "dev"
  function_name    = aws_lambda_function.main.function_name
  function_version = "$LATEST"
}
```

### Promoting Versions

```bash
# Get current latest version
LATEST_VERSION=$(aws lambda get-function \
    --function-name my-lambda-function \
    --query 'Configuration.Version' \
    --output text)

# Update production alias to latest version
terraform apply \
    -var="prod_function_version=${LATEST_VERSION}" \
    -var-file="prod.tfvars"
```

## Monitoring and Observability

### CloudWatch Configuration

```hcl
# CloudWatch alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.lambda_function_name}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors"
  
  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }
  
  alarm_actions = [var.sns_topic_arn]
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.lambda_function_name}-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "30000"  # 30 seconds
  alarm_description   = "This metric monitors lambda duration"
  
  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }
  
  alarm_actions = [var.sns_topic_arn]
}
```

### X-Ray Tracing

```hcl
# Enable X-Ray tracing
resource "aws_lambda_function" "main" {
  # ... other configuration ...
  
  tracing_config {
    mode = "Active"
  }
}

# X-Ray service map
resource "aws_xray_sampling_rule" "lambda_sampling" {
  rule_name      = "${var.lambda_function_name}-sampling"
  priority       = 9000
  version        = 1
  reservoir_size = 1
  fixed_rate     = 0.1
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_type   = "AWS::Lambda::Function"
  service_name   = var.lambda_function_name
  resource_arn   = "*"
}
```

## Rollback Procedures

### Quick Rollback

```bash
# Rollback to previous version
PREVIOUS_VERSION=$(aws lambda list-versions-by-function \
    --function-name my-lambda-function \
    --query 'Versions[-2].Version' \
    --output text)

# Update production alias
aws lambda update-alias \
    --function-name my-lambda-function \
    --name prod \
    --function-version $PREVIOUS_VERSION
```

### Terraform Rollback

```bash
# Rollback using Terraform
terraform apply \
    -var="prod_function_version=PREVIOUS_VERSION" \
    -var-file="prod.tfvars"
```

## CI/CD Integration

### GitHub Actions Example

**File: `.github/workflows/deploy-lambda.yml`**

```yaml
name: Deploy Lambda

on:
  push:
    branches: [main]
    paths: ['lambda/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        curl -L -o pants https://github.com/pantsbuild/scie-pants/releases/latest/download/scie-pants-linux-x86_64
        chmod +x pants
        ./pants --version
    
    - name: Build Lambda
      run: ./pants package ::
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Deploy with Terraform
      run: |
        cd lambda/my_lambda
        terraform init
        terraform apply -auto-approve \
          -var="lambda_file_path=../../dist/lambda.my_lambda.src.python.my_lambda_lambda/lambda.zip" \
          -var="layer_file_path=../../dist/lambda.my_lambda.src.python.my_lambda_lambda/layer.zip" \
          -var-file="prod.tfvars"
```

## Best Practices

### Security
- Use least privilege IAM roles
- Enable VPC configuration for database access
- Encrypt environment variables
- Use AWS Secrets Manager for sensitive data

### Performance
- Right-size memory allocation
- Use provisioned concurrency for consistent performance
- Optimize package size
- Monitor cold start metrics

### Cost Optimization
- Use appropriate timeout values
- Monitor unused functions
- Optimize memory vs. duration trade-offs
- Use reserved concurrency when needed

### Reliability
- Implement proper error handling
- Use dead letter queues
- Set up comprehensive monitoring
- Test rollback procedures

This deployment guide provides a comprehensive approach to deploying Lambda functions in a production environment while maintaining best practices for security, performance, and reliability.