variable "github_repositories" {
  description = "List of GitHub repositories that can assume these roles"
  type        = list(string)
  validation {
    condition     = length(var.github_repositories) > 0
    error_message = "At least one GitHub repository must be specified."
  }
}

variable "deploy_repositories" {
  description = "List of GitHub deploy code repositories that can assume the deploy role"
  type        = list(string)
  validation {
    condition     = length(var.deploy_repositories) > 0
    error_message = "At least one GitHub deploy repository must be specified."
  }
}

variable "source_branch" {
  description = "Source branch (GitHub context)"
  type        = string
}

variable "permissions_boundary_policy_name" {
  description = "Name of the existing permissions boundary policy"
  type        = string
}

variable "github_oidc_provider_url" {
  description = "URL of the GitHub OIDC provider"
  type        = string
  default     = "https://token.actions.githubusercontent.com"
}

variable "tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default = {
    ManagedBy = "Terraform"
    Module    = "bootstrap-roles"
  }
}

variable "app_name_short" {
  description = "Short name of the application"
  type        = string
}

variable "iam_policy_path" {
  description = "Base path where IAM policy JSON files are stored"
  type        = string
}

variable "iam_policy_filedef" {
  description = "file name of the IAM policy JSON file"
  type        = string
  default     = "github_policyfile.json"
}