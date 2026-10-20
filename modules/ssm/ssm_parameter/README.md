## ssm_parameter

This module deploys an AWS Systems Manager (SSM) Parameter Store parameter compliant with organisation standards.

> [!NOTE]
> **Best Practice:** While this module supports SecureString with KMS encryption, [Secrets Manager](https://example.atlassian.net/wiki/) is recommended for sensitive credentials (API keys, passwords). The reason: Secrets Manager supports **resource-based policies** (Deny by default), while SSM only supports IAM-based access control.

## Usage

```tf
module "ssm_parameter" {
  source  = "registry.example.com/terraform-modules__aws-services/ssm_parameter/aws"
  version = "2026.4.3-weekly"

  parameter_name  = "/myapp/database/password"
  parameter_value = "supersecret123"
  parameter_type  = "SecureString"

  kms_key_id = "arn:aws:kms:eu-west-1:123456789012:key/00000000-0000-0000-0000-000000000000"

  tags = {
    CE_Application_ID   = "APM0000000"
    CE_Environment      = "DEV"
    CE_Application_Name = "My Application"
    CE_DataSensitivity  = "HighlySensitive"
  }
}
```

## Parameter Types

You can specify one of three parameter types:

### SecureString (Recommended for Sensitive Data)
```tf
parameter_type  = "SecureString"
parameter_value = "my-secret-password"
kms_key_id      = "arn:aws:kms:..."  # Required for Sensitive/HighlySensitive
```

### String (Plain Text)
```tf
parameter_type  = "String"
parameter_value = "my-configuration-value"
```

### StringList (Comma-separated Values)
```tf
parameter_type  = "String"
parameter_value = "value1,value2,value3"
```

## Structured Data

For JSON configuration, use `jsonencode()`:

```tf
parameter_value = jsonencode({
  database = {
    host = "db.example.com"
    port = 5432
  }
  features = {
    feature_a = true
    feature_b = false
  }
})
```

## KMS Encryption

> [!WARNING]  
> A custom KMS key ID is required when CE_DataSensitivity tag is Sensitive or HighlySensitive.
> Without a custom key, the default `aws/ssm` key is used, which means **all principals** with SSM access in the account can decrypt the parameter.

```tf
kms_key_id = "arn:aws:kms:eu-west-1:111111111:key/aaaaaaaaaaaaa"
```

## Parameter Tiers

### Standard (Default)
- Up to 4 KB parameter value size
- No additional charges
- Suitable for most use cases

```tf
tier = "Standard"
```

### Advanced
- Up to 8 KB parameter value size
- Additional charges apply
- Supports parameter policies

```tf
tier = "Advanced"
```

### Intelligent-Tiering
- Automatically moves parameters between Standard and Advanced based on size
- Optimizes costs

```tf
tier = "Intelligent-Tiering"
```

## Managing parameter values outside Terraform

When the parameter value is managed outside of Terraform (e.g., updated manually via AWS Console/CLI, SSM Session Manager, or external automation), set `ignore_value_changes = true`:

```tf
module "external_config" {
  source  = "registry.example.com/terraform-modules__aws-services/ssm_parameter/aws"
  version = "2026.4.3-weekly"

  parameter_name  = "/myapp/runtime-config"
  parameter_value = "PLACEHOLDER"  # Initial placeholder value
  parameter_type  = "String"
  
  ignore_value_changes = true  # Terraform won't overwrite external updates

  tags = {
    CE_Application_ID   = "APM0000000"
    CE_Environment      = "DEV"
    CE_Application_Name = "My Application"
    CE_DataSensitivity  = "Internal"
  }
}
```

> [!IMPORTANT]
> Unlike Secrets Manager, **SSM parameters require an initial value at creation**. Use a placeholder value (e.g., `"PLACEHOLDER"` or `"REPLACE_ME"`) that you'll replace after the parameter is created.

When `ignore_value_changes = true`:
1. `terraform apply` creates the parameter with the placeholder value
2. Manually set the real value via AWS Console/CLI
3. Terraform will not overwrite externally-set values
4. Other attributes (name, type, KMS key, tags) remain managed by Terraform

### Use Cases for `ignore_value_changes`

- **Runtime configuration** updated by application code
- **Feature flags** managed by a separate control plane
- **Credentials** rotated by AWS Secrets Manager or external tools
- **Dynamic values** set by CI/CD pipelines or automation

### Migrating existing parameters

If you have an existing parameter managed by Terraform and want to switch to external management:

1. Add `ignore_value_changes = true` to your module call
2. Run `terraform apply` - Terraform will update the lifecycle policy
3. Future external updates won't be overwritten by Terraform

## Parameter Naming Conventions

Parameter names must follow AWS SSM constraints:

- Must begin with `/` (forward slash)
- Can contain: letters, numbers, hyphens (`-`), underscores (`_`), periods (`.`), forward slashes (`/`)
- Maximum length: 2048 characters

**Recommended hierarchy:**

```
/application-name/environment/component/setting
```

**Examples:**
```tf
parameter_name = "/myapp/prod/database/connection-string"
parameter_name = "/myapp/dev/api/rate-limit"
parameter_name = "/shared/tools/monitoring/endpoint"
```

## Access Control

> [!IMPORTANT]
> Unlike AWS Secrets Manager, **SSM Parameter Store does not support resource-based policies**. Access control must be managed through IAM policies on roles and users.

### Using the Module's IAM Policy Output

The module provides an IAM policy document output that you can attach to your roles:

```tf
module "app_parameter" {
  source  = "registry.example.com/terraform-modules__aws-services/ssm_parameter/aws"
  version = "2026.4.3-weekly"

  parameter_name  = "/myapp/config"
  parameter_value = jsonencode({ key = "value" })
  
  allowed_role_arns = [
    "arn:aws:iam::123456789012:role/MyAppRole"
  ]

  tags = { ... }
}

# Create IAM policy from module output
resource "aws_iam_policy" "parameter_access" {
  name   = "myapp-parameter-access"
  policy = module.app_parameter.iam_policy_json
}

# Attach to role
resource "aws_iam_role_policy_attachment" "attach" {
  role       = "MyAppRole"
  policy_arn = aws_iam_policy.parameter_access.arn
}
```

The generated policy includes:
- ✅ `ssm:GetParameter` on the specific parameter ARN
- ✅ `kms:Decrypt` on the KMS key (if using SecureString with custom KMS)

### Manual IAM Policy Example

If you prefer to write your own IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParameterHistory"
      ],
      "Resource": "arn:aws:ssm:eu-west-1:123456789012:parameter/myapp/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt"
      ],
      "Resource": "arn:aws:kms:eu-west-1:123456789012:key/YOUR-KMS-KEY-ID"
    }
  ]
}
```

## Advanced: Data Types

The `data_type` parameter allows SSM to validate and format specific AWS resource types:

### AMI IDs
```tf
data_type      = "aws:ec2:image"
parameter_value = "ami-0abcdef1234567890"
```

This enables validation and formatting in the AWS Console.

<!-- BEGIN_TF_DOCS -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| parameter\_name | The name of the parameter. Must begin with / and follow SSM naming constraints. | `string` | n/a | yes |
| tags | A map of tags to assign to the resource. Must include CE\_Application\_ID, CE\_Application\_Name, CE\_Environment and CE\_DataSensitivity. | `map(string)` | n/a | yes |
| allowed\_role\_arns | List of IAM role ARNs that should have access to this parameter. Module will generate an IAM policy document that can be attached to these roles. | `list(string)` | `[]` | no |
| data\_type | The data type for the parameter. Use 'text' for general strings, 'aws:ec2:image' for AMI IDs. | `string` | `"text"` | no |
| description | A description for the parameter | `string` | `"Parameter created by Terraform Module"` | no |
| ignore\_value\_changes | When true, Terraform will ignore external changes to the parameter value. Useful when the value is updated outside of Terraform. | `bool` | `false` | no |
| kms\_key\_id | The KMS key ID for encryption (only for SecureString type). Will use aws/ssm if not set. A custom KMS key ID is required when CE\_DataSensitivity is Sensitive or HighlySensitive. | `string` | `null` | no |
| parameter\_type | The type of the parameter. Valid values: String, StringList, SecureString | `string` | `"SecureString"` | no |
| parameter\_value | The value of the parameter. Use jsonencode() for structured data. For externally-managed parameters, set to a placeholder like 'PLACEHOLDER' and enable ignore\_value\_changes. | `string` | `"PLACEHOLDER"` | no |
| tier | The tier of the parameter. Standard allows up to 4KB, Advanced allows up to 8KB. | `string` | `"Standard"` | no |

## Outputs

| Name | Description |
|------|-------------|
| iam\_policy\_json | IAM policy JSON that can be attached to roles for parameter access (only if allowed\_role\_arns is provided) |
| iam\_policy\_statements | IAM policy statements for parameter access (for use in custom policies) |
| parameter\_arn | The ARN of the parameter |
| parameter\_name | The name of the parameter |
| parameter\_type | The type of the parameter |
| parameter\_version | The version of the parameter |
<!-- END_TF_DOCS -->
