# ECS Default Execution Role Module

This module deploys the ECS Default Execution Role following organisation standards. It should be invoked only once per GitHub repository. The module provisions an IAM role for the ECS service, configured as the execution role, and attaches the AWS-managed policy AmazonECSTaskExecutionRolePolicy.

## Usage

```tf
module "execution_role" {
  source = "registry.example.com/terraform-modules__aws-services/ecs_default_execution_role/aws"
  version = "2026.4.3-weekly"

  tags = {
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
| tags | A map of tags to assign to the resource. Must include CE\_Application\_ID, CE\_Application\_Name, and CE\_Environment. | `map(string)` | n/a | yes |

## Outputs

| Name | Description |
|------|-------------|
| role\_arn | The ARN of the default ECS execution role |
<!-- END_TF_DOCS -->