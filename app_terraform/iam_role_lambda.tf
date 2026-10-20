data "aws_iam_policy_document" "allow_put_events" {
  statement {
    actions   = ["events:PutEvents"]
    effect    = "Allow"
    resources = ["arn:aws:events:${local.aws_region_name}:${local.aws_account_id}:event-bus/default"]
  }
}

resource "aws_iam_policy" "allow_put_events" {
  name        = "${local.iam_prefix}_allow_put_events"
  description = "allow put events policy"
  policy      = data.aws_iam_policy_document.allow_put_events.json
}

data "aws_iam_policy_document" "policy_write_cloudwatch_logs" {
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams"
    ]
    effect    = "Allow"
    resources = ["arn:aws:logs:${local.aws_region_name}:${local.aws_account_id}:log-group:*"]
  }
}

resource "aws_iam_policy" "policy_write_cloudwatch_logs" {
  name        = "${local.iam_prefix}_write_cloudwatch_logs"
  description = "lambda cloudwatch policy"
  policy      = data.aws_iam_policy_document.policy_write_cloudwatch_logs.json
}

data "aws_iam_policy_document" "policy_s3_read_write_access" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket"
    ]
    effect    = "Allow"
    resources = ["arn:aws:s3:::${module.s3_bucket_project.bucket_name}/*"]
  }
  statement {
    actions = [
      "s3:PutObject"
    ]
    effect    = "Allow"
    resources = ["arn:aws:s3:::${module.s3_bucket_project.bucket_name}/*"]
  }
}

resource "aws_iam_policy" "policy_s3_read_write_access" {
  name        = "${local.iam_prefix}_s3_read_write_access"
  description = "A S3 read write policy"
  policy      = data.aws_iam_policy_document.policy_s3_read_write_access.json
}

data "aws_iam_policy_document" "policy_s3_data_read_write" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket"
    ]
    effect = "Allow"
    resources = [
      "arn:aws:s3:::${module.s3_data_bucket.bucket_name}",
      "arn:aws:s3:::${module.s3_data_bucket.bucket_name}/*"
    ]
  }
  statement {
    actions = [
      "s3:PutObject"
    ]
    effect = "Allow"
    resources = [
      "arn:aws:s3:::${module.s3_data_bucket.bucket_name}/*"
    ]
  }
}

resource "aws_iam_policy" "policy_s3_data_read_write" {
  name        = "${local.iam_prefix}_s3_data_read_write"
  description = "Allow Lambda read/write access to the data S3 bucket"
  policy      = data.aws_iam_policy_document.policy_s3_data_read_write.json
}


module "lambda_rotation_role" {
  source = "../modules/iam/iam_role_service"

  role_name   = "${local.iam_prefix}_lambda_rotation_role"
  aws_service = "lambda"
  managed_policies_arns = {
    policy_1 = aws_iam_policy.allow_put_events.arn
    policy_2 = aws_iam_policy.policy_write_cloudwatch_logs.arn
  }
  tags = merge(local.standard_tags, {})
}

module "role_lambda_function" {
  source = "../modules/iam/iam_role_service"

  role_name   = "${local.iam_prefix}_lambda_role"
  aws_service = "lambda"
  managed_policies_arns = {
    policy_1 = aws_iam_policy.allow_put_events.arn
    policy_2 = aws_iam_policy.policy_write_cloudwatch_logs.arn
    policy_3 = aws_iam_policy.policy_s3_read_write_access.arn
    policy_4 = aws_iam_policy.policy_ecr_pull.arn
    policy_5 = aws_iam_policy.policy_s3_data_read_write.arn
  }
  tags = merge(local.standard_tags, {})
}

data "aws_iam_policy_document" "policy_ecr_pull" {
  statement {
    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability"
    ]
    effect    = "Allow"
    resources = [module.ecr.ecr_repository_arn]
  }
  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    effect    = "Allow"
    resources = ["*"]
  }
}

resource "aws_iam_policy" "policy_ecr_pull" {
  name        = "${local.iam_prefix}_ecr_pull"
  description = "Allow pulling images from ECR"
  policy      = data.aws_iam_policy_document.policy_ecr_pull.json
}
