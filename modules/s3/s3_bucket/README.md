# s3_bucket

This module deploys an S3 Bucket compliant with organisation standards. For bucket encryption, cutomer KMS can be used. By default AES256 is enabled. Bucket key is enabled by default. Can be disabled if required. Please see the documentation for the cost benefits of using S3 bucket key.
https://docs.aws.amazon.com/AmazonS3/latest/userguide/configuring-bucket-key.html


## Usage

```tf
module "my_bucket" {
  source  = "registry.example.com/terraform-modules__aws-services/s3_bucket/aws"
  version = "2026.4.3-weekly"

  bucket_name       = "mybucket"
  bucket_policy     = data.aws_iam_policy_document.my_bucket_policy.json
  kms_key_id        = "arn:aws:kms:eu-west-1:123456789:key/abcdedfgh-123456789" # Provide value if KMS is preffered for SSE

  tags = {
    CE_Application_ID   = "APM1234567"
    CE_Application_Name = "Prod Application"
    CE_Environment      = "PROD"
    CE_DataSensitivity  = "Internal"  # Public | Internal | Sensitive | HighlySensitive
    MyOtherTag          = "Value"
  }
}
```

> **Tags:** Use the [`tags_mandatory_tags`](../../tags/tags_mandatory_tags) or [`tags_accelerator_tags`](../../tags/tags_accelerator_tags) module as the source of truth for tag validation and convenient outputs. See the [Tagging Policy](https://example.atlassian.net/wiki/) for valid values.

## Usage with Notifications

S3 bucket notifications can be configured to trigger Lambda functions, SQS queues, or SNS topics on object events.

```tf
module "my_bucket" {
  source  = "registry.example.com/terraform-modules__aws-services/s3_bucket/aws"
  version = "2026.4.3-weekly"

  bucket_name = "mybucket"

  # Optional: S3 event notifications
  notifications = {
    lambda_functions = [
      {
        lambda_function_arn = "arn:aws:lambda:eu-west-1:123456789:function:my-processor"
        events              = ["s3:ObjectCreated:*"]
        filter_prefix       = "input/"
        filter_suffix       = ".csv"
      }
    ]
    sqs_queues = [
      {
        queue_arn     = "arn:aws:sqs:eu-west-1:123456789:my-queue"
        events        = ["s3:ObjectRemoved:*"]
        filter_prefix = "archive/"
      }
    ]
    sns_topics = [
      {
        topic_arn     = "arn:aws:sns:eu-west-1:123456789:my-topic"
        events        = ["s3:ObjectCreated:Put"]
        filter_prefix = "uploads/"
      }
    ]
  }

  tags = {
    CE_Application_ID   = "APM1234567"
    CE_Application_Name = "Prod Application"
    CE_Environment      = "PROD"
    CE_DataSensitivity  = "Sensitive"  # Public | Internal | Sensitive | HighlySensitive
  }
}
```

**Note**: When using Lambda notifications, ensure the Lambda function has the appropriate resource-based policy allowing S3 to invoke it. This can be configured via the `lambda_permissions` variable in the `lambda_function` module.

## Usage with Custom Lifecycle Rules

Custom lifecycle rules (expiration, transition) can be added alongside the built-in rules (multipart upload cleanup, noncurrent version expiration).

```tf
module "my_bucket" {
  source  = "registry.example.com/terraform-modules__aws-services/s3_bucket/aws"
  version = "2026.4.3-weekly"

  bucket_name = "mybucket"

  lifecycle_rules = [
    {
      id         = "Expire temp objects after 30 days"
      filter     = { prefix = "temp/" }
      expiration = { days = 30 }
    },
    {
      id         = "Archive to Glacier after 90 days"
      transition = [{ days = 90, storage_class = "GLACIER" }]
    }
  ]

  tags = {
    CE_Application_ID   = "APM1234567"
    CE_Environment      = "PROD"
    CE_Application_Name = "Prod Application"
    CE_DataSensitivity  = "Internal"
  }
}
```

**Note**: Each rule must define at least one action (`expiration` or `transition`). All custom rules are automatically enabled. The module always includes built-in rules for multipart upload cleanup (7 days) and noncurrent version expiration (60 days, when versioning is enabled).

<!-- BEGIN_TF_DOCS -->
## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| bucket\_name | Name of the S3 bucket (globally unique) | `string` | n/a | yes |
| tags | A map of tags to assign to the resource. Must include CE\_Application\_ID, CE\_Application\_Name, CE\_Environment, and CE\_DataSensitivity. | `map(string)` | n/a | yes |
| bucket\_policy | Bucket policy in JSON format | `string` | `null` | no |
| enable\_bucket\_key | Enable bucket key for server-side encryption | `bool` | `true` | no |
| kms\_key\_id | KMS Key ID for S3 bucket encryption | `string` | `null` | no |
| lifecycle\_rules | Additional lifecycle rules for the S3 bucket (expiration, transition). All rules are enabled. | <pre>list(object({<br>    id = string<br>    filter = optional(object({<br>      prefix                   = optional(string)<br>      object_size_greater_than = optional(number)<br>      object_size_less_than    = optional(number)<br>      tags                     = optional(map(string))<br>    }))<br>    expiration = optional(object({<br>      days                         = optional(number)<br>      date                         = optional(string)<br>      expired_object_delete_marker = optional(bool)<br>    }))<br>    transition = optional(list(object({<br>      days          = optional(number)<br>      date          = optional(string)<br>      storage_class = string<br>    })))<br>  }))</pre> | `[]` | no |
| notifications | S3 bucket notification configurations for Lambda, SQS, and SNS targets | <pre>object({<br>    lambda_functions = optional(list(object({<br>      lambda_function_arn = string<br>      events              = list(string)<br>      filter_prefix       = optional(string, null)<br>      filter_suffix       = optional(string, null)<br>    })), [])<br>    sqs_queues = optional(list(object({<br>      queue_arn     = string<br>      events        = list(string)<br>      filter_prefix = optional(string, null)<br>      filter_suffix = optional(string, null)<br>    })), [])<br>    sns_topics = optional(list(object({<br>      topic_arn     = string<br>      events        = list(string)<br>      filter_prefix = optional(string, null)<br>      filter_suffix = optional(string, null)<br>    })), [])<br>  })</pre> | `null` | no |
| versionning | Whether to enable bucket versionning | `bool` | `true` | no |

## Outputs

| Name | Description |
|------|-------------|
| bucket\_arn | Bucket ARN |
| bucket\_domain\_name | Domain name of the bucket |
| bucket\_name | Bucket name |
| bucket\_regional\_domain\_name | Regional domain name of the bucket |
| hosted\_zone\_id | Hosted zone ID (for Route53 alias records) |
<!-- END_TF_DOCS -->
