# -----------------------------------------------------------------------------
# External IAM Roles (assumed by Lambdas via boto3 sts:AssumeRole)
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "cedl_coupa_attachments_assume_role" {
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

data "aws_iam_policy_document" "cedl_coupa_attachments_policy" {
  statement {
    sid    = "ReadCedlUnstructuredData"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:ListBucket",
    ]

    resources = [
      "arn:${local.aws_partition}:s3:::${var.cedl_s3_bucket_name}",
      "arn:${local.aws_partition}:s3:::${var.cedl_s3_bucket_name}/*",
    ]
  }

  statement {
    sid    = "ReadWriteGenAIObjects"
    effect = "Allow"

    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
    ]

    resources = [
      "arn:${local.aws_partition}:s3:::${var.cedl_s3_bucket_name}/DUMMY_UNSTRUCTURED_DATA/GEN_AI/*",
    ]
  }

  statement {
    sid    = "ListGenAIPrefix"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]

    resources = [
      "arn:${local.aws_partition}:s3:::${var.cedl_s3_bucket_name}",
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["DUMMY_UNSTRUCTURED_DATA/GEN_AI/*"]
    }
  }

  statement {
    sid     = "AssumeRoleCrossAccount"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    resources = [
      var.cedl_cross_account_role_arn,
    ]
  }
}

resource "aws_iam_policy" "cedl_coupa_attachments_access" {
  name        = "${local.iam_prefix}-ext-cedl-coupa-attachments-access-${local.iam_suffix}"
  description = "Allow access to CEDL S3 buckets for Coupa attachments and cross-account assume role"
  policy      = data.aws_iam_policy_document.cedl_coupa_attachments_policy.json
}

resource "aws_iam_role" "cedl_coupa_attachments_access" {
  name                 = "${local.iam_prefix}-ext-cedl-coupa-attachments-access-${local.iam_suffix}"
  assume_role_policy   = data.aws_iam_policy_document.cedl_coupa_attachments_assume_role.json
  permissions_boundary = "arn:${local.aws_partition}:iam::${local.aws_account_id}:policy/CE_AppAdminBoundary"
  tags                 = merge(local.standard_tags, {})
}

resource "aws_iam_role_policy_attachment" "cedl_coupa_attachments_access" {
  role       = aws_iam_role.cedl_coupa_attachments_access.name
  policy_arn = aws_iam_policy.cedl_coupa_attachments_access.arn
}

# -----------------------------------------------------------------------------
# Policy allowing Lambda roles to assume the CEDL S3 Coupa attachments role
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "allow_assume_cedl_coupa_role" {
  statement {
    sid     = "AllowAssumeCedlCoupaRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    resources = [
      aws_iam_role.cedl_coupa_attachments_access.arn,
    ]
  }
}

resource "aws_iam_policy" "allow_assume_cedl_coupa_role" {
  name        = "${local.iam_prefix}-ext-allow-assume-cedl-coupa-role-${local.iam_suffix}"
  description = "Allow Lambda roles to assume the CEDL Coupa attachments access role"
  policy      = data.aws_iam_policy_document.allow_assume_cedl_coupa_role.json
}
