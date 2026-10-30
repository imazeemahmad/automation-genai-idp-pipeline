variable "CE_MIO_Code" {
  description = "MIO code for tagging"
  type        = string
}

variable "CE_Business_Entity" {
  description = "Business entity for tagging"
  type        = string
}

variable "CE_Application_ID" {
  description = "Application ID for tagging"
  type        = string

  validation {
    condition     = can(regex("^APM\\d{7}$", var.CE_Application_ID))
    error_message = "CE_Application_ID must be in the format APM_______ (7 digits)."
  }
}

variable "CE_SLA" {
  description = "SLA for tagging"
  type        = string
}

variable "CE_App_Instance_Name" {
  description = "App instance name for tagging"
  type        = string
  validation {
    condition     = length(var.CE_App_Instance_Name) > 0
    error_message = "App instance name must be not empty."
  }
}

variable "Version" {
  description = "Version for tagging"
  type        = string
}

variable "terraform_execution_role" {
  description = "IAM role name used by Terraform to manage resources (CE_AppAdmin for local, App_<app>_Github for CI)"
  type        = string
  default     = "CE_AppAdmin"
}

variable "CE_Environment" {
  description = "Deployment environment"
  type        = string
  default     = "SBX"

  validation {
    condition     = contains(["SBX", "DEV", "UAT", "PROD"], var.CE_Environment)
    error_message = "environment must be SBX, DEV, UAT or PROD."
  }
}

variable "team" {
  description = "Owner team of the project"
  type        = string
  default     = "COE Automation"
}

variable "cloudwatch_log_retention_days" {
  description = "Retention period in days for CloudWatch log groups"
  type        = number
  default     = 90

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.cloudwatch_log_retention_days)
    error_message = "cloudwatch_log_retention_days must be a valid CloudWatch Logs retention value."
  }
}

variable "contacts_alerting" {
  description = "List of email addresses to subscribe to tech alert notifications"
  type        = list(string)
  default     = ["email@example.com"]

  validation {
    condition     = alltrue([for email in var.contacts_alerting : can(regex("^[^@]+@[^@]+\\.[^@]+$", email))])
    error_message = "All entries in contacts_alerting must be valid email addresses."
  }
}

variable "contacts_business_alerting" {
  description = "List of email addresses to subscribe to business alert notifications"
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for email in var.contacts_business_alerting : can(regex("^[^@]+@[^@]+\\.[^@]+$", email))])
    error_message = "All entries in contacts_business_alerting must be valid email addresses."
  }
}

variable "contact" {
  description = "Contact email for the project (used in tags)"
  type        = string
  default     = "email@example.com"
}

variable "region" {
  description = "value"
  type        = string
  default     = "us-east-1"
}

variable "app_name_short" {
  description = "Short name of the application"
  type        = string
  default     = "ContractMetadata"
}

variable "region_short" {
  description = "Short region identifier for resource naming (e.g. 'emea', 'us')"
  type        = string
  default     = "emea"
}

variable "workflows" {
  description = <<-EOT
    Map of workflows to orchestrate via EventBridge + Step Function.
    Each entry creates a separate EventBridge rule + DLQ with its own schedule and hacat_codes input.
    Key = logical name (used in resource naming, e.g. "biomarker", "vaccines").
    Value = { schedule_expression, enabled, hacat_codes }
  EOT
  type = map(object({
    schedule_expression = string
    enabled             = optional(bool, true)
    hacat_codes         = map(list(string))
  }))
  default = {
    biomarker = {
      schedule_expression = "cron(0 8 * * ? *)"
      enabled             = true
      hacat_codes = {
        biomarker = ["HC1001"]
      }
    }
  }

  validation {
    condition     = length(var.workflows) > 0
    error_message = "At least one workflow must be defined."
  }
}

