output "parameter_arn" {
  description = "The ARN of the parameter"
  value       = var.ignore_value_changes ? aws_ssm_parameter.parameter_external[0].arn : aws_ssm_parameter.parameter[0].arn
}

output "parameter_name" {
  description = "The name of the parameter"
  value       = var.ignore_value_changes ? aws_ssm_parameter.parameter_external[0].name : aws_ssm_parameter.parameter[0].name
}

output "parameter_version" {
  description = "The version of the parameter"
  value       = var.ignore_value_changes ? aws_ssm_parameter.parameter_external[0].version : aws_ssm_parameter.parameter[0].version
}

output "parameter_type" {
  description = "The type of the parameter"
  value       = var.ignore_value_changes ? aws_ssm_parameter.parameter_external[0].type : aws_ssm_parameter.parameter[0].type
}

output "iam_policy_json" {
  description = "IAM policy JSON that can be attached to roles for parameter access (only if allowed_role_arns is provided)"
  value       = length(var.allowed_role_arns) > 0 ? data.aws_iam_policy_document.allow_parameter_access[0].json : null
}

output "iam_policy_statements" {
  description = "IAM policy statements for parameter access (for use in custom policies)"
  value       = length(var.allowed_role_arns) > 0 ? data.aws_iam_policy_document.allow_parameter_access[0].statement : null
}
