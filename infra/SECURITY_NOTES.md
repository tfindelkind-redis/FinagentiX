# Azure Infrastructure Security Notes

## Current Configuration (Development Phase)

### Azure OpenAI Network Access
**Current State**: Private endpoint only (public access disabled)

**Architecture**:
- Azure OpenAI has `publicNetworkAccess: 'Disabled'`
- Private Endpoint connects to VNet subnet `openai-subnet` (10.0.2.0/24)
- Private DNS Zone `privatelink.openai.azure.com` resolves to private IP
- Container Apps in VNet can access via private endpoint

**For Local Development**:
The agents cannot access Azure OpenAI from your local machine because it's behind a private endpoint.

**Solutions**:

#### Option 1: Enable Public Access with IP Allowlist (Recommended for Dev)
Run the helper script:
```bash
./scripts/enable_openai_dev_access.sh
```

Or manually via Azure CLI:
```bash
# Get your public IP
MY_IP=$(curl -s https://api.ipify.org)

# Enable public access with your IP
az cognitiveservices account update \
    -g finagentix-dev-rg \
    -n openai-<resourceToken> \
    --public-network-access Enabled

az cognitiveservices account network-rule add \
    -g finagentix-dev-rg \
    -n openai-<resourceToken> \
    --ip-address "$MY_IP"
```

#### Option 2: Use IaC Parameters for Development
Deploy with development parameters:
```bash
azd provision --parameters-file infra/main.parameters.dev.json
```

Or set parameters directly:
```bash
azd provision \
    --parameter enableOpenAIPublicAccess=true \
    --parameter openAIAllowedIpAddresses='["YOUR_IP/32"]'
```

#### Option 3: Use Azure Bastion/VPN
- Connect via Azure Bastion to a VM in the VNet
- Use Point-to-Site VPN to access the VNet directly
- Use Express Route for production-grade connectivity

**Modified Files**:
- `infra/stages/stage2-ai-services.bicep` - Added `enablePublicAccess` and `allowedIpAddresses` parameters
- `infra/main.bicep` - Passes new parameters to AI services module
- `infra/main.parameters.json` - Production config (public access disabled)
- `infra/main.parameters.dev.json` - Development config (public access enabled)

### Storage Account Network Access
**Current State**: Public network access enabled with `Allow` default action

**Rationale**:
- Enables data ingestion from local development machines
- Required for Azure CLI/SDK uploads during data collection phase
- Necessary for `scripts/upload_to_azure.py` to function
- Allows rapid prototyping and development workflows

**Modified Files**:
- `infra/stages/stage1a-storage-only.bicep`
- `infra/stages/stage1-data-platform.bicep`

**Settings**:
```bicep
networkAcls: {
  defaultAction: 'Allow'
  bypass: 'AzureServices'
}
publicNetworkAccess: 'Enabled'
```

## Production Security Recommendations

### 1. Restrict Storage Network Access

Once data ingestion is complete and the system is running in production, consider:

#### Option A: IP Allowlist
```bicep
networkAcls: {
  defaultAction: 'Deny'
  bypass: 'AzureServices'
  ipRules: [
    {
      value: 'YOUR_OFFICE_IP/32'
      action: 'Allow'
    }
  ]
}
publicNetworkAccess: 'Enabled'
```

#### Option B: VPN/Private Network Only
```bicep
networkAcls: {
  defaultAction: 'Deny'
  bypass: 'AzureServices'
}
publicNetworkAccess: 'Disabled'
```

### 2. Enable Diagnostic Logging

Add storage account diagnostics:
```bicep
resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'storage-diagnostics'
  scope: storageAccount
  properties: {
    logs: [
      {
        category: 'StorageRead'
        enabled: true
      }
      {
        category: 'StorageWrite'
        enabled: true
      }
      {
        category: 'StorageDelete'
        enabled: true
      }
    ]
    metrics: [
      {
        category: 'Transaction'
        enabled: true
      }
    ]
    workspaceId: logAnalyticsWorkspaceId
  }
}
```

### 3. Enable Soft Delete

Add blob soft delete for data protection:
```bicep
resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 30  // Increase from 7 to 30 days
    }
    containerDeleteRetentionPolicy: {
      enabled: true
      days: 30
    }
  }
}
```

