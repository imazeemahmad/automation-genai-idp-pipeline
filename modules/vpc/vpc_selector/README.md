# VPC Get Id

This module resolves and returns a single VPC ID based on the following priority:
- Uses explicit vpc_id variable if provided.
- Else, selects from filtered VPCs if exactly one matches the supplied filters.
- Else, selects from all VPCs in the region if exactly one exists.
- Otherwise, fails with a clear validation error requiring user intervention.

It simplifies infra setup by automating VPC selection logic and enforcing idempotency, avoiding ambiguous or accidental usage of multiple VPCs.

## Usage

```tf
module "vpc_selector" {
  source  = "registry.example.com/terraform-modules__aws-services/vpc_selector/aws"
  version = "2026.4.3-weekly"

  vpc_id      = "my_vpc_id" (optional)
  vpc_filters = [           (optional)
    content {
      name   = filter.value.name
      values = filter.value.values
    }
  ]

}
```

<!-- BEGIN_TF_DOCS -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| vpc\_filters | List of filters to apply to select the VPC (optional) | <pre>list(object({<br>    name   = string<br>    values = list(string)<br>  }))</pre> | `null` | no |
| vpc\_id | The ID of the VPC (optional) | `string` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| vpc\_id | n/a |
<!-- END_TF_DOCS -->