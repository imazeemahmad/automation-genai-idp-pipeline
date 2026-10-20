# ECS Cluster Module

This module deploys an ECS Cluster compliant with organisation standards.

## Usage

```tf
module "ecs_cluster" {
  source  = "registry.example.com/terraform-modules__aws-services/ecs_cluster/aws"
  version = "2026.4.3-weekly"

  cluster_name = "Dev_test_ecs_cluster"
  tags = {
    CE_Application_Name = "APM0000000"
    CE_Application_ID = "APM0000000"
    CE_Environment    = "DEV"
    Purpose           = "Integration tests for the Terraform module catalog"
  }
}
```

<!-- BEGIN_TF_DOCS -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| cluster\_name | The name of the ECS Cluster | `string` | n/a | yes |
| tags | A map of tags to assign to the resource. Must include CE\_Application\_ID, CE\_Application\_Name, and CE\_Environment. | `map(string)` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| cloudwatch\_log\_group\_arn | The ARN of the CloudWatch log group for the API Gateway |
| cluster\_id | The ID of the ECS cluster |
<!-- END_TF_DOCS -->