# Environment – AWS account number placeholders

All real AWS account numbers in this repository were replaced by the placeholder:

```
AWSACCNNNNNN
```

The same placeholder is used for **every** account, so after a search/replace you cannot tell from the value alone which account belongs where. Use the tables below to restore the right number at each location.

> Do **not** commit real account numbers back into the repository if it is shared outside the team. Prefer keeping them in your local, untracked `*.tfvars` files or in CI variables.

## 1. Accounts to look up

The roles are named for the project, so each "logical account" below is inferred from the role name. Confirm with your cloud team.

| Logical account | Used by | Where to get the real number |
|---|---|---|
| **A – App account (DEV / SBX)** | Roles `App_procdb-ext-*-dev` (Snowflake read, Coupa attachments access); Bedrock Data Automation invocations in the test payload | AWS Console → account menu, or `aws sts get-caller-identity --query Account --output text` while logged in to the DEV account |
| **B – CEDL / Coupa data-platform account (DEV / SBX)** | Role `App_Project-coupa-pdb-cross-account-dev` | Ask the CEDL / Coupa data-platform team |
| **C – App account (UAT)** | Roles `App_procdb-ext-*-uat` | `aws sts get-caller-identity` while logged in to the UAT account |
| **D – CEDL / Coupa data-platform account (UAT)** | Role `App_Project-coupa-pdb-cross-account-uat` | Ask the CEDL / Coupa data-platform team |
| **E – AWS-owned Lambda Powertools layer account** | Public layer `AWSLambdaPowertoolsPythonV3-…` | Public AWS value, see the Powertools docs at <https://docs.powertools.aws.dev/lambda/python/latest/> ("Lambda Layer" section, which lists the layer ARNs per region) |

## 2. Locations to restore

Paths are relative to the repository root. Line numbers are as of this change.

| # | File | Line | Setting / context | Account |
|---|---|---|---|---|
| 1 | `env/dev/variables.tfvars` | 71 | `coupa_access_role_arn` (`…sf-read-coupa-tables-dev`) | A |
| 2 | `env/dev/variables.tfvars` | 74 | commented-out `coupa_cross_account_role_arn` (`App_Project-coupa-pdb-cross-account-dev`) | B |
| 3 | `env/dev/variables.tfvars` | 75 | `coupa_cross_account_role_arn` (`…cedl-coupa-attachments-access-dev`) | A |
| 4 | `env/dev/variables.tfvars` | 76 | `cedl_cross_account_role_arn` (`App_Project-coupa-pdb-cross-account-dev`) | B |
| 5 | `env/sbx/variables.tfvars` | 62 | `coupa_access_role_arn` (`…sf-read-coupa-tables-dev`) | A |
| 6 | `env/sbx/variables.tfvars` | 65 | commented-out `coupa_cross_account_role_arn` (`App_Project-coupa-pdb-cross-account-dev`) | B |
| 7 | `env/sbx/variables.tfvars` | 66 | `coupa_cross_account_role_arn` (`…cedl-coupa-attachments-access-dev`) | A |
| 8 | `env/sbx/variables.tfvars` | 67 | `cedl_cross_account_role_arn` (`App_Project-coupa-pdb-cross-account-dev`) | B |
| 9 | `env/uat/variables.tfvars` | 64 | `coupa_access_role_arn` (`…sf-read-coupa-tables-uat`) | C |
| 10 | `env/uat/variables.tfvars` | 67 | `coupa_cross_account_role_arn` (`…cedl-coupa-attachments-access-uat`) | C |
| 11 | `env/uat/variables.tfvars` | 68 | `cedl_cross_account_role_arn` (`App_Project-coupa-pdb-cross-account-uat`) | D |
| 12 | `app_terraform/lambda_function.tf` | 4 | `powertools_layer_arn` (public AWS layer) | E |
| 13 | `app_src/tests/integration/payloads/ocr_po_file_get_status.json` | 5 | Bedrock `invocationArn` (region `eu-west-1`) | A |
| 14 | `app_src/tests/unit/services/test_purchase_order_file_service_get_ocr_status.py` | 172 | Bedrock `invocation_arn` in a unit test (the test does not need the real value) | A |

