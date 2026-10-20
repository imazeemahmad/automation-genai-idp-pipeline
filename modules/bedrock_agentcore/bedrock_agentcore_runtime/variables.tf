variable "vpc_config" {
  type = object({
    security_group_ids = list(string)
    subnet_ids         = list(string)
  })
  description = "VPC configuration if the Agent Runtime requires networking. If not specified, defaults will be used."
  default     = null
}

variable "image_uri" {
  description = "The URI of the Docker image"
  type        = string
}

variable "agent_runtime_env_variables" {
  description = "Environment variables for the AgentCore Runtime container"
  type        = map(string)
  default     = {}
}

variable "agent_runtime_name" {
  description = "Name of the Bedrock agent runtime (letters, digits, underscore; max 48)"
  type        = string
}

variable "role_arn" {
  description = "IAM role ARN used by the Bedrock Agent Runtime"
  type        = string
}

variable "server_protocol" {
  description = "The server protocol for the agent runtime. Specifies how the agent runtime communicates with clients. Valid values: MCP, HTTP, A2A."
  type        = string
  default     = null

  validation {
    condition     = var.server_protocol == null || contains(["MCP", "HTTP", "A2A"], var.server_protocol)
    error_message = "server_protocol must be one of: MCP, HTTP, A2A"
  }
}

variable "tags" {
  type        = map(string)
  description = "A map of tags to assign to the resource. Must include CE_Application_ID, CE_Application_Name, and CE_Environment."
}