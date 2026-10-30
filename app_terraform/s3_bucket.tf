locals {
  # S3 build bucket name convention: app-<app_name_short>-<name>-<env>[-<developer>]
  s3_project_bucket_name = "${local.resource_prefix}-common-build-${local.resource_suffix}"
}

# -----------------------------------------------------------------------------
# Dedicated KMS key for the build S3 bucket
# Minimal policy: only Terraform/CI roles need access (no Lambda/SFN dependency)
# -----------------------------------------------------------------------------

resource "aws_kms_key" "s3_build_bucket_key" {
  description             = "KMS key for S3 build bucket encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowRootFullAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:${local.aws_partition}:iam::${local.aws_account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowAdministrators"
        Effect = "Allow"
        Principal = {
          AWS = [
            "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
            data.aws_iam_role.github_bootstrap.arn,
          ]
        }
        Action = [
          "kms:Create*",
          "kms:Describe*",
          "kms:Enable*",
          "kms:List*",
          "kms:Put*",
          "kms:Update*",
          "kms:Revoke*",
          "kms:Disable*",
          "kms:Get*",
          "kms:Delete*",
          "kms:TagResource",
          "kms:UntagResource",
          "kms:ScheduleKeyDeletion",
          "kms:CancelKeyDeletion"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowS3ServiceUsage"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowCIUsage"
        Effect = "Allow"
        Principal = {
          AWS = [
            "arn:${local.aws_partition}:iam::${local.aws_account_id}:role/CE_AppAdmin",
            data.aws_iam_role.github_bootstrap.arn,
            data.aws_iam_role.github_deploy.arn,
          ]
        }
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey*",
          "kms:DescribeKey",
          "kms:ReEncrypt*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(local.standard_tags, {})
}

resource "aws_kms_alias" "s3_build_bucket_key_alias" {
  name          = "alias/${local.s3_project_bucket_name}"
  target_key_id = aws_kms_key.s3_build_bucket_key.key_id
}

module "s3_bucket_project" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/s3_bucket/aws"
  version = var.jfrog_module_versions["s3_bucket"]

  bucket_name   = local.s3_project_bucket_name
  bucket_policy = data.aws_iam_policy_document.s3_bucket_policy.json
  kms_key_id    = aws_kms_key.s3_build_bucket_key.key_id

  lifecycle_rules = [
    {
      id = "Keep only last ${var.s3_build_noncurrent_versions_to_keep} noncurrent versions"
      noncurrent_version_expiration = {
        noncurrent_days           = 1
        newer_noncurrent_versions = var.s3_build_noncurrent_versions_to_keep
      }
      expiration = {
        expired_object_delete_marker = true
      }
    }
  ]

  tags = merge(local.standard_tags, {
    CE_DataSensitivity = "Internal"
  })
}

data "aws_iam_policy_document" "s3_bucket_policy" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
      "s3:PutObject"
    ]
    resources = [
      "arn:${local.aws_partition}:s3:::${local.s3_project_bucket_name}",
      "arn:${local.aws_partition}:s3:::${local.s3_project_bucket_name}/*"
    ]
    principals {
      type        = "AWS"
      identifiers = [data.aws_iam_role.existing.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }

  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      "arn:${local.aws_partition}:s3:::${local.s3_project_bucket_name}",
      "arn:${local.aws_partition}:s3:::${local.s3_project_bucket_name}/*"
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}
