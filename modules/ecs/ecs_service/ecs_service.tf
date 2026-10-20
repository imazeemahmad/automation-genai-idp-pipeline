module "vpc_selector" {
  source  = "registry.example.com/terraform-modules__aws-services/vpc_selector/aws"
  version = "0.0.0-latest"

  vpc_id      = var.vpc_id
  vpc_filters = var.vpc_filters
}

data "aws_subnets" "default_subnets" {
  filter {
    name   = "vpc-id"
    values = [module.vpc_selector.vpc_id]
  }
}

data "aws_security_group" "default_sg" {
  vpc_id = module.vpc_selector.vpc_id
  filter {
    name   = "group-name"
    values = ["default"]
  }
}


resource "aws_ecs_service" "service" {
  name            = var.service_name
  cluster         = var.ecs_cluster_id
  task_definition = var.task_definition_arn
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = length(var.subnets) == 0 ? data.aws_subnets.default_subnets.ids : var.subnets
    security_groups = length(var.security_groups) == 0 ? [data.aws_security_group.default_sg.id] : var.security_groups
    # Default: No public IP to enhance security
    assign_public_ip = var.allow_public_ip
    # assign_public_ip = var.assign_public_ip
  }

  desired_count = var.desired_count

  # Ensure it always runs on the latest Fargate platform version
  platform_version = "LATEST"

  health_check_grace_period_seconds = var.health_check_grace_period_seconds

  dynamic "load_balancer" {
    for_each = var.load_balancer != null ? var.load_balancer : []
    content {
      target_group_arn = lookup(load_balancer.value, "target_group_arn", null)
      container_name   = load_balancer.value.container_name
      container_port   = load_balancer.value.container_port
    }
  }

  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:ecs_service"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "__VERSION__"
  })
}

