variable "CE_MIO_Code" {
  description = "MIO code for tagging"
  type        = string
}

variable "CE_Business_Entity" {
  description = "Business entity for tagging"
  type        = string
}

variable "CE_Application_ID" {
  description = "Application ID for tagging"
  type        = string

  validation {
    condition     = can(regex("^APM\\d{7}$", var.CE_Application_ID))
    error_message = "CE_Application_ID must be in the format APM_______ (7 digits)."
  }
}

variable "CE_SLA" {
  description = "SLA for tagging"
  type        = string
}

variable "CE_Instance_Scheduler" {
  description = "Instance scheduler for tagging"
  type        = string
}

variable "CE_App_Instance_Name" {
  description = "App instance name for tagging"
  type        = string
  validation {
    condition     = length(var.CE_App_Instance_Name) > 0
    error_message = "App instance name must be not empty."
  }
}

variable "Version" {
  description = "Version for tagging"
  type        = string
}

variable "CE_Environment" {
  description = "Deployment environment"
  type        = string
  default     = "SBX"

  validation {
    condition     = contains(["SBX", "DEV", "UAT", "PROD"], var.CE_Environment)
    error_message = "environment must be SBX, DEV, UAT or PROD."
  }
}

variable "team" {
  description = "Owner team of the project"
  type        = string
  default     = "COE Automation"
}

variable "contact" {
  description = "Contact email for the project"
  type        = string
  default     = "team@example.com"
}

variable "region" {
  description = "value"
  type        = string
  default     = "us-east-1"
}

variable "app_name_short" {
  description = "Short name of the application"
  type        = string
  default     = "ContractMetadata"
}

