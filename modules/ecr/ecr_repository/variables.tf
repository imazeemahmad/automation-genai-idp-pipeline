variable "ecr_repository_name" {
  description = "The name of the ECR repository"
  type        = string
}

variable "kms_key_arn" {
  description = "The ARN of the KMS key to use for encryption"
  type        = string
}

variable "additional_role_arn" {
  description = "The ARN of the additional IAM role to grant access"
  type        = string
  default     = null
}

variable "service_access" {
  description = <<-EOT
    List of AWS service principals that need to pull images from this repository.
    Each entry specifies the service and an ARN pattern condition for access control.

    Example:
    ```
    service_access = [
      {
        service         = "lambda.amazonaws.com"
        source_arn_pattern = "arn:aws:lambda:eu-west-1:123456789012:function:my-app-*"
      },
      {
        service         = "ecs-tasks.amazonaws.com"
        source_arn_pattern = "arn:aws:ecs:eu-west-1:123456789012:*"
      }
    ]
    ```
  EOT
  type = list(object({
    service            = string
    source_arn_pattern = string
  }))
  default = []
}

variable "image_count" {
  description = "Number of images after which images should expire"
  type        = number
}

variable "image_tag_mutability" {
  description = "Control ECR repository tag mutability. Allowed values: MUTABLE, IMMUTABLE."
  type        = string
  default     = "IMMUTABLE"

  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "image_tag_mutability must be one of MUTABLE, IMMUTABLE."
  }
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to assign to the resource. Adding tags from providers one."
}
