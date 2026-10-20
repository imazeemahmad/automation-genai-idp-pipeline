data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_region" "current" {}

data "aws_ssm_parameter" "release_current" {
  count = local.is_poc ? 0 : 1
  name  = module.current_release_parameter.parameter_name
}

data "aws_iam_role" "existing" {
  name = local.role_name
}

locals {
  # is on poc (running on terminal outside github action)
  is_poc = var.CE_Environment == "SBX" ? true : false
  #
  role_name = local.is_poc ? "CE_AppAdmin" : "App_Github_${var.app_name_short}"

  permissions_boundary_arn = "arn:aws:iam:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:policy/CE_AppAdminRunnerBoundary"
  aws_account_id           = data.aws_caller_identity.current.account_id
  aws_region_name          = data.aws_region.current.region
  # development elements
  python_release = "3.12"
  # 
  release_tag = local.is_poc ? "poc" : try(data.aws_ssm_parameter.release_current[0].value, "0.0.0")

  # lambda prefix
  lambda_prefix = "app${local.is_poc ? "-poc" : ""}-${lower(var.app_name_short)}"
  # IAM, object prefix 
  iam_prefix = "App${local.is_poc ? "_poc" : ""}_${var.app_name_short}"

  # standard tags
  standard_tags = {
    # Mandatory tags (outside provider ones)
    CE_Business_Entity = var.CE_Business_Entity
    # application, security tag
    app_name_short = var.app_name_short
  }

  # Lambda function handlers — maps handler names to their Python entry points
  lambda_handlers = {
    process_procurements_handler = {
      handler     = "handlers.process_procurements_handler.handler" # mandatory for not poc
      memory_size = null
      timeout     = null
      env_vars = {
        DATA_BUCKET_NAME = module.s3_data_bucket.bucket_name
      }
    }
    process_procurement_handler = {
      handler     = "handlers.process_procurement_handler.handler"
      memory_size = null
      timeout     = null
      env_vars = {
        DATA_BUCKET_NAME = module.s3_data_bucket.bucket_name
      }
    }
  }

}