### 4. Enable Azure Defender for Storage

Add threat protection:
```bicep
resource storageDefender 'Microsoft.Security/pricings@2022-03-01' = {
  name: 'StorageAccounts'
  properties: {
    pricingTier: 'Standard'
  }
}
```

### 5. Implement Lifecycle Management

Add automatic data archival:
```bicep
resource lifecyclePolicy 'Microsoft.Storage/storageAccounts/managementPolicies@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          name: 'archive-old-data'
          enabled: true
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: ['blockBlob']
              prefixMatch: ['sec-filings/', 'news-articles/']
            }
            actions: {
              baseBlob: {
                tierToCool: {
                  daysAfterModificationGreaterThan: 90
                }
                tierToArchive: {
                  daysAfterModificationGreaterThan: 180
                }
              }
            }
          }
        }
      ]
    }
  }
}
```

### 6. Use Managed Identities

For container apps and services accessing storage:
```bicep
// Assign Storage Blob Data Contributor role to Container App
resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerApp.id, storageAccount.id, 'Storage Blob Data Contributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: containerApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}
```

### 7. Enable Encryption with Customer-Managed Keys (Optional)

For sensitive data, use your own encryption keys:
```bicep
resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' existing = {
  name: keyVaultName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  // ... other properties
  properties: {
    encryption: {
      services: {
        blob: {
          enabled: true
          keyType: 'Account'
        }
      }
      keySource: 'Microsoft.Keyvault'
      keyvaultproperties: {
        keyname: 'storage-key'
        keyvaulturi: keyVault.properties.vaultUri
      }
    }
  }
}
```

## Monitoring and Alerts

### Recommended Alerts

1. **Unusual Access Patterns**
   - Metric: Failed authentication attempts
   - Threshold: > 10 in 5 minutes

2. **Data Exfiltration**
   - Metric: Egress traffic
   - Threshold: > 10GB in 1 hour

3. **Unauthorized Access Attempts**
   - Metric: 403 errors
   - Threshold: > 50 in 5 minutes

4. **Mass Deletion**
   - Metric: Delete operations
   - Threshold: > 100 in 5 minutes

## Implementation Timeline

### Phase 1: Development (Current)
- ✅ Public network access enabled
- ✅ Basic private endpoints configured
- ✅ HTTPS-only traffic enforced
- ✅ Minimum TLS 1.2

### Phase 2: Staging
- [ ] Add IP allowlists for known dev machines
- [ ] Enable diagnostic logging
- [ ] Configure blob soft delete (30 days)
- [ ] Set up monitoring alerts

### Phase 3: Production
- [ ] Restrict to private network only
- [ ] Enable Azure Defender for Storage
- [ ] Implement lifecycle management policies
- [ ] Use managed identities exclusively
- [ ] Consider customer-managed encryption keys
- [ ] Regular security audits

## Commands for Security Hardening

### Lock down storage after data upload:
```bash
# Disable public network access
az storage account update \
  -n st<RESOURCE_ID> \
  -g finagentix-dev-rg \
  --public-network-access Disabled \
  --default-action Deny

# Enable diagnostic logs
az monitor diagnostic-settings create \
  --name storage-diagnostics \
  --resource /subscriptions/.../storageAccounts/st<RESOURCE_ID> \
  --logs '[{"category": "StorageWrite", "enabled": true}]' \
  --workspace /subscriptions/.../workspaces/...
```

### Check current security settings:
```bash
# View network rules
az storage account show \
  -n st<RESOURCE_ID> \
  -g finagentix-dev-rg \
  --query "{PublicAccess:publicNetworkAccess, DefaultAction:networkRuleSet.defaultAction}"

# List IP rules
az storage account network-rule list \
  --account-name st<RESOURCE_ID> \
  -g finagentix-dev-rg
```

## References

- [Azure Storage Security Guide](https://docs.microsoft.com/azure/storage/common/storage-security-guide)
- [Best Practices for Azure Storage](https://docs.microsoft.com/azure/storage/blobs/security-recommendations)
- [Azure Storage Encryption](https://docs.microsoft.com/azure/storage/common/storage-service-encryption)
- [Azure Private Link](https://docs.microsoft.com/azure/private-link/private-endpoint-overview)
