# -----------------------------------------------------------------------------
# External IAM Role — Snowflake Lambda read access to Coupa tables
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "snowflake_read_coupa_tables_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = ["arn:${local.aws_partition}:iam::${local.aws_account_id}:root"]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:PrincipalArn"
      values   = ["arn:${local.aws_partition}:iam::${local.aws_account_id}:role/${local.iam_prefix}-lambda-*"]
    }
  }
}

data "aws_iam_policy_document" "snowflake_read_coupa_tables_policy" {
  statement {
    sid    = "S3BiomarkerProcessAccess"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]

    resources = [
      "arn:${local.aws_partition}:s3:::${var.snowflake_biomarker_s3_bucket_name}",
      "arn:${local.aws_partition}:s3:::${var.snowflake_biomarker_s3_bucket_name}/*",
    ]
  }
}

resource "aws_iam_policy" "snowflake_read_coupa_tables_access" {
  name        = "${local.iam_prefix}-ext-sf-read-coupa-tables-${local.iam_suffix}"
  description = "Allow Snowflake Lambda to read Coupa tables (external access)"
  policy      = data.aws_iam_policy_document.snowflake_read_coupa_tables_policy.json
}

resource "aws_iam_role" "snowflake_read_coupa_tables_access" {
  name                 = "${local.iam_prefix}-ext-sf-read-coupa-tables-${local.iam_suffix}"
  assume_role_policy   = data.aws_iam_policy_document.snowflake_read_coupa_tables_assume_role.json
  permissions_boundary = "arn:${local.aws_partition}:iam::${local.aws_account_id}:policy/CE_AppAdminBoundary"
  tags                 = merge(local.standard_tags, {})
}

resource "aws_iam_role_policy_attachment" "snowflake_read_coupa_tables_access" {
  role       = aws_iam_role.snowflake_read_coupa_tables_access.name
  policy_arn = aws_iam_policy.snowflake_read_coupa_tables_access.arn
}

# -----------------------------------------------------------------------------
# Policy allowing Lambda roles to assume the Snowflake Coupa tables role
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "allow_assume_snowflake_coupa_role" {
  statement {
    sid     = "AllowAssumeSnowflakeCoupaRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    resources = [
      aws_iam_role.snowflake_read_coupa_tables_access.arn,
    ]
  }
}

resource "aws_iam_policy" "allow_assume_snowflake_coupa_role" {
  name        = "${local.iam_prefix}-ext-assume-sf-coupa-role-${local.iam_suffix}"
  description = "Allow Lambda roles to assume the Snowflake Coupa tables access role"
  policy      = data.aws_iam_policy_document.allow_assume_snowflake_coupa_role.json
}
