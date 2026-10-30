# Required by the module
CE_MIO_Code          = "AP000000"
CE_Business_Entity   = "Automation COE"
CE_Application_ID    = "APM0000000"
CE_SLA               = "SLA8"
CE_App_Instance_Name = "ProcurementBooster"
Version              = "0.0.1"
region               = "eu-west-1"
CE_Environment       = "UAT"

# COE team informations
team    = "COE Automation"
contact = "email@example.com"

# Alerting
contacts_alerting = [
  "email@example.com",
  "email@example.com",
  "email@example.com"
]

contacts_business_alerting = []

# Short application (prefix of every objects, only characters and numbers)
app_name_short = "idp"

# Workflows
workflows = {
  biomarker = {
    schedule_expression = "rate(12 hours)"
    enabled             = true
    hacat_codes = {
      biomarker = ["HC1001"]
    }
  }
  lnd = {
    schedule_expression = "rate(12 hours)"
    enabled             = true
    hacat_codes = {
      lnd = ["HC1003"]
    }
  }
  vaccines = {
    schedule_expression = "rate(12 hours)"
    enabled             = false
    hacat_codes = {
      biomarker = ["HC1007"]
    }
  }
}

# Step Function logging
step_function_logging_level = "ALL"

# DLQ retention
sfn_dlq_retention_days = 3

# Logging
cloudwatch_log_retention_days = 30

# Coupa / Snowflake connection
coupa_account                = "dummy_account"
coupa_warehouse              = "DUMMY_WAREHOUSE_02"
coupa_access_role_arn        = "arn:aws:iam::AWSACCNNNNNN:role/App_idp-ext-sf-read-coupa-tables-uat"
coupa_schema                 = "DUMMY_SCHEMA_UAT"
coupa_database               = "DUMMY_DATABASE_UAT"
coupa_cross_account_role_arn = "arn:aws:iam::AWSACCNNNNNN:role/App_idp-ext-cedl-coupa-attachments-access-uat"
cedl_cross_account_role_arn  = "arn:aws:iam::AWSACCNNNNNN:role/App_Project-coupa-pdb-cross-account-uat"

# CEDL S3 bucket (managed externally)
cedl_bucket_name   = "dummy-cedl-unstructured-data-uat"
cedl_bucket_prefix = "DUMMY_UNSTRUCTURED_DATA"

# Coupa cross-account access
cedl_s3_bucket_name = "dummy-cedl-unstructured-data-uat"

# Snowflake biomarker S3 bucket (to be confirmed for deletion)
snowflake_biomarker_s3_bucket_name = "pdb-s3-biomarker-process"

# Powertools
powertools_log_level = "INFO"

# Lambda Advanced Logging Controls (must be aligned with powertools_log_level
# so that Powertools logs are not filtered out by the Lambda platform)
application_log_level = "INFO"

# S3 data bucket lifecycle (retention per prefix, in days)
s3_data_prefix_retention_days = {
  "incoming"    = 30
  "llm-extract" = 30
  "ocr-data"    = 30
  "ocr-jobs"    = 10
  "output"      = 30
}

# LibreOffice converter image (repository:tag). ECR registry is prepended by Terraform.
libreoffice_converter_image = "app-idp-emea-libreoffice-converter-uat:1.0.1"
