<!--
Thanks for contributing to the Procurement Data Booster.
Before you submit:
- Keep the PR focused on one logical change.
- Target the correct base branch (feature/fix/chore/ci -> develop; promotion -> uat/main via release/*).
- Use Conventional Commits; the PR will be merged.
-->

## Description

<!-- What does this PR do and why? -->

## Linked issues

<!-- Fixes #123 / Relates to JIRA-456 -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Infrastructure / Terraform
- [ ] CI / pipeline
- [ ] Documentation

## Testing

<!-- How was this tested? Unit tests, integration tests, sandbox deploy, terraform plan output... -->

- [ ] Unit tests added/updated (`pytest app_src/tests/unit/`)
- [ ] `terraform plan` reviewed (for infra changes)

## Governance checklist

- [ ] No secrets or credentials in the code
- [ ] `permissions:` in any new/updated workflow are least-privilege (no `write-all`/`read-all`)
- [ ] Terraform outputs added for any new resource (see `app_terraform/outputs.tf`)
- [ ] Compliance impact assessed (GxP, SOX, SaMD — if applicable)
- [ ] Documentation updated if behaviour changed
