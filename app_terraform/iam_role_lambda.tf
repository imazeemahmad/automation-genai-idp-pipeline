data "aws_iam_policy_document" "allow_put_events" {
  statement {
    actions   = ["events:PutEvents"]
    effect    = "Allow"
    resources = ["arn:${local.aws_partition}:events:${local.aws_region_name}:${local.aws_account_id}:event-bus/default"]
  }
}

resource "aws_iam_policy" "allow_put_events" {
  name        = "${local.iam_prefix}-allow-put-events-${local.iam_suffix}"
  description = "allow put events policy"
  policy      = data.aws_iam_policy_document.allow_put_events.json
}

# -----------------------------------------------------------------------------
# X-Ray tracing policy for Lambda functions
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "policy_lambda_xray" {
  statement {
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
      "xray:GetSamplingRules",
      "xray:GetSamplingTargets"
    ]
    effect    = "Allow"
    resources = ["*"]
  }
}

resource "aws_iam_policy" "policy_lambda_xray" {
  name        = "${local.iam_prefix}-lambda-xray-${local.iam_suffix}"
  description = "Allow Lambda functions to send traces to X-Ray"
  policy      = data.aws_iam_policy_document.policy_lambda_xray.json
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
    effect = "Allow"
    resources = [
      "arn:${local.aws_partition}:logs:${local.aws_region_name}:${local.aws_account_id}:log-group:/aws/lambda/${local.resource_prefix}-*",
      "arn:${local.aws_partition}:logs:${local.aws_region_name}:${local.aws_account_id}:log-group:/aws/lambda/${local.resource_prefix}-*:*"
    ]
  }
}

resource "aws_iam_policy" "policy_write_cloudwatch_logs" {
  name        = "${local.iam_prefix}-write-cloudwatch-logs-${local.iam_suffix}"
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
    resources = ["arn:${local.aws_partition}:s3:::${module.s3_bucket_project.bucket_name}/*"]
  }
  statement {
    actions = [
      "s3:PutObject"
    ]
    effect    = "Allow"
    resources = ["arn:${local.aws_partition}:s3:::${module.s3_bucket_project.bucket_name}/*"]
  }
}

resource "aws_iam_policy" "policy_s3_read_write_access" {
  name        = "${local.iam_prefix}-s3-read-write-access-${local.iam_suffix}"
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
      "arn:${local.aws_partition}:s3:::${module.s3_data_bucket.bucket_name}",
      "arn:${local.aws_partition}:s3:::${module.s3_data_bucket.bucket_name}/*"
    ]
  }
  statement {
    actions = [
      "s3:PutObject"
    ]
    effect = "Allow"
    resources = [
      "arn:${local.aws_partition}:s3:::${module.s3_data_bucket.bucket_name}/*"
    ]
  }
}

resource "aws_iam_policy" "policy_s3_data_read_write" {
  name        = "${local.iam_prefix}-s3-data-read-write-${local.iam_suffix}"
  description = "Allow Lambda read/write access to the data S3 bucket"
  policy      = data.aws_iam_policy_document.policy_s3_data_read_write.json
}






data "aws_iam_policy_document" "policy_dynamodb_read_write" {
  statement {
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:DeleteItem",
      "dynamodb:Query",
      "dynamodb:BatchGetItem",
      "dynamodb:BatchWriteItem"
    ]
    effect = "Allow"
    resources = [
      module.dynamodb_procurement.dynamodb_table_arn
    ]
  }
}

resource "aws_iam_policy" "policy_dynamodb_read_write" {
  name        = "${local.iam_prefix}-dynamodb-read-write-${local.iam_suffix}"
  description = "Allow Lambda read/write access to the DynamoDB procurement table"
  policy      = data.aws_iam_policy_document.policy_dynamodb_read_write.json
}

data "aws_iam_policy_document" "policy_ecr_pull" {
  statement {
    actions = [
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability"
    ]
    effect = "Allow"
    resources = [
      module.ecr.ecr_repository_arn,
      module.ecr_libreoffice_converter.ecr_repository_arn
    ]
  }
  statement {
    actions   = ["ecr:GetAuthorizationToken"]
    effect    = "Allow"
    resources = ["*"]
  }
}

resource "aws_iam_policy" "policy_ecr_pull" {
  name        = "${local.iam_prefix}-ecr-pull-${local.iam_suffix}"
  description = "Allow pulling images from ECR"
  policy      = data.aws_iam_policy_document.policy_ecr_pull.json
}

# -----------------------------------------------------------------------------
# IAM Policy — Invoke LibreOffice Converter Lambda
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "policy_invoke_libreoffice_converter" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    effect    = "Allow"
    resources = ["arn:${local.aws_partition}:lambda:${local.aws_region_name}:${local.aws_account_id}:function:${local.resource_prefix}-common-libreoffice-converter-${local.resource_suffix}"]
  }
}

