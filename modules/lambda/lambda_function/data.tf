data "aws_caller_identity" "current" {}

locals {
  default_log_retention = {
    DEV  = "1"
    TEST = "7"
    PROD = "30"
  }[var.CE_Environment]
  
  log_retention = coalesce(
    var.log_retention,
    local.default_log_retention
  )

  restricted_principals = [
      "*",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/*",
      "arn:aws:sts::${data.aws_caller_identity.current.account_id}:assumed-role/*"
  ] # Add more as needed
  xray_configuration    = var.xray_enabled ? "Active" : "PassThrough"

  # Deployment type
  is_container = var.deployment_config.container != null
  image_config = local.is_container && (
        var.deployment_config.container.entry_point != [] || 
        var.deployment_config.container.command != []
      )
  package_type = local.is_container ? "Image" : "Zip"
}