## 3. How to replace the placeholder

> **Warning:** a global search/replace is wrong here, because the placeholder stands for several different accounts. Edit location by location, using the table above.

### Option A – manual (recommended)

1. Open each file from the table in your editor.
2. At the given line, replace `AWSACCNNNNNN` with the 12-digit number of the account named in the last column.
3. Verify afterwards that no placeholder remains where it matters:

```bash
grep -rn "AWSACCNNNNNN" . --exclude-dir=.git --exclude=environment.md
```

### Option B – scripted

Fill in the five values in your own shell session. **Do not save them in a file inside the repo.**

```bash
ACC_A=000000000000   # DEV/SBX app account
ACC_B=000000000000   # DEV/SBX CEDL / Coupa data-platform account
ACC_C=000000000000   # UAT app account
ACC_D=000000000000   # UAT CEDL / Coupa data-platform account
ACC_E=000000000000   # AWS Powertools layer account (public)

# DEV and SBX
for f in env/dev/variables.tfvars env/sbx/variables.tfvars; do
  sed -i -E \
    -e "/App_Project-coupa-pdb-cross-account-dev/ s/AWSACCNNNNNN/${ACC_B}/" \
    -e "s/AWSACCNNNNNN/${ACC_A}/" "$f"
done

# UAT
sed -i -E \
  -e "/App_Project-coupa-pdb-cross-account-uat/ s/AWSACCNNNNNN/${ACC_D}/" \
  -e "s/AWSACCNNNNNN/${ACC_C}/" env/uat/variables.tfvars

# Powertools layer, test payload and unit test
sed -i "s/AWSACCNNNNNN/${ACC_E}/" app_terraform/lambda_function.tf
sed -i "s/AWSACCNNNNNN/${ACC_A}/" \
  app_src/tests/integration/payloads/ocr_po_file_get_status.json \
  app_src/tests/unit/services/test_purchase_order_file_service_get_ocr_status.py
```

The order inside each `sed` matters: the more specific rule (account B or D, by role name) runs first on a line, then the general rule fills the rest.

### Validate

```bash
terraform -chdir=app_terraform fmt -check
terraform -chdir=app_terraform validate
pytest app_src/tests/unit
```

## 4. Email addresses

All real email addresses were replaced by:

```
email@example.com
```

### Locations to restore

| # | File | Line | Setting | Restore to |
|---|---|---|---|---|
| 1 | `env/dev/variables.tfvars` | 13 | `contact` (used in resource tags) | Project contact |
| 2 | `env/sbx/variables.tfvars` | 13 | `contact` | Project contact |
| 3 | `env/uat/variables.tfvars` | 13 | `contact` | Project contact |
| 4 | `env/dev/variables.tfvars` | 17–19 | `contacts_alerting` (3 entries) | Tech alert recipients |
| 5 | `env/sbx/variables.tfvars` | 17–19 | `contacts_alerting` (3 entries) | Tech alert recipients |
| 6 | `env/uat/variables.tfvars` | 17–19 | `contacts_alerting` (3 entries) | Tech alert recipients |
| 7 | `app_terraform/variables.tf` | 77 | default of `contacts_alerting` | A tech alert recipient |
| 8 | `app_terraform/variables.tf` | 99 | default of `contact` | Project contact |

### Behaviour to be aware of

- The three `contacts_alerting` entries in each tfvars file now hold the **same** value. Terraform builds the SNS email subscriptions with `toset(var.contacts_alerting)` (`app_terraform/observability.tf`), so duplicates collapse into one subscription and nothing breaks. Until you restore real addresses, alert emails go to a non-existent mailbox.
- Restore **one distinct address per entry**, otherwise you only get one subscriber.
- Recipients must confirm the SNS subscription from the email they receive after `terraform apply`.
- The values still pass the regex validation in `variables.tf`.

### How to replace

Edit each entry by hand. A global replace is wrong, because one placeholder stands for several people.

```hcl
contact = "project.contact@your-domain.com"

contacts_alerting = [
  "first.recipient@your-domain.com",
  "second.recipient@your-domain.com",
  "third.recipient@your-domain.com"
]
```

Then check:

```bash
grep -rn "email@example.com" . --exclude-dir=.git --exclude=environment.md
terraform -chdir=app_terraform validate
```

Note: `app_src/tests/unit/parsers/test_email_eml_parser.py` already uses `sender@example.com` and `receiver@example.com`. These are test values and were not changed.

## 5. Organisation name placeholder (`grand_org`)

Every occurrence of the organisation name (any capitalisation) was replaced by `grand_org`. The only exception is all-caps identifiers, which became `GRAND_ORG` so they stay valid constant names. 44 files and about 160 occurrences changed.

> **Important:** `grand_org` is an underscore placeholder, **not** a working value. Most of the places below are real external endpoints, so Terraform, GitHub Actions, Docker and the devcontainer **will fail until the real name is restored**. Hostnames cannot contain underscores. This applies to any pipeline you run on the sanitised copy.

### Categories and where they are

| Category | Example after replacement | Files | Breaks if not restored |
|---|---|---|---|
| Private Terraform module registry | `grand_org.jfrog.io/terraform-innersource-local__aws-services/<module>/aws` | `app_terraform/*.tf` (`dynamodb`, `ecr`, `eventbridge`, `iam_role_lambda`, `kms`, `lambda_function`, `s3_bucket`, `s3_data_bucket`, `ssm_parameter`, `step_function`) | `terraform init` |
| JFrog host and token variable | `grand_org.jfrog.io`, `TF_TOKEN_grand_org_jfrog_io` | `.github/actions/setup-terraform-env/action.yaml`, `scripts/deploy-sandbox.sh` | Registry login. The variable name must match the host with `.` replaced by `_`. |
| GitHub reusable actions and workflows | `grand_org-InnerSource/github-actions-library/…@main`, `grand_org-GitHub/cyber-prisma-code-shared-workflow/…` | `.github/actions/*`, `.github/workflows/*` | CI workflows |
| Code owners | `@grand_org/GenAI_Automation_team-admins` | `.github/CODEOWNERS` | Review requirements |
| Artifactory Docker mirror | `docker-innersource-remote.artifactory.grand_org.com/python` | `app_src/app/lambdas_container/libreoffice_converter/Dockerfile`, `.github/workflows/libreoffice-converter-deploy.yaml` | Image build |
| Devcontainer features | `ghcr.io/grand_org-innersource/devcontainer-features/…` | `.devcontainer/devcontainer.json`, `.devcontainer/README.md` | Devcontainer build |
| Atlassian site | `https://grand_org.atlassian.net/` | `.github/ISSUE_TEMPLATE/config.yml`, `docs/*.md` | Issue-template link |
| Coupa / Snowflake account | `grand_org-emea_df_s2p` | `env/{dev,sbx,uat}/variables.tfvars` | Snowflake connection |
| S3 bucket names | `grand_org-emea-cedl-df-s2p-unstructured-data-{dev,uat}` | `env/{dev,sbx,uat}/variables.tfvars` | Bucket access. Underscores are invalid in S3 bucket names. |
| SonarQube project key | `grand_org-github-genai_automation-procurementdatabooster` | `sonar-project.properties` | Quality-gate scan |
| Repository URL | `https://github.com/grand_org-GitHub/GenAI_Automation-ProcurementDataBooster/pull/23` | `app_terraform/variables.tf` (comment) | None, comment only |
| Prompt variables | `GRAND_ORG_STAFF_COUNT`, `GRAND_ORG_ENTITY` | `app_src/app/prompts/*` | Must match the fields your data uses, so check the original name |
| Prose and prompts | "senior analyst at grand_org", "All grand_org employees" | `app_src/app/prompts/**`, `README.md`, `docs/*.md`, comments | Wording only |

### How to restore

The original name appeared in more than one capitalisation, so first decide what you are restoring:

- **Git history:** the files are modified, not committed. If you use `git checkout` on the tracked ones, you also lose your other uncommitted changes, so be careful.
- **Your own backup:** the originals were copied to the scratchpad `backup2` folder.
- **By search/replace:** the variants differ by file type.