resource "aws_iam_policy" "policy_invoke_libreoffice_converter" {
  name        = "${local.iam_prefix}-invoke-lo-converter-${local.iam_suffix}"
  description = "Allow convert_po_file Lambda to invoke the LibreOffice converter Lambda"
  policy      = data.aws_iam_policy_document.policy_invoke_libreoffice_converter.json
}

data "aws_iam_policy_document" "policy_assume_coupa_role" {
  statement {
    actions   = ["sts:AssumeRole"]
    effect    = "Allow"
    resources = [var.coupa_access_role_arn]
  }
}

resource "aws_iam_policy" "policy_assume_coupa_role" {
  name        = "${local.iam_prefix}-assume-coupa-role-${local.iam_suffix}"
  description = "Allow Lambda to assume the Snowflake access role for Coupa queries"
  policy      = data.aws_iam_policy_document.policy_assume_coupa_role.json
}

data "aws_iam_policy_document" "policy_assume_cross_account_role" {
  statement {
    actions   = ["sts:AssumeRole"]
    effect    = "Allow"
    resources = [var.coupa_cross_account_role_arn]
  }
}

resource "aws_iam_policy" "policy_assume_cross_account_role" {
  name        = "${local.iam_prefix}-assume-cross-account-role-${local.iam_suffix}"
  description = "Allow Lambda to assume the cross-account role for CEDL S3 bucket access"
  policy      = data.aws_iam_policy_document.policy_assume_cross_account_role.json
}

data "aws_iam_policy_document" "policy_ssm_read_write" {
  statement {
    actions = [
      "ssm:GetParameter",
      "ssm:PutParameter"
    ]
    effect = "Allow"
    resources = [
      "arn:${local.aws_partition}:ssm:${local.aws_region_name}:${local.aws_account_id}:parameter${local.ssm_prefix}/*"
    ]
  }
}

resource "aws_iam_policy" "policy_ssm_read_write" {
  name        = "${local.iam_prefix}-ssm-read-write-${local.iam_suffix}"
  description = "Allow Lambda read/write access to SSM parameters"
  policy      = data.aws_iam_policy_document.policy_ssm_read_write.json
}

data "aws_iam_policy_document" "policy_bedrock_bda" {
  statement {
    actions = [
      "bedrock:InvokeDataAutomationAsync",
      "bedrock:GetDataAutomationStatus"
    ]
    effect = "Allow"
    resources = [
      awscc_bedrock_data_automation_project.ocr.project_arn,
      "arn:${local.aws_partition}:bedrock:*:${local.aws_account_id}:data-automation-profile/eu.data-automation-v1",
      "arn:${local.aws_partition}:bedrock:*:${local.aws_account_id}:data-automation-invocation/*"
    ]
  }
}

resource "aws_iam_policy" "policy_bedrock_bda" {
  name        = "${local.iam_prefix}-bedrock-bda-${local.iam_suffix}"
  description = "Allow Lambda to invoke Bedrock Data Automation"
  policy      = data.aws_iam_policy_document.policy_bedrock_bda.json
}

data "aws_iam_policy_document" "policy_bedrock_prompt" {
  statement {
    actions = [
      "bedrock:InvokeModel",
      "bedrock:Converse",
      "bedrock:GetPrompt",
      "bedrock:RenderPrompt"
    ]
    effect = "Allow"
    resources = [
      "arn:${local.aws_partition}:bedrock:*::foundation-model/*",
      "arn:${local.aws_partition}:bedrock:${local.aws_region_name}:${local.aws_account_id}:prompt/*",
      "arn:${local.aws_partition}:bedrock:${local.aws_region_name}:${local.aws_account_id}:inference-profile/*",
      "arn:${local.aws_partition}:bedrock:${local.aws_region_name}::inference-profile/*"
    ]
  }

  statement {
    actions = [
      "aws-marketplace:ViewSubscriptions",
      "aws-marketplace:Subscribe"
    ]
    effect    = "Allow"
    resources = ["*"]
  }
}

resource "aws_iam_policy" "policy_bedrock_prompt" {
  name        = "${local.iam_prefix}-bedrock-prompt-${local.iam_suffix}"
  description = "Allow Lambda to invoke Bedrock models and prompts via converse API"
  policy      = data.aws_iam_policy_document.policy_bedrock_prompt.json
}

module "lambda_dedicated_role" {
  source   = "grand_org.jfrog.io/terraform-innersource-local__aws-services/iam_role_service/aws"
  version  = var.jfrog_module_versions["iam_role_service"]
  for_each = local.lambdas_with_dedicated_role

  role_name   = "${local.iam_prefix}-lambda-${each.value.name}-${local.iam_suffix}"
  aws_service = "lambda"
  managed_policies_arns = merge(
    {
      cloudwatch     = aws_iam_policy.policy_write_cloudwatch_logs.arn
      kms_data       = aws_iam_policy.policy_kms_data.arn
      kms_lambda_env = aws_iam_policy.policy_kms_lambda_env.arn
      xray           = aws_iam_policy.policy_lambda_xray.arn
    },
    each.value.custom_policies_arns
  )
  tags = merge(local.standard_tags, {})
}
