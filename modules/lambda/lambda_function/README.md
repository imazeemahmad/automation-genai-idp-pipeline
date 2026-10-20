# lambda.function

This module deploys a Lambda Function with support for both ZIP and container-based deployments.

## Deployment Types

The module supports two mutually exclusive deployment types via the `deployment_config` variable:

- **ZIP deployment**: Deploy Lambda code from an S3 bucket using `deployment_config.zip`
- **Container deployment**: Deploy Lambda from an ECR container image using `deployment_config.container`

Exactly one of `zip` or `container` must be provided within `deployment_config`.

## Usage

### ZIP Deployment

```hcl
module "lambda_function" {
  source  = "registry.example.com/terraform-modules__aws-services/lambda_function/aws"
  version = "2026.4.3-weekly"

  function_name = "my-zip-lambda"
  role_arn      = "arn:aws:iam::123456789:role/App_my_lambda_role"

  deployment_config = {
    zip = {
      runtime   = "python3.13"
      handler   = "lambda.handler"
      s3_bucket = "mybucket"
      s3_key    = "path/to/lambda.py.zip"
    }
  }

  logging_config = {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
  }

  env_vars = {
    var_a = "my_env_var"
  }

  destinations = {
    on_failure_arn = "arn:aws:sns::123456789:my-topic"
  }

  lambda_permissions = {
    "s3_invoke" = {
      principal      = "s3.amazonaws.com"
      action         = "lambda:InvokeFunction"
      source_arn     = "arn:aws:s3:::mybucket"
      source_account = "123456789"
    }
  }

  tags = {
    CE_Application_ID   = "APM0000000"
    CE_Application_Name = "MyApp"
    CE_Environment      = "DEV"
  }
}
```

### Container Deployment

```hcl
module "lambda_function" {
  source  = "registry.example.com/terraform-modules__aws-services/lambda_function/aws"
  version = "2026.4.3-weekly"

  function_name = "my-container-lambda"
  role_arn      = "arn:aws:iam::123456789:role/App_my_lambda_role"

  deployment_config = {
    container = {
      image_uri = "123456789.dkr.ecr.eu-west-1.amazonaws.com/my-repo:v1.0"
    }
  }

  tags = {
    CE_Application_ID   = "APM0000000"
    CE_Application_Name = "MyApp"
    CE_Environment      = "DEV"
  }
}
```

> **Note:** When using container deployments, the Lambda will only be updated when the `image_uri` value changes. If you push a new image with the same tag (e.g., `:latest`), Terraform will not detect the change and the Lambda will not be redeployed. Use immutable tags (e.g., `:v1.0.1`, `:sha-abc123`) for automatic updates, or run `terraform apply -replace=module.<name>.aws_lambda_function.lambda_function` to force an update.

<!-- BEGIN_TF_DOCS -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| deployment\_config | Lambda deployment configuration. Exactly one of 'zip' or 'container' must be provided. | <pre>object({<br>    zip = optional(object({<br>      runtime   = string<br>      handler   = string<br>      s3_bucket = string<br>      s3_key    = string<br>      layers    = optional(list(string), [])<br>    }))<br>    container = optional(object({<br>      image_uri = string<br>    }))<br>  })</pre> | n/a | yes |
| function\_name | Name of the Lambda function | `string` | n/a | yes |
| role\_arn | ARN of the Lambda execution role | `string` | n/a | yes |
| tags | A map of tags to assign to the resource. Must include CE\_Application\_ID, CE\_Application\_Name, and CE\_Environment. | `map(string)` | n/a | yes |
| architectures | Runtime architecture | `list(string)` | <pre>[<br>  "arm64"<br>]</pre> | no |
| destinations | Set the destinations for the Lambda function (Up to 1 destination on\_failure and 1 destination on success) | <pre>object({<br>    on_failure_arn = optional(string, null)<br>    on_success_arn = optional(string, null)<br>  })</pre> | <pre>{<br>  "on_failure_arn": null,<br>  "on_success_arn": null<br>}</pre> | no |
| env\_vars | Environment variables to set for the lambda function | `map(string)` | `{}` | no |
| ephemeral\_storage | The amount of Ephemeral storage(/tmp) to allocate for the Lambda Function in MB. This parameter is used to expand the total amount of Ephemeral storage available, beyond the default amount of 512MB. | `number` | `512` | no |
| kms\_key\_arn | KMS key used to encrypt the environment variables | `string` | `null` | no |
| lambda\_permissions | n/a | <pre>map(object({<br>    principal      = string<br>    action         = string<br>    source_arn     = optional(string, null)<br>    source_account = optional(string, null)<br>  }))</pre> | `{}` | no |
| logging\_config | Lambda logging configuration. log\_format sets the format (Text or JSON). application\_log\_level and system\_log\_level optionally control log detail levels. | <pre>object({<br>    log_format            = string<br>    application_log_level = optional(string, null)<br>    system_log_level      = optional(string, null)<br>  })</pre> | `null` | no |
| memory\_size | Amount of RAM allocated to the function | `number` | `128` | no |
| reserved\_concurrent\_executions | Amount of reserved concurrent executions | `number` | `-1` | no |
| timeout | Amount of time that the function can run in seconds (max = 900 s = 15 min) | `number` | `60` | no |
| vpc\_config | VPC configuration if the Lambda requires networking. If not specified, default will be used. | <pre>object({<br>    security_group_ids = list(string)<br>    subnet_ids         = list(string)<br>  })</pre> | `null` | no |
| xray\_enabled | Enable X-Ray tracing for the Lambda function | `bool` | `false` | no |

## Outputs

| Name | Description |
|------|-------------|
| lambda\_arn | Lambda function arn |
| lambda\_cw\_log\_group | Log group ARN |
| lambda\_invoke\_arn | Lambda function invoke ARN |
| lambda\_name | Lambda function name |
| lambda\_qualified\_arn | n/a |
<!-- END_TF_DOCS -->