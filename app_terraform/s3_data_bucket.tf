locals {
  # S3 data bucket name convention: app-<app_name_short>-<name>-<env>[-<developer>]
  s3_data_bucket_name = "${local.resource_prefix}-common-po-data-${local.resource_suffix}"

  # All known S3 data bucket prefixes
  s3_data_prefixes = ["incoming", "llm-extract", "ocr-data", "ocr-jobs", "output"]

  # Build lifecycle rules: one rule per (hacat_code, prefix)
  s3_data_lifecycle_rules = flatten([
    for code_key, code in var.hacat_codes : [
      for prefix in local.s3_data_prefixes : {
        id = "Expire ${prefix} for ${code}"
        filter = {
          prefix = "${code}/${prefix}/"
        }
        expiration = {
          days = lookup(var.s3_data_prefix_retention_days, prefix, var.s3_data_default_retention_days)
        }
        transition = null
      }
    ]
  ])
}

module "s3_data_bucket" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/s3_bucket/aws"
  version = var.jfrog_module_versions["s3_bucket"]

  bucket_name = local.s3_data_bucket_name
  kms_key_id  = module.kms_data.kms_key_id

  lifecycle_rules = local.s3_data_lifecycle_rules

  tags = merge(local.standard_tags, {
    CE_DataSensitivity = "Internal"
  })
}

data "aws_iam_policy_document" "s3_data_bucket_policy" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket",
      "s3:PutObject"
    ]
    resources = [
      "arn:${local.aws_partition}:s3:::${local.s3_data_bucket_name}",
      "arn:${local.aws_partition}:s3:::${local.s3_data_bucket_name}/*"
    ]
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:PrincipalArn"
      values   = ["arn:${local.aws_partition}:iam::${data.aws_caller_identity.current.account_id}:role/${local.iam_prefix}-lambda-*"]
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
      "arn:${local.aws_partition}:s3:::${local.s3_data_bucket_name}",
      "arn:${local.aws_partition}:s3:::${local.s3_data_bucket_name}/*"
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

resource "aws_s3_bucket_policy" "s3_data_bucket" {
  bucket = module.s3_data_bucket.bucket_name
  policy = data.aws_iam_policy_document.s3_data_bucket_policy.json
}

# Upload the optional mapping.json file for each HACAT that defines a mapping S3 key.
# Uses the SAME filter as module.hacat_mapping_s3_key_parameter so the object key and
# the mappingS3Key SSM parameter value stay in sync (both from var.hacat_mapping_s3_key).
# Terraform owns the object content and re-uploads whenever the source file changes.
resource "aws_s3_object" "hacat_mapping_file" {
  for_each = {
    for map_key, entry in local.hacat_codes_map :
    map_key => entry
    if trimspace(var.hacat_mapping_s3_key[entry.key]) != ""
  }

  bucket       = module.s3_data_bucket.bucket_name
  key          = var.hacat_mapping_s3_key[each.value.key]
  source       = "${path.module}/../app_src/app/prompts/${each.value.key}/mappings.json"
  source_hash  = filemd5("${path.module}/../app_src/app/prompts/${each.value.key}/mappings.json")
  content_type = "application/json"

  server_side_encryption = "aws:kms"
  kms_key_id             = module.kms_data.kms_key_arn

  tags = {
    CE_DataSensitivity = "Internal"
  }
}
