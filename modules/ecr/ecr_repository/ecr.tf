data "aws_caller_identity" "current" {}

resource "aws_ecr_repository" "ecr" {
  name                 = var.ecr_repository_name
  image_tag_mutability = var.image_tag_mutability
  tags = merge(var.tags, {
    Terraform_Module_Name    = "shared-modules:aws:ecr_repository"
    Terraform_Module_Repo    = "https://github.com/example-org/terraform-aws-library"
    Terraform_Module_Version = "1.2.0"
  })

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = var.kms_key_arn != null ? "KMS" : "AES256"
    kms_key         = var.kms_key_arn != null ? var.kms_key_arn : null
  }
}

resource "aws_ecr_lifecycle_policy" "ecr_lifecycle_policy" {
  repository = aws_ecr_repository.ecr.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Expire old images when the total count is more than defined value"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = var.image_count
      }
      action = {
        type = "expire"
      }
    }]
  })
}

data "aws_iam_policy_document" "ecr_policy" {
  # Base statement: Allow account root read-only access
  statement {
    sid    = "AllowReadOnlyRoot"
    effect = "Allow"

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }

    actions = [
      "ecr:BatchGetImage",
      "ecr:BatchCheckLayerAvailability",
      "ecr:GetDownloadUrlForLayer"
    ]
  }

  # Additional role statement (if provided)
  dynamic "statement" {
    for_each = var.additional_role_arn != null ? [var.additional_role_arn] : []

    content {
      sid    = "AllowAdminRole"
      effect = "Allow"

      principals {
        type        = "AWS"
        identifiers = [statement.value]
      }

      actions = [
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability",
        "ecr:CompleteLayerUpload",
        "ecr:GetDownloadUrlForLayer",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart"
      ]
    }
  }

  # Service access statements (for Lambda, ECS, CodeBuild, etc.)
  dynamic "statement" {
    for_each = { for idx, access in var.service_access : idx => access }

    content {
      sid    = "ServiceAccess${statement.key}"
      effect = "Allow"

      principals {
        type        = "Service"
        identifiers = [statement.value.service]
      }

      actions = [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ]

      condition {
        test     = "StringLike"
        variable = "aws:sourceArn"
        values   = [statement.value.source_arn_pattern]
      }
    }
  }
}

resource "aws_ecr_repository_policy" "ecr_policy" {
  repository = aws_ecr_repository.ecr.name
  policy     = data.aws_iam_policy_document.ecr_policy.json
}
