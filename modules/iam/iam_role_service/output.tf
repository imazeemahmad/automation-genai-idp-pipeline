output "role_arn" {
  value       = aws_iam_role.app.arn
  description = "ARN of the IAM role"
}

output "instance_profile_arn" {
  value       = join("", aws_iam_instance_profile.app.*.arn)
  description = "ARN of the EC2 instance profile"
}

output "role_name" {
  value       = aws_iam_role.app.name
  description = "Name of the IAM role"
}
