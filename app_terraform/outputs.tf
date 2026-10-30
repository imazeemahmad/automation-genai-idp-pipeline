# -----------------------------------------------------------------------------
# Bedrock Prompts
# -----------------------------------------------------------------------------

output "bedrock_prompt_arns" {
  description = "Map of prompt names to their ARNs"
  value = {
    for k, v in aws_bedrockagent_prompt.prompt : k => v.arn
  }
}

output "bedrock_prompt_ids" {
  description = "Map of prompt names to their IDs"
  value = {
    for k, v in aws_bedrockagent_prompt.prompt : k => v.id
  }
}

output "bedrock_prompt_names" {
  description = "Map of prompt keys to their deployed names"
  value       = local.bedrock_prompt_names
}

# -----------------------------------------------------------------------------
# Lambda Functions
# -----------------------------------------------------------------------------

output "lambda_layer_arn" {
  description = "ARN of the Lambda dependencies layer"
  value       = aws_lambda_layer_version.dependencies.arn
}

output "lambda_layer_name" {
  description = "Name of the Lambda dependencies layer"
  value       = aws_lambda_layer_version.dependencies.layer_name
}

output "lambda_function_arns" {
  description = "Map of Lambda function names to their ARNs"
  value = {
    for k, v in module.define_lambdas : k => v.lambda_arn
  }
}

output "lambda_function_names" {
  description = "Map of Lambda function keys to their deployed names"
  value = {
    for k, v in module.define_lambdas : k => v.lambda_name
  }
}

# -----------------------------------------------------------------------------
# S3 Buckets
# -----------------------------------------------------------------------------

output "s3_bucket_project_name" {
  description = "Name of the project S3 bucket"
  value       = module.s3_bucket_project.bucket_name
}

output "s3_data_bucket_name" {
  description = "Name of the data S3 bucket"
  value       = module.s3_data_bucket.bucket_name
}

# -----------------------------------------------------------------------------
# DynamoDB
# -----------------------------------------------------------------------------

output "dynamodb_table_name" {
  description = "Name of the procurement DynamoDB table"
  value       = module.dynamodb_procurement.dynamodb_table_name
}

# -----------------------------------------------------------------------------
# Step Functions
# -----------------------------------------------------------------------------

output "step_function_arns" {
  description = "Map of workflow keys to their Step Function ARNs"
  value = {
    for k, v in aws_sfn_state_machine.workflow : k => v.arn
  }
}

output "step_function_names" {
  description = "Map of workflow keys to their Step Function names"
  value = {
    for k, v in aws_sfn_state_machine.workflow : k => v.name
  }
}

# -----------------------------------------------------------------------------
# ECR
# -----------------------------------------------------------------------------

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = module.ecr.ecr_repository_url
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = local.ecr_repository_name
}

output "ecr_libreoffice_converter_repository_url" {
  description = "URL of the LibreOffice converter ECR repository"
  value       = module.ecr_libreoffice_converter.ecr_repository_url
}

output "ecr_libreoffice_converter_repository_name" {
  description = "Name of the LibreOffice converter ECR repository"
  value       = local.ecr_libreoffice_converter_repository_name
}

# -----------------------------------------------------------------------------
# KMS
# -----------------------------------------------------------------------------

output "kms_data_key_arn" {
  description = "ARN of the KMS key for data encryption (S3 + DynamoDB)"
  value       = module.kms_data.kms_key_arn
}

output "kms_messaging_key_arn" {
  description = "ARN of the KMS key for messaging encryption (SNS + SQS)"
  value       = module.kms_messaging.kms_key_arn
}

output "kms_ssm_key_arn" {
  description = "ARN of the KMS key for SSM SecureString parameters"
  value       = module.kms_ssm.kms_key_arn
}

output "kms_ecr_key_arn" {
  description = "ARN of the KMS key for ECR image encryption"
  value       = module.kms_ecr.kms_key_arn
}

output "kms_key_aliases" {
  description = "Map of KMS key purposes to their aliases"
  value = {
    data      = local.kms_data_alias_name
    messaging = local.kms_messaging_alias_name
    ssm       = local.kms_ssm_alias_name
    ecr       = local.kms_ecr_alias_name
  }
}

output "s3_build_bucket_kms_key_arn" {
  description = "ARN of the dedicated KMS key for the S3 build bucket"
  value       = aws_kms_key.s3_build_bucket_key.arn
}



# -----------------------------------------------------------------------------
# EventBridge
# -----------------------------------------------------------------------------

output "eventbridge_rule_names" {
  description = "Map of schedule keys to their EventBridge rule names"
  value = {
    for k, v in aws_cloudwatch_event_rule.step_function_schedule : k => v.name
  }
}

output "eventbridge_dlq_names" {
  description = "Map of schedule keys to their SQS dead letter queue names"
  value = {
    for k, v in aws_sqs_queue.sfn_dlq : k => v.name
  }
}

# -----------------------------------------------------------------------------
# Observability
# -----------------------------------------------------------------------------

output "sns_alerts_topic_name" {
  description = "Name of the SNS topic for tech alerts"
  value       = aws_sns_topic.sfn_alerts.name
}

output "sns_business_alerts_topic_name" {
  description = "Name of the SNS topic for business alerts"
  value       = aws_sns_topic.business_alerts.name
}

output "cloudwatch_alarm_sfn_dlq_names" {
  description = "Map of schedule keys to their CloudWatch DLQ alarm names"
  value = {
    for k, v in aws_cloudwatch_metric_alarm.sfn_dlq_alarm : k => v.alarm_name
  }
}

