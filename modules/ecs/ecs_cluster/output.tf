output "cloudwatch_log_group_arn" {
  value       = aws_cloudwatch_log_group.ecs_log_group.name
  description = "The ARN of the CloudWatch log group for the API Gateway"
}

output "cluster_id" {
  value       = aws_ecs_cluster.ecs_cluster.id
  description = "The ID of the ECS cluster"
}
