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