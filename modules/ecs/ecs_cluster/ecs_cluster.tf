data "aws_caller_identity" "current" {}

locals {
  log_retention = {
    DEV  = "1"
    TEST = "7"
    PROD = "30"
  }
  iam_prefix = "App_"
  region     = "eu-west-1"
  account_id = data.aws_caller_identity.current.account_id
}

resource "aws_cloudwatch_log_group" "ecs_log_group" {
  name              = "/aws/ecs/${var.cluster_name}"
  retention_in_days = local.log_retention[var.tags.CE_Environment]
}

resource "aws_ecs_cluster" "ecs_cluster" {
  name = var.cluster_name
  configuration {
    execute_command_configuration {
      # ? kms_key_id = ""
      log_configuration {
        # cloud_watch_encryption_enabled = false
        cloud_watch_log_group_name = resource.aws_cloudwatch_log_group.ecs_log_group.name
        # s3_bucket_name                 = ""
        # s3_bucket_encryption_enabled   = false
        # s3_key_prefix                  = ""
      }
      logging = "OVERRIDE"
    }
    /*managed_storage_configuration {
      fargate_ephemeral_storage_kms_key_id = ""
      kms_key_id =  " "
    }*/
  }
  /*
  service_connect_defaults {
    namespace = ""
  }*/

  setting {
    name  = "containerInsights"
    value = "enhanced"
  }

  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:ecs_cluster"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "__VERSION__"
  })
}
