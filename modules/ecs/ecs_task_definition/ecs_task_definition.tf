resource "aws_ecs_task_definition" "task_definition" {
  family                   = var.family
  container_definitions    = jsonencode(local.container_definitions)
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  network_mode             = "awsvpc"
  pid_mode                 = "task"

  execution_role_arn = var.execution_role_arn
  task_role_arn      = var.task_role_arn != "" ? var.task_role_arn : null

  # Dynamic volume blocks for EFS and other volume types
  dynamic "volume" {
    for_each = var.volumes
    content {
      name = volume.value.name

      dynamic "efs_volume_configuration" {
        for_each = volume.value.efs_volume_configuration != null ? [volume.value.efs_volume_configuration] : []
        content {
          file_system_id = efs_volume_configuration.value.file_system_id
          root_directory = efs_volume_configuration.value.root_directory
          # Explicitly default to ENABLED for security compliance (CKV_AWS_97)
          transit_encryption      = coalesce(efs_volume_configuration.value.transit_encryption, "ENABLED")
          transit_encryption_port = efs_volume_configuration.value.transit_encryption_port

          dynamic "authorization_config" {
            for_each = efs_volume_configuration.value.authorization_config != null ? [efs_volume_configuration.value.authorization_config] : []
            content {
              access_point_id = authorization_config.value.access_point_id
              iam             = authorization_config.value.iam
            }
          }
        }
      }
    }
  }

  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:ecs_task_definition"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "__VERSION__"
  })
}
