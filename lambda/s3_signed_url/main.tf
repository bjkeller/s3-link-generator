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

resource "aws_lambda_function" "main" {
  filename         = data.local_file.lambda_zip.filename
  function_name    = var.lambda_function_name
  role            = var.role_arn
  handler         = var.lambda_handler
  source_code_hash = data.local_file.lambda_zip.content_base64sha256
  runtime         = var.runtime
  timeout         = var.timeout
  memory_size     = var.memory_size
  
  layers = [aws_lambda_layer_version.dependencies.arn]
  
  # VPC configuration (uncomment if needed)
  # vpc_config {
  #   security_group_ids = var.security_group_ids
  #   subnet_ids         = var.subnet_ids
  # }
  
  environment {
    variables = merge(
      {
        POWERTOOLS_SERVICE_NAME = var.lambda_function_name
      },
      var.environment_variables
    )
  }
  
  # Enable X-Ray tracing
  tracing_config {
    mode = "Active"
  }
  
  publish = true
  
  tags = var.tags
}

data "local_file" "layer_zip" {
  filename = var.layer_file_path
}

resource "aws_lambda_layer_version" "dependencies" {
  filename            = data.local_file.layer_zip.filename
  source_code_hash    = data.local_file.layer_zip.content_base64sha256
  layer_name          = var.layer_name
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