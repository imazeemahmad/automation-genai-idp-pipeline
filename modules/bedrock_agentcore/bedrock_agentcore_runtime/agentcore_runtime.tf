module "vpc_selector" {
  source  = "../../vpc/vpc_selector"
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

locals {
  effective_security_group_ids = var.vpc_config != null ? var.vpc_config.security_group_ids : [data.aws_security_group.default_sg.id]
  effective_subnet_ids         = var.vpc_config != null ? var.vpc_config.subnet_ids : data.aws_subnets.default_subnets.ids
}

resource "aws_bedrockagentcore_agent_runtime" "agent" {
  agent_runtime_name = var.agent_runtime_name
  role_arn           = var.role_arn

  environment_variables = var.agent_runtime_env_variables

  agent_runtime_artifact {
    container_configuration {
      container_uri = var.image_uri
    }
  }

  network_configuration {
    network_mode = "VPC"
    network_mode_config {
      security_groups = local.effective_security_group_ids
      subnets         = local.effective_subnet_ids
    }
  }

  dynamic "protocol_configuration" {
    for_each = var.server_protocol != null ? [1] : []
    content {
      server_protocol = var.server_protocol
    }
  }

  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:bedrock_agentcore_runtime"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "1.2.0"
  })

}