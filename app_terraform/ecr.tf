locals {
  # ECR repository name convention: app-<app_name_short>-<region_short>-<env>[-<developer>]
  ecr_repository_name = "${local.resource_prefix}-${local.resource_suffix}"

  # Dedicated repository for the LibreOffice converter container image
  ecr_libreoffice_converter_repository_name = "${local.resource_prefix}-libreoffice-converter-${local.resource_suffix}"
}

module "ecr" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/ecr_repository/aws"
  version = var.jfrog_module_versions["ecr_repository"]

  ecr_repository_name = local.ecr_repository_name
  kms_key_arn         = module.kms_ecr.kms_key_arn
  additional_role_arn = data.aws_iam_role.existing.arn
  image_count         = var.ecr_image_count

  # Allow Lambda service to pull container images.
  # Uses a wildcard ARN pattern (not module.define_lambdas refs) to avoid a
  # dependency cycle that would force Lambda creation during bootstrap.
  service_access = [
    {
      service            = "lambda.amazonaws.com"
      source_arn_pattern = "arn:${local.aws_partition}:lambda:${local.aws_region_name}:${local.aws_account_id}:function:${local.resource_prefix}-*"
    }
  ]

  tags = merge(local.standard_tags, {})
}

module "ecr_libreoffice_converter" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/ecr_repository/aws"
  version = var.jfrog_module_versions["ecr_repository"]

  ecr_repository_name = local.ecr_libreoffice_converter_repository_name
  kms_key_arn         = module.kms_ecr.kms_key_arn
  additional_role_arn = data.aws_iam_role.existing.arn
  image_count         = var.ecr_image_count

  # Allow Lambda service to pull container images.
  # Uses a wildcard ARN pattern (not module.define_lambdas refs) to avoid a
  # dependency cycle that would force Lambda creation during bootstrap.
  service_access = [
    {
      service            = "lambda.amazonaws.com"
      source_arn_pattern = "arn:${local.aws_partition}:lambda:${local.aws_region_name}:${local.aws_account_id}:function:${local.resource_prefix}-*"
    }
  ]

  tags = merge(local.standard_tags, {})
}
