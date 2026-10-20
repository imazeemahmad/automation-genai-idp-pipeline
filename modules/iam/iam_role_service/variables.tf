variable "role_name" {
  type        = string
  description = "Name of the role, which must start with App_"
  validation {
    condition     = can(regex("^App_.{5,}", var.role_name))
    error_message = "The role name must start with App_"
  }
}

variable "inline_policies_json" {
  type        = map(string)
  description = "Map of inline policy names to JSON policy documents"
  default     = {}
}

variable "managed_policies_arns" {
  type        = map(string)
  description = "Map of managed policies ARNs"
  default     = {}
}

variable "aws_service" {
  type        = string
  description = "AWS service to trust, e.g. ec2, lambda"
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to assign to the resource. Adding tags from providers one."
}
