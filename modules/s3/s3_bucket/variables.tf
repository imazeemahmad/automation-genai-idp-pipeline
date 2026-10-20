variable "bucket_name" {
  type        = string
  description = "Name of the S3 bucket (globally unique)"
}

variable "versionning" {
  type        = bool
  description = "Whether to enable bucket versionning"
  default     = true
}

variable "bucket_policy" {
  type        = string
  description = "Bucket policy in JSON format"
  default     = null
}

variable "kms_key_id" {
  type        = string
  description = "KMS Key ID for S3 bucket encryption"
  default     = null
}

variable "enable_bucket_key" {
  description = "Enable bucket key for server-side encryption"
  type        = bool
  default     = true
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to assign to the resource. Adding tags from providers one."
}

variable "lifecycle_rules" {
  description = "Additional lifecycle rules for the S3 bucket (expiration, transition). All rules are enabled."
  type = list(object({
    id = string
    filter = optional(object({
      prefix                   = optional(string)
      object_size_greater_than = optional(number)
      object_size_less_than    = optional(number)
      tags                     = optional(map(string))
    }))
    expiration = optional(object({
      days                         = optional(number)
      date                         = optional(string)
      expired_object_delete_marker = optional(bool)
    }))
    transition = optional(list(object({
      days          = optional(number)
      date          = optional(string)
      storage_class = string
    })))
  }))
  default = []

  validation {
    condition = alltrue([
      for rule in var.lifecycle_rules :
      rule.expiration != null || rule.transition != null
    ])
    error_message = "Each lifecycle rule must define at least one action (expiration or transition)."
  }

  validation {
    condition = alltrue([
      for rule in var.lifecycle_rules :
      length(rule.id) > 0
    ])
    error_message = "Lifecycle rule id must not be empty."
  }

  validation {
    condition = alltrue([
      for rule in var.lifecycle_rules :
      rule.transition == null || alltrue([
        for t in rule.transition :
        contains(["GLACIER", "DEEP_ARCHIVE", "INTELLIGENT_TIERING", "STANDARD_IA", "ONEZONE_IA", "GLACIER_IR"], t.storage_class)
      ])
    ])
    error_message = "transition.storage_class must be one of: GLACIER, DEEP_ARCHIVE, INTELLIGENT_TIERING, STANDARD_IA, ONEZONE_IA, GLACIER_IR."
  }
}

variable "notifications" {
  description = "S3 bucket notification configurations for Lambda, SQS, and SNS targets"
  type = object({
    lambda_functions = optional(list(object({
      lambda_function_arn = string
      events              = list(string)
      filter_prefix       = optional(string, null)
      filter_suffix       = optional(string, null)
    })), [])
    sqs_queues = optional(list(object({
      queue_arn     = string
      events        = list(string)
      filter_prefix = optional(string, null)
      filter_suffix = optional(string, null)
    })), [])
    sns_topics = optional(list(object({
      topic_arn     = string
      events        = list(string)
      filter_prefix = optional(string, null)
      filter_suffix = optional(string, null)
    })), [])
  })
  default = null
}
