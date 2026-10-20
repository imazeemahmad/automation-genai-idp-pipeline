terraform {
  backend "s3" {
    bucket       = var.bucket
    region       = var.region
    key          = var.key
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

      # application, security tag
      app_name_short = var.app_name_short

      # development Tags
      team    = var.team
      version = var.Version
      contact = var.contact
    }
  }
}