variable "hacat_allowed_file_extensions" {
  description = "Map of HACAT logical names to their allowed file extensions (dot-prefixed, e.g. [\".pdf\", \".jpeg\"])"
  type        = map(list(string))
  default = {
    biomarker = [".pdf", ".docx", ".doc"]
    vaccine   = [".pdf", ".docx", ".xlsx", ".eml", ".msg"]
    lnd       = [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xlsx", ".xls"]
    tco       = [".pdf", ".docx", ".xlsx"]
  }
}

variable "hacat_cedl_export_path" {
  description = "Map of HACAT logical names to their CEDL export subfolder path (e.g. 'GEN_AI/BIOMARKER')"
  type        = map(string)
  default = {
    biomarker = "GEN_AI/BIOMARKER"
    vaccine   = "GEN_AI/VACCINE"
    lnd       = "GEN_AI/LnD"
    tco       = "GEN_AI/TCO"
  }
}

variable "hacat_mapping_s3_key" {
  description = "Map of HACAT logical names to the S3 key of their optional mapping.json file. An empty value means no mappingS3Key SSM parameter is created for that HACAT (mapping feature disabled)."
  type        = map(string)
  default = {
    biomarker = ""
    vaccine   = ""
    lnd       = "HC1003/mappings/mappings.json"
    tco       = ""
  }
}

variable "sfn_max_concurrency_orders" {
  description = "Maximum number of purchase orders processed in parallel by the Step Function"
  type        = number
  default     = 10

  validation {
    condition     = var.sfn_max_concurrency_orders >= 1 && var.sfn_max_concurrency_orders <= 40
    error_message = "sfn_max_concurrency_orders must be between 1 and 40."
  }
}

variable "sfn_max_concurrency_files" {
  description = "Maximum number of files processed in parallel per purchase order by the Step Function"
  type        = number
  default     = 5

  validation {
    condition     = var.sfn_max_concurrency_files >= 1 && var.sfn_max_concurrency_files <= 20
    error_message = "sfn_max_concurrency_files must be between 1 and 20."
  }
}

variable "step_function_logging_level" {
  description = "Step Function logging level (ALL, ERROR, FATAL, OFF)"
  type        = string
  default     = "ERROR"

  validation {
    condition     = contains(["ALL", "ERROR", "FATAL", "OFF"], var.step_function_logging_level)
    error_message = "step_function_logging_level must be ALL, ERROR, FATAL, or OFF."
  }
}

variable "sfn_dlq_retention_days" {
  description = "Number of days to retain messages in the Step Function DLQ"
  type        = number
  default     = 14

  validation {
    condition     = var.sfn_dlq_retention_days >= 1 && var.sfn_dlq_retention_days <= 14
    error_message = "sfn_dlq_retention_days must be between 1 and 14."
  }
}

variable "ecr_image_count" {
  description = "Maximum number of images to retain in ECR repository"
  type        = number
  default     = 20
}

variable "libreoffice_converter_image" {
  description = <<-EOT
    LibreOffice converter ECR image as "<repository>:<tag>"
    (e.g. "app-idp-emea-libreoffice-converter-sbx:1.0.0"). The ECR registry
    (<account>.dkr.ecr.<region>.amazonaws.com) is prepended dynamically by
    Terraform. Defaults to the shared SBX image so developer sandboxes reuse it.
  EOT
  type        = string
  default     = "app-idp-emea-libreoffice-converter-sbx:latest"
}

variable "hacat_codes" {
  description = "Map of HACAT category codes used as S3 key prefixes (e.g. { biomarker = \"HC1001\" })"
  type        = map(string)
  default = {
    biomarker = "HC1001"
    vaccine   = "HC1002"
    lnd       = "HC1003"
    tco       = "HC1004"
  }
}

variable "powertools_log_level" {
  description = "Log level for AWS Lambda Powertools (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
  type        = string
  default     = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.powertools_log_level)
    error_message = "powertools_log_level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL."
  }
}

variable "ssm_max_age" {
  description = "Cache duration in seconds for SSM parameters fetched by Lambda functions (0 = no cache)"
  type        = number
  default     = 300

  validation {
    condition     = var.ssm_max_age >= 0 && var.ssm_max_age <= 86400
    error_message = "ssm_max_age must be between 0 and 86400 seconds (24 hours)."
  }
}

variable "application_log_level" {
  description = "Application log level for Lambda Advanced Logging Controls (TRACE, DEBUG, INFO, WARN, ERROR, FATAL). Should be aligned with powertools_log_level so Powertools logs are not filtered by the platform."
  type        = string
  default     = "INFO"

  validation {
    condition     = contains(["TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"], var.application_log_level)
    error_message = "application_log_level must be TRACE, DEBUG, INFO, WARN, ERROR, or FATAL."
  }
}

