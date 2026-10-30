# -----------------------------------------------------------------------------
# Step Functions - Per-workflow state machines (one per project)
# -----------------------------------------------------------------------------

locals {
  # Step Function name convention: app-<app_name_short>-<region_short>-<key>-orchestration-<env>[-<developer>]
  step_function_names = {
    for k, v in var.workflows :
    k => "${local.resource_prefix}-${k}-orchestration-${local.resource_suffix}"
  }
}

# -----------------------------------------------------------------------------
# Step Functions - IAM Roles (one per workflow)
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "policy_sfn_invoke_lambdas" {
  statement {
    actions = ["lambda:InvokeFunction"]
    effect  = "Allow"
    resources = [
      for k, v in module.define_lambdas : v.lambda_arn
    ]
  }
}

resource "aws_iam_policy" "policy_sfn_invoke_lambdas" {
  name        = "${local.iam_prefix}-sfn-invoke-lambdas-${local.iam_suffix}"
  description = "Allow Step Functions to invoke Lambda functions"
  policy      = data.aws_iam_policy_document.policy_sfn_invoke_lambdas.json
}

data "aws_iam_policy_document" "policy_sfn_logging" {
  for_each = var.workflows

  # Scoped actions — restricted to the Step Function log group
  statement {
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]
    effect = "Allow"
    resources = [
      aws_cloudwatch_log_group.sfn_logs[each.key].arn,
      "${aws_cloudwatch_log_group.sfn_logs[each.key].arn}:*"
    ]
  }

  # Global actions — required by Step Functions log delivery (cannot be scoped to a single resource).
  # These CloudWatch Logs API actions do not support resource-level permissions and require Resource: "*".
  # Step Functions manages log delivery internally and needs PutLogEvents at resource "*" as well.
  # See: https://docs.aws.amazon.com/step-functions/latest/dg/cw-logs.html
  statement {
    actions = [
      "logs:CreateLogDelivery",
      "logs:CreateLogStream",
      "logs:GetLogDelivery",
      "logs:UpdateLogDelivery",
      "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries",
      "logs:PutLogEvents",
      "logs:PutResourcePolicy",
      "logs:DescribeResourcePolicies",
      "logs:DescribeLogGroups"
    ]
    effect    = "Allow"
    resources = ["*"]
  }
}

resource "aws_iam_policy" "policy_sfn_logging" {
  for_each = var.workflows

  name        = "${local.iam_prefix}-sfn-${each.key}-logging-${local.iam_suffix}"
  description = "Allow Step Functions to deliver logs to CloudWatch (${each.key})"
  policy      = data.aws_iam_policy_document.policy_sfn_logging[each.key].json
}

data "aws_iam_policy_document" "policy_sfn_xray" {
  statement {
    actions = [
      "xray:PutTraceSegments",
      "xray:PutTelemetryRecords",
      "xray:GetSamplingRules",
      "xray:GetSamplingTargets"
    ]
    effect    = "Allow"
    resources = ["*"]
  }
}

resource "aws_iam_policy" "policy_sfn_xray" {
  name        = "${local.iam_prefix}-sfn-xray-${local.iam_suffix}"
  description = "Allow Step Functions to send traces to X-Ray"
  policy      = data.aws_iam_policy_document.policy_sfn_xray.json
}

data "aws_iam_policy_document" "policy_sfn_sns_publish" {
  statement {
    actions   = ["sns:Publish"]
    effect    = "Allow"
    resources = [aws_sns_topic.sfn_alerts.arn]
  }
}

resource "aws_iam_policy" "policy_sfn_sns_publish" {
  name        = "${local.iam_prefix}-sfn-sns-publish-${local.iam_suffix}"
  description = "Allow Step Functions to publish failure notifications to SNS"
  policy      = data.aws_iam_policy_document.policy_sfn_sns_publish.json
}

module "role_step_function" {
  source   = "grand_org.jfrog.io/terraform-innersource-local__aws-services/iam_role_service/aws"
  version  = var.jfrog_module_versions["iam_role_service"]
  for_each = var.workflows

  role_name   = "${local.iam_prefix}-sf-${each.key}-orchestration-${local.iam_suffix}"
  aws_service = "states"
  managed_policies_arns = {
    policy_1 = aws_iam_policy.policy_sfn_invoke_lambdas.arn
    policy_2 = aws_iam_policy.policy_sfn_logging[each.key].arn
    policy_3 = aws_iam_policy.policy_sfn_sns_publish.arn
    policy_4 = aws_iam_policy.policy_sfn_xray.arn
    policy_5 = aws_iam_policy.policy_kms_messaging.arn
  }
  tags = merge(local.standard_tags, {})
}

# -----------------------------------------------------------------------------
# Step Functions - State Machines (one per workflow)
# -----------------------------------------------------------------------------

# IAM eventual consistency: AWS may take a few seconds to propagate newly
# attached policies. This sleep ensures the logging policy is visible to the
# Step Functions service before the state machine is created or updated.
resource "time_sleep" "wait_for_sfn_iam" {
  for_each   = var.workflows
  depends_on = [module.role_step_function]

  create_duration = "15s"
}

resource "aws_sfn_state_machine" "workflow" {
  for_each = var.workflows

  name     = local.step_function_names[each.key]
  role_arn = module.role_step_function[each.key].role_arn

  # Explicit dependency: wait for IAM propagation (via time_sleep) before
  # creating/updating the state machine to avoid AccessDeniedException on the log destination.
  depends_on = [time_sleep.wait_for_sfn_iam]

  definition = templatefile("${path.module}/step_function_definition.json", {
    coupa_po_retrieval_lambda_arn         = module.define_lambdas["coupa_po_retrieval"].lambda_arn
    cedl_copy_po_files_lambda_arn         = module.define_lambdas["cedl_copy_po_files"].lambda_arn
    convert_po_file_lambda_arn            = module.define_lambdas["convert_po_file"].lambda_arn
    ocr_po_file_lambda_arn                = module.define_lambdas["ocr_po_file"].lambda_arn
    ocr_po_file_get_status_lambda_arn     = module.define_lambdas["ocr_po_file_get_status"].lambda_arn
    consolidate_po_data_lambda_arn        = module.define_lambdas["consolidate_po_data"].lambda_arn
    cedl_export_po_output_data_lambda_arn = module.define_lambdas["cedl_export_po_output_data"].lambda_arn
    sns_tech_alerts_topic_arn             = aws_sns_topic.sfn_alerts.arn
    aws_region                            = local.aws_region_name
    max_concurrency_orders                = var.sfn_max_concurrency_orders
    max_concurrency_files                 = var.sfn_max_concurrency_files
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn_logs[each.key].arn}:*"
    include_execution_data = true
    level                  = var.step_function_logging_level
  }

  tracing_configuration {
    enabled = true
  }

  tags = merge(local.standard_tags, {})
}

resource "aws_cloudwatch_log_group" "sfn_logs" {
  for_each = var.workflows

  name              = "/aws/vendedlogs/states/${local.step_function_names[each.key]}"
  retention_in_days = var.cloudwatch_log_retention_days

  tags = merge(local.standard_tags, {})
}
