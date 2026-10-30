# -----------------------------------------------------------------------------
# EventBridge - Scheduled rules to trigger Step Functions (one per workflow)
# -----------------------------------------------------------------------------

locals {
  # EventBridge naming convention: <resource_prefix>-<key>-event-sfn-<resource_suffix>
  eventbridge_rule_names = {
    for k, v in var.workflows :
    k => "${local.resource_prefix}-${k}-event-sfn-${local.resource_suffix}"
  }
  # DLQ naming convention: <resource_prefix>-<key>-event-dlq-<resource_suffix>
  eventbridge_dlq_names = {
    for k, v in var.workflows :
    k => "${local.resource_prefix}-${k}-event-dlq-${local.resource_suffix}"
  }
}

resource "aws_cloudwatch_event_rule" "step_function_schedule" {
  for_each = var.workflows

  name                = local.eventbridge_rule_names[each.key]
  description         = "Scheduled trigger for the ${each.key} Step Function"
  schedule_expression = each.value.schedule_expression
  state               = each.value.enabled ? "ENABLED" : "DISABLED"

  tags = merge(local.standard_tags, {})
}

resource "aws_cloudwatch_event_target" "step_function_target" {
  for_each = var.workflows

  rule     = aws_cloudwatch_event_rule.step_function_schedule[each.key].name
  arn      = aws_sfn_state_machine.workflow[each.key].arn
  role_arn = module.role_eventbridge_sfn[each.key].role_arn

  input = jsonencode({
    workflow_name = each.key
    hacat_list    = flatten([for codes in values(each.value.hacat_codes) : codes])
    po_numbers    = null
  })

  dead_letter_config {
    arn = aws_sqs_queue.sfn_dlq[each.key].arn
  }
}

# -----------------------------------------------------------------------------
# EventBridge - Dead Letter Queues (SQS) — one per schedule
# -----------------------------------------------------------------------------

resource "aws_sqs_queue" "sfn_dlq" {
  for_each = var.workflows

  name                      = local.eventbridge_dlq_names[each.key]
  message_retention_seconds = var.sfn_dlq_retention_days * 86400
  kms_master_key_id         = module.kms_messaging.kms_key_id

  tags = merge(local.standard_tags, {})
}

resource "aws_sqs_queue_policy" "sfn_dlq_policy" {
  for_each = var.workflows

  queue_url = aws_sqs_queue.sfn_dlq[each.key].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.sfn_dlq[each.key].arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_cloudwatch_event_rule.step_function_schedule[each.key].arn
          }
        }
      },
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "sqs:*"
        Resource  = aws_sqs_queue.sfn_dlq[each.key].arn
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# -----------------------------------------------------------------------------
# EventBridge - IAM Roles to start Step Function executions (one per workflow)
# -----------------------------------------------------------------------------

data "aws_iam_policy_document" "policy_eventbridge_start_sfn" {
  for_each = var.workflows

  statement {
    actions   = ["states:StartExecution"]
    effect    = "Allow"
    resources = [aws_sfn_state_machine.workflow[each.key].arn]
  }
}

resource "aws_iam_policy" "policy_eventbridge_start_sfn" {
  for_each = var.workflows

  name        = "${local.iam_prefix}-eventbridge-start-sfn-${each.key}-${local.iam_suffix}"
  description = "Allow EventBridge to start Step Function execution (${each.key})"
  policy      = data.aws_iam_policy_document.policy_eventbridge_start_sfn[each.key].json
}

module "role_eventbridge_sfn" {
  source   = "grand_org.jfrog.io/terraform-innersource-local__aws-services/iam_role_service/aws"
  version  = var.jfrog_module_versions["iam_role_service"]
  for_each = var.workflows

  role_name   = "${local.iam_prefix}-event-${each.key}-sfn-schedule-${local.iam_suffix}"
  aws_service = "events"
  managed_policies_arns = {
    policy_1 = aws_iam_policy.policy_eventbridge_start_sfn[each.key].arn
  }
  tags = merge(local.standard_tags, {})
}
