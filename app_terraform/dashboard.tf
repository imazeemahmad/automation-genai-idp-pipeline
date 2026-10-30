# -----------------------------------------------------------------------------
# CloudWatch Dashboard - Lambda Metrics
# -----------------------------------------------------------------------------

locals {
  dashboard_name = "${local.resource_prefix}-common-infra-dashboard-${local.resource_suffix}"

  # Lambda functions ordered by Step Function execution flow (dispatcher removed)
  lambda_dashboard_order = [
    "coupa_po_retrieval",
    "cedl_copy_po_files",
    "ocr_po_file",
    "ocr_po_file_get_status",
    "consolidate_po_data",
    "cedl_export_po_output_data",
  ]

  lambda_dashboard_descriptions = {
    coupa_po_retrieval         = "Retrieves purchase order metadata from Coupa via Snowflake"
    cedl_copy_po_files         = "Copies PO attachment files from CEDL S3 bucket to data bucket"
    ocr_po_file                = "Launches Bedrock Data Automation (OCR) async job for a PO file"
    ocr_po_file_get_status     = "Polls Bedrock Data Automation job status and copies OCR results"
    consolidate_po_data        = "Consolidates OCR outputs from all files into structured JSON via LLM"
    cedl_export_po_output_data = "Exports consolidated PO data back to CEDL"
  }

  # Y offset for DynamoDB section (after all Lambda widgets)
  dynamodb_y_offset = length(local.lambda_dashboard_order) * 8

  # Y offset for Step Function section (after DynamoDB: header 2 + 2 rows of 6)
  sfn_y_offset = local.dynamodb_y_offset + 16

  # Number of workflows determines height of the SFN section
  # Each workflow gets one row of 4 widgets (height 6) + header (height 2)
  sfn_section_height = 2 + length(var.workflows) * 8

  # Y offset for S3 section (after Step Function section)
  s3_y_offset = local.sfn_y_offset + local.sfn_section_height

  # Y offset for Error Rate section (after S3: header 2 + 1 row of 6)
  error_rate_y_offset = local.s3_y_offset + 10

  # Build the dashboard JSON body directly
  dashboard_body = jsonencode({
    widgets = concat(
      flatten([
        for idx, key in local.lambda_dashboard_order : [
          {
            type   = "text"
            x      = 0
            y      = idx * 8
            width  = 24
            height = 2
            properties = {
              markdown = "## Lambda - ${local.lambda_function_names[key]}\n${local.lambda_dashboard_descriptions[key]}"
            }
          },
          {
            type   = "metric"
            x      = 0
            y      = idx * 8 + 2
            width  = 5
            height = 6
            properties = {
              title   = "Invocations"
              region  = local.aws_region_name
              period  = 300
              stat    = "Sum"
              view    = "timeSeries"
              stacked = false
              metrics = [["AWS/Lambda", "Invocations", "FunctionName", local.lambda_function_names[key]]]
            }
          },
          {
            type   = "metric"
            x      = 5
            y      = idx * 8 + 2
            width  = 5
            height = 6
            properties = {
              title   = "Errors"
              region  = local.aws_region_name
              period  = 300
              stat    = "Sum"
              view    = "timeSeries"
              stacked = false
              metrics = [["AWS/Lambda", "Errors", "FunctionName", local.lambda_function_names[key]]]
            }
          },
          {
            type   = "metric"
            x      = 10
            y      = idx * 8 + 2
            width  = 5
            height = 6
            properties = {
              title   = "Duration"
              region  = local.aws_region_name
              period  = 300
              stat    = "Average"
              view    = "timeSeries"
              stacked = false
              metrics = [
                ["AWS/Lambda", "Duration", "FunctionName", local.lambda_function_names[key], { stat = "Average" }],
                ["AWS/Lambda", "Duration", "FunctionName", local.lambda_function_names[key], { stat = "Maximum" }]
              ]
            }
          },
          {
            type   = "metric"
            x      = 15
            y      = idx * 8 + 2
            width  = 5
            height = 6
            properties = {
              title   = "Concurrent Executions"
              region  = local.aws_region_name
              period  = 300
              stat    = "Maximum"
              view    = "timeSeries"
              stacked = false
              metrics = [["AWS/Lambda", "ConcurrentExecutions", "FunctionName", local.lambda_function_names[key]]]
            }
          },
          {
            type   = "metric"
            x      = 20
            y      = idx * 8 + 2
            width  = 4
            height = 6
            properties = {
              title   = "Cold Starts"
              region  = local.aws_region_name
              period  = 300
              stat    = "Sum"
              view    = "timeSeries"
              stacked = false
              metrics = [[local.metrics_namespace, "ColdStart", "function_name", local.lambda_function_names[key], "service", key]]
            }
          }
        ]
      ]),
      # DynamoDB section
      [
        {
          type   = "text"
          x      = 0
          y      = local.dynamodb_y_offset
          width  = 24
          height = 2
          properties = {
            markdown = "## DynamoDB - ${local.dynamodb_table_name}\nProcurement data store (POs, files, statuses)"
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = local.dynamodb_y_offset + 2
          width  = 8
          height = 6
          properties = {
            title   = "Read Capacity (Consumed)"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", local.dynamodb_table_name]]
          }
        },
        {
          type   = "metric"
          x      = 8
          y      = local.dynamodb_y_offset + 2
          width  = 8
          height = 6
          properties = {
            title   = "Write Capacity (Consumed)"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", local.dynamodb_table_name]]
          }
        },
        {
          type   = "metric"
          x      = 16
          y      = local.dynamodb_y_offset + 2
          width  = 8
          height = 6
          properties = {
            title   = "Throttled Requests"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [
              ["AWS/DynamoDB", "ReadThrottleEvents", "TableName", local.dynamodb_table_name],
              ["AWS/DynamoDB", "WriteThrottleEvents", "TableName", local.dynamodb_table_name]
            ]
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = local.dynamodb_y_offset + 8
          width  = 8
          height = 6
          properties = {
            title   = "Latency (GetItem)"
            region  = local.aws_region_name
            period  = 300
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
            metrics = [["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", local.dynamodb_table_name, "Operation", "GetItem"]]
          }
        },
        {
          type   = "metric"
          x      = 8
          y      = local.dynamodb_y_offset + 8
          width  = 8
          height = 6
          properties = {
            title   = "Latency (PutItem)"
            region  = local.aws_region_name
            period  = 300
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
            metrics = [["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", local.dynamodb_table_name, "Operation", "PutItem"]]
          }
        },
        {
          type   = "metric"
          x      = 16
          y      = local.dynamodb_y_offset + 8
          width  = 8
          height = 6
          properties = {
            title   = "System Errors"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [["AWS/DynamoDB", "SystemErrors", "TableName", local.dynamodb_table_name]]
          }
        }
      ],
      # Step Functions section — one row per workflow
      [
        {
          type   = "text"
          x      = 0
          y      = local.sfn_y_offset
          width  = 24
          height = 2
          properties = {
            markdown = "## Step Functions\nPurchase Order Processing Workflow orchestration (per project)"
          }
        }
      ],
      flatten([
        for idx, key in keys(var.workflows) : [
          {
            type   = "text"
            x      = 0
            y      = local.sfn_y_offset + 2 + idx * 8
            width  = 24
            height = 2
            properties = {
              markdown = "### ${key} — ${local.step_function_names[key]}"
            }
          },
          {
            type   = "metric"
            x      = 0
            y      = local.sfn_y_offset + 4 + idx * 8
            width  = 6
            height = 6
            properties = {
              title   = "Executions Started"
              region  = local.aws_region_name
              period  = 300
              stat    = "Sum"
              view    = "timeSeries"
              stacked = false
              metrics = [["AWS/States", "ExecutionsStarted", "StateMachineArn", aws_sfn_state_machine.workflow[key].arn]]
            }
          },
          {
            type   = "metric"
            x      = 6
            y      = local.sfn_y_offset + 4 + idx * 8
            width  = 6
            height = 6
            properties = {
              title   = "Executions Succeeded"
              region  = local.aws_region_name
              period  = 300
              stat    = "Sum"
              view    = "timeSeries"
              stacked = false
              metrics = [["AWS/States", "ExecutionsSucceeded", "StateMachineArn", aws_sfn_state_machine.workflow[key].arn]]
            }
          },
          {
            type   = "metric"
            x      = 12
            y      = local.sfn_y_offset + 4 + idx * 8
            width  = 6
            height = 6
            properties = {
              title   = "Executions Failed"
              region  = local.aws_region_name
              period  = 300
              stat    = "Sum"
              view    = "timeSeries"
              stacked = false
              metrics = [["AWS/States", "ExecutionsFailed", "StateMachineArn", aws_sfn_state_machine.workflow[key].arn]]
            }
          },
          {
            type   = "metric"
            x      = 18
            y      = local.sfn_y_offset + 4 + idx * 8
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
                ["AWS/States", "ExecutionTime", "StateMachineArn", aws_sfn_state_machine.workflow[key].arn, { stat = "Average" }],
                ["AWS/States", "ExecutionTime", "StateMachineArn", aws_sfn_state_machine.workflow[key].arn, { stat = "Maximum" }]
              ]
            }
          }
        ]
      ]),
      # S3 Data Bucket section
      [
        {
          type   = "text"
          x      = 0
          y      = local.s3_y_offset
          width  = 24
          height = 2
          properties = {
            markdown = "## S3 - ${local.s3_data_bucket_name}\nPO files storage (incoming, OCR results, extracted data)"
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = local.s3_y_offset + 2
          width  = 8
          height = 6
          properties = {
            title   = "Number of Objects"
            region  = local.aws_region_name
            period  = 86400
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
            metrics = [["AWS/S3", "NumberOfObjects", "BucketName", local.s3_data_bucket_name, "StorageType", "AllStorageTypes"]]
          }
        },
        {
          type   = "metric"
          x      = 8
          y      = local.s3_y_offset + 2
          width  = 8
          height = 6
          properties = {
            title   = "Bucket Size (Bytes)"
            region  = local.aws_region_name
            period  = 86400
            stat    = "Average"
            view    = "timeSeries"
            stacked = false
            metrics = [["AWS/S3", "BucketSizeBytes", "BucketName", local.s3_data_bucket_name, "StorageType", "StandardStorage"]]
          }
        },
        {
          type   = "metric"
          x      = 16
          y      = local.s3_y_offset + 2
          width  = 8
          height = 6
          properties = {
            title   = "4xx / 5xx Errors"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [
              ["AWS/S3", "4xxErrors", "BucketName", local.s3_data_bucket_name, "FilterId", "AllRequests"],
              ["AWS/S3", "5xxErrors", "BucketName", local.s3_data_bucket_name, "FilterId", "AllRequests"]
            ]
          }
        }
      ],
      # Lambda Overview section
      [
        {
          type   = "text"
          x      = 0
          y      = local.error_rate_y_offset
          width  = 24
          height = 2
          properties = {
            markdown = "## Lambda Overview\nAll functions — invocations, error rate, duration, and throttles"
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = local.error_rate_y_offset + 2
          width  = 12
          height = 6
          properties = {
            title   = "Invocations per Lambda"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = true
            metrics = [
              for key in local.lambda_dashboard_order :
              ["AWS/Lambda", "Invocations", "FunctionName", local.lambda_function_names[key]]
            ]
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = local.error_rate_y_offset + 2
          width  = 12
          height = 6
          properties = {
            title   = "Errors per Lambda"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [
              for key in local.lambda_dashboard_order :
              ["AWS/Lambda", "Errors", "FunctionName", local.lambda_function_names[key]]
            ]
          }
        },
        {
          type   = "metric"
          x      = 0
          y      = local.error_rate_y_offset + 8
          width  = 12
          height = 6
          properties = {
            title   = "Duration p90 (ms)"
            region  = local.aws_region_name
            period  = 300
            stat    = "p90"
            view    = "timeSeries"
            stacked = false
            metrics = [
              for key in local.lambda_dashboard_order :
              ["AWS/Lambda", "Duration", "FunctionName", local.lambda_function_names[key]]
            ]
          }
        },
        {
          type   = "metric"
          x      = 12
          y      = local.error_rate_y_offset + 8
          width  = 12
          height = 6
          properties = {
            title   = "Throttles"
            region  = local.aws_region_name
            period  = 300
            stat    = "Sum"
            view    = "timeSeries"
            stacked = false
            metrics = [
              for key in local.lambda_dashboard_order :
              ["AWS/Lambda", "Throttles", "FunctionName", local.lambda_function_names[key]]
            ]
          }
        }
      ]
    )
  })
}

resource "aws_cloudwatch_dashboard" "lambda_dashboard" {
  dashboard_name = local.dashboard_name
  dashboard_body = local.dashboard_body
}
