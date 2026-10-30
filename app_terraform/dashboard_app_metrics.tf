# -----------------------------------------------------------------------------
# CloudWatch Dashboard - Application Custom Metrics (Powertools)
# -----------------------------------------------------------------------------

locals {
  app_dashboard_name = "${local.resource_prefix}-common-app-metrics-${local.resource_suffix}"

  # Sorted workflow keys for consistent dashboard ordering
  _workflow_keys = keys(var.workflows)

  app_dashboard_body = jsonencode({
    widgets = concat(
      # ─── Workflow Overview (y=0) ─────────────────────────────────────────
      [
        {
          type   = "text"
          x      = 0
          y      = 0
          width  = 24
          height = 2
          properties = {
            markdown = "## Workflow Overview\nStep Function executions — started, succeeded, failed and duration (all projects)"
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 2
          width  = 6
          height = 6
          properties = {
            title   = "Executions Started"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [
              for key in local._workflow_keys :
              ["AWS/States", "ExecutionsStarted", "StateMachineArn", aws_sfn_state_machine.workflow[key].arn]
            ]
          }
        },
        {
          type   = "metric"
          x      = 6
          y      = 2
          width  = 6
          height = 6
          properties = {
            title   = "Executions Succeeded"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [
              for key in local._workflow_keys :
              ["AWS/States", "ExecutionsSucceeded", "StateMachineArn", aws_sfn_state_machine.workflow[key].arn]
            ]
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 2
          width  = 6
          height = 6
          properties = {
            title   = "Executions Failed"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [
              for key in local._workflow_keys :
              ["AWS/States", "ExecutionsFailed", "StateMachineArn", aws_sfn_state_machine.workflow[key].arn]
            ]
          }
        },
        {
          type   = "metric"
          x      = 18
          y      = 2
          width  = 6
          height = 6
          properties = {
            title   = "Execution Time"
            region  = local.aws_region_name
            period  = 300
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
            metrics = [
              for pair in flatten([
                for key in local._workflow_keys : [
                  { arn = aws_sfn_state_machine.workflow[key].arn, s = "Average" },
                  { arn = aws_sfn_state_machine.workflow[key].arn, s = "Maximum" }
                ]
              ]) :
              ["AWS/States", "ExecutionTime", "StateMachineArn", pair.arn, { stat = pair.s }]
            ]
          }
        }
      ],
      # ─── Step 1: Purchase Order Retrieval (y=8) ──────────────────────────
      [
        {
          type   = "text"
          x      = 0
          y      = 8
          width  = 24
          height = 2
          properties = {
            markdown = "## 1 — Purchase Order Retrieval\nRetrieves PO metadata from Coupa/Snowflake and filters files by allowed extensions"
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 10
          width  = 12
          height = 6
          properties = {
            title   = "Purchase Orders Retrieved"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [[local.metrics_namespace, "PurchaseOrdersRetrieved", "service", "coupa_po_retrieval"]]
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 10
          width  = 12
          height = 6
          properties = {
            title   = "Files Filtered (Unsupported Extension)"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [[local.metrics_namespace, "FilesFilteredByExtension", "service", "coupa_po_retrieval"]]
          }
        }
      ],
      # ─── Step 2: File Download — CEDL Copy (y=16) ───────────────────────
      [
        {
          type   = "text"
          x      = 0
          y      = 16
          width  = 24
          height = 2
          properties = {
            markdown = "## 2 — File Download (CEDL Copy)\nCopies PO attachment files from CEDL S3 bucket to data bucket"
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 18
          width  = 24
          height = 6
          properties = {
            title   = "Files Downloaded"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [[local.metrics_namespace, "FilesDownloaded", "service", "cedl_copy_po_files"]]
          }
        }
      ],
      # ─── Step 3: OCR — File Processing (y=24) ───────────────────────────
      [
        {
          type   = "text"
          x      = 0
          y      = 24
          width  = 24
          height = 2
          properties = {
            markdown = "## 3 — OCR (File Processing)\nBedrock Data Automation — files succeeded vs failed during OCR"
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 26
          width  = 12
          height = 6
          properties = {
            title   = "File Processing Succeeded"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [[local.metrics_namespace, "FileProcessingSucceeded", "service", "ocr_po_file_get_status"]]
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 26
          width  = 12
          height = 6
          properties = {
            title   = "File Processing Failed"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [
              [local.metrics_namespace, "FileProcessingFailed", "service", "ocr_po_file"],
              [local.metrics_namespace, "FileProcessingFailed", "service", "ocr_po_file_get_status"]
            ]
          }
        }
      ],
      # ─── Step 4: LLM Consolidation (y=32) ───────────────────────────────
      [
        {
          type   = "text"
          x      = 0
          y      = 32
          width  = 24
          height = 2
          properties = {
            markdown = "## 4 — LLM Consolidation\nConsolidates OCR outputs into structured JSON via Bedrock Converse"
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 34
          width  = 24
          height = 6
          properties = {
            title   = "LLM Duration (ms)"
            region  = local.aws_region_name
            period  = 300
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
            metrics = [
              [local.metrics_namespace, "LlmDuration", "service", "consolidate_po_data", { stat = "Average" }],
              [local.metrics_namespace, "LlmDuration", "service", "consolidate_po_data", { stat = "Maximum" }],
              [local.metrics_namespace, "LlmDuration", "service", "consolidate_po_data", { stat = "p90" }]
            ]
          }
        }
      ],
      # ─── Step 5: Export — PO Processing (y=40) ──────────────────────────
      [
        {
          type   = "text"
          x      = 0
          y      = 40
          width  = 24
          height = 2
          properties = {
            markdown = "## 5 — Export (CEDL)\nExports consolidated PO data back to CEDL — POs succeeded vs failed"
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = 42
          width  = 12
          height = 6
          properties = {
            title   = "PO Succeeded"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [[local.metrics_namespace, "PurchaseOrderSucceeded", "service", "cedl_export_po_output_data"]]
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = 42
          width  = 12
          height = 6
          properties = {
            title   = "PO Failed"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [
              [local.metrics_namespace, "PurchaseOrderFailed", "service", "cedl_copy_po_files"],
              [local.metrics_namespace, "PurchaseOrderFailed", "service", "consolidate_po_data"],
              [local.metrics_namespace, "PurchaseOrderFailed", "service", "cedl_export_po_output_data"]
            ]
          }
        }
      ]
    )
  })
}

resource "aws_cloudwatch_dashboard" "app_metrics_dashboard" {
  dashboard_name = local.app_dashboard_name
  dashboard_body = local.app_dashboard_body
}
