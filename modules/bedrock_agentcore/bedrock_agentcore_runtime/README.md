# bedrock_agentcore_runtime

This module deploys an AWS Bedrock AgentCore Agent Runtime.

## Usage

```tf
module "bedrock_agentcore_runtime" {
  source  = "registry.example.com/terraform-modules__aws-services/bedrock_agentcore_runtime/aws"
  version = "2026.4.3-weekly"

  agent_runtime_name = "my_agent_runtime"
  image_uri          = "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-agent:latest"
  role_arn           = "arn:aws:iam::123456789012:role/App_my_agent_runtime"

  # Optional VPC configuration (omit to use defaults)
  vpc_config = {
    subnet_ids         = ["subnet-abc", "subnet-def"]
    security_group_ids = ["sg-1234567890abcdef0"]
  }

  # Optional protocol configuration (MCP, HTTP, or A2A)
  server_protocol = "HTTP"

  tags = {
    CE_Application_ID   = "APM0000000"
    CE_Application_Name = "MyApp"
    CE_Environment      = "DEV"
  }
}
```

<!-- BEGIN_TF_DOCS -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| agent\_runtime\_name | Name of the Bedrock agent runtime (letters, digits, underscore; max 48) | `string` | n/a | yes |
| image\_uri | The URI of the Docker image | `string` | n/a | yes |
| role\_arn | IAM role ARN used by the Bedrock Agent Runtime | `string` | n/a | yes |
| tags | A map of tags to assign to the resource. Must include CE\_Application\_ID, CE\_Application\_Name, and CE\_Environment. | `map(string)` | n/a | yes |
| agent\_runtime\_env\_variables | Environment variables for the AgentCore Runtime container | `map(string)` | `{}` | no |
| server\_protocol | The server protocol for the agent runtime. Specifies how the agent runtime communicates with clients. Valid values: MCP, HTTP, A2A. | `string` | `null` | no |
| vpc\_config | VPC configuration if the Agent Runtime requires networking. If not specified, defaults will be used. | <pre>object({<br>    security_group_ids = list(string)<br>    subnet_ids         = list(string)<br>  })</pre> | `null` | no |

## Outputs

| Name | Description |
|------|-------------|
| agent\_runtime\_arn | Bedrock Agent Runtime ARN |
| agent\_runtime\_id | Bedrock Agent Runtime id |
| role\_arn | IAM role ARN used by the Bedrock Agent Runtime |
<!-- END_TF_DOCS -->

## Notes
- The execution role must include baseline permissions for CloudWatch Logs, X-Ray tracing, CloudWatch metrics, and Bedrock model invocation. See the AWS documentation for recommended statements: [IAM Permissions for AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html#runtime-permissions-execution).
- Networking is configured for VPC mode. If `vpc_config` is not provided, defaults will be used for subnets and security group.

