output "step_functions_name" {
  value       = aws_sfn_state_machine.sfn_state_machine.name
  description = "Step functions name"
}

output "step_functions_arn" {
  value       = aws_sfn_state_machine.sfn_state_machine.arn
  description = "Step functions ARN"
}
