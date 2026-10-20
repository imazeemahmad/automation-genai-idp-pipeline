module "s3_bucket_project" {
  source = "../modules/s3/s3_bucket"

  bucket_name   = "${local.lambda_prefix}-bucket"
  bucket_policy = data.aws_iam_policy_document.s3_bucket_policy.json
  kms_key_id    = module.kms.kms_key_id

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
      "arn:aws:s3:::${module.s3_bucket_project.bucket_name}",
      "arn:aws:s3:::${module.s3_bucket_project.bucket_name}/*"
    ]
    principals {
      type        = "AWS"
      identifiers = [data.aws_iam_role.existing.arn]
    }
  }
}