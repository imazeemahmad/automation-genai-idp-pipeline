terraform {
  required_version = ">= 1.14.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.56.0"
      # chnaged because of this issue https://github.com/hashicorp/terraform-provider-aws/issues/49180
      # once corrected we can rollback
    }
    awscc = {
      source  = "hashicorp/awscc"
      version = ">= 1.91.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.8.0, < 3.0.0"
    }
    null = {
      source  = "hashicorp/null"
      version = ">= 3.3.0, < 4.0.0"
    }
    time = {
      source  = "hashicorp/time"
      version = ">= 0.12.0, < 1.0.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.6.0, < 4.0.0"
    }
  }

  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      # Global Tags
      CE_Application_ID    = var.CE_Application_ID
      CE_App_Instance_Name = var.CE_App_Instance_Name
      CE_MIO_Code          = var.CE_MIO_Code
      CE_Environment       = var.CE_Environment
      CE_SLA               = var.CE_SLA

      # application, security tag
      app_name_short = var.app_name_short

      # development Tags
      team    = var.team
      version = var.Version
      contact = var.contact
    }
  }
}

provider "awscc" {
  region = var.region
}
