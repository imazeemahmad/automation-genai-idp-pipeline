variable "service_name" {
  description = "ECS Service name"
  type        = string
}

variable "ecs_cluster_id" {
  description = "value"
  type        = string
}

variable "task_definition_arn" {
  description = "ARN of the task definition"
  type        = string
}

variable "vpc_id" {
  description = "The VPC ID of the VPC endpoint"
  type        = string
  default     = null
}

variable "vpc_filters" {
  description = "List of filters to apply to the VPC endpoint"
  type = list(object({
    name   = string
    values = list(string)
  }))
  default = null
}

variable "subnets" {
  description = "List of subnets for the service. If not specified, default will be used."
  type        = list(string)
  default     = []
}

variable "security_groups" {
  description = "List of security groups for the service. If not specified, default will be used."
  type        = list(string)
  default     = []
}

variable "allow_public_ip" {
  description = "Controls whether the ECS service should have a public IP. Default: false"
  type        = bool
  default     = false
}

variable "desired_count" {
  description = "Number of desired tasks to run"
  type        = number
}

variable "health_check_grace_period_seconds" {
  description = "(Optional) Seconds to ignore failing load balancer health checks on newly instantiated tasks to prevent premature shutdown. Only valid for services configured to use load balancers."
  type        = string
  default     = null

}

variable "load_balancer" {
  description = <<EOT
  List of load balancer configurations for the ECS service.

  Each object supports:
  - `target_group_arn` (Optional, string): ARN of the ALB/NLB Target Group (required for ALB/NLB).
  - `container_name` (Required, string): Name of the container to associate with the load balancer.
  - `container_port` (Required, number): Port on the container to associate with the load balancer.
  EOT
  type = list(object({
    target_group_arn = optional(string) # Only for ALB/NLB
    container_name   = string
    container_port   = number
  }))
  default = null
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
