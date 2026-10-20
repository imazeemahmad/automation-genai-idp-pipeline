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