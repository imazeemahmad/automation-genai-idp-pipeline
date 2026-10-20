module "ecr" {
  source              = "../modules/ecr/ecr_repository"
  ecr_repository_name = local.lambda_prefix
  kms_key_arn         = module.kms.kms_key_arn
  additional_role_arn = data.aws_iam_role.existing.arn
  image_count         = 1000

  # Allow Lambda service to pull container images
  service_access = [
    for k, m in try(module.define_lambdas, {}) : {
      service            = "lambda.amazonaws.com"
      source_arn_pattern = m.lambda_arn
    }
  ]

  tags = merge(local.standard_tags, {})
}
