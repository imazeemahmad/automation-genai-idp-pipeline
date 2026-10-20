# AWS Systems Manager (SSM) Modules

This folder contains Terraform modules for AWS Systems Manager resources.

## Available Modules

- **[ssm_parameter](./ssm_parameter/)** - AWS Systems Manager Parameter Store for configuration management

## the organisation Policy: When to Use SSM vs Secrets Manager

> **Reference:** [AWS Service - Secrets Manager](https://example.atlassian.net/wiki/)

According to the organisation policies:

| Data Type | Storage |
|-----------|---------|
| **Sensitive data** (API keys, passwords, credentials) | **Secrets Manager** |
| **Non-sensitive settings** (configuration, feature flags) | **SSM Parameter Store** |

### Use SSM Parameter Store when:
- Storing **non-sensitive** application configuration
- Storing hierarchical configuration data
- Feature flags and runtime settings
- Environment-specific configuration
- Cost is a concern (Standard tier is free)

### Use Secrets Manager when:
- Storing **sensitive data** (API keys, passwords, tokens)
- Database credentials requiring automatic rotation
- Credentials needing cross-region replication
- Data requiring resource-based access policies

> [!NOTE]
> **Why Secrets Manager for sensitive data?** Both SSM SecureString and Secrets Manager use identical KMS encryption. The difference is **access control**:
> - **Secrets Manager**: Supports resource-based policies (Deny by default - only specific roles can access)
> - **SSM Parameter Store**: IAM-only access control (no resource-level Deny policies)
>
> For sensitive credentials, Secrets Manager provides an additional security layer that SSM cannot offer.

## Key Differences

| Feature | SSM Parameter Store | Secrets Manager |
|---------|---------------------|-----------------|
| **Primary Use** | Configuration & secrets | Secrets only |
| **Automatic Rotation** | No (manual only) | Yes (built-in) |
| **Resource Policies** | No | Yes |
| **Cost** | Free (Standard), $0.05/param (Advanced) | $0.40/secret/month + API calls |
| **Max Size** | 4KB (Standard), 8KB (Advanced) | 64KB |
| **Versioning** | Yes | Yes |
| **Cross-Region Replication** | No | Yes |

## Best Practices

1. **Use hierarchical naming**: `/app-name/env/component/setting`
2. **Use SecureString for sensitive data** with custom KMS keys
3. **Tag consistently** with CE_* tags for governance
4. **Use ignore_value_changes** for runtime-managed parameters
5. **Implement least-privilege IAM policies** for parameter access

### When to use

- ✅ Configuration values
- ✅ Lower cost (Standard is free)
- ✅ Need hierarchical naming
- ✅ Integration with Systems Manager features