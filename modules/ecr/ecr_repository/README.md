# ECR module

This module deploys an ECR repository compliant with organisation standards.

## Features

- Automatic image scanning on push
- Configurable KMS encryption (AES256 default, KMS optional)
- Lifecycle policy to expire old images
- Repository policy with optional cross-account access
- Immutable tags by default for security

## Usage

### Basic Usage (Single Account)

```tf
module "ecr" {
  source  = "registry.example.com/terraform-modules__aws-services/ecr_repository/aws"
  version = "2026.4.3-weekly"

  ecr_repository_name  = "my-application"
  kms_key_arn          = null  # Uses AES256 encryption
  image_count          = 100
  image_tag_mutability = "IMMUTABLE"

  tags = {
    CE_Application_ID   = "APM1234567"
    CE_Application_Name = "My Application"
    CE_Environment      = "DEV"
  }
}
```

### With KMS Encryption and Cross-Account Access

```tf
module "ecr" {
  source  = "registry.example.com/terraform-modules__aws-services/ecr_repository/aws"
  version = "2026.4.3-weekly"

  ecr_repository_name  = "test-ecr-repository"
  kms_key_arn          = "arn:aws:kms:eu-west-1:123456789:key/abcdedfgh-123456789"
  additional_role_arn  = "arn:aws:iam::987654321:role/cross-account-role"  # Optional: for cross-account access
  image_count          = 1000
  image_tag_mutability = "IMMUTABLE"

  tags = {
    CE_Application_ID   = "APM1234567"
    CE_Application_Name = "Test application"
    CE_Environment      = "DEV"
  }
}
```

### Usage with AWS Services (Lambda, ECS, CodeBuild, etc.)

When using this ECR repository to store container images for AWS services, you must add the `service_access` variable. This grants AWS service principals permission to pull images from the repository.

```tf
module "ecr" {
  source  = "registry.example.com/terraform-modules__aws-services/ecr_repository/aws"
  version = "2026.4.3-weekly"

  ecr_repository_name  = "my-container"
  kms_key_arn          = module.kms.key_arn
  image_count          = 10
  image_tag_mutability = "IMMUTABLE"
  
  # Grant IAM role permission to push/pull images
  additional_role_arn = module.task_role.role_arn
  
  # Grant AWS service principals permission to pull images
  service_access = [
    {
      service            = "lambda.amazonaws.com"
      source_arn_pattern = "arn:aws:lambda:eu-west-1:123456789012:function:my-app-*"
    },
    {
      service            = "ecs-tasks.amazonaws.com"
      source_arn_pattern = "arn:aws:ecs:eu-west-1:123456789012:*"
    }
  ]
  
  tags = {
    CE_Application_ID   = "APM1234567"
    CE_Application_Name = "My Application"
    CE_Environment      = "DEV"
  }
}
```

## Notes

- The `additional_role_arn` is optional. If not provided, only the account root has access.
- For single-account deployments, ECS pulls images via IAM policies on the execution role, so repository policies are typically not needed.
- Without `service_access`, Lambda container deployments may fail with: "The function does not have permission to access the specified image."
- Image scanning results are available in the ECR console and via AWS APIs.
<!-- BEGIN_TF_DOCS -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| ecr\_repository\_name | The name of the ECR repository | `string` | n/a | yes |
| image\_count | Number of images after which images should expire | `number` | n/a | yes |
| kms\_key\_arn | The ARN of the KMS key to use for encryption | `string` | n/a | yes |
| tags | A map of tags to assign to the resource. Must include CE\_Application\_ID, CE\_Application\_Name, and CE\_Environment. | `map(string)` | n/a | yes |
| additional\_role\_arn | The ARN of the additional IAM role to grant access | `string` | `null` | no |
| image\_tag\_mutability | Control ECR repository tag mutability. Allowed values: MUTABLE, IMMUTABLE. | `string` | `"IMMUTABLE"` | no |
| service\_access | List of AWS service principals that need to pull images from this repository.<br>Each entry specifies the service and an ARN pattern condition for access control.<br><br>Example:<pre>service_access = [<br>  {<br>    service         = "lambda.amazonaws.com"<br>    source_arn_pattern = "arn:aws:lambda:eu-west-1:123456789012:function:my-app-*"<br>  },<br>  {<br>    service         = "ecs-tasks.amazonaws.com"<br>    source_arn_pattern = "arn:aws:ecs:eu-west-1:123456789012:*"<br>  }<br>]</pre> | <pre>list(object({<br>    service            = string<br>    source_arn_pattern = string<br>  }))</pre> | `[]` | no |

## Outputs

| Name | Description |
|------|-------------|
| ecr\_repository\_arn | The ARN of the ECR repository |
| ecr\_repository\_url | The URL of the ECR repository |
<!-- END_TF_DOCS -->
