
output "lambda_name" {
  value       = aws_lambda_function.lambda_function.function_name
  description = "Lambda function name"
}

output "lambda_arn" {
  value       = aws_lambda_function.lambda_function.arn
  description = "Lambda function arn"
}

output "lambda_qualified_arn" {
  value       = aws_lambda_function.lambda_function.qualified_arn
  description = ""
}

output "lambda_invoke_arn" {
  value       = aws_lambda_function.lambda_function.invoke_arn
  description = "Lambda function invoke ARN"
}

output "lambda_cw_log_group" {
  value       = aws_cloudwatch_log_group.lambda_log_group.arn
  description = "Log group ARN"
}