```bash
# Replace <ORG> with the real name, lower-case, e.g. the GitHub / JFrog / hostname form
ORG=<real-name-lowercase>
ORG_CAP=<Real-name-capitalised>      # used in prose and in GitHub org names such as <Org>-InnerSource

# 1. Hostnames, buckets, module registry, token variable, Sonar key, devcontainer features
grep -rlI "grand_org" . --exclude-dir=.git --exclude=environment.md | xargs sed -i "s/grand_org/${ORG}/g"

# 2. All-caps identifiers
grep -rlI "GRAND_ORG" . --exclude-dir=.git --exclude=environment.md | xargs sed -i "s/GRAND_ORG/${ORG^^}/g"

# 3. Prose, GitHub orgs ("<Org>-InnerSource", "<Org>-GitHub") and prompts: re-capitalise by hand
grep -rn "${ORG}-InnerSource\|${ORG}-GitHub\|${ORG} employees\|at ${ORG}" . --exclude-dir=.git --exclude=environment.md
```

Step 3 is optional for GitHub (organisation names are case-insensitive), but prose and prompts read better with the proper capitalisation.

Then verify:

```bash
grep -rIn "grand_org\|GRAND_ORG" . --exclude-dir=.git --exclude=environment.md   # should print nothing
terraform -chdir=app_terraform init -backend=false
```

## 6. Application IDs (MIO code and Application ID)

| Placeholder | Setting | Files |
|---|---|---|
| `AP000000` | `CE_MIO_Code` | `env/dev/variables.tfvars`, `env/sbx/variables.tfvars`, `env/uat/variables.tfvars` (line 2) |
| `APM0000000` | `CE_Application_ID` | same three files (line 4) |

Restore the real values from your application inventory. `APM0000000` still satisfies the `^APM\d{7}$` validation in `app_terraform/variables.tf`, so the placeholder does not break `terraform validate`.

## 7. Snowflake / Coupa / CEDL connection parameters

| Placeholder | Setting | Where |
|---|---|---|
| `dummy_account` | `coupa_account` (Snowflake account identifier) | `env/{dev,sbx,uat}/variables.tfvars` |
| `DUMMY_WAREHOUSE_01` / `DUMMY_WAREHOUSE_02` | `coupa_warehouse` (01 = DEV/SBX, 02 = UAT) | same |
| `DUMMY_DATABASE_DEV` / `DUMMY_DATABASE_UAT` | `coupa_database` | `env/*/variables.tfvars` and the default in `app_terraform/variables.tf` |
| `DUMMY_SCHEMA` / `DUMMY_SCHEMA_UAT` | `coupa_schema` (UAT uses its own schema) | `env/*/variables.tfvars` and the default in `app_terraform/variables.tf` |
| `DUMMY_UNSTRUCTURED_DATA` | CEDL export prefix: `cedl_bucket_prefix`, the S3 path in IAM policies, and the examples in docs and tests | `env/*/variables.tfvars`, `app_terraform/external_coupa_access_iam_role.tf` (lines 49 and 69), `docs/runbooks/update-project-configuration-confluence.md`, `app_src/tests/unit/repositories/test_purchase_order_file_objects_repository.py` |
| `dummy-cedl-unstructured-data-dev` / `-uat` | `cedl_bucket_name` and `cedl_s3_bucket_name` (externally managed CEDL bucket) | `env/*/variables.tfvars` |

Restore these from the Snowflake and CEDL owners. Until you do, the Coupa retrieval Lambda cannot connect and the IAM policies point to a non-existent prefix.

## 8. HACAT codes

Dummy codes keep the original format (two letters plus four digits). Mapping by role:

| Placeholder | Used as | Appears in |
|---|---|---|
| `HC1001` | Biomarker workflow code (DEV/SBX default and most tests) | `env/*/variables.tfvars`, handler examples, tests, payloads, docs |
| `HC1002` | Vaccine workflow code | `env/*/variables.tfvars`, docs |
| `HC1003` | L&D workflow code | `env/*/variables.tfvars`, docs |
| `HC1004` | TCO workflow code | `env/*/variables.tfvars`, docs |
| `HC1005` | Sample code in two handler docstrings and tests | `cedl_copy_po_files_handler.py`, `coupa_po_retrieval_handler.py`, related tests |
| `HC1006` | Sample code in `test_coupa_repository.py` | tests only |
| `HC1007` | UAT biomarker code and the Vaccines row in the runbook | `env/uat/variables.tfvars`, `docs/runbooks/update-project-configuration-confluence.md` |

