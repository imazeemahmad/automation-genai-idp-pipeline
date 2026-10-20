output "vpc_id" {
  value = local.selected_vpc_id

  precondition {
    condition     = local.selected_vpc_id != null
    error_message = "Could not select a VPC ID. Provide one or ensure exactly one VPC exists (optionally matching filters)."
  }
}
