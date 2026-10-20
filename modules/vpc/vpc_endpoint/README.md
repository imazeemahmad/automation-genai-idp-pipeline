# VPC Endpoint Module

This module creates VPC endpoints compliant with organisation standards.
## Usage

```tf
module "vpc_endpoint" {
  source  = "registry.example.com/terraform-modules__aws-services/vpc_endpoint/aws"
  version = "2026.4.3-weekly"

  name              = "my_enpoint_name"
  vpc_id            = "my_vpc_id"
  endpoint_type     = "Interface"
  service_name      = "aws.api.eu-west-1.kendra-ranking"
  security_groups   = ["sg-ef6ab19c"]

  tags = {
      name                = "my-vpc-endpoint"
      CE_Application_Name = "APM0000000"
      CE_Application_ID   = "APM0000000"
      CE_Environment      = "DEV"
      Purpose             = "Integration tests for the Terraform module catalog"
  }
}
```

<!-- BEGIN_TF_DOCS -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| security\_groups | List of security groups for the service. If not specified, default will be used. | `list(string)` | n/a | yes |
| service\_name | The service name of the VPC endpoint | `string` | n/a | yes |
| tags | A map of tags to assign to the resource. Must include CE\_Application\_ID, CE\_Application\_Name, and CE\_Environment. | `map(string)` | n/a | yes |
| endpoint\_type | The type of VPC endpoint | `string` | `"Gateway"` | no |
| name | The name of the VPC endpoint | `string` | `null` | no |
| subnets | List of subnets for the service. If not specified, default will be used. | `list(string)` | `[]` | no |
| vpc\_filters | List of filters to apply to select the VPC (optional) | <pre>list(object({<br>    name   = string<br>    values = list(string)<br>  }))</pre> | `null` | no |
| vpc\_id | The ID of the VPC (optional) | `string` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| arn | n/a |
| id | n/a |
<!-- END_TF_DOCS -->