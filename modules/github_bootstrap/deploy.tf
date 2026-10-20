# Data source to get the existing permissions boundary policy
# Trust policy document for GitHub OIDC
data "aws_iam_policy_document" "github_deploy_policy" {
  statement {
    effect = "Allow"

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    actions = ["sts:AssumeRoleWithWebIdentity"]

    condition {
      test     = "ForAllValues:StringEquals"
      variable = "token.actions.githubusercontent.com/example-org:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com/example-org:sub"
      values   = local.all_deploy_refs
    }
  }
}

# First role: deploy
resource "aws_iam_role" "deploy" {
  name                 = "App_Github_${var.app_name_short}_deploy"
  assume_role_policy   = data.aws_iam_policy_document.github_deploy_policy.json
  permissions_boundary = data.aws_iam_policy.permissions_boundary.arn

  tags = merge(var.tags, {
    Name    = "App_Github_${var.app_name_short}_deploy"
    Purpose = "GitHub ${var.app_name_short} Github Deploy Role"
  })
}

# Policy document for deploy access
data "aws_iam_policy_document" "deploy_policy" {
  statement {
    sid    = "IAMReadManagedRolePolicies"
    effect = "Allow"
    actions = [
          "iam:Get*",
          "iam:List*",
          "account:ListRegions"
    ]
    resources = ["arn:aws:iam::${local.aws_account_id}:*"]
  }

  statement {
    sid    = "ListSpecificBuckets"
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "Repository"
    effect = "Allow"
    actions = [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:CompleteLayerUpload",
        "ecr:GetDownloadUrlForLayer",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart"
      ]
      resources = ["arn:aws:ecr:${local.aws_region_name}:${local.aws_account_id}:repository/${local.lambda_prefix}"]
    }

  statement {
    sid    = "ReleaseParameterRights"
    effect = "Allow"
    actions = [
        "ssm:PutParameter",
        "ssm:GetParameter"
      ]
      resources = [
        "arn:aws:ssm:${local.aws_region_name}:${local.aws_account_id}:parameter/App_${var.app_name_short}/release/current",
        "arn:aws:ssm:${local.aws_region_name}:${local.aws_account_id}:parameter/App_${var.app_name_short}/release/previous"
      ]
    }

  statement {
    sid = "S3ObjectCreateReadDelete"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:DeleteObjectVersion",
      "s3:DeleteObjectTagging",
      "s3:GetObjectVersion",
      "s3:GetObjectAcl",
      "s3:GetObjectTagging",
      "s3:PutObjectTagging",
      "s3:PutObjectAcl"
    ]
    resources = [ "arn:aws:s3:::${local.lambda_prefix}-*/*" ]
  }

  statement {
    sid    = "ReadBucketContents"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
      "s3:GetBucketVersioning",
      "s3:GetBucketAcl",
      "s3:GetBucketPolicy",
      "s3:GetBucketTagging",
      "s3:GetBucketNotification",
      "s3:GetBucketLogging"
    ]
    resources = ["arn:aws:s3:::${local.lambda_prefix}-*"]
  }

  statement {
    sid    = "LambdaCodeDeploy"
    effect = "Allow"

    actions = [
      "lambda:UpdateFunctionCode",
      "lambda:GetFunction"
    ]
    resources = ["arn:aws:lambda:${local.aws_region_name}:${local.aws_account_id}:function:App_${var.app_name_short}*"]
  }
}

# Create the deploy policy : "App_Github_<short_app_name>_Access_For_Deploy"
resource "aws_iam_policy" "deploy_policy" {
  name        = local.deploy_policy_name
  description = "Policy to deploy code for deploy role"
  policy      = data.aws_iam_policy_document.deploy_policy.json

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(var.tags, {
    Name    = local.deploy_policy_name
    Purpose = "Deploy code Role"
  })
}

# Attach the deploy policy to the role
resource "aws_iam_role_policy_attachments_exclusive" "deploy_policies_attachment" {
  role_name       = aws_iam_role.deploy.name
  policy_arns     = [
    resource.aws_iam_policy.deploy_policy.arn
  ]
}
