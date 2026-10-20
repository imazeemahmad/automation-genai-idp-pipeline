variable "parameter_name" {
  type        = string
  description = "The name of the parameter. Must begin with / and follow SSM naming constraints."
  validation {
    condition     = can(regex("^/", var.parameter_name))
    error_message = "Parameter name must begin with a forward slash (/)."
  }
  validation {
    condition     = can(regex("^[a-zA-Z0-9/_.-]+$", var.parameter_name))
    error_message = "Parameter name can only contain letters, numbers, hyphens (-), underscores (_), periods (.), and forward slashes (/)."
  }
}

variable "description" {
  type        = string
  description = "A description for the parameter"
  default     = "Parameter created by Terraform Module"
}

variable "parameter_value" {
  description = "The value of the parameter. Use jsonencode() for structured data. For externally-managed parameters, set to a placeholder like 'PLACEHOLDER' and enable ignore_value_changes."
  type        = string
  sensitive   = true
  default     = "PLACEHOLDER"
}

variable "parameter_type" {
  type        = string
  description = "The type of the parameter. Valid values: String, StringList, SecureString"
  default     = "SecureString"

  validation {
    condition     = contains(["String", "StringList", "SecureString"], var.parameter_type)
    error_message = "Parameter type must be one of: String, StringList, SecureString."
  }
}

variable "tier" {
  type        = string
  description = "The tier of the parameter. Standard allows up to 4KB, Advanced allows up to 8KB."
  default     = "Standard"

  validation {
    condition     = contains(["Standard", "Advanced", "Intelligent-Tiering"], var.tier)
    error_message = "Tier must be one of: Standard, Advanced, Intelligent-Tiering."
  }
}

variable "data_type" {
  type        = string
  description = "The data type for the parameter. Use 'text' for general strings, 'aws:ec2:image' for AMI IDs."
  default     = "text"
}

variable "kms_key_id" {
  type        = string
  description = "The KMS key ID for encryption (only for SecureString type). Will use aws/ssm if not set. A custom KMS key ID is required when CE_DataSensitivity is Sensitive or HighlySensitive."
  default     = null
  validation {
    condition = (
      contains(["Sensitive", "HighlySensitive"], lookup(var.tags, "CE_DataSensitivity", ""))
      ? var.kms_key_id != null
      : true
    )
    error_message = "A custom KMS key ID is required when CE_DataSensitivity is Sensitive or HighlySensitive."
  }
}

variable "ignore_value_changes" {
  type        = bool
  description = "When true, Terraform will ignore external changes to the parameter value. Useful when the value is updated outside of Terraform."
  default     = false
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to assign to the resource. Must include CE_DataSensitivity."
  validation {
    condition     = contains(["Public", "Internal", "Sensitive", "HighlySensitive"], lookup(var.tags, "CE_DataSensitivity", ""))
    error_message = "The tags must include CE_DataSensitivity with a value of Public, Internal, Sensitive, or HighlySensitive."
  }
}

variable "allowed_role_arns" {
  description = "List of IAM role ARNs that should have access to this parameter. Module will generate an IAM policy document that can be attached to these roles."
  type        = list(string)
  default     = []
}
