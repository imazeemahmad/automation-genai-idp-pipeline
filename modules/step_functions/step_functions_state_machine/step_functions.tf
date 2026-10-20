locals {
  definition = (
    length(var.definition_variables) > 0
    ? templatefile(var.definition, var.definition_variables)
    : file(var.definition)
  )
}

resource "aws_sfn_state_machine" "sfn_state_machine" {
  name       = var.name
  role_arn   = var.role_arn
  definition = local.definition

  logging_configuration {
    log_destination        = var.logging_configuration_log_destination
    include_execution_data = var.logging_configuration_include_execution_data
    level                  = var.logging_configuration_level
  }

  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:step_functions_state_machine"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "__VERSION__"
  })
}
