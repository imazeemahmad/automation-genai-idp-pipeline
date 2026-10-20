resource "null_resource" "lambda_build" {
  count = local.is_poc ? 1 : 0

  triggers = {
    requirements = filemd5("../app_src/app/lambdas/requirements.txt")
    source_code  = sha256(join("", [for f in fileset("../app_src/app/lambdas", "**/*.py") : filemd5("../app_src/app/lambdas/${f}")]))
  }

  provisioner "local-exec" {
    command = <<-EOT
      rm -rf ${path.module}/modules/lambda_build
      mkdir -p ${path.module}/modules/lambda_build
      pip install -r ../app_src/app/lambdas/requirements.txt \
        -t ${path.module}/modules/lambda_build/ \
        --platform manylinux2014_aarch64 \
        --implementation cp \
        --python-version 3.12 \
        --abi cp312 \
        --only-binary=:all: \
        --upgrade \
        --quiet
      cp -r ../app_src/app/lambdas/* ${path.module}/modules/lambda_build/
    EOT
  }
}

data "archive_file" "lambda_zip" {
  count = local.is_poc ? 1 : 0

  type        = "zip"
  source_dir  = "${path.module}/modules/lambda_build"
  output_path = "${path.module}/modules/lambda_package.zip"

  depends_on = [null_resource.lambda_build]
}

resource "aws_s3_object" "lambda_zip" {
  count = local.is_poc ? 1 : 0

  bucket = module.s3_bucket_project.bucket_name
  key    = "${local.lambda_prefix}/lambda_dependencies.zip"
  source = data.archive_file.lambda_zip[0].output_path
  etag   = data.archive_file.lambda_zip[0].output_md5
}

module "define_lambdas" {
  source   = "../modules/lambda/lambda_function"
  for_each = local.lambda_handlers

  function_name = "${local.iam_prefix}_${lower(each.key)}_lambda"
  memory_size   = coalesce(each.value.memory_size, 256)
  timeout       = coalesce(each.value.timeout, 30)
  role_arn      = module.role_lambda_function.role_arn
  kms_key_arn   = aws_kms_key.lambda_env_key.arn

  deployment_config = {
    zip = local.is_poc ? {
      runtime   = "python${local.python_release}"
      handler   = each.value.handler
      s3_bucket = resource.aws_s3_object.lambda_zip[0].bucket
      s3_key    = resource.aws_s3_object.lambda_zip[0].key
    } : null
    container = local.is_poc ? null : {
      image_uri = "${module.ecr.ecr_repository_url}:${local.release_tag}"
      command   = ["lambdas.${each.value.handler}"]
    }
  }


  logging_config = {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
  }

  env_vars = each.value.env_vars

  destinations = {
    on_failure_arn = "arn:aws:events:${local.aws_region_name}:${local.aws_account_id}:event-bus/default"
  }

  tags = merge(local.standard_tags, {})
}

resource "aws_kms_key" "lambda_env_key" {
  description = "Key for encrypting Lambda environment variables"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaUseOfKey"
        Effect = "Allow"
        Principal = {
          AWS = module.role_lambda_function.role_arn
        }
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowRootUserToManageKey"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.aws_account_id}:root"
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

  name          = "alias/${local.iam_prefix}_${each.key}_lambda"
  target_key_id = aws_kms_key.lambda_env_key.key_id
}
