data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
data "aws_region" "current" {}

data "aws_iam_role" "existing" {
  name = local.role_name
}

data "aws_iam_role" "github_bootstrap" {
  name = "App_Github_${var.app_name_short}_bootstrap"
}

data "aws_iam_role" "github_deploy" {
  name = "App_Github_${var.app_name_short}_deploy"
}

locals {
  # Role used by Terraform to manage resources (overridable via variable for CI)
  # Falls back to default "CE_AppAdmin" if variable is passed as empty string
  role_name = coalesce(var.terraform_execution_role, "CE_AppAdmin")

  # HACAT codes — derived from workflows variable
  # Map of "workflow_key/hacat_key" -> code (e.g. "biomarker/biomarker" -> "HC1001")
  hacat_codes_map = merge([
    for sched_key, sched in var.workflows : {
      for hacat_key, codes in sched.hacat_codes :
      "${sched_key}/${hacat_key}" => {
        key  = hacat_key
        code = codes[0]
      }
    }
  ]...)

  # tflint-ignore: terraform_unused_declarations
  permissions_boundary_arn = "arn:${data.aws_partition.current.partition}:iam::${data.aws_caller_identity.current.account_id}:policy/CE_AppAdminRunnerBoundary"
  aws_account_id           = data.aws_caller_identity.current.account_id
  aws_region_name          = data.aws_region.current.region
  aws_partition            = data.aws_partition.current.partition
  # development elements
  python_release = "3.12"

  # Extract developer suffix from CE_App_Instance_Name (e.g. "sbx-ProcurementBooster-developer-4" -> "developer-4")
  # If no developer suffix, instance_suffix is empty
  _instance_parts = split("-", var.CE_App_Instance_Name)
  instance_suffix = length(local._instance_parts) > 2 ? join("-", slice(local._instance_parts, 2, length(local._instance_parts))) : ""
  _suffix_lower   = local.instance_suffix != "" ? "-${lower(local.instance_suffix)}" : ""

  # Resource prefix: app-<app_name_short>-<region_short>
  resource_prefix = "app-${var.app_name_short}-${var.region_short}"
  # Resource suffix: <env>[-<developer>]
  resource_suffix = "${lower(var.CE_Environment)}${local._suffix_lower}"

  # lambda prefix (used for S3 key paths)
  lambda_prefix = "${local.resource_prefix}${local._suffix_lower}"
  # ssm prefix
  ssm_prefix = "/app-${var.app_name_short}-${var.region_short}-${lower(var.CE_Environment)}${local._suffix_lower}"

  # CloudWatch metrics namespace for Powertools
  metrics_namespace = "ProcurementDataBooster"

  # IAM prefix — base for IAM resource names
  # Pattern: App_<app_name_short>-<name>-<env>[-<developer>]
  iam_prefix = "App_${var.app_name_short}"
  iam_suffix = "${lower(var.CE_Environment)}${local._suffix_lower}"

  # LibreOffice converter image. Only the registry (account/region) is computed
  # here; the repository:tag comes from var.libreoffice_converter_image.
  ecr_registry                    = "${local.aws_account_id}.dkr.ecr.${local.aws_region_name}.amazonaws.com"
  libreoffice_converter_image_uri = "${local.ecr_registry}/${var.libreoffice_converter_image}"

  # Mapping for CE_Environment tag (JFrog modules only accept DEV, TEST, PROD)
  module_environment = lookup({
    "SBX"  = "DEV"
    "DEV"  = "DEV"
    "UAT"  = "TEST"
    "PROD" = "PROD"
  }, var.CE_Environment, "DEV")

  # standard tags
  standard_tags = {
    # Mandatory tags (outside provider ones)
    CE_Business_Entity  = var.CE_Business_Entity
    CE_Application_ID   = var.CE_Application_ID
    CE_Application_Name = var.CE_App_Instance_Name
    CE_Environment      = local.module_environment
    # application, security tag
    app_name_short  = var.app_name_short
    deployment_repo = "GenAI_Automation-ProcurementDataBooster"
    deployment_ref  = var.Version
  }

  # Lambda function handlers — maps handler names to their Python entry points
  # name follows: <domain>-<platform>-<action> (prefix/env/suffix added in lambda_function.tf)
  lambda_handlers = {
    coupa_po_retrieval = {
      name        = "common-coupa-po-retrieval"
      handler     = "handlers.coupa_po_retrieval_handler.handler"
      memory_size = null
      timeout     = null
      env_vars = {
        POWERTOOLS_SERVICE_NAME = "coupa_po_retrieval"
        POWERTOOLS_LOG_LEVEL    = var.powertools_log_level
        DATA_BUCKET_NAME        = module.s3_data_bucket.bucket_name
        PROCUREMENT_TABLE_NAME  = module.dynamodb_procurement.dynamodb_table_name
        COUPA_ACCOUNT           = var.coupa_account
        COUPA_WAREHOUSE         = var.coupa_warehouse
        COUPA_ACCESS_ROLE_ARN   = var.coupa_access_role_arn
        COUPA_DATABASE          = var.coupa_database
        COUPA_SCHEMA            = var.coupa_schema
        SSM_PREFIX              = local.ssm_prefix
        SSM_MAX_AGE             = tostring(var.ssm_max_age)
      }
      custom_policies_arns = {
        s3_data      = aws_iam_policy.policy_s3_data_read_write.arn
        dynamodb     = aws_iam_policy.policy_dynamodb_read_write.arn
        eventbridge  = aws_iam_policy.allow_put_events.arn
        assume_coupa = aws_iam_policy.policy_assume_coupa_role.arn
        ssm          = aws_iam_policy.policy_ssm_read_write.arn
        kms_ssm      = aws_iam_policy.policy_kms_ssm.arn
      }
    }

    cedl_copy_po_files = {
      name        = "common-cedl-copy-po-files"
      handler     = "handlers.cedl_copy_po_files_handler.handler"
      memory_size = null
      timeout     = null
      env_vars = {
        POWERTOOLS_SERVICE_NAME      = "cedl_copy_po_files"
        POWERTOOLS_LOG_LEVEL         = var.powertools_log_level
        CEDL_BUCKET_NAME             = var.cedl_bucket_name
        CEDL_BUCKET_PREFIX           = var.cedl_bucket_prefix
        DATA_BUCKET_NAME             = module.s3_data_bucket.bucket_name
        PROCUREMENT_TABLE_NAME       = module.dynamodb_procurement.dynamodb_table_name
        COUPA_CROSS_ACCOUNT_ROLE_ARN = var.coupa_cross_account_role_arn
        CEDL_CROSS_ACCOUNT_ROLE_ARN  = var.cedl_cross_account_role_arn
        SSM_PREFIX                   = local.ssm_prefix
        SSM_MAX_AGE                  = tostring(var.ssm_max_age)
      }
      custom_policies_arns = {
        s3_data           = aws_iam_policy.policy_s3_data_read_write.arn
        assume_cross_acct = aws_iam_policy.policy_assume_cross_account_role.arn
        dynamodb          = aws_iam_policy.policy_dynamodb_read_write.arn
        eventbridge       = aws_iam_policy.allow_put_events.arn
        ssm               = aws_iam_policy.policy_ssm_read_write.arn
        kms_ssm           = aws_iam_policy.policy_kms_ssm.arn
      }
    }

    ocr_po_file = {
      name        = "common-ocr-po-file"
      handler     = "handlers.ocr_po_file_handler.handler"
      memory_size = null
      timeout     = null
      env_vars = {
        POWERTOOLS_SERVICE_NAME = "ocr_po_file"
        POWERTOOLS_LOG_LEVEL    = var.powertools_log_level
        DATA_BUCKET_NAME        = module.s3_data_bucket.bucket_name
        PROCUREMENT_TABLE_NAME  = module.dynamodb_procurement.dynamodb_table_name
        BDA_PROJECT_ARN         = awscc_bedrock_data_automation_project.ocr.project_arn
        BDA_PROFILE_ARN         = "arn:${local.aws_partition}:bedrock:${local.aws_region_name}:${local.aws_account_id}:data-automation-profile/eu.data-automation-v1"
      }
      custom_policies_arns = {
        s3_data     = aws_iam_policy.policy_s3_data_read_write.arn
        dynamodb    = aws_iam_policy.policy_dynamodb_read_write.arn
        eventbridge = aws_iam_policy.allow_put_events.arn
        bedrock_bda = aws_iam_policy.policy_bedrock_bda.arn
      }
    }

    ocr_po_file_get_status = {
      name        = "common-ocr-po-file-get-status"
      handler     = "handlers.ocr_po_file_get_status_handler.handler"
      memory_size = null
      timeout     = null
      env_vars = {
        POWERTOOLS_SERVICE_NAME      = "ocr_po_file_get_status"
        POWERTOOLS_LOG_LEVEL         = var.powertools_log_level
        CEDL_BUCKET_NAME             = var.cedl_bucket_name
        CEDL_BUCKET_PREFIX           = var.cedl_bucket_prefix
        DATA_BUCKET_NAME             = module.s3_data_bucket.bucket_name
        PROCUREMENT_TABLE_NAME       = module.dynamodb_procurement.dynamodb_table_name
        COUPA_CROSS_ACCOUNT_ROLE_ARN = var.coupa_cross_account_role_arn
        SSM_PREFIX                   = local.ssm_prefix
        SSM_MAX_AGE                  = tostring(var.ssm_max_age)
        BDA_PROJECT_ARN              = awscc_bedrock_data_automation_project.ocr.project_arn
        BDA_PROFILE_ARN              = "arn:${local.aws_partition}:bedrock:${local.aws_region_name}:${local.aws_account_id}:data-automation-profile/eu.data-automation-v1"
      }
      custom_policies_arns = {
        s3_data     = aws_iam_policy.policy_s3_data_read_write.arn
        dynamodb    = aws_iam_policy.policy_dynamodb_read_write.arn
        eventbridge = aws_iam_policy.allow_put_events.arn
        bedrock_bda = aws_iam_policy.policy_bedrock_bda.arn
      }
    }

    consolidate_po_data = {
      name        = "common-consolidate-po-data"
      handler     = "handlers.consolidate_po_data_handler.handler"
      memory_size = null
      timeout     = 900
      env_vars = {
        POWERTOOLS_SERVICE_NAME = "consolidate_po_data"
        POWERTOOLS_LOG_LEVEL    = var.powertools_log_level
        DATA_BUCKET_NAME        = module.s3_data_bucket.bucket_name
        PROCUREMENT_TABLE_NAME  = module.dynamodb_procurement.dynamodb_table_name
        SSM_PREFIX              = local.ssm_prefix
        SSM_MAX_AGE             = tostring(var.ssm_max_age)
      }
      custom_policies_arns = {
        s3_data        = aws_iam_policy.policy_s3_data_read_write.arn
        dynamodb       = aws_iam_policy.policy_dynamodb_read_write.arn
        eventbridge    = aws_iam_policy.allow_put_events.arn
        ssm            = aws_iam_policy.policy_ssm_read_write.arn
        kms_ssm        = aws_iam_policy.policy_kms_ssm.arn
        bedrock_prompt = aws_iam_policy.policy_bedrock_prompt.arn
      }
    }

    cedl_export_po_output_data = {
      name        = "common-cedl-export-po-output-data"
      handler     = "handlers.cedl_export_po_output_data_handler.handler"
      memory_size = null
      timeout     = null
      env_vars = {
        POWERTOOLS_SERVICE_NAME      = "cedl_export_po_output_data"
        POWERTOOLS_LOG_LEVEL         = var.powertools_log_level
        DATA_BUCKET_NAME             = module.s3_data_bucket.bucket_name
        PROCUREMENT_TABLE_NAME       = module.dynamodb_procurement.dynamodb_table_name
        CEDL_BUCKET_NAME             = var.cedl_bucket_name
        CEDL_BUCKET_PREFIX           = var.cedl_bucket_prefix
        COUPA_CROSS_ACCOUNT_ROLE_ARN = var.coupa_cross_account_role_arn
        CEDL_CROSS_ACCOUNT_ROLE_ARN  = var.cedl_cross_account_role_arn
        SSM_PREFIX                   = local.ssm_prefix
        SSM_MAX_AGE                  = tostring(var.ssm_max_age)
      }
      custom_policies_arns = {
        s3_data           = aws_iam_policy.policy_s3_data_read_write.arn
        assume_cross_acct = aws_iam_policy.policy_assume_cross_account_role.arn
        dynamodb          = aws_iam_policy.policy_dynamodb_read_write.arn
        eventbridge       = aws_iam_policy.allow_put_events.arn
        ssm               = aws_iam_policy.policy_ssm_read_write.arn
        kms_ssm           = aws_iam_policy.policy_kms_ssm.arn
      }
    }

    convert_po_file = {
      name        = "common-convert-po-file"
      handler     = "handlers.convert_po_file_handler.handler"
      memory_size = null
      timeout     = 120
      env_vars = {
        POWERTOOLS_SERVICE_NAME          = "convert_po_file"
        POWERTOOLS_LOG_LEVEL             = var.powertools_log_level
        DATA_BUCKET_NAME                 = module.s3_data_bucket.bucket_name
        PROCUREMENT_TABLE_NAME           = module.dynamodb_procurement.dynamodb_table_name
        LIBREOFFICE_CONVERTER_LAMBDA_ARN = "arn:${data.aws_partition.current.partition}:lambda:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:function:${local.resource_prefix}-common-libreoffice-converter-${local.resource_suffix}"
      }
      custom_policies_arns = {
        s3_data             = aws_iam_policy.policy_s3_data_read_write.arn
        dynamodb            = aws_iam_policy.policy_dynamodb_read_write.arn
        invoke_lo_converter = aws_iam_policy.policy_invoke_libreoffice_converter.arn
        eventbridge         = aws_iam_policy.allow_put_events.arn
      }
    }

    libreoffice_converter = {
      name            = "common-libreoffice-converter"
      deployment_type = "container"
      image_uri       = local.libreoffice_converter_image_uri
      architectures   = ["x86_64"]
      memory_size     = 1024
      timeout         = 120
      env_vars = {
        POWERTOOLS_SERVICE_NAME = "libreoffice_converter"
        POWERTOOLS_LOG_LEVEL    = var.powertools_log_level
        S3_BUCKET_NAME          = module.s3_data_bucket.bucket_name
        HOME                    = "/tmp"
      }
      custom_policies_arns = {
        s3_data     = aws_iam_policy.policy_s3_data_read_write.arn
        ecr_pull    = aws_iam_policy.policy_ecr_pull.arn
        eventbridge = aws_iam_policy.allow_put_events.arn
      }
    }


  }

  # ---------------------------------------------------------------------------
  # Bedrock Prompts — auto-discovered from app_src/app/prompts/**/*.md
  # ---------------------------------------------------------------------------
  # Global defaults:     app_src/app/prompts/config.yaml
  # Per-prompt override: app_src/app/prompts/<path>/<name>-config.yaml (optional)
  # ---------------------------------------------------------------------------

  _prompts_base_path = "../app_src/app/prompts"
  _prompt_files = [
    for f in fileset(local._prompts_base_path, "**/*.md") : f
    if f != "README.md" && !endswith(f, "_system.md")
  ]

  # Global default configuration
  _prompt_defaults = yamldecode(file("${local._prompts_base_path}/config.yaml"))

  # Per-prompt override files (only those that exist)
  _prompt_override_files = fileset(local._prompts_base_path, "**/*_config.yaml")

  # Build a map of prompt key -> override config
  # Uses try() to handle config files with only comments (yamldecode returns null)
  _prompt_overrides = {
    for f in local._prompt_override_files : trimsuffix(f, "_config.yaml") => try(yamldecode(file("${local._prompts_base_path}/${f}")), {})
  }

  # Merged prompt map: defaults + per-prompt overrides
  bedrock_prompts = {
    for f in local._prompt_files : trimsuffix(f, ".md") => merge(
      local._prompt_defaults,
      lookup(local._prompt_overrides, trimsuffix(f, ".md"), {})
    )
  }

  # Bedrock prompt naming convention:
  # app-<app_name_short>-<name>-<env>[-<developer>]
  # Hierarchy separators (/) and underscores are flattened to hyphens
  bedrock_prompt_names = {
    for k, v in local.bedrock_prompts : k => "${local.resource_prefix}-${replace(replace(k, "/", "-"), "_", "-")}-${local.resource_suffix}"
  }
}
