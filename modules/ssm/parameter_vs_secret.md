# SSM Parameter Store vs Secrets Manager

> **the organisation Policy Reference:** [AWS Service - Secrets Manager](https://example.atlassian.net/wiki/)

## the organisation Policy Summary

| Data Type | Required Storage | Reason |
|-----------|------------------|--------|
| **Sensitive data** (API keys, passwords) | **Secrets Manager** | Resource-based policies required |
| **Non-sensitive settings** (config, flags) | **SSM Parameter Store** | Cost-effective, hierarchical |

## Quick Comparison

| Feature | Secrets Manager | SSM Parameter Store |
|---------|----------------|---------------------|
| **KMS Encryption** | ✅ Yes (AES-256) | ✅ Yes (AES-256) |
| **Custom KMS Key** | ✅ Yes | ✅ Yes |
| **Resource Policies** | ✅ Yes (Deny by default) | ❌ No |
| **Access Control Layers** | 2 (IAM + Resource) | 1 (IAM only) |
| **Automatic Rotation** | ✅ Yes | ❌ No |
| **Initial Value** | Optional (can be empty) | **Required** (use placeholder) |
| **Access Control Output** | `allowed_role_arns` → resource policy | `allowed_role_arns` → IAM policy output |
| **External Management** | Omit `secret_string` | `ignore_value_changes = true` |

## Encryption: Technically Identical

Both services use **identical KMS encryption**:
- Same AES-256 encryption algorithm
- Same KMS key management
- Same encryption at rest and in transit

**The encryption is NOT the security difference.**

## Access Control: The Real Difference

### Secrets Manager (2 layers of defense)
```
Request → IAM Policy → Resource Policy → Access
                            ↓
                   Can DENY everyone except specific roles
```

### SSM Parameter Store (1 layer)
```
Request → IAM Policy → Access
              ↓
     Can only ALLOW (no resource-level Deny)
```

### Why This Matters

| Attack Scenario | SSM | Secrets Manager |
|-----------------|-----|-----------------|
| Compromised admin role | ❌ Can read all parameters | ✅ Resource policy blocks access |
| Overly permissive IAM | ❌ Exposes data | ✅ Resource policy is last defense |
| Lateral movement | ❌ Broader exposure | ✅ Contained by resource policy |

---

## Pattern Comparison

### Secrets Manager (Your MWAA Pattern)

```terraform
module "secrets" {
  source  = "registry.example.com/.../secrets_manager_secret/aws"
  version = "0.0.0-latest"

  secret_name   = "airflow/variables/..."
  secret_string = "REPLACE_ME"  # Placeholder

  allowed_role_arns = [
    "arn:aws:iam::123:role/mwaa-execution",
    "arn:aws:iam::123:role/cicd-deployer"
  ]
  # ↑ Creates resource-based policy automatically
}
```

**Access Control:** Automatic via resource policy

---

### SSM Parameter Store (New Module)

```terraform
module "parameters" {
  source  = "registry.example.com/.../ssm_parameter/aws"
  version = "0.0.0-latest"

  parameter_name  = "/airflow/config/..."
  parameter_value = "PLACEHOLDER"  # Required initial value
  parameter_type  = "SecureString"

  ignore_value_changes = true  # External management

  allowed_role_arns = [
    "arn:aws:iam::123:role/mwaa-execution",
    "arn:aws:iam::123:role/cicd-deployer"
  ]
  # ↑ Generates IAM policy document (you attach it)
}

# You must attach the IAM policy
resource "aws_iam_policy" "param_access" {
  policy = module.parameters.iam_policy_json
}

resource "aws_iam_role_policy_attachment" "attach" {
  role       = "mwaa-execution"
  policy_arn = aws_iam_policy.param_access.arn
}
```

**Access Control:** Manual IAM policy attachment required

---

## Why the Difference?

### Secrets Manager
- **Resource-based policies** are supported
- Module creates policy automatically
- No additional IAM work needed

### SSM Parameter Store
- **No resource-based policies** (AWS limitation)
- Module generates IAM policy as output
- You attach it to roles manually

---

## Migration Path: Secrets → SSM

If you want to convert secrets to parameters:

```terraform
# Before: Secrets Manager
module "secret" {
  source        = ".../secrets_manager_secret/aws"
  secret_string = "REPLACE_ME"
  allowed_role_arns = [...]
}

# After: SSM Parameter
module "parameter" {
  source               = ".../ssm_parameter/aws"
  parameter_value      = "PLACEHOLDER"
  ignore_value_changes = true
  allowed_role_arns    = [...]
}

resource "aws_iam_policy" "access" {
  policy = module.parameter.iam_policy_json
}

resource "aws_iam_role_policy_attachment" "attach" {
  role       = "your-role"
  policy_arn = aws_iam_policy.access.arn
}
```

---

## When to Use Each (the organisation Policy)

### Use Secrets Manager when:
- ✅ **Sensitive data** (API keys, passwords, tokens, credentials)
- ✅ Need automatic rotation
- ✅ Need resource-based policies (the organisation security requirement)
- ✅ Need cross-region replication

### Use SSM Parameter Store when:
- ✅ **Non-sensitive** configuration values
- ✅ Feature flags and runtime settings
- ✅ Environment-specific configuration
- ✅ Hierarchical naming needed
- ✅ Cost optimization (Standard tier is free)

> [!NOTE]
> **Why Secrets Manager for sensitive data?** Both use identical KMS encryption. The difference is access control:
> - Secrets Manager provides **resource-based policies** (can Deny by default)
> - SSM only has IAM-based access control (cannot Deny at resource level)
>
> For defense in depth, Secrets Manager offers an additional security layer that SSM cannot provide.
