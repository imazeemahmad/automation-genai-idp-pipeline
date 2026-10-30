locals {
  # AWS Lambda Powertools layer ARN (arm64)
  _python_version_compact = replace(local.python_release, ".", "")
  powertools_layer_arn    = "arn:${local.aws_partition}:lambda:${local.aws_region_name}:AWSACCNNNNNN:layer:AWSLambdaPowertoolsPythonV3-python${local._python_version_compact}-arm64:7"

  # All lambdas get a dedicated role
  lambdas_with_dedicated_role = local.lambda_handlers

  # Role ARN resolution per Lambda
  lambda_role_arns = {
    for k, v in local.lambda_handlers : k => module.lambda_dedicated_role[k].role_arn
  }

  # Lambda function name convention:
  # app-<app_name_short>-<region_short>-<name>-<env>[-<developer>]
  lambda_function_names = {
    for k, v in local.lambda_handlers : k => "${local.resource_prefix}-${v.name}-${local.resource_suffix}"
  }

  # Source hashes for change detection
  layer_source_hash = filemd5("../app_src/app/lambdas/requirements.txt")
}

# -----------------------------------------------------------------------------
# Lambda Layer (Python dependencies)
# Artifacts are uploaded to S3 by scripts/push-lambda-artifacts.sh
# Terraform reads them from S3 (no local file dependency)
# -----------------------------------------------------------------------------

locals {
  lambda_s3_bucket    = module.s3_bucket_project.bucket_name
  lambda_layer_s3_key = "${local.lambda_prefix}/layer.zip"
  lambda_code_s3_key  = "${local.lambda_prefix}/code.zip"
}

resource "aws_lambda_layer_version" "dependencies" {
  layer_name               = "${local.resource_prefix}-common-dependencies-${local.resource_suffix}"
  s3_bucket                = local.lambda_s3_bucket
  s3_key                   = local.lambda_layer_s3_key
  source_code_hash         = local.layer_source_hash
  compatible_runtimes      = ["python${local.python_release}"]
  compatible_architectures = ["arm64"]
  description              = "Python dependencies for procurement lambdas"
}

# -----------------------------------------------------------------------------
# Lambda Code (application code only)
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# Lambda Functions
# -----------------------------------------------------------------------------

module "define_lambdas" {
  source   = "grand_org.jfrog.io/terraform-innersource-local__aws-services/lambda_function/aws"
  version  = var.jfrog_module_versions["lambda_function"]
  for_each = local.lambda_handlers

  function_name = local.lambda_function_names[each.key]
  memory_size   = coalesce(each.value.memory_size, 256)
  timeout       = coalesce(each.value.timeout, 30)
  role_arn      = local.lambda_role_arns[each.key]
  kms_key_arn   = aws_kms_key.lambda_env_key.arn
  xray_enabled  = true
  architectures = lookup(each.value, "architectures", ["arm64"])

  deployment_config = {
    zip = lookup(each.value, "deployment_type", "zip") == "zip" ? {
      runtime   = "python${local.python_release}"
      handler   = each.value.handler
      s3_bucket = local.lambda_s3_bucket
      s3_key    = local.lambda_code_s3_key
      layers = concat(
        [
          aws_lambda_layer_version.dependencies.arn,
          local.powertools_layer_arn,
        ],
        lookup(each.value, "extra_layers", [])
      )
    } : null
    container = lookup(each.value, "deployment_type", "zip") == "container" ? {
      image_uri = each.value.image_uri
    } : null
  }

  logging_config = {
    log_format            = "JSON"
    application_log_level = var.application_log_level
    system_log_level      = var.system_log_level
  }

  env_vars = merge(each.value.env_vars, {
    POWERTOOLS_METRICS_NAMESPACE = local.metrics_namespace
  })

  destinations = {
    on_failure_arn = "arn:${local.aws_partition}:events:${local.aws_region_name}:${local.aws_account_id}:event-bus/default"
  }

  tags = merge(local.standard_tags, {})
}

# -----------------------------------------------------------------------------
# KMS Key for Lambda environment variables encryption
# -----------------------------------------------------------------------------

resource "aws_kms_key" "lambda_env_key" {
  description = "Key for encrypting Lambda environment variables"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowRootAccountFullAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:${local.aws_partition}:iam::${local.aws_account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })
  is_enabled          = true
  enable_key_rotation = true
}

resource "aws_kms_alias" "lambda_env_key_alias" {
  for_each = local.lambda_handlers

  name          = "alias/${local.lambda_function_names[each.key]}"
  target_key_id = aws_kms_key.lambda_env_key.key_id
}

# -----------------------------------------------------------------------------
# KMS IAM Policy for Lambda environment variables key
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "policy_kms_lambda_env" {
  statement {
    actions = [
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:GenerateDataKey*",
      "kms:DescribeKey"
    ]
    effect    = "Allow"
    resources = [aws_kms_key.lambda_env_key.arn]
  }
}

resource "aws_iam_policy" "policy_kms_lambda_env" {
  name        = "${local.iam_prefix}-kms-lambda-env-${local.iam_suffix}"
  description = "Allow Lambda roles to use the environment variables KMS key"
  policy      = data.aws_iam_policy_document.policy_kms_lambda_env.json
}
