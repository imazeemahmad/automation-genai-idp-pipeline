
variable "function_name" {
  type        = string
  description = "Name of the Lambda function"
}

variable "architectures" {
  type        = list(string)
  description = "Runtime architecture"
  default     = ["arm64"]
  validation {
    condition = alltrue([
      for arch in var.architectures : contains(["x86_64", "arm64"], arch)
    ])
    error_message = "architectures must be a list with either 'x86_64' or 'arm64'"
  }
}

variable "kms_key_arn" {
  type        = string
  description = "KMS key used to encrypt the environment variables"
  default     = null
}

variable "deployment_config" {
  description = "Lambda deployment configuration. Exactly one of 'zip' or 'container' must be provided."
  type = object({
    zip = optional(object({
      runtime   = string
      handler   = string
      s3_bucket = string
      s3_key    = string
      layers    = optional(list(string), [])
    }))
    container = optional(object({
      image_uri   = string
      entry_point = optional(list(string), [])
      command     = optional(list(string), [])
    }))
  })

  validation {
    condition     = (var.deployment_config.zip != null) != (var.deployment_config.container != null)
    error_message = "Exactly one of 'zip' or 'container' must be provided in deployment_config."
  }
}

variable "memory_size" {
  type        = number
  description = "Amount of RAM allocated to the function"
  default     = 128
}

variable "timeout" {
  type        = number
  description = "Amount of time that the function can run in seconds (max = 900 s = 15 min)"
  default     = 60
}

variable "role_arn" {
  type        = string
  description = "ARN of the Lambda execution role"
}

variable "reserved_concurrent_executions" {
  type        = number
  description = "Amount of reserved concurrent executions"
  default     = -1
}

variable "vpc_config" {
  type = object({
    security_group_ids = list(string)
    subnet_ids         = list(string)
  })
  description = "VPC configuration if the Lambda requires networking. If not specified, default will be used."
  default     = null
}

variable "ephemeral_storage" {
  type        = number
  description = "The amount of Ephemeral storage(/tmp) to allocate for the Lambda Function in MB. This parameter is used to expand the total amount of Ephemeral storage available, beyond the default amount of 512MB."
  default     = 512
}

variable "env_vars" {
  type        = map(string)
  description = "Environment variables to set for the lambda function"
  default     = {}
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to assign to the resource. Adding tags from providers one."
}

variable "destinations" {
  description = "Set the destinations for the Lambda function (Up to 1 destination on_failure and 1 destination on success)"
  type = object({
    on_failure_arn = optional(string, null)
    on_success_arn = optional(string, null)
  })
  default = {
    on_failure_arn = null
    on_success_arn = null
  }
}

variable "lambda_permissions" {
  type = map(object({
    principal      = string
    action         = string
    source_arn     = optional(string, null)
    source_account = optional(string, null)
  }))
  default = {}
}

variable "xray_enabled" {
  type        = bool
  description = "Enable X-Ray tracing for the Lambda function"
  default     = false
}

variable "logging_config" {
  description = "Lambda logging configuration. log_format sets the format (Text or JSON). application_log_level and system_log_level optionally control log detail levels."
  type = object({
    log_format            = string
    application_log_level = optional(string, null)
    system_log_level      = optional(string, null)
  })
  default = null

  validation {
    condition     = var.logging_config == null || contains(["Text", "JSON"], var.logging_config.log_format)
    error_message = "log_format must be 'Text' or 'JSON'."
  }
  validation {
    condition     = var.logging_config == null || var.logging_config.application_log_level == null || contains(["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"], var.logging_config.application_log_level)
    error_message = "application_log_level must be one of: TRACE, DEBUG, INFO, WARN, ERROR, FATAL."
  }
  validation {
    condition     = var.logging_config == null || var.logging_config.system_log_level == null || contains(["DEBUG", "INFO", "WARN"], var.logging_config.system_log_level)
    error_message = "system_log_level must be one of: DEBUG, INFO, WARN."
  }
}

variable "log_retention" {
  description = "Override log retention in days (optional)"
  type        = string
  default     = null
}

variable "CE_Environment" {
  description = "Deployment environment"
  type        = string
  default     = "DEV"

  validation {
    condition     = contains(["DEV", "UAT", "PROD"], var.CE_Environment)
    error_message = "environment must be DEV, UAT or PROD."
  }
}

