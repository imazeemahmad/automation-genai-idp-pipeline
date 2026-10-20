# iam_role_service

This module deploys an IAM Role that trusts an AWS service (e.g. EC2, Lambda, SQS...).

To comply with organisation standards, the role name must start with `App_`.
It will automatically have the standard permission boundary attached.

## Usage

```tf
module "my_role" {
  source  = "registry.example.com/terraform-modules__aws-services/iam_role_service/aws"
  version = "2026.4.3-weekly"

  role_name             = "App_myrole"
  aws_service           = "lambda"
  inline_policies_json  = {
    inline_policy_name_1 = file("mypolicy_.json")
    inline_policy_name_2 = data.aws_iam_policy_document.inline_policy.json
  }
  managed_policies_arns = {
    policy_1 = "arn:aws:iam::${local.aws_account_id}:policy/App_mypolicy_1"
    policy_2 = "arn:aws:iam::${local.aws_account_id}:policy/App_mypolicy_2"
  }
  
  tags = {
    CE_Application_ID = "APM1234567"
    CE_Environment    = "PROD"
    MyOtherTag        = "Value"
  }
}
```

<!-- BEGIN_TF_DOCS -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| aws\_service | AWS service to trust, e.g. ec2, lambda | `string` | n/a | yes |
| role\_name | Name of the role, which must start with App\_ | `string` | n/a | yes |
| tags | A map of tags to assign to the resource. Must include CE\_Application\_ID, CE\_Application\_Name, and CE\_Environment. | `map(string)` | n/a | yes |
| inline\_policies\_json | Map of inline policy names to JSON policy documents | `map(string)` | `{}` | no |
| managed\_policies\_arns | Map of managed policies ARNs | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| instance\_profile\_arn | ARN of the EC2 instance profile |
| role\_arn | ARN of the IAM role |
| role\_name | Name of the IAM role |
<!-- END_TF_DOCS -->