# Store parameter in AWS Systems Manager Parameter Store
# Standard parameter - value managed by Terraform
resource "aws_ssm_parameter" "parameter" {
  count = var.ignore_value_changes ? 0 : 1

  name        = var.parameter_name
  description = var.description
  type        = var.parameter_type
  value       = var.parameter_value
  tier        = var.tier
  key_id      = var.kms_key_id
  data_type   = var.data_type

  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:ssm_parameter"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "__VERSION__"
  })
}

# Parameter with ignored value changes - for external management
resource "aws_ssm_parameter" "parameter_external" {
  count = var.ignore_value_changes ? 1 : 0

  name        = var.parameter_name
  description = var.description
  type        = var.parameter_type
  value       = var.parameter_value
  tier        = var.tier
  key_id      = var.kms_key_id
  data_type   = var.data_type

  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:ssm_parameter"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "__VERSION__"
  })

  lifecycle {
    ignore_changes = [value]
  }
}

# Migration block for users switching from managed to external
moved {
  from = aws_ssm_parameter.parameter
  to   = aws_ssm_parameter.parameter_external[0]
}

# IAM policy document that can be attached to roles
# Allows GetParameter access only to specific roles
data "aws_iam_policy_document" "allow_parameter_access" {
  count = length(var.allowed_role_arns) > 0 ? 1 : 0

  statement {
    sid    = "AllowGetParameter"
    effect = "Allow"
    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParameterHistory"
    ]
    resources = [
      var.ignore_value_changes ? aws_ssm_parameter.parameter_external[0].arn : aws_ssm_parameter.parameter[0].arn
    ]
  }

  # If using SecureString with custom KMS key, add KMS decrypt permission
  dynamic "statement" {
    for_each = var.parameter_type == "SecureString" && var.kms_key_id != null ? [1] : []
    content {
      sid    = "AllowKMSDecrypt"
      effect = "Allow"
      actions = [
        "kms:Decrypt"
      ]
      resources = [var.kms_key_id]
    }
  }
}

# Note: SSM Parameter Store does not support resource-based policies
# The above policy document should be attached to IAM roles that need access
# Use the iam_policy_json output to create an IAM policy
