# Data source to get current AWS account ID
data "aws_caller_identity" "current" {
}
data "aws_region" "current" {}

# Data source to get the existing permissions boundary policy
data "aws_iam_policy" "permissions_boundary" {
  name = var.permissions_boundary_policy_name
}
# Data source to get the OIDC provider
data "aws_iam_openid_connect_provider" "github" {
  url = var.github_oidc_provider_url
}

# Create the list of trusted repository refs
locals {
  #
  aws_account_id          = data.aws_caller_identity.current.account_id
  aws_region_name         = data.aws_region.current.region
  # lambda prefix
  lambda_prefix           = "app-${lower(var.app_name_short)}"

  #
  policy_admin_name       = "App_Github_${var.app_name_short}_project_Admin_Access_For_Bootstrap"
  policy_name             = "App_Github_${var.app_name_short}_project_Access_For_Bootstrap"
  read_policy_name        = "App_Github_${var.app_name_short}_Read_Access_For_Bootstrap"
  deploy_policy_name      = "App_Github_${var.app_name_short}_Access_For_Deploy"

  # Default to main branch for each repo (terraform)
  branch_refs = [
    for repo in var.github_repositories : "repo:${repo}:refs/heads/${var.source_branch}"
  ]

  # branch for each repo (terraform)
  branch_deploy_refs = [
    for repo in var.deploy_repositories : "repo:${repo}:refs/heads/${var.source_branch}"
  ]

  # Add envirnment additional refs
  additional_refs = [
    for repo in var.github_repositories : "repo:${repo}:environment:*"
  ]

  # Combine all trusted refs
  all_trusted_refs = concat(local.branch_refs, local.additional_refs)

  # Combine all trusted refs
  all_deploy_refs = concat(local.branch_refs, local.additional_refs)
}

