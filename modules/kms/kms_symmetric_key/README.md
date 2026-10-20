# KMS module

This module deploys a symmetric KMS key compliant with organisation standards. 
The following points are useful while deploying the KMS resource with the module.

- It is recommended to use different roles for administer, encrypt and decrypt with the KMS key for better security and managebility but according to the specific project need, these roles can be same as well.

- You can use single or multiple role ARNs for different KMS activity group (administrator/encrypt/decrypt)

- For certain cases where you need to allow the entire account with the KMS activities (encrypt/decrypt), you can use 
 the following against the specific activity role ARN
 "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"

## Usage

```tf
module "kms" {
  source  = "registry.example.com/terraform-modules__aws-services/kms_symmetric_key/aws"
  version = "2026.4.3-weekly"

  iam_role_administrator = ["test_role_admin1", "test_role_admin2"] # The list can contain single or multiple IAM role ARNs
  iam_role_encrypt = ["test_role_encrypt1", "test_role_encrypt2"]   # The list can contain single or multiple IAM role ARNs
  iam_role_decrypt = ["test_role_decrypt1", "test_role_decrypt2"]   # The list can contain single or multiple IAM role ARNs
  deletion_window_in_days = 30               # value 30 or less
  key_alias = "kms_test_key_sandbox"         # use the alias you want to set for easy identification
  
  tags = {
    CE_Application_ID    = "APM2467135"
    CE_Application_Name  = "Test application"
    CE_Environment       = "DEV"
  }
}
```
<!-- BEGIN_TF_DOCS -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| iam\_role\_administrator | The list of ARNs of the IAM roles which will administer and use the KMS key | `list(string)` | n/a | yes |
| iam\_role\_decrypt | The list of ARNs of the IAM role that will decrypt with the KMS key | `list(string)` | n/a | yes |
| iam\_role\_encrypt | The list of ARNs of the IAM role that will encrypt with the KMS key | `list(string)` | n/a | yes |
| key\_alias | The alias name for the KMS key | `string` | n/a | yes |
| tags | A map of tags to assign to the resource. Must include CE\_Application\_ID, CE\_Application\_Name, and CE\_Environment. | `map(string)` | n/a | yes |
| allowed\_services | List of AWS service names allowed to use the key for encryption/decryption (e.g., ['sns', 'sqs']). Services will be granted GenerateDataKey and Decrypt permissions with SourceAccount condition. Required for cross-service encryption like SNS-to-SQS delivery. Note: Lambda should use IAM roles (iam\_role\_encrypt/iam\_role\_decrypt) instead of service principal access. | `list(string)` | `[]` | no |
| deletion\_window\_in\_days | The number of days before the KMS key is deleted after a deletion request | `number` | `30` | no |

## Outputs

| Name | Description |
|------|-------------|
| kms\_key\_arn | The ARN of the KMS key |
| kms\_key\_id | The ID of the KMS key |
<!-- END_TF_DOCS -->
