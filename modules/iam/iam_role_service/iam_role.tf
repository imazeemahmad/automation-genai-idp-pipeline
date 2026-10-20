data "aws_caller_identity" "current" {
}

locals {
  aws_account_id = data.aws_caller_identity.current.account_id
  # If it's an EC2 role, automatically add the standard EC2 policy
  ec2_policy_arn = (var.aws_service == "ec2") ? "arn:aws:iam::${local.aws_account_id}:policy/ce-ExampleSSM-PolicyforEC2" : ""
  ec2_policy_map = local.ec2_policy_arn != "" ? { ec2_policy = local.ec2_policy_arn } : {}

  managed_policies = merge(
    var.managed_policies_arns,
    local.ec2_policy_map
  )
}

resource "aws_iam_role" "app" {
  name                 = var.role_name
  assume_role_policy   = data.aws_iam_policy_document.assume_role.json
  permissions_boundary = "arn:aws:iam::${local.aws_account_id}:policy/CE_AppAdminBoundary"
  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:iam_role_service"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "1.2.0"
  })
}

resource "aws_iam_role_policy_attachment" "attachment" {
  for_each = local.managed_policies

  role       = resource.aws_iam_role.app.name
  policy_arn = each.value
}

resource "aws_iam_role_policy" "inline" {
  for_each = var.inline_policies_json

  role   = resource.aws_iam_role.app.name
  name   = each.key
  policy = each.value
}

# If it's an EC2 Role, create an instance profile
resource "aws_iam_instance_profile" "app" {
  count = var.aws_service == "ec2" ? 1 : 0
  name  = var.role_name
  role  = aws_iam_role.app.name
  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:iam_role_service"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "1.2.0"
  })
}

# Create a trust to the right AWS service
data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["${var.aws_service}.amazonaws.com"]
    }
  }
}
