variable "iam_role_administrator" {
  description = "The list of ARNs of the IAM roles which will administer and use the KMS key"
  type        = list(string)
}

variable "iam_role_encrypt" {
  description = "The list of ARNs of the IAM role that will encrypt with the KMS key"
  type        = list(string)
}

variable "iam_role_decrypt" {
  description = "The list of ARNs of the IAM role that will decrypt with the KMS key"
  type        = list(string)
}

variable "deletion_window_in_days" {
  description = "The number of days before the KMS key is deleted after a deletion request"
  type        = number
  default     = 30
}

variable "key_alias" {
  description = "The alias name for the KMS key"
  type        = string
}

variable "allowed_services" {
  description = "List of AWS service names allowed to use the key for encryption/decryption (e.g., ['sns', 'sqs']). Services will be granted GenerateDataKey and Decrypt permissions with SourceAccount condition. Required for cross-service encryption like SNS-to-SQS delivery. Note: Lambda should use IAM roles (iam_role_encrypt/iam_role_decrypt) instead of service principal access."
  type        = list(string)
  default     = []

  validation {
    condition     = !contains([for svc in var.allowed_services : lower(svc)], "lambda")
    error_message = "Lambda should not be added to allowed_services. Use iam_role_encrypt and iam_role_decrypt variables to grant Lambda execution roles access to the key."
  }
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to assign to the resource. Adding tags from providers one."
}