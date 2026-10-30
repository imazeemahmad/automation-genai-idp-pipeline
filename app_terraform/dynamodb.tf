locals {
  # DynamoDB table name convention:
  # app-<app_name_short>-<region_short>-<env>[-<developer>]
  dynamodb_table_name = "${local.resource_prefix}-${local.resource_suffix}"
}

module "dynamodb_procurement" {
  source  = "grand_org.jfrog.io/terraform-innersource-local__aws-services/dynamodb_table/aws"
  version = var.jfrog_module_versions["dynamodb_table"]

  dynamodb_table_name = local.dynamodb_table_name
  billing_mode        = "PAY_PER_REQUEST"
  hash_key            = "PK"
  range_key           = "SK"

  table_attributes = [
    { name = "PK", type = "S" },
    { name = "SK", type = "S" },
  ]

  server_side_encryption_enabled = true
  kms_key_arn                    = module.kms_data.kms_key_arn

  point_in_time_recovery_enabled = true

  tags = merge(local.standard_tags, {
    CE_Backup_Selection = "CE_NoBackup"
    CE_DataSensitivity  = "Internal"
  })
}
