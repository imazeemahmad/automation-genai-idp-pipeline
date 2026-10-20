resource "null_resource" "validate_principals" {
  count = length([
    for k, v in var.lambda_permissions : k if contains(local.restricted_principals, v.principal)
  ])

  provisioner "local-exec" {
    command = "echo 'Found overly permissive principals' && exit 1"
  }
}

data "aws_s3_object" "lambda_zip" {
  count  = var.deployment_config.zip != null ? 1 : 0
  bucket = var.deployment_config.zip.s3_bucket
  key    = var.deployment_config.zip.s3_key
}

resource "aws_lambda_function" "lambda_function" {
  function_name = var.function_name
  package_type  = local.package_type
  architectures = var.architectures

  # ZIP-only attributes
  runtime          = var.deployment_config.zip != null ? var.deployment_config.zip.runtime : null
  handler          = var.deployment_config.zip != null ? var.deployment_config.zip.handler : null
  s3_bucket        = var.deployment_config.zip != null ? var.deployment_config.zip.s3_bucket : null
  s3_key           = var.deployment_config.zip != null ? var.deployment_config.zip.s3_key : null
  source_code_hash = var.deployment_config.zip != null ? data.aws_s3_object.lambda_zip[0].etag : null
  layers           = var.deployment_config.zip != null ? var.deployment_config.zip.layers : null

  # Container-only attribute
  image_uri         = local.is_container ? var.deployment_config.container.image_uri : null
  dynamic "image_config" {
    for_each = local.image_config ? [1] : []
    content {
      command     = local.is_container ? var.deployment_config.container.command : null
      entry_point = local.is_container ? var.deployment_config.container.entry_point : null
    }
  }

  # Shared attributes
  memory_size                    = var.memory_size
  timeout                        = var.timeout
  role                           = var.role_arn
  kms_key_arn                    = var.kms_key_arn
  reserved_concurrent_executions = var.reserved_concurrent_executions

  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [1] : []
    content {
      security_group_ids = var.vpc_config.security_group_ids
      subnet_ids         = var.vpc_config.subnet_ids
    }
  }

  tracing_config {
    mode = local.xray_configuration
  }

  dynamic "logging_config" {
    for_each = var.logging_config != null ? [1] : []
    content {
      log_format            = var.logging_config.log_format
      application_log_level = var.logging_config.application_log_level
      system_log_level      = var.logging_config.system_log_level
    }
  }

  ephemeral_storage {
    size = var.ephemeral_storage
  }

  environment {
    variables = var.env_vars
  }

  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:lambda_function"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "1.2.0"
  })
}

resource "aws_cloudwatch_log_group" "lambda_log_group" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = local.log_retention
  depends_on        = [resource.aws_lambda_function.lambda_function]
}

resource "aws_lambda_function_event_invoke_config" "lambda_destinations" {

  function_name = aws_lambda_function.lambda_function.function_name

  destination_config {
    dynamic "on_failure" {
      for_each = var.destinations.on_failure_arn != null ? [var.destinations.on_failure_arn] : []
      content {
        destination = on_failure.value
      }
    }

    dynamic "on_success" {
      for_each = var.destinations.on_success_arn != null ? [var.destinations.on_success_arn] : []
      content {
        destination = on_success.value
      }
    }
  }
}

resource "aws_lambda_permission" "permissions" {
  for_each      = var.lambda_permissions
  function_name = aws_lambda_function.lambda_function.function_name

  action    = each.value.action
  principal = each.value.principal

  source_arn     = each.value.source_arn
  source_account = each.value.source_account

}
