module "current_release_parameter" {
  source               = "../modules/ssm/ssm_parameter"
  parameter_name       = "/App_${var.app_name_short}/release/current"
  parameter_value      = "0.0.0"
  parameter_type       = "String"
  tier                 = "Standard"
  ignore_value_changes = true

  tags = merge(local.standard_tags, {
    CE_DataSensitivity = "Internal"
  })
}

module "code_release_parameter" {
  source               = "../modules/ssm/ssm_parameter"
  parameter_name       = "/App_${var.app_name_short}/release/previous"
  parameter_value      = "0.0.0"
  parameter_type       = "String"
  tier                 = "Standard"
  ignore_value_changes = true

  tags = merge(local.standard_tags, {
    CE_DataSensitivity = "Internal"
  })
}
