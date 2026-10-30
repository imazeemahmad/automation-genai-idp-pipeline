# Lambda Invoke Commands

Manual invocation guide for each Lambda function via AWS CLI.

## Setup

Export your environment before running any command:

```bash
export AWS_ENV=sbx-developer-5
```

> **Naming convention**: `app-idp-emea-<name>-$AWS_ENV`

---

## 1. Coupa PO Retrieval

Retrieves Purchase Orders from Coupa/Snowflake.

Reset the `lastExecution` SSM parameter to force a full retrieval:

```bash
aws ssm put-parameter \
  --name "/app-idp-emea-$AWS_ENV/hacat/HC1001/lastExecution" \
  --value "1970-01-01T00:00:00Z" \
  --type String \
  --overwrite
```

Invoke the Lambda:

```bash
aws lambda invoke \
  --function-name app-idp-emea-common-coupa-po-retrieval-$AWS_ENV \
  --cli-binary-format raw-in-base64-out \
  --payload file://app_src/tests/integration/payloads/coupa_po_retrieval.json \
  --output json \
  /dev/stdout | jq
```

---

## 2. CEDL Copy PO Files

Copies PO attachment files from the CEDL bucket to the project data bucket.

```bash
aws lambda invoke \
  --function-name app-idp-emea-common-cedl-copy-po-files-$AWS_ENV \
  --cli-binary-format raw-in-base64-out \
  --payload file://app_src/tests/integration/payloads/cedl_copy_po_files.json \
  --output json \
  /dev/stdout | jq
```

---

## 3. OCR PO File

Starts OCR processing (Bedrock Data Automation) on a PO attachment file.

```bash
aws lambda invoke \
  --function-name app-idp-emea-common-ocr-po-file-$AWS_ENV \
  --cli-binary-format raw-in-base64-out \
  --payload file://app_src/tests/integration/payloads/ocr_po_file.json \
  --output json \
  /tmp/ocr_po_file_result.json

cat /tmp/ocr_po_file_result.json | jq

INVOCATION_ARN=$(jq -r '.invocationArn' /tmp/ocr_po_file_result.json)
jq --arg arn "$INVOCATION_ARN" '.invocationArn = $arn' \
  app_src/tests/integration/payloads/ocr_po_file_get_status.json > tmp.json \
  && mv tmp.json app_src/tests/integration/payloads/ocr_po_file_get_status.json
```

---

## 4. OCR PO File Get Status

Checks the status of an ongoing OCR job. The `<invocationArn>` in the payload is automatiquement mis à jour par la commande de l'étape 3.

```bash
aws lambda invoke \
  --function-name app-idp-emea-common-ocr-po-file-get-status-$AWS_ENV \
  --cli-binary-format raw-in-base64-out \
  --payload file://app_src/tests/integration/payloads/ocr_po_file_get_status.json \
  --output json \
  /dev/stdout | jq
```

---

## 5. Consolidate PO Data

Reads all OCR outputs for a PO, assembles them into a documents array, invokes Bedrock for extraction + consolidation, and stores the structured JSON result.

> **Note**: This Lambda may take several minutes to complete (LLM invocation). Use `--cli-read-timeout` to avoid CLI timeout errors.

```bash
aws lambda invoke \
  --function-name app-idp-emea-common-consolidate-po-data-$AWS_ENV \
  --cli-binary-format raw-in-base64-out \
  --cli-read-timeout 300 \
  --payload file://app_src/tests/integration/payloads/consolidate_po_data.json \
  --output json \
  /tmp/consolidate_po_data_result.json

cat /tmp/consolidate_po_data_result.json | jq

TIMESTAMP=$(jq -r '.timestamp' /tmp/consolidate_po_data_result.json)
jq --arg ts "$TIMESTAMP" '.timestamp = $ts' \
  app_src/tests/integration/payloads/cedl_export_po_output_data.json > tmp.json \
  && mv tmp.json app_src/tests/integration/payloads/cedl_export_po_output_data.json
```

---

## 6. CEDL Export PO Output Data

Exports consolidated output data back to the CEDL bucket.

```bash
aws lambda invoke \
  --function-name app-idp-emea-common-cedl-export-po-output-data-$AWS_ENV \
  --cli-binary-format raw-in-base64-out \
  --payload file://app_src/tests/integration/payloads/cedl_export_po_output_data.json \
  --output json \
  /dev/stdout | jq
```

---

## 7. Step Function (Full Workflow)

Starts the full purchase order processing workflow (all steps end-to-end).

```bash
WORKFLOW_NAME="biomarker"
SFN_ARN=$(aws stepfunctions list-state-machines --query "stateMachines[?contains(name,'app-idp-emea-${WORKFLOW_NAME}-orchestration-${AWS_ENV}')].stateMachineArn" --output text)

aws stepfunctions start-execution \
  --state-machine-arn "$SFN_ARN" \
  --input file://app_src/tests/integration/payloads/step_function.json
```

To follow the execution status:

```bash
EXECUTION_ARN=$(aws stepfunctions list-executions \
  --state-machine-arn "$SFN_ARN" \
  --max-results 1 \
  --query "executions[0].executionArn" \
  --output text)

aws stepfunctions describe-execution --execution-arn "$EXECUTION_ARN" | jq '.status'
```

---

## Utilities

### Purge DynamoDB Table

Deletes all items from the project's DynamoDB table using `batch-write-item` (25 deletes per request):

```bash
TABLE_NAME="app-idp-emea-$AWS_ENV"

aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --projection-expression "PK, SK" \
  --output json \
| jq -c '[.Items[] | {DeleteRequest: {Key: .}}]
         | range(0; length; 25) as $i
         | .[$i:$i+25]' \
| while read -r batch; do
    aws dynamodb batch-write-item \
      --request-items "{\"$TABLE_NAME\": $batch}"
  done
```

> ⚠️ This command deletes **all** items from the table. Use only in sandbox environments.

---

## Notes

- Payload JSON files are located in `app_src/tests/integration/payloads/`.
- Add `--region eu-west-1` if your CLI is not configured for the correct region.
- To tail logs: `aws logs tail /aws/lambda/app-idp-emea-common-<name>-$AWS_ENV --follow`
