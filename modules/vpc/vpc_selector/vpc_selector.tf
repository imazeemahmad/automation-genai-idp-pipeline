locals {
  vpc_filters = var.vpc_filters != null ? var.vpc_filters : [
    {
      name   = "tag:Terraform_ID"
      values = ["1"]
    }
  ]
}


data "aws_vpcs" "filtered" {
  dynamic "filter" {
    for_each = local.vpc_filters
    content {
      name   = filter.value.name
      values = filter.value.values
    }
  }
}

# Get all VPCs (as fallback)
data "aws_vpcs" "all" {}

locals {
  selected_vpc_id = var.vpc_id != null ? var.vpc_id : length(data.aws_vpcs.filtered.ids) == 1 ? data.aws_vpcs.filtered.ids[0] : length(data.aws_vpcs.all.ids) == 1 ? data.aws_vpcs.all.ids[0] : null
}

