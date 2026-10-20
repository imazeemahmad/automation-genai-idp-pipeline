variable "family" {
  description = "The family name of the ECS task definition"
  type        = string
}

variable "container_definitions" {
  description = "List of container definitions with full AWS ECS container definition support"
  type = list(object({
    name      = string
    image     = string
    cpu       = optional(number)
    memory    = optional(number)
    essential = optional(bool, true)
    user      = optional(string, "1000")
    portMappings = optional(list(object({
      containerPort = number
      hostPort      = optional(number)
      protocol      = optional(string, "tcp")
    })), [])
    logConfiguration = optional(object({
      logDriver = string
      options   = map(string)
    }))
    # Environment variables support
    environment = optional(list(object({
      name  = string
      value = string
    })), [])
    # Secrets Manager / SSM Parameter Store support
    secrets = optional(list(object({
      name      = string
      valueFrom = string
    })), [])
    # Container health check support
    healthCheck = optional(object({
      command     = list(string)
      interval    = optional(number, 30)
      timeout     = optional(number, 5)
      retries     = optional(number, 3)
      startPeriod = optional(number, 0)
    }))
    # Volume mount support
    mountPoints = optional(list(object({
      sourceVolume  = string
      containerPath = string
      readOnly      = optional(bool, false)
    })), [])
    # Volumes from other containers
    volumesFrom = optional(list(object({
      sourceContainer = string
      readOnly        = optional(bool, false)
    })), [])
    # Linux-specific parameters
    linuxParameters = optional(object({
      readonlyRootFilesystem = optional(bool, true)
      initProcessEnabled     = optional(bool, false)
      capabilities = optional(object({
        add  = optional(list(string), [])
        drop = optional(list(string), [])
      }))
    }))
    # Working directory
    workingDirectory = optional(string)
    # Entry point override
    entryPoint = optional(list(string))
    # Command override
    command = optional(list(string))
    # Ulimits
    ulimits = optional(list(object({
      name      = string
      softLimit = number
      hardLimit = number
    })), [])
    # Dependency ordering
    dependsOn = optional(list(object({
      containerName = string
      condition     = string
    })), [])
    # Start/Stop timeout
    startTimeout = optional(number)
    stopTimeout  = optional(number)
  }))
}

variable "cpu" {
  description = "Number of cpu units used by the task."
  type        = number
}

variable "memory" {
  description = "Amount (in MiB) of memory used by the task."
  type        = number
}

variable "execution_role_arn" {
  description = "The ARN of the task execution role"
  type        = string
}

variable "task_role_arn" {
  description = "The ARN of the task role"
  type        = string
  default     = ""
}

variable "volumes" {
  description = "List of volumes to attach to the task definition"
  type = list(object({
    name = string
    efs_volume_configuration = optional(object({
      file_system_id          = string
      root_directory          = optional(string, "/")
      transit_encryption      = optional(string, "ENABLED")
      transit_encryption_port = optional(number)
      authorization_config = optional(object({
        access_point_id = optional(string)
        iam             = optional(string, "ENABLED")
      }))
    }))
  }))
  default = []
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