About 40 files changed. The same code is also used as an S3 prefix (`<hacat>/incoming/...`) and in the SSM path `/<app-prefix>/hacat/<hacat>/...`. The SSM parameters under the old codes will not be found under the new ones.

The mapping from placeholder to the real code is in the backup folder (see section 11). `ZZ1001`–`ZZ1011` in `app_src/app/prompts/tco/extract_data.md` are expense category codes and were not changed.

## 9. Developer names

| Placeholder | Where |
|---|---|
| `developer-1` … `developer-5` | `env/sbx/developers/developer-N.tfvars` and `developer-N.backend.tfvars` (file names and content), `scripts/deploy-sandbox.sh`, `scripts/push-lambda-artifacts.sh`, `docs/*.md`, `app_src/tests/integration/README.md`, `app_src/app/prompts/README.md`, `app_terraform/data.tf` (comment) |

- `developer-1` is the repository owner. `developer-2` to `developer-5` are the other four developers. The original names are only in the backup (`backup3\env_sbx_developers_orig\` shows the original file names).
- The placeholder is used in the instance name (`sbx-ProcurementBooster-developer-N`), the state key (`App-poc-ProcurementBoosterData-developer-N.tfstate`) and the sandbox image name.
- To restore: rename the files back and replace the placeholder in each, or simply keep the neutral names. `./scripts/deploy-sandbox.sh developer-1 init` works as before because the script looks files up by the same name.
- Existing sandbox deployments and remote state use the **old** names. After this change, `terraform` treats `developer-N` as a new deployment with an empty state, so either rename the state objects or keep the old keys in your local copy.

## 10. `procdb` renamed to `idp`

Every occurrence in text and the file contents was changed (71 files changed in total for sections 6–10). No file or folder name contained `procdb`.

| Was | Now |
|---|---|
| `app-procdb-emea-…` (resource names, log groups, SSM prefix, ECR images, buckets) | `app-idp-emea-…` |
| `App_procdb-ext-…` (IAM roles) | `App_idp-ext-…` |
| `App_Github_procdb_bootstrap`, `deploy_procdb` | `App_Github_idp_bootstrap`, `deploy_idp` |
| `app_name_short = "procdb"` | `app_name_short = "idp"` |
| `ProcDB` (text) | `IDP` |

This is functional, not cosmetic: `app_name_short` is the prefix of every resource name. Deploying with the new value **creates new resources** and does not rename existing ones. The IAM role names in `coupa_access_role_arn` and `coupa_cross_account_role_arn` must match the roles in the Snowflake and CEDL accounts, so update those roles or revert the names.

To revert: `grep -rl "idp" . | xargs sed -i 's/idp/procdb/g'`, but check first, because `idp` may also appear naturally in other words.

## 11. Backups of the originals

Outside the repository, in the session scratchpad:

```
C:\Users\PU112509\AppData\Local\Temp\2\claude\D--Projects-Github-claude\17a1bc8e-23e5-444a-8c1f-73a9253dc7fa\scratchpad\
  backup\    accounts and emails
  backup2\   organisation name
  backup3\   application IDs, Snowflake, HACAT, developers, procdb (71 files + env_sbx_developers_orig\)
```

They contain real values, so don't commit or share them. Delete them when you no longer need them.

## 12. Related values that were not changed

These are not account numbers, but they contain pieces of one, so decide separately whether to mask them.

| File | Value | Note |
|---|---|---|
| `env/dev/backend_config.tfvars` and `env/sbx/backend_config.tfvars` | `bucket = "tfstate-<first 6 digits of account A>-eu-west-1-…"` | Must stay the real bucket name for `terraform init` to work |
| `env/uat/backend_config.tfvars` | `bucket = "tfstate-<first 6 digits of account C>-eu-west-1-…"` | Same |
| Unit tests under `app_src/tests/unit/` | `123456789012`, `987654321098` | Dummy values, not real accounts. They were left as is. |
