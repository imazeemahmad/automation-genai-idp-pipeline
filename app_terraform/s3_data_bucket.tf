module "s3_data_bucket" {
  source = "../modules/s3/s3_bucket"

  bucket_name   = "${local.lambda_prefix}-data"
  bucket_policy = data.aws_iam_policy_document.s3_data_bucket_policy.json
  kms_key_id    = module.kms.kms_key_id

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
      "arn:aws:s3:::${module.s3_data_bucket.bucket_name}",
      "arn:aws:s3:::${module.s3_data_bucket.bucket_name}/*"
    ]
    principals {
      type        = "AWS"
      identifiers = [module.role_lambda_function.role_arn]
    }
  }
}
