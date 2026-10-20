# ECS Task Definition Module

This module deploys an ECS Task Definition compliant with organisation standards.

Note: A separate [module](./../ecs_default_execution_role) exists for creating a default ECS execution role.

## Features

- Full container definition support including environment variables, secrets, and health checks
- Security defaults: non-root user (1001), read-only root filesystem, privileged=false
- EFS volume support for persistent storage
- Automatic CloudWatch Logs configuration
- Container dependency ordering

## Usage

### Basic Usage

```tf
module "ecs_task_definition" {
  source = "registry.example.com/terraform-modules__aws-services/ecs_task_definition/aws"
  version = "2026.4.3-weekly"

  family             = "my-app"
  execution_role_arn = module.execution_role.role_arn
  task_role_arn      = module.task_role.role_arn
  cpu                = 256
  memory             = 512

  container_definitions = [
    {
      name      = "app"
      image     = "123456789.dkr.ecr.eu-west-1.amazonaws.com/my-app:latest"
      cpu       = 256
      memory    = 512
      essential = true
    }
  ]

  tags = {
    CE_Application_ID   = "APM0000000"
    CE_Application_Name = "My Application"
    CE_Environment      = "DEV"
  }
}
```

### With Environment Variables and Secrets

```tf
module "ecs_task_definition" {
  source  = "registry.example.com/terraform-modules__aws-services/ecs_task_definition/aws"
  version = "2026.4.3-weekly"

  family             = "my-app"
  execution_role_arn = module.execution_role.role_arn
  task_role_arn      = module.task_role.role_arn
  cpu                = 512
  memory             = 1024

  container_definitions = [
    {
      name      = "app"
      image     = "123456789.dkr.ecr.eu-west-1.amazonaws.com/my-app:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]

      # Environment variables
      environment = [
        { name = "NODE_ENV", value = "production" },
        { name = "LOG_LEVEL", value = "info" }
      ]

      # Secrets from Secrets Manager or SSM Parameter Store
      secrets = [
        { name = "DATABASE_URL", valueFrom = "arn:aws:secretsmanager:eu-west-1:123456789:secret:db-url" },
        { name = "API_KEY", valueFrom = "arn:aws:ssm:eu-west-1:123456789:parameter/api-key" }
      ]

      # Container health check
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ]

  tags = {
    CE_Application_ID   = "APM0000000"
    CE_Application_Name = "My Application"
    CE_Environment      = "DEV"
  }
}
```

### With EFS Volume

```tf
module "ecs_task_definition" {
  source  = "registry.example.com/terraform-modules__aws-services/ecs_task_definition/aws"
  version = "2026.4.3-weekly"

  family             = "my-app"
  execution_role_arn = module.execution_role.role_arn
  cpu                = 256
  memory             = 512

  volumes = [
    {
      name = "data"
      efs_volume_configuration = {
        file_system_id     = "fs-12345678"
        root_directory     = "/app-data"
        transit_encryption = "ENABLED"
        authorization_config = {
          access_point_id = "fsap-12345678"
          iam             = "ENABLED"
        }
      }
    }
  ]

  container_definitions = [
    {
      name      = "app"
      image     = "my-app:latest"
      essential = true

      mountPoints = [
        {
          sourceVolume  = "data"
          containerPath = "/data"
          readOnly      = false
        }
      ]
    }
  ]

  tags = {
    CE_Application_ID   = "APM0000000"
    CE_Application_Name = "My Application"
    CE_Environment      = "DEV"
  }
}
```

## Container Definition Fields

| Field | Description | Default |
|-------|-------------|---------|
| `name` | Container name | Required |
| `image` | Docker image | Required |
| `cpu` | CPU units | Optional |
| `memory` | Memory in MiB | Optional |
| `essential` | Stop task if container fails | `true` |
| `user` | Linux user (non-root enforced) | `"1000"` |
| `portMappings` | Port mappings | `[]` |
| `environment` | Environment variables | `[]` |
| `secrets` | Secrets Manager/SSM references | `[]` |
| `healthCheck` | Container health check | `null` |
| `mountPoints` | Volume mount points | `[]` |
| `volumesFrom` | Volumes from other containers | `[]` |
| `linuxParameters` | Linux-specific options | `{readonlyRootFilesystem: true}` |
| `workingDirectory` | Working directory | `null` |
| `entryPoint` | Entry point override | `null` |
| `command` | Command override | `null` |
| `dependsOn` | Container dependencies | `[]` |

