## 0.1.2 (2026-08-26)

### Fix

- deduplicate po file per po if it exists

## 0.1.1 (2026-08-25)

## 0.1.0 (2026-08-21)

### Feat

- improve visualization of app and infra metrics
- track po file from po retrieval step instead of from download step
- track po processing by execution
- extract and consolidation using one llm call
- export to cedl
- make allowed extensions configurable per project
- prepare release
- add step function trigger and prepare-release workflows
- add step function trigger and prepare-release workflows
- add workflow to trigger step function from GitHub Actions
- add workflow to trigger step function from GitHub Actions
- add workflow to trigger step function from GitHub Actions
- add workflow to trigger step function from GitHub Actions
- add workflow to trigger step function from GitHub Actions
- add workflow to trigger step function from GitHub Actions
- add workflow to trigger step function from GitHub Actions
- consolidation by merge
- update model to sonnet
- extract data from po file
- get ocr status
- start ocr on po file
- copy files from coupa per PO
- retrieve po to process (#14)
- init procurement file processing
- init procurement processing tracking

### Fix

- add default variable
- jfrog token access
- security improvement
- s3 policy cycle loop with lambda roles
- change s3 module
- namming convention
- merge errors
- naming issues
- correct naming issues (#6)
- missing sbx env

### Refactor

- remove dead code
- align statuses with spec
- remove unused statuses
- externalize ssm max_age
- standardization of SSM usage
- use datetime instead of str, exclude duplicated keys, naming
- force po retrieval and ignore last execution
- use previous and existing po files for consolidation
- use ssm parameter to force the re-execution of PO
- batch updates
- rename procurement to purchase order

### Perf

- decrease wait time and number of polling
