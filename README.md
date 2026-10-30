# GenAI Automation – Procurement Data Booster

Automates procurement purchase order processing for grand_org. The system ingests purchase order data from Coupa, stores and processes it via AWS Lambda and DynamoDB, and enriches it with AI-powered biomarker extraction using Amazon Bedrock.

## Documentation

Detailed documentation lives in [`docs/`](docs/). Start here:

| Topic | Document |
|-------|----------|
| Local dev environment (Codespaces / Dev Container) | [`docs/local-development-confluence.md`](docs/local-development-confluence.md) |
| Sandbox deployment (`deploy-sandbox.sh`) | [`docs/deploy-sandbox-confluence.md`](docs/deploy-sandbox-confluence.md) |
| Lambda build & push scripts | [`docs/build-push-artifacts-confluence.md`](docs/build-push-artifacts-confluence.md) |
| CI/CD pipeline & bootstrap | [`docs/cicd-confluence.md`](docs/cicd-confluence.md) |
| Code quality checks (pre-commit, SonarQube, Prisma) | [`docs/quality-checks-confluence.md`](docs/quality-checks-confluence.md) |
| Operational runbooks (replay, troubleshooting, configuration) | [`docs/runbooks/`](docs/runbooks/) |

## Manual Pipeline Execution

The pipeline can be triggered manually by starting an execution of the Step Function, either
end-to-end or one Lambda at a time. The full command reference (state machine + each Lambda,
with ready-to-use payloads) lives in
[`app_src/tests/integration/README.md`](app_src/tests/integration/README.md).

The state machine input selects the workflow, the HACAT code(s) to process, and optionally a
list of PO numbers (set `po_numbers` to `null` to retrieve all new POs):

```json
{
  "workflow_name": "biomarker",
  "hacat_list": ["HC1001"],
  "po_numbers": ["E003770751", "E003658990"]
}
```

The pipeline iterates over each HACAT, fetches new POs from Coupa, then for each PO copies
files, runs OCR, extracts data via LLM, consolidates, and exports.

### Reprocessing purchase orders

To replay POs that were already ingested (targeted replay by PO number, or a time-window
replay via the `lastExecution` watermark), follow the
[Replay Purchase Orders runbook](docs/runbooks/replay-purchase-orders-confluence.md).

## Deployment

Lambda functions are deployed as zip packages with a separate **Lambda Layer** for Python dependencies. This decouples dependency management from application code, resulting in faster deployments and smaller artifacts.

```
build/
├── layer.zip   ← Python dependencies (pydantic, snowflake-connector, etc.)
└── code.zip    ← Application code only (handlers, models, services, repositories)
```

- **Layer** (`layer.zip`): all pip dependencies. Only rebuilt when dependencies change.
- **Code** (`code.zip`): application source only. Rebuilt on every code change.

Terraform uploads both zips to S3 and references them in the Lambda configuration.

For the how-to, see:

- **Local sandbox deployment** — [`docs/deploy-sandbox-confluence.md`](docs/deploy-sandbox-confluence.md)
- **Build & push scripts** — [`docs/build-push-artifacts-confluence.md`](docs/build-push-artifacts-confluence.md)
- **CI/CD pipeline & first-time bootstrap** — [`docs/cicd-confluence.md`](docs/cicd-confluence.md)

## KMS Encryption Keys

The project uses **dedicated KMS keys per domain** rather than a single shared key. This follows the principle of least privilege and reduces blast radius in case of key compromise.

### Key inventory

| Key | Alias pattern | Encrypts | Consumed by |
|-----|--------------|----------|-------------|
| `kms_data` | `app-idp-emea-kms-data-<env>` | S3 data bucket, DynamoDB table | Lambda roles (via IAM policy) |
| `kms_messaging` | `app-idp-emea-kms-messaging-<env>` | SNS topics, SQS dead-letter queues | Step Function role (via IAM policy) |
| `kms_ssm` | `app-idp-emea-kms-ssm-<env>` | SSM SecureString parameters | Lambda roles that access SSM (via IAM policy) |
| `kms_ecr` | `app-idp-emea-kms-ecr-<env>` | ECR container images | GitHub CI/CD roles |
| `lambda_env_key` | `alias/<function-name>` | Lambda environment variables | Lambda roles (via IAM policy) |
| `s3_build_bucket_key` | `alias/<build-bucket-name>` | S3 build bucket (layer/code zips) | CI/CD roles, Terraform |

### Design decisions

**IAM delegation over key policy principals** — Key policies grant encrypt/decrypt to the AWS account root (`arn:aws:iam::<account>:root`). This enables IAM policy-based access control and avoids the chicken-and-egg problem where roles referenced in a key policy must exist before the key can be created.

**One IAM policy per key** — Each key has a corresponding IAM policy (`policy_kms_data`, `policy_kms_messaging`, `policy_kms_ssm`, `policy_kms_lambda_env`) that is attached only to roles that need it. A Lambda that reads S3 and DynamoDB gets `policy_kms_data`, but not `policy_kms_messaging`.

**Tag-based condition** — All KMS IAM policies include a `aws:ResourceTag/app_name_short` condition as defense-in-depth. Even if the policy is accidentally attached to the wrong role, it only works against keys tagged with the correct application name.

**Separation of concerns** — Compromising the messaging key (SNS/SQS) does not grant access to business data (S3/DynamoDB). Audit trails in CloudTrail clearly show which domain was accessed.

## Data Model (DynamoDB)

The procurement table (`PROCUREMENT_TABLE_NAME`) is a single-table design with a
`PK` (hash) / `SK` (range) schema and no secondary indexes. A purchase order (PO)
is scoped by its HACAT category code: the HACAT is part of the partition key, so
the same PO number can be processed independently under several HACATs without
key collisions.

### Item types

| Item | PK | SK | Key attributes |
|------|----|----|----------------|
| PO tracking record | `PO#HACAT#{hacat}#PO#{po_number}` | `EXEC#{execution_id}` | `po_number`, `hacat`, `execution_id`, `status`, `nb_files`, `timestamp` |
| PO file record | `PO_FILE#HACAT#{hacat}#PO#{po_number}` | `PO_FILE#{file_name}` | `po_number`, `filename`, `hacat`, `status`, `timestamp`, `original_filename` |

### Access patterns

- **PO status update** — direct `update_item` on `(hacat, po_number, execution_id)`.
- **PO file status update / get** — direct access on `(hacat, po_number, file_name)`.
- **List a PO's files** — `find_by_po(hacat, po_number)` runs a Query on
  `PK = PO_FILE#HACAT#{hacat}#PO#{po_number}`, returning only the files of that
  specific (PO, HACAT) pair.

### Cardinality

One HACAT owns many POs, and a single PO can belong to several HACATs. Each
`(PO, HACAT)` pair is an independent processing unit: it has its own tracking
record, its own file records, and its own S3 prefix
(`{hacat}/incoming/{po_number}/...`). The Step Function fans out per HACAT and
then per PO, so a PO shared across HACATs is processed once per HACAT branch.
