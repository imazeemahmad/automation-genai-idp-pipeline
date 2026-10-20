# Trust policy document for GitHub OIDC
data "aws_iam_policy_document" "github_trust_policy" {
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
      values   = local.all_trusted_refs
    }
  }
}

# First role: Bootstrap
resource "aws_iam_role" "bootstrap" {
  name                 = "App_Github_${var.app_name_short}"
  assume_role_policy   = data.aws_iam_policy_document.github_trust_policy.json
  permissions_boundary = data.aws_iam_policy.permissions_boundary.arn

  tags = merge(var.tags, {
    Name    = "App_Github_${var.app_name_short}"
    Purpose = "GitHub ${var.app_name_short} Bootstrap Role"
  })
}

# Policy document for read access
data "aws_iam_policy_document" "read_policy" {
  statement {
    sid    = "IAMReadManagedRolePolicies"
    effect = "Allow"
    actions = [
          "iam:Get*",
          "iam:List*",
          "iam:Generate*",
          "account:ListRegions"
    ]
    resources = ["arn:aws:iam::${local.aws_account_id}:*"]
  }

  // --- VPC READ ONLY ---
  statement {
    sid    = "VpcReadAccess"
    effect = "Allow"
    actions = [
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeRouteTables",
          "ec2:DescribeNetworkInterfaces"
    ]
    resources = ["*"]
  }

  statement {
    sid    = "ListSpecificBuckets"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]
    resources = ["arn:aws:s3:::tfstate-*"]
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
    resources = ["arn:aws:s3:::tfstate-*"]
  }

  statement {
    sid    = "ReadWriteObjects"
    effect = "Allow"

    actions = [
      "s3:putObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:GetObjectVersion",
      "s3:GetObjectAcl",
      "s3:GetObjectTagging"
    ]

    resources = ["arn:aws:s3:::tfstate-*/*"]
  }
}

# Create the read policy : "App_Github_<short_app_name>_Read_Access_For_Bootstrap"
resource "aws_iam_policy" "read_policy" {
  name        = local.read_policy_name
  description = "Policy for read access created by bootstrap role"
  policy      = data.aws_iam_policy_document.read_policy.json

  tags = merge(var.tags, {
    Name    = local.read_policy_name
    Purpose = "Read Access for Bootstrap Role"
  })
}

# Create the project global policy (restricts, iam, ecr, ssm, s3, pks)
resource "aws_iam_policy" "project_admin_policy" {
  name        = local.policy_admin_name
  description = "Policy for project ${var.app_name_short}"
  policy      = data.aws_iam_policy_document.project_admin_policy.json

  tags = merge(var.tags, {
    Name    = local.policy_name
    Purpose = "Admin Project policy for Bootstrap Role"
  })
}

# Create the project policy objects (lambda, bedrock ...) 
resource "aws_iam_policy" "project_policy" {
  name        = local.policy_name
  description = "Policy for project ${var.app_name_short}"
  policy      = data.aws_iam_policy_document.project_policy.json

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(var.tags, {
    Name    = local.policy_name
    Purpose = "Project policy for Bootstrap Role"
  })
}

# Attach the policies to the project role
resource "aws_iam_role_policy_attachments_exclusive" "policies_attachment" {
  role_name       = aws_iam_role.bootstrap.name
  policy_arns = [ 
      aws_iam_policy.read_policy.arn,
      aws_iam_policy.project_admin_policy.arn,
      aws_iam_policy.project_policy.arn
  ]
}