## Security Defaults

This module enforces the following security defaults:
- **Non-root user**: Containers run as user `1001` by default (user `0` is automatically changed)
- **Read-only root filesystem**: Enabled by default via `linuxParameters`
- **Privileged mode**: Always disabled (`privileged = false`)
<!-- BEGIN_TF_DOCS -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| container\_definitions | List of container definitions with full AWS ECS container definition support | <pre>list(object({<br>    name      = string<br>    image     = string<br>    cpu       = optional(number)<br>    memory    = optional(number)<br>    essential = optional(bool, true)<br>    user      = optional(string, "1000")<br>    portMappings = optional(list(object({<br>      containerPort = number<br>      hostPort      = optional(number)<br>      protocol      = optional(string, "tcp")<br>    })), [])<br>    logConfiguration = optional(object({<br>      logDriver = string<br>      options   = map(string)<br>    }))<br>    # Environment variables support<br>    environment = optional(list(object({<br>      name  = string<br>      value = string<br>    })), [])<br>    # Secrets Manager / SSM Parameter Store support<br>    secrets = optional(list(object({<br>      name      = string<br>      valueFrom = string<br>    })), [])<br>    # Container health check support<br>    healthCheck = optional(object({<br>      command     = list(string)<br>      interval    = optional(number, 30)<br>      timeout     = optional(number, 5)<br>      retries     = optional(number, 3)<br>      startPeriod = optional(number, 0)<br>    }))<br>    # Volume mount support<br>    mountPoints = optional(list(object({<br>      sourceVolume  = string<br>      containerPath = string<br>      readOnly      = optional(bool, false)<br>    })), [])<br>    # Volumes from other containers<br>    volumesFrom = optional(list(object({<br>      sourceContainer = string<br>      readOnly        = optional(bool, false)<br>    })), [])<br>    # Linux-specific parameters<br>    linuxParameters = optional(object({<br>      readonlyRootFilesystem = optional(bool, true)<br>      initProcessEnabled     = optional(bool, false)<br>      capabilities = optional(object({<br>        add  = optional(list(string), [])<br>        drop = optional(list(string), [])<br>      }))<br>    }))<br>    # Working directory<br>    workingDirectory = optional(string)<br>    # Entry point override<br>    entryPoint = optional(list(string))<br>    # Command override<br>    command = optional(list(string))<br>    # Ulimits<br>    ulimits = optional(list(object({<br>      name      = string<br>      softLimit = number<br>      hardLimit = number<br>    })), [])<br>    # Dependency ordering<br>    dependsOn = optional(list(object({<br>      containerName = string<br>      condition     = string<br>    })), [])<br>    # Start/Stop timeout<br>    startTimeout = optional(number)<br>    stopTimeout  = optional(number)<br>  }))</pre> | n/a | yes |
| cpu | Number of cpu units used by the task. | `number` | n/a | yes |
| execution\_role\_arn | The ARN of the task execution role | `string` | n/a | yes |
| family | The family name of the ECS task definition | `string` | n/a | yes |
| memory | Amount (in MiB) of memory used by the task. | `number` | n/a | yes |
| tags | A map of tags to assign to the resource. Must include CE\_Application\_ID, CE\_Application\_Name, and CE\_Environment. | `map(string)` | n/a | yes |
| task\_role\_arn | The ARN of the task role | `string` | `""` | no |
| volumes | List of volumes to attach to the task definition | <pre>list(object({<br>    name = string<br>    efs_volume_configuration = optional(object({<br>      file_system_id          = string<br>      root_directory          = optional(string, "/")<br>      transit_encryption      = optional(string, "ENABLED")<br>      transit_encryption_port = optional(number)<br>      authorization_config = optional(object({<br>        access_point_id = optional(string)<br>        iam             = optional(string, "ENABLED")<br>      }))<br>    }))<br>  }))</pre> | `[]` | no |

## Outputs

| Name | Description |
|------|-------------|
| task\_arn | The ARN of the ECS task definition |
<!-- END_TF_DOCS -->