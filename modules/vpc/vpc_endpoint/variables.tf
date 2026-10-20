variable "name" {
  description = "The name of the VPC endpoint"
  type        = string
  default     = null
}

variable "vpc_id" {
  description = "The ID of the VPC (optional)"
  type        = string
  default     = null
}

variable "vpc_filters" {
  description = "List of filters to apply to select the VPC (optional)"
  type = list(object({
    name   = string
    values = list(string)
  }))
  default = null
}

variable "endpoint_type" {
  description = "The type of VPC endpoint"
  type        = string
  default     = "Gateway"
  validation {
    condition     = contains(["Interface", "Gateway"], var.endpoint_type)
    error_message = "The endpoint_type must be either 'Interface' or 'Gateway'."
  }
}

variable "service_name" {
  description = "The service name of the VPC endpoint"
  type        = string
  validation {
    condition     = can(regex("^(aws\\.api\\.|com\\.amazonaws\\.).+", var.service_name))
    error_message = "Service name must start with 'aws.api.' or 'com.amazonaws.'."
  }
}

variable "subnets" {
  description = "List of subnets for the service. If not specified, default will be used."
  type        = list(string)
  default     = []
}

variable "security_groups" {
  description = "List of security groups for the service. If not specified, default will be used."
  type        = list(string)
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to assign to the resource. Must include CE_Application_ID, CE_Application_Name, and CE_Environment."

  validation {
    condition     = can(regex("^APM\\d{7}$", lookup(var.tags, "CE_Application_ID", "")))
    error_message = "The tags must include CE_Application_ID in the format APM_______ (7 digits)."
  }
  validation {
    condition     = length(lookup(var.tags, "CE_Application_Name", "")) > 0
    error_message = "The tags must include a non-empty CE_Application_Name."
  }
  validation {
    condition     = contains(["DEV", "TEST", "PROD"], lookup(var.tags, "CE_Environment", ""))
    error_message = "The tags must include CE_Environment with a value of DEV, TEST, or PROD."
  }
}
