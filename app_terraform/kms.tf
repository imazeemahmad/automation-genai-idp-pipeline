module "kms" {
  source = "../modules/kms/kms_symmetric_key"
  iam_role_administrator = [
    "arn:aws:iam::${local.aws_account_id}:role/CE_AppAdmin"
  ]
  iam_role_encrypt = [
    "arn:aws:iam::${local.aws_account_id}:role/CE_AppAdmin"
  ]
  iam_role_decrypt = [
    "arn:aws:iam::${local.aws_account_id}:role/CE_AppAdmin"
  ]
  deletion_window_in_days = 30
  key_alias               = "${local.iam_prefix}_kms_key"
  allowed_services        = ["s3", "sqs"]
  tags                    = merge(local.standard_tags, {})
}
