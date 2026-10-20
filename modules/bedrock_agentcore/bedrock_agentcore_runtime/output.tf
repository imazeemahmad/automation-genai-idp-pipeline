output "agent_runtime_id" {
  value       = aws_bedrockagentcore_agent_runtime.agent.agent_runtime_id
  description = "Bedrock Agent Runtime id"
}

output "agent_runtime_arn" {
  value       = aws_bedrockagentcore_agent_runtime.agent.agent_runtime_arn
  description = "Bedrock Agent Runtime ARN"
}

output "role_arn" {
  value       = var.role_arn
  description = "IAM role ARN used by the Bedrock Agent Runtime"
}
