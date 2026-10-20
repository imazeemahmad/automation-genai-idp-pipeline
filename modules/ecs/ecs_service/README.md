# ECS Service Module

This module deploys an ECS Service compliant with organisation standards.

## Usage

```tf
module "ecs_service" {
  source              = "registry.example.com/terraform-modules__aws-services/ecs_service/aws"
  version = "2026.4.3-weekly"

  service_name        = "my-service"
  ecs_cluster_id      = module.ecs_cluster.cluster_id
  task_definition_arn = module.ecs_task_definition.task_arn
  allow_public_ip     = false
  desired_count       = 2

  tags = {
    CE_Application_Name = "APM0000000"
    CE_Application_ID   = "APM0000000"
    CE_Environment      = "DEV"
  }
}

```
<!-- BEGIN_TF_DOCS -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| desired\_count | Number of desired tasks to run | `number` | n/a | yes |
| ecs\_cluster\_id | value | `string` | n/a | yes |
| service\_name | ECS Service name | `string` | n/a | yes |
| tags | A map of tags to assign to the resource. Must include CE\_Application\_ID, CE\_Application\_Name, and CE\_Environment. | `map(string)` | n/a | yes |
| task\_definition\_arn | ARN of the task definition | `string` | n/a | yes |
| allow\_public\_ip | Controls whether the ECS service should have a public IP. Default: false | `bool` | `false` | no |
| health\_check\_grace\_period\_seconds | (Optional) Seconds to ignore failing load balancer health checks on newly instantiated tasks to prevent premature shutdown. Only valid for services configured to use load balancers. | `string` | `null` | no |
| load\_balancer | List of load balancer configurations for the ECS service.<br><br>  Each object supports:<br>  - `target_group_arn` (Optional, string): ARN of the ALB/NLB Target Group (required for ALB/NLB).<br>  - `container_name` (Required, string): Name of the container to associate with the load balancer.<br>  - `container_port` (Required, number): Port on the container to associate with the load balancer. | <pre>list(object({<br>    target_group_arn = optional(string) # Only for ALB/NLB<br>    container_name   = string<br>    container_port   = number<br>  }))</pre> | `null` | no |
| security\_groups | List of security groups for the service. If not specified, default will be used. | `list(string)` | `[]` | no |
| subnets | List of subnets for the service. If not specified, default will be used. | `list(string)` | `[]` | no |
| vpc\_filters | List of filters to apply to the VPC endpoint | <pre>list(object({<br>    name   = string<br>    values = list(string)<br>  }))</pre> | `null` | no |
| vpc\_id | The VPC ID of the VPC endpoint | `string` | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| name | n/a |
<!-- END_TF_DOCS -->