variable "system_log_level" {
  description = "System log level for Lambda Advanced Logging Controls (DEBUG, INFO, WARN)."
  type        = string
  default     = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARN"], var.system_log_level)
    error_message = "system_log_level must be DEBUG, INFO, or WARN."
  }
}

variable "s3_data_prefix_retention_days" {
  description = "Map of S3 data bucket prefix names to their retention (expiration) in days. Prefixes not listed here use the default of 30 days. Example: { \"ocr-jobs\" = 7, \"output\" = 90 }"
  type        = map(number)
  default = {
    "incoming"    = 30
    "llm-extract" = 30
    "ocr-data"    = 30
    "ocr-jobs"    = 7
    "output"      = 30
  }

  validation {
    condition     = alltrue([for days in values(var.s3_data_prefix_retention_days) : days >= 1])
    error_message = "All retention values in s3_data_prefix_retention_days must be at least 1 day."
  }
}

variable "s3_data_default_retention_days" {
  description = "Default retention (expiration) in days for S3 data bucket prefixes not explicitly configured in s3_data_prefix_retention_days"
  type        = number
  default     = 30

  validation {
    condition     = var.s3_data_default_retention_days >= 1
    error_message = "s3_data_default_retention_days must be at least 1 day."
  }
}

variable "s3_build_noncurrent_versions_to_keep" {
  description = "Number of noncurrent object versions to retain in the build S3 bucket"
  type        = number
  default     = 10

  validation {
    condition     = var.s3_build_noncurrent_versions_to_keep >= 1
    error_message = "s3_build_noncurrent_versions_to_keep must be at least 1."
  }
}

# ─── Coupa / Snowflake connection ────────────────────────────────────────────

variable "coupa_account" {
  description = "Snowflake account identifier for Coupa data source"
  type        = string
}

variable "coupa_warehouse" {
  description = "Snowflake warehouse to use for Coupa queries"
  type        = string
}

variable "coupa_access_role_arn" {
  description = "IAM role ARN to assume for Snowflake workload identity authentication"
  type        = string
}

variable "coupa_database" {
  description = "Snowflake database name for Coupa data"
  type        = string
  default     = "DUMMY_DATABASE_DEV"
}

variable "coupa_schema" {
  description = "Snowflake schema name for Coupa data"
  type        = string
  default     = "DUMMY_SCHEMA"
}

variable "coupa_cross_account_role_arn" {
  description = "IAM role ARN to assume as intermediate step for cross-account access (same account, grants STS permissions to assume the CEDL role)"
  type        = string
}

variable "cedl_cross_account_role_arn" {
  description = "IAM role ARN to assume for final cross-account access to the CEDL S3 bucket (in the CEDL account, requires external ID)"
  type        = string
}

variable "coupa_role_external_id" {
  description = "External ID used when assuming the CEDL cross-account role. Injected at deploy time via TF_VAR_coupa_role_external_id (GitHub secret)."
  type        = string
  sensitive   = true
  default     = "PLACEHOLDER"
}

variable "cedl_bucket_name" {
  description = "Name of the CEDL S3 bucket containing PO attachment files (managed in another account)"
  type        = string
}

variable "cedl_s3_bucket_name" {
  description = "Name of the CEDL S3 bucket used for Coupa attachments access (cross-account)"
  type        = string
}

variable "snowflake_biomarker_s3_bucket_name" {
  description = "Name of the S3 bucket used by Snowflake for biomarker data processing"
  type        = string
}

variable "cedl_bucket_prefix" {
  description = "S3 key prefix in the CEDL bucket where PO attachment files are stored"
  type        = string
  default     = ""
}

# ─── JFrog Module Versions ───────────────────────────────────────────────────

variable "jfrog_module_versions" {
  description = "Map of innersource Terraform module versions hosted on JFrog"
  type        = map(string)
  const       = true
  default = {
    #https://github.com/grand_org-GitHub/GenAI_Automation-ProcurementDataBooster/pull/23
    s3_bucket         = "0.0.0-beta-fix-s3tagsfilter"
    dynamodb_table    = "2.1.0"
    kms_symmetric_key = "2.1.0"
    iam_role_service  = "2.1.0"
    ecr_repository    = "2.1.0"
    lambda_function   = "2.1.0"
    ssm_parameter     = "2.1.0"
  }
}
