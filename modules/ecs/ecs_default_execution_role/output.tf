output "role_arn" {
  value       = module.execution_role.role_arn
  description = "The ARN of the default ECS execution role"
}
