data "aws_caller_identity" "current" {}

resource "aws_kms_key" "kms" {
  description                        = "A symmetric encryption KMS key"
  enable_key_rotation                = true
  deletion_window_in_days            = var.deletion_window_in_days
  bypass_policy_lockout_safety_check = true
  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:kms_symmetric_key"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "1.2.0"
  })
  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "key-default-1"
    Statement = concat([
      {
        Sid    = "Allow administration of the key"
        Effect = "Allow"
        Principal = {
          AWS = var.iam_role_administrator
        },
        Action = [
          "kms:ReplicateKey",
          "kms:Create*",
          "kms:Put*",
          "kms:Update*",
          "kms:Revoke*",
          "kms:Disable*",
          "kms:Delete*",
          "kms:ScheduleKeyDeletion",
          "kms:CancelKeyDeletion",
          "kms:PutKeyPolicy",
          "kms:CreateAlias",
          "kms:DeleteAlias"
        ],
        Resource = "*"
      },
      {
        Sid    = "Allow general use of the key"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        },
        Action = [
          "kms:Describe*",
          "kms:Enable*",
          "kms:List*",
          "kms:Get*",
          "kms:CreateAlias",
          "kms:TagResource",
          "kms:UntagResource"
        ],
        Resource = "*"
      },
      {
        Sid    = "Allow encryption with the key"
        Effect = "Allow"
        Principal = {
          AWS = var.iam_role_encrypt
        },
        Action = [
          "kms:Encrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey",
          "kms:GenerateDataKeyWithoutPlaintext"
        ],
        Resource = "*"
      },
      {
        Sid    = "Allow decryption with the key"
        Effect = "Allow"
        Principal = {
          AWS = var.iam_role_decrypt
        },
        Action = [
          "kms:Decrypt"
        ],
        Resource = "*"
      }
      ],
      # Conditionally add AWS service principals (e.g., SNS, SQS) for cross-service encryption
      length(var.allowed_services) > 0 ? [
        {
          Sid    = "Allow AWS services to use the key"
          Effect = "Allow"
          Principal = {
            Service = [for svc in var.allowed_services : "${svc}.amazonaws.com"]
          }
          Action = [
            "kms:GenerateDataKey*",
            "kms:Decrypt"
          ]
          Resource = "*"
          Condition = {
            StringEquals = {
              "aws:SourceAccount" = data.aws_caller_identity.current.account_id
            }
          }
        }
      ] : []
    )
  })
}

resource "aws_kms_alias" "alias" {
  name          = "alias/${var.key_alias}"
  target_key_id = aws_kms_key.kms.id
}