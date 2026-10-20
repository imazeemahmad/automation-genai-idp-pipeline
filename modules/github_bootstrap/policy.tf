# Policy document for S3 read access
data "aws_iam_policy_document" "project_admin_policy" {
  statement {
    sid    = "DenyCreateWrongAppTag"
    effect = "Deny"
    actions   = [
      "bedrock:CreateAgent",
      "bedrock-agentcore:CreateAgentRuntime",
      "bedrock-agentcore:TagResource",
      "dynamodb:CreateTable",
      "dynamodb:CreateBackup",
      "ec2:RunInstances",
      "ec2:CreateVolume",
      "ec2:CreateSnapshot",
      "ec2:CreateImage",
      "elasticfilesystem:CreateFileSystem",
      "iam:CreateRole",
      "iam:CreateUser",
      "iam:CreatePolicy",
      "kms:TagResource",
      "lambda:CreateFunction",
      "rds:CreateDBInstance",
      "rds:CreateDBCluster",
      "rds:CreateDBSnapshot",
      "secretsmanager:CreateSecret",
      "sqs:CreateQueue",
      "sns:CreateTopic",
      "ssm:CreateDocument",
      "ssm:PutParameter",
      "states:CreateStateMachine"
    ]
    resources = ["*"]
    condition {
      test     = "StringNotEqualsIfExists"
      variable = "aws:RequestTag/app_name_short"
      values   = [var.app_name_short]
    }
  }

  statement {
    sid = "Tagging"
    effect = "Allow"
    actions = [
      "tag:GetResources",
      "tag:TagResources",
      "tag:UntagResources",
      "tag:GetTagKeys",
      "tag:GetTagValues"
    ]
    resources =["*"]
    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/app_name_short"
      values   = [var.app_name_short]
    }
  }

  statement {
    sid = "KmsAlias"
    effect = "Allow"
    actions = [
      "kms:CreateAlias",
      "kms:UpdateAlias",
      "kms:DeleteAlias"
    ]
    resources =[
      "arn:aws:kms:${local.aws_region_name}:${local.aws_account_id}:key/*",
      "arn:aws:kms:${local.aws_region_name}:${local.aws_account_id}:alias/App_${var.app_name_short}_*"
    ]
  }

  statement {
    sid    = "AllowRestrictRegion"
    effect = "Allow"
    actions = [
      "kms:CreateKey",
      "kms:ListAliases"
    ]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = [local.aws_region_name]
    }
  }

  statement {
    sid = "KmsKeyLifecycle"
    effect = "Allow"
    actions = [
        # --- Read / List (Terraform needs these)
        "kms:GetKeyPolicy",
        "kms:ListResourceTags",
        # --- Setting key
        "kms:GetKeyRotationStatus",
        "kms:UntagResource",
        "kms:TagResource",
        "kms:EnableKeyRotation"
    ]
    resources =[
      "arn:aws:kms:${local.aws_region_name}:${local.aws_account_id}:key/*"
    ]
  }

  statement {
    sid = "AllowKmsAccessByAppTag"
    effect = "Allow"
    actions = [
      # --- Cryptographic usage
      "kms:Encrypt",
      "kms:Decrypt",
      "kms:ReEncrypt*",
      "kms:GenerateDataKey*",
      # --- Grants & aliases (on existing keys)
      "kms:CreateGrant",
      "kms:ListGrants",
      "kms:RevokeGrant",
      "kms:RetireGrant",
      # --- Key management on existing keys
      "kms:EnableKey",
      "kms:DisableKey",
      "kms:ScheduleKeyDeletion",
      "kms:CancelKeyDeletion",
      "kms:UpdateKeyDescription",
      "kms:PutKeyPolicy"
    ]
    resources =["arn:aws:kms:${local.aws_region_name}:${local.aws_account_id}:key/*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ResourceTag/app_name_short"
      values   = [var.app_name_short]
    }
  }

  statement {
    sid = "CreateAppRolesWithBoundary"
    effect = "Allow"
    actions = [
      "iam:CreateRole",
      "iam:CreateUser"
    ]
    resources = ["arn:aws:iam::${local.aws_account_id}:role/App_${var.app_name_short}_*"]
    condition {
      test     = "StringLike"
      variable = "iam:PermissionsBoundary"
      values   = ["arn:aws:iam::${local.aws_account_id}:policy/CE_AppAdminBoundary"]
    }
  }

  statement {
    sid    = "AllowAttachDefinedPolicyToRole"
    effect = "Allow"
    actions = [
      "iam:AttachRolePolicy"
    ]
    resources = ["arn:aws:iam::${local.aws_account_id}:role/App_${var.app_name_short}_*"    ]
    condition {
      test     = "StringLike"
      variable = "iam:PolicyARN"
      values   = [
        "arn:aws:iam::${local.aws_account_id}:policy/App_${var.app_name_short}_*",
        "arn:aws:iam::${local.aws_account_id}:policy/ce-ExampleSSM-PolicyforEC2"
      ]
    }
  }

  statement {
    sid = "AllowSetupPolicyWithPrefix"
    effect = "Allow"
    actions = [
      "iam:PutRolePolicy",
      "iam:PassRole",
      "iam:TagRole",
      "iam:CreatePolicy",
      "iam:CreatePolicyVersion",
      "iam:DeleteInstanceProfile",
      "iam:DeletePolicyVersion",
      "iam:DetachRolePolicy",
      "iam:PassRole",
      "iam:DeleteRole",
      "iam:DeleteRolePolicy",
      "iam:DeletePolicy",
      "iam:UpdateRole*",
      "iam:TagPolicy",
      "iam:UntagPolicy",
      "iam:UpdateAssumeRolePolicy",
      "iam:SetDefaultPolicyVersion"
    ]
    resources = [ "arn:aws:iam::${local.aws_account_id}:role/App_${var.app_name_short}_*",
      "arn:aws:iam::${local.aws_account_id}:policy/App_${var.app_name_short}_*"
    ]
  }

  statement {
    sid = "ssmRolePolicy"
    effect = "Allow"
    actions = [
      "ssm:PutParameter",          # create / update
      "ssm:GetParameter",          # read single
      "ssm:GetParameters",         # read multiple
      "ssm:GetParametersByPath",   # read by hierarchy
      "ssm:AddTagsToResource",     # add tags
      "ssm:ListTagsForResource",
      "ssm:DeleteParameter",       # delete single
      "ssm:DeleteParameters"       # delete multiple
    ]
    resources = ["arn:aws:ssm:${local.aws_region_name}:${local.aws_account_id}:parameter/App_${var.app_name_short}/*"]
  }

  statement {
    sid    = "ManageRepository"
    effect = "Allow"
    actions = [
        "ecr:BatchGetImage",
        "ecr:CompleteLayerUpload",
        "ecr:CreateRepository",
        "ecr:DeleteRepository",
        "ecr:DeleteLifecyclePolicy",
        "ecr:DeleteRepositoryPolicy",
        "ecr:GetDownloadUrlForLayer",
        "ecr:GetAuthorizationToken",
        "ecr:GetLifecyclePolicy",
        "ecr:GetRepositoryPolicy",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:PutImageScanningConfiguration",
        "ecr:PutImageTagMutability",
        "ecr:PutLifecyclePolicy",
        "ecr:SetRepositoryPolicy",
        "ecr:TagResource",
        "ecr:UntagResource",
        "ecr:ListTagsForResource",              
        "ecr:UploadLayerPart"
     ]    
    resources = ["arn:aws:ecr:${local.aws_region_name}:${local.aws_account_id}:repository/${local.lambda_prefix}"]
  }

  statement {
    sid = "S3Bucket"
    effect = "Allow"
    actions = [
      "s3:CreateBucket",
      "s3:Get*",
      "s3:Put*",
      "s3:DeleteBucket*",
      "s3:List*"
    ]
    resources = [ "arn:aws:s3:::${local.lambda_prefix}-*" ]
  }

  statement {
    sid = "S3ObjectCreateReadDelete"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:DeleteObjectVersion",
      "s3:DeleteObjectTagging",
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:GetObjectAcl",
      "s3:GetObjectTagging",
      "s3:PutObjectTagging",
      "s3:PutObjectAcl"
    ]
    resources = [ "arn:aws:s3:::${local.lambda_prefix}-*/*" ]
  }

  statement {
    sid = "S3AccessPoint"
    effect = "Allow"
    actions = [
      "s3:CreateAccessPoint",
      "s3:DeleteAccessPoint",
      "s3:DeleteAccessPointPolicy",
      "s3:ListAccessPoints",
      "s3:GetAccessPoint",
      "s3:GetAccessPointPolicy",
      "s3:GetAccessPointPublicAccessBlock",
      "s3:PutAccessPointPolicy",
      "s3:PutAccessPointPublicAccessBlock"
    ]
    resources = [ "arn:aws:s3:${local.aws_region_name}:${local.aws_account_id}:accesspoint/App_${var.app_name_short}_*" ]
    condition {
      test     = "StringEquals"
      variable = "s3:ResourceTag/app_name_short"
      values   = [var.app_name_short]
    }
  }

}


