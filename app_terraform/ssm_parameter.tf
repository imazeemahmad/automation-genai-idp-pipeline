module "hacat_last_execution_parameter" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/ssm_parameter/aws"
  version = var.jfrog_module_versions["ssm_parameter"]

  for_each = local.hacat_codes_map

  parameter_name       = "${local.ssm_prefix}/hacat/${each.value.code}/lastExecution"
  description          = "Last execution timestamp for HACAT ${each.value.key} (${each.value.code})"
  parameter_value      = "1970-01-01T00:00:00Z"
  parameter_type       = "String"
  tier                 = "Standard"
  ignore_value_changes = true

  tags = merge(local.standard_tags, {
    CE_DataSensitivity = "Internal"
  })
}

module "hacat_llm_extract_prompt_arn_parameter" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/ssm_parameter/aws"
  version = var.jfrog_module_versions["ssm_parameter"]

  for_each = local.hacat_codes_map

  parameter_name       = "${local.ssm_prefix}/hacat/${each.value.code}/llmExtractPromptArn"
  description          = "Bedrock Prompt ARN for LLM extraction — HACAT ${each.value.key} (${each.value.code})"
  parameter_value      = "${aws_bedrockagent_prompt.prompt["${each.value.key}/extract_data"].arn}:${awscc_bedrock_prompt_version.prompt_version["${each.value.key}/extract_data"].version}"
  parameter_type       = "String"
  tier                 = "Standard"
  ignore_value_changes = false

  tags = merge(local.standard_tags, {
    CE_DataSensitivity = "Internal"
  })
}

module "hacat_allowed_file_extensions_parameter" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/ssm_parameter/aws"
  version = var.jfrog_module_versions["ssm_parameter"]

  for_each = local.hacat_codes_map

  parameter_name       = "${local.ssm_prefix}/hacat/${each.value.code}/allowedFileExtensions"
  description          = "Allowed file extensions (JSON array) for HACAT ${each.value.key} (${each.value.code})"
  parameter_value      = jsonencode(var.hacat_allowed_file_extensions[each.value.key])
  parameter_type       = "String"
  tier                 = "Standard"
  ignore_value_changes = true

  tags = merge(local.standard_tags, {
    CE_DataSensitivity = "Internal"
  })
}

module "hacat_batch_size_parameter" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/ssm_parameter/aws"
  version = var.jfrog_module_versions["ssm_parameter"]

  for_each = local.hacat_codes_map

  parameter_name       = "${local.ssm_prefix}/hacat/${each.value.code}/batchSize"
  description          = "Max number of purchase orders per Step Function execution for HACAT ${each.value.key} (${each.value.code})"
  parameter_value      = "50"
  parameter_type       = "String"
  tier                 = "Standard"
  ignore_value_changes = true

  tags = merge(local.standard_tags, {
    CE_DataSensitivity = "Internal"
  })
}

module "hacat_cedl_export_path_parameter" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/ssm_parameter/aws"
  version = var.jfrog_module_versions["ssm_parameter"]

  for_each = local.hacat_codes_map

  parameter_name       = "${local.ssm_prefix}/hacat/${each.value.code}/cedlExportPath"
  description          = "CEDL export subfolder path for HACAT ${each.value.key} (${each.value.code})"
  parameter_value      = var.hacat_cedl_export_path[each.value.key]
  parameter_type       = "String"
  tier                 = "Standard"
  ignore_value_changes = true

  tags = merge(local.standard_tags, {
    CE_DataSensitivity = "Internal"
  })
}

module "hacat_mapping_s3_key_parameter" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/ssm_parameter/aws"
  version = var.jfrog_module_versions["ssm_parameter"]

  for_each = {
    for map_key, entry in local.hacat_codes_map :
    map_key => entry
    if trimspace(var.hacat_mapping_s3_key[entry.key]) != ""
  }

  parameter_name       = "${local.ssm_prefix}/hacat/${each.value.code}/mappingS3Key"
  description          = "S3 key of the optional mapping.json file for HACAT ${each.value.key} (${each.value.code})"
  parameter_value      = var.hacat_mapping_s3_key[each.value.key]
  parameter_type       = "String"
  tier                 = "Standard"
  ignore_value_changes = true

  tags = merge(local.standard_tags, {
    CE_DataSensitivity = "Internal"
  })
}

module "coupa_cross_account_external_id_parameter" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/ssm_parameter/aws"
  version = var.jfrog_module_versions["ssm_parameter"]

  parameter_name       = "${local.ssm_prefix}/coupa/crossAccountExternalId"
  parameter_value      = var.coupa_role_external_id
  parameter_type       = "SecureString"
  tier                 = "Standard"
  ignore_value_changes = false
  kms_key_id           = module.kms_ssm.kms_key_id

  tags = merge(local.standard_tags, {
    CE_DataSensitivity = "Sensitive"
  })
}
