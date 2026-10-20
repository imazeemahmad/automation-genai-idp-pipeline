variable "tags" {
  type        = map(string)
  description = "A map of tags to assign to the resource."
}

variable "name" {
  description = "(Required) Name of the Step Functions"
  type        = string
  # default     = "default-step-functions"
}

variable "role_arn" {
  description = "(Required) The ARN of the IAM role to use for this state machine"
  type        = string
}

variable "definition" {
  description = "(Required) Path to a JSON file that contains the Amazon States Language definition of the state machine. When `definition_variables` is provided, the file is processed with `templatefile()`; otherwise it is read with `file()`."
  type        = string
}

variable "definition_variables" {
  description = "A map of variables to substitute in the definition file using templatefile(). When provided, the definition file is processed as a template. When empty (default), the file is read as-is."
  type        = map(string)
  default     = {}
}

variable "logging_configuration_log_destination" {
  description = "(Optional) The ARN of the CloudWatch Logs log group to which you want to send log data."
  type        = string
  default     = "*"
}

variable "logging_configuration_include_execution_data" {
  description = "(Optional) Set to true to include the execution data in the log."
  type        = bool
  default     = false
}

variable "logging_configuration_level" {
  description = "(Optional) Set the logging level."
  type        = string
  default     = "OFF"

  validation {
    condition     = contains(["ALL", "ERROR", "FATAL", "OFF"], var.logging_configuration_level)
    error_message = "The logging_configuration_level must be ALL|ERROR|FATAL|OFF"
  }
}