data "aws_iam_policy_document" "project_policy" {

  statement {
    sid    = "BedrockAgentRestrictedAccess"
    effect = "Allow"
    actions = [
      # Agent
      "bedrock:CreateAgent",
      "bedrock:UpdateAgent",
      "bedrock:DeleteAgent",
      "bedrock:GetAgent",
      "bedrock:ListAgents",
      # Alias
      "bedrock:CreateAgentAlias",
      "bedrock:UpdateAgentAlias",
      "bedrock:DeleteAgentAlias",
      "bedrock:GetAgentAlias",
      "bedrock:ListAgentAliases",
      # Version
      "bedrock:CreateAgentVersion",
      "bedrock:GetAgentVersion",
      "bedrock:ListAgentVersions",
      # BedrockRuntime
      "bedrock:InvokeModel",
      "bedrock:InvokeAgent",
      "bedrock:Retrieve",
      "bedrock:RetrieveAndGenerate"
    ]

    resources = [
      "arn:aws:bedrock:${local.aws_region_name}:${local.aws_account_id}:agent/*",
      "arn:aws:bedrock:${local.aws_region_name}:${local.aws_account_id}:agent-alias/App_${var.app_name_short}*"
    ]
  }

  statement {
    sid    = "BedrockAgentCoreRuntime"
    effect = "Allow"
    actions = [
      "bedrock-agentcore:CreateAgentRuntime",
      "bedrock-agentcore:UpdateAgentRuntime",
      "bedrock-agentcore:DeleteAgentRuntime",
      "bedrock-agentcore:GetAgentRuntime",
      "bedrock-agentcore:ListAgentRuntimes",
      "bedrock-agentcore:CreateAgentRuntimeEndpoint",
      "bedrock-agentcore:UpdateAgentRuntimeEndpoint",
      "bedrock-agentcore:GetAgentRuntimeEndpoint",
      "bedrock-agentcore:DeleteAgentRuntimeEndpoint",
      "bedrock-agentcore:ListAgentRuntimesEndpoints",
      "bedrock-agentcore:TagResource",
      "bedrock-agentcore:UntagResource",
      "bedrock-agentcore:ListTagsForResource",
      "bedrock-agentcore:CreateWorkloadIdentity",
      "bedrock-agentcore:UpdateWorkloadIdentity",
      "bedrock-agentcore:DeleteWorkloadIdentity",
      "bedrock-agentcore:UntagResource",
      "bedrock-agentcore:ListTagsForResource"
    ]
    resources = [
      "arn:aws:bedrock-agentcore:${local.aws_region_name}:${local.aws_account_id}:runtime/*",
      "arn:aws:bedrock-agentcore:${local.aws_region_name}:${local.aws_account_id}:workload-identity-directory/*",
    ]
  }

  statement {
    sid = "LambdaRights"
    effect = "Allow"
    actions = [
      "lambda:CreateFunction",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
      "lambda:DeleteFunction",
      "lambda:GetFunctionEventInvokeConfig",
      "lambda:PutFunctionEventInvokeConfig",
      "lambda:DeleteFunctionEventInvokeConfig",
      "lambda:GetPolicy",
      "lambda:GetFunction",
      "lambda:GetFunctionConfiguration",
      "lambda:GetFunctionCodeSigningConfig",
      "lambda:PublishVersion",
      "lambda:ListVersionsByFunction",
      "lambda:ListFunctions",
      "lambda:AddPermission",
      "lambda:RemovePermission",
      "lambda:TagResource",
      "lambda:UntagResource",
      "lambda:ListTags"
    ]
    resources = ["arn:aws:lambda:${local.aws_region_name}:${local.aws_account_id}:function:App_${var.app_name_short}*"]
  }

  statement {
    sid    = "AllowDescribe"
    effect = "Allow"
    actions = [
      "ecr:DescribeRepositories",
      "kms:DescribeKey",
      "logs:DescribeLogGroups",
      "logs:DescribeLogStreams",
      "ssm:DescribeParameters"     # list / metadata
    ]
    resources = ["*"]
  }

  statement {
    sid = "LogsStreams"
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:PutRetentionPolicy",
      "logs:DeleteLogStream",
      "logs:ListTagsForResource",
      "logs:TagResource"
    ]
    resources = [
      "arn:aws:logs:${local.aws_region_name}:${local.aws_account_id}:log-group:/aws/lambda/App_${var.app_name_short}*",
      "arn:aws:logs:${local.aws_region_name}:${local.aws_account_id}:log-group:/aws/bedrock-agentcore/runtimes/App_${var.app_name_short}*",
      "arn:aws:logs:${local.aws_region_name}:${local.aws_account_id}:log-group:/aws/ec2/App_${var.app_name_short}*",
      "arn:aws:logs:${local.aws_region_name}:${local.aws_account_id}:log-group:/aws/apigateway/App_${var.app_name_short}*"
    ]
  }

}