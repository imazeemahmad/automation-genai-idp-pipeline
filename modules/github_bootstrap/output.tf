output "boostrap_role" {
  description = "Details of the bootstrap role"
  value = {
    name = aws_iam_role.bootstrap.name
    arn  = aws_iam_role.bootstrap.arn
    id   = aws_iam_role.bootstrap.id
  }
}

output "deploy_role" {
  description = "Details of the deploy role"
  value = {
    name = aws_iam_role.deploy.name
    arn  = aws_iam_role.deploy.arn
    id   = aws_iam_role.deploy.id
  }
}

output "policy" {
  description = "Details of the created read policy"
  value = {
    name = aws_iam_policy.read_policy.name
    arn  = aws_iam_policy.read_policy.arn
    id   = aws_iam_policy.read_policy.id
  }
}

output "permissions_boundary_arn" {
  description = "ARN of the permissions boundary policy used"
  value       = data.aws_iam_policy.permissions_boundary.arn
}

output "github_oidc_provider_arn" {
  description = "ARN of the GitHub OIDC provider"
  value       = data.aws_iam_openid_connect_provider.github.arn
}

output "trusted_repositories" {
  description = "List of GitHub repositories that can assume these roles"
  value       = var.github_repositories
}
