# -----------------------------------------------------------------------------
# SNS Topic - Notification target for alarms
# -----------------------------------------------------------------------------

locals {
  sns_alerts_topic_name          = "${local.resource_prefix}-common-tech-alerts-${local.resource_suffix}"
  sns_business_alerts_topic_name = "${local.resource_prefix}-common-business-alerts-${local.resource_suffix}"
  alarm_sfn_dlq_names = {
    for k, v in var.workflows :
    k => "${local.resource_prefix}-${k}-event-dlq-messages-${local.resource_suffix}"
  }
  alarm_sfn_execution_failed_names = {
    for k, v in var.workflows :
    k => "${local.resource_prefix}-${k}-sfn-execution-failed-${local.resource_suffix}"
  }
}

resource "aws_sns_topic" "sfn_alerts" {
  name              = local.sns_alerts_topic_name
  display_name      = "[${var.CE_Environment}] IDP Tech Alerts"
  kms_master_key_id = module.kms_messaging.kms_key_id

  tags = merge(local.standard_tags, {})
}

data "aws_iam_policy_document" "sns_alerts_policy" {
  statement {
    sid    = "AllowCloudWatchAlarmsPublish"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.sfn_alerts.arn]
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.aws_account_id]
    }
  }
}

resource "aws_sns_topic_policy" "sfn_alerts" {
  arn    = aws_sns_topic.sfn_alerts.arn
  policy = data.aws_iam_policy_document.sns_alerts_policy.json
}

resource "aws_sns_topic_subscription" "sfn_alerts_email" {
  for_each = toset(var.contacts_alerting)

  topic_arn = aws_sns_topic.sfn_alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

# -----------------------------------------------------------------------------
# SNS Topic - Business alerts
# -----------------------------------------------------------------------------

resource "aws_sns_topic" "business_alerts" {
  name              = local.sns_business_alerts_topic_name
  display_name      = "[${var.CE_Environment}] IDP Business Alerts"
  kms_master_key_id = module.kms_messaging.kms_key_id

  tags = merge(local.standard_tags, {})
}

data "aws_iam_policy_document" "sns_business_alerts_policy" {
  statement {
    sid    = "AllowCloudWatchAlarmsPublish"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.business_alerts.arn]
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.aws_account_id]
    }
  }
}

resource "aws_sns_topic_policy" "business_alerts" {
  arn    = aws_sns_topic.business_alerts.arn
  policy = data.aws_iam_policy_document.sns_business_alerts_policy.json
}

resource "aws_sns_topic_subscription" "business_alerts_email" {
  for_each = toset(var.contacts_business_alerting)

  topic_arn = aws_sns_topic.business_alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

# -----------------------------------------------------------------------------
# CloudWatch Alarm - DLQ messages (EventBridge failed to start Step Function)
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "sfn_dlq_alarm" {
  for_each = var.workflows

  alarm_name          = local.alarm_sfn_dlq_names[each.key]
  alarm_description   = "Alert when EventBridge fails to start the Step Function (messages landed in DLQ) [${each.key}]"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.sfn_dlq[each.key].name
  }

  alarm_actions = [aws_sns_topic.sfn_alerts.arn]

  tags = merge(local.standard_tags, {})
}

# -----------------------------------------------------------------------------
# CloudWatch Alarm - Step Function execution failures (one per workflow)
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "sfn_execution_failed_alarm" {
  for_each = var.workflows

  alarm_name          = local.alarm_sfn_execution_failed_names[each.key]
  alarm_description   = "Alert when the ${each.key} Step Function execution fails"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.workflow[each.key].arn
  }

  alarm_actions = [aws_sns_topic.sfn_alerts.arn]

  tags = merge(local.standard_tags, {})
}
