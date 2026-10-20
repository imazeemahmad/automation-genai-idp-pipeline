data "aws_region" "current" {}

locals {
  # Default log configuration for containers that don't specify one
  default_log_configuration = {
    logDriver = "awslogs"
    options = {
      "awslogs-group"         = "/ecs/${var.family}"
      "awslogs-region"        = data.aws_region.current.name
      "awslogs-stream-prefix" = "app"
    }
  }

  container_definitions = [
    for container in var.container_definitions : {
      # Required fields
      name      = container.name
      image     = container.image
      essential = container.essential

      # Optional resource allocation
      cpu    = container.cpu
      memory = container.memory

      # Security: Never allow privileged containers
      privileged = false

      # Security: Enforce non-root user (default to 1001 if not specified or if root)
      user = coalesce(
        lookup(container, "user", "0") == "0" ? "1001" : lookup(container, "user", "1001"),
        "1001"
      )

      # Port mappings
      portMappings = container.portMappings

      # Log configuration with sensible defaults
      logConfiguration = container.logConfiguration != null ? {
        logDriver = container.logConfiguration.logDriver
        options = merge(
          local.default_log_configuration.options,
          container.logConfiguration.options
        )
      } : local.default_log_configuration

      # Environment variables
      environment = container.environment

      # Secrets from Secrets Manager or SSM Parameter Store
      secrets = container.secrets

      # Container health check
      healthCheck = container.healthCheck

      # Volume mounts
      mountPoints = container.mountPoints

      # Volumes from other containers
      volumesFrom = container.volumesFrom

      # Linux parameters with security defaults
      linuxParameters = merge(
        {
          readonlyRootFilesystem = true
          initProcessEnabled     = false
        },
        try(container.linuxParameters, {}),
        try(container.linuxParameters.capabilities, null) != null ? {
          capabilities = merge(
            {
              add  = []
              drop = []
            },
            container.linuxParameters.capabilities
          )
        } : {}
      )

      # Working directory
      workingDirectory = container.workingDirectory

      # Entry point and command overrides
      entryPoint = container.entryPoint
      command    = container.command

      # Resource limits
      ulimits = container.ulimits

      # Container dependencies
      dependsOn = container.dependsOn

      # Timeouts
      startTimeout = container.startTimeout
      stopTimeout  = container.stopTimeout
    }
  ]

  # Check if both ARNs are provided and not the same
  role_validation_condition = coalesce(var.execution_role_arn, "") != coalesce(var.task_role_arn, "")

  # Fail if the validation condition is not met
  _ = (
    local.role_validation_condition && var.execution_role_arn != "" && var.task_role_arn != "" ?
    true :
    fail("Execution Role ARN and Task Role ARN must be different if both are provided.")
  )
}