output "cloudwatch_alarm_sfn_execution_failed_names" {
  description = "Map of workflow keys to their CloudWatch SFN execution failure alarm names"
  value = {
    for k, v in aws_cloudwatch_metric_alarm.sfn_execution_failed_alarm : k => v.alarm_name
  }
}

output "cloudwatch_log_group_sfn_names" {
  description = "Map of workflow keys to their CloudWatch log group names for Step Functions"
  value = {
    for k, v in aws_cloudwatch_log_group.sfn_logs : k => v.name
  }
}

# -----------------------------------------------------------------------------
# IAM Roles
# -----------------------------------------------------------------------------

output "iam_lambda_role_names" {
  description = "Map of Lambda function keys to their IAM role names"
  value = {
    for k, v in module.lambda_dedicated_role : k => v.role_name
  }
}

output "iam_step_function_role_names" {
  description = "Map of workflow keys to their Step Function IAM role names"
  value = {
    for k, v in module.role_step_function : k => v.role_name
  }
}

output "iam_eventbridge_role_names" {
  description = "Map of workflow keys to their EventBridge IAM role names"
  value = {
    for k, v in module.role_eventbridge_sfn : k => v.role_name
  }
}

# -----------------------------------------------------------------------------
# IAM Policies
# -----------------------------------------------------------------------------

output "iam_policy_names" {
  description = "Map of IAM policy logical names to their deployed names"
  value = {
    allow_put_events                   = aws_iam_policy.allow_put_events.name
    write_cloudwatch_logs              = aws_iam_policy.policy_write_cloudwatch_logs.name
    s3_read_write_access               = aws_iam_policy.policy_s3_read_write_access.name
    s3_data_read_write                 = aws_iam_policy.policy_s3_data_read_write.name
    dynamodb_read_write                = aws_iam_policy.policy_dynamodb_read_write.name
    ecr_pull                           = aws_iam_policy.policy_ecr_pull.name
    invoke_libreoffice_converter       = aws_iam_policy.policy_invoke_libreoffice_converter.name
    assume_coupa_role                  = aws_iam_policy.policy_assume_coupa_role.name
    ssm_read_write                     = aws_iam_policy.policy_ssm_read_write.name
    kms_data                           = aws_iam_policy.policy_kms_data.name
    kms_messaging                      = aws_iam_policy.policy_kms_messaging.name
    kms_ssm                            = aws_iam_policy.policy_kms_ssm.name
    kms_lambda_env                     = aws_iam_policy.policy_kms_lambda_env.name
    sfn_invoke_lambdas                 = aws_iam_policy.policy_sfn_invoke_lambdas.name
    sfn_xray                           = aws_iam_policy.policy_sfn_xray.name
    sfn_sns_publish                    = aws_iam_policy.policy_sfn_sns_publish.name
    cedl_coupa_attachments_access      = aws_iam_policy.cedl_coupa_attachments_access.name
    allow_assume_cedl_coupa_role       = aws_iam_policy.allow_assume_cedl_coupa_role.name
    snowflake_read_coupa_tables_access = aws_iam_policy.snowflake_read_coupa_tables_access.name
    allow_assume_snowflake_coupa_role  = aws_iam_policy.allow_assume_snowflake_coupa_role.name
  }
}

# -----------------------------------------------------------------------------
# External IAM Roles
# -----------------------------------------------------------------------------

output "iam_external_cedl_coupa_attachments_role_name" {
  description = "Name of the external CEDL Coupa attachments access IAM role"
  value       = aws_iam_role.cedl_coupa_attachments_access.name
}

output "iam_external_cedl_coupa_attachments_role_arn" {
  description = "ARN of the external CEDL Coupa attachments access IAM role"
  value       = aws_iam_role.cedl_coupa_attachments_access.arn
}

output "iam_external_snowflake_read_coupa_tables_role_name" {
  description = "Name of the external Snowflake read Coupa tables IAM role"
  value       = aws_iam_role.snowflake_read_coupa_tables_access.name
}

output "iam_external_snowflake_read_coupa_tables_role_arn" {
  description = "ARN of the external Snowflake read Coupa tables IAM role"
  value       = aws_iam_role.snowflake_read_coupa_tables_access.arn
}

# -----------------------------------------------------------------------------
# KMS (Lambda environment variables)
# -----------------------------------------------------------------------------

output "kms_lambda_env_key_arn" {
  description = "ARN of the KMS key for Lambda environment variable encryption"
  value       = aws_kms_key.lambda_env_key.arn
}

# -----------------------------------------------------------------------------
# SSM Parameters (HACAT)
# -----------------------------------------------------------------------------

output "ssm_hacat_parameter_names" {
  description = "Map of HACAT codes to their SSM parameter names"
  value = {
    for k, v in module.hacat_last_execution_parameter : k => v.parameter_name
  }
}

# -----------------------------------------------------------------------------
# CloudWatch Dashboard
# -----------------------------------------------------------------------------

output "cloudwatch_infra_dashboard_name" {
  description = "Name of the CloudWatch dashboard for infrastructure metrics"
  value       = aws_cloudwatch_dashboard.lambda_dashboard.dashboard_name
}

output "cloudwatch_app_metrics_dashboard_name" {
  description = "Name of the CloudWatch dashboard for application custom metrics"
  value       = aws_cloudwatch_dashboard.app_metrics_dashboard.dashboard_name
}
