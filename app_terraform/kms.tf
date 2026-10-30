resource "random_string" "kms_suffix" {
  length  = 4
  special = false
  upper   = false
}

locals {
  # KMS key alias conventions: app-<app_name_short>-<region_short>-<purpose>-<random>-<env>[-<developer>]
  kms_data_alias_name      = "${local.resource_prefix}-kms-data-${random_string.kms_suffix.result}-${local.resource_suffix}"
  kms_messaging_alias_name = "${local.resource_prefix}-kms-messaging-${random_string.kms_suffix.result}-${local.resource_suffix}"
  kms_ssm_alias_name       = "${local.resource_prefix}-kms-ssm-${random_string.kms_suffix.result}-${local.resource_suffix}"
  kms_ecr_alias_name       = "${local.resource_prefix}-kms-ecr-${random_string.kms_suffix.result}-${local.resource_suffix}"
}

# -----------------------------------------------------------------------------
# KMS Key: Data (S3 data bucket + DynamoDB)
# Used by: Lambda roles (via IAM policy delegation)
# -----------------------------------------------------------------------------

module "kms_data" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/kms_symmetric_key/aws"
  version = var.jfrog_module_versions["kms_symmetric_key"]

  iam_role_administrator = [
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
    data.aws_iam_role.github_bootstrap.arn,
  ]
  # Root enables IAM policy-based delegation — avoids chicken-and-egg with Lambda roles
  iam_role_encrypt = [
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:root",
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
    data.aws_iam_role.github_bootstrap.arn,
  ]
  iam_role_decrypt = [
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:root",
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
    data.aws_iam_role.github_bootstrap.arn,
    data.aws_iam_role.github_deploy.arn,
  ]
  deletion_window_in_days = 30
  key_alias               = local.kms_data_alias_name
  allowed_services        = ["s3", "dynamodb"]
  tags                    = merge(local.standard_tags, {})
}

# -----------------------------------------------------------------------------
# KMS Key: Messaging (SNS + SQS)
# Used by: Step Function role, EventBridge service (via IAM policy delegation)
# -----------------------------------------------------------------------------

module "kms_messaging" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/kms_symmetric_key/aws"
  version = var.jfrog_module_versions["kms_symmetric_key"]

  iam_role_administrator = [
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
    data.aws_iam_role.github_bootstrap.arn,
  ]
  iam_role_encrypt = [
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:root",
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
    data.aws_iam_role.github_bootstrap.arn,
  ]
  iam_role_decrypt = [
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:root",
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
    data.aws_iam_role.github_bootstrap.arn,
    data.aws_iam_role.github_deploy.arn,
  ]
  deletion_window_in_days = 30
  key_alias               = local.kms_messaging_alias_name
  allowed_services        = ["sns", "sqs"]
  tags                    = merge(local.standard_tags, {})
}

# -----------------------------------------------------------------------------
# KMS Key: SSM (SecureString parameters)
# Used by: Lambda roles (via IAM policy delegation)
# -----------------------------------------------------------------------------

module "kms_ssm" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/kms_symmetric_key/aws"
  version = var.jfrog_module_versions["kms_symmetric_key"]

  iam_role_administrator = [
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
    data.aws_iam_role.github_bootstrap.arn,
  ]
  iam_role_encrypt = [
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:root",
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
    data.aws_iam_role.github_bootstrap.arn,
  ]
  iam_role_decrypt = [
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:root",
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
    data.aws_iam_role.github_bootstrap.arn,
    data.aws_iam_role.github_deploy.arn,
  ]
  deletion_window_in_days = 30
  key_alias               = local.kms_ssm_alias_name
  allowed_services        = []
  tags                    = merge(local.standard_tags, {})
}

# -----------------------------------------------------------------------------
# KMS Key: ECR (container image encryption)
# Used by: GitHub CI/CD roles, Lambda service (image pull)
# -----------------------------------------------------------------------------

module "kms_ecr" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/kms_symmetric_key/aws"
  version = var.jfrog_module_versions["kms_symmetric_key"]

  iam_role_administrator = [
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
    data.aws_iam_role.github_bootstrap.arn,
  ]
  iam_role_encrypt = [
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:root",
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
    data.aws_iam_role.github_bootstrap.arn,
  ]
  iam_role_decrypt = [
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:root",
    "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
    data.aws_iam_role.github_bootstrap.arn,
    data.aws_iam_role.github_deploy.arn,
  ]
  deletion_window_in_days = 30
  key_alias               = local.kms_ecr_alias_name
  allowed_services        = []
  tags                    = merge(local.standard_tags, {})
}

# -----------------------------------------------------------------------------
# KMS IAM Policies — one per key, grants encrypt/decrypt via IAM delegation
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "policy_kms_data" {
  statement {
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]
    effect    = "Allow"
    resources = [module.kms_data.kms_key_arn]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/app_name_short"
      values   = [var.app_name_short]
    }
  }
}

resource "aws_iam_policy" "policy_kms_data" {
  name        = "${local.iam_prefix}-kms-data-${local.iam_suffix}"
  description = "Allow encrypt/decrypt on the data KMS key (S3 + DynamoDB)"
  policy      = data.aws_iam_policy_document.policy_kms_data.json
}

data "aws_iam_policy_document" "policy_kms_messaging" {
  statement {
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]
    effect    = "Allow"
    resources = [module.kms_messaging.kms_key_arn]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/app_name_short"
      values   = [var.app_name_short]
    }
  }
}

resource "aws_iam_policy" "policy_kms_messaging" {
  name        = "${local.iam_prefix}-kms-messaging-${local.iam_suffix}"
  description = "Allow encrypt/decrypt on the messaging KMS key (SNS + SQS)"
  policy      = data.aws_iam_policy_document.policy_kms_messaging.json
}

data "aws_iam_policy_document" "policy_kms_ssm" {
  statement {
    actions = [
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]
    effect    = "Allow"
    resources = [module.kms_ssm.kms_key_arn]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/app_name_short"
      values   = [var.app_name_short]
    }
  }
}

resource "aws_iam_policy" "policy_kms_ssm" {
  name        = "${local.iam_prefix}-kms-ssm-${local.iam_suffix}"
  description = "Allow encrypt/decrypt on the SSM KMS key"
  policy      = data.aws_iam_policy_document.policy_kms_ssm.json
}
