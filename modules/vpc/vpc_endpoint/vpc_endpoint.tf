locals {
  private_dns_enabled = var.endpoint_type == "Interface" ? true : false
}

module "vpc_selector" {
  source = "../vpc_selector"

  vpc_id      = var.vpc_id
  vpc_filters = var.vpc_filters
}

data "aws_subnets" "default_subnets" {
  filter {
    name   = "vpc-id"
    values = [module.vpc_selector.vpc_id]
  }
}

resource "aws_vpc_endpoint" "vpc_endpoint" {
  vpc_endpoint_type = var.endpoint_type
  service_name      = var.service_name

  vpc_id = var.vpc_id == null ? module.vpc_selector.vpc_id : var.vpc_id
  dns_options {
    # Enable DNS name = true
    dns_record_ip_type = "ipv4"
  }

  subnet_ids         = length(var.subnets) == 0 ? data.aws_subnets.default_subnets.ids : var.subnets
  security_group_ids = var.security_groups

  private_dns_enabled = local.private_dns_enabled # Recommended for AWS services

  tags = merge(var.tags,
    var.name != null ? { Name  = var.name } : {}, {
      Terraform_Module_Name    = "shared-modules:aws:vpc_endpoint"
      Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
      Terraform_Module_Version = "__VERSION__"
  })
}
