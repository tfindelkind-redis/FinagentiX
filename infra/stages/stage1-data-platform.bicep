// Stage 1: Data Platform - Azure Managed Redis + Storage Account
targetScope = 'resourceGroup'

@description('Environment name')
param environmentName string

@description('Primary location for resources')
param location string = resourceGroup().location

@description('Unique resource token')
param resourceToken string

@description('Resource tags')
param tags object = {}

@description('Redis SKU for Azure Managed Redis')
@allowed(['Balanced_B1', 'Balanced_B5', 'Balanced_B10', 'MemoryOptimized_M1', 'MemoryOptimized_M5', 'ComputeOptimized_C1'])
param redisSku string = 'Balanced_B5'

@description('VNet ID for private endpoints')
param vnetId string

@description('Redis subnet ID')
param redisSubnetId string

@description('Storage subnet ID')
param storageSubnetId string

@description('Private DNS Zone ID for Redis')
param privateDnsZoneIdRedis string

@description('Private DNS Zone ID for Storage')
param privateDnsZoneIdStorage string

// Azure Managed Redis
resource redisEnterprise 'Microsoft.Cache/redisEnterprise@2024-09-01-preview' = {
  name: 'redis-${resourceToken}'
  location: location
  tags: tags
  sku: {
    name: redisSku
  }
  properties: {
    minimumTlsVersion: '1.2'
  }
}

// Redis Database with required modules (Azure Managed Redis includes these by default)
resource redisDatabase 'Microsoft.Cache/redisEnterprise/databases@2024-09-01-preview' = {
  parent: redisEnterprise
  name: 'default'
  properties: {
    clientProtocol: 'Encrypted'
    port: 10000
    clusteringPolicy: 'EnterpriseCluster'
    evictionPolicy: 'NoEviction'
    modules: [
      {
        name: 'RediSearch'
      }
      {
        name: 'RedisJSON'
      }
      {
        name: 'RedisTimeSeries'
      }
      {
        name: 'RedisBloom'
      }
    ]
    persistence: {
      aofEnabled: true
      aofFrequency: '1s'
    }
  }
}

// Private Endpoint for Redis
resource redisPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: 'pe-redis-${resourceToken}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: redisSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'redis-connection'
        properties: {
          privateLinkServiceId: redisEnterprise.id
          groupIds: [
            'redisEnterprise'
          ]
        }
      }
    ]
  }
}

// Private DNS Zone Group for Redis
resource redisDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = {
  parent: redisPrivateEndpoint
  name: 'redis-dns-zone-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config1'
        properties: {
          privateDnsZoneId: privateDnsZoneIdRedis
        }
      }
    ]
  }
}

// Storage Account
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: 'st${resourceToken}'
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    networkAcls: {
      defaultAction: 'Allow' // Changed from 'Deny' to allow data ingestion from local machines
      bypass: 'AzureServices'
    }
    publicNetworkAccess: 'Enabled' // Allow uploads via Azure CLI/SDK during development
  }
}

// Blob Services
resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    deleteRetentionPolicy: {
      enabled: true
      days: 7
    }
  }
}

// Storage Containers
resource secFilingsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobServices
  name: 'sec-filings'
  properties: {
    publicAccess: 'None'
  }
}

resource newsArticlesContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobServices
  name: 'news-articles'
  properties: {
    publicAccess: 'None'
  }
}

// Private Endpoint for Storage
resource storagePrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: 'pe-storage-${resourceToken}'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: storageSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'storage-connection'
        properties: {
          privateLinkServiceId: storageAccount.id
          groupIds: [
            'blob'
          ]
        }
      }
    ]
  }
}

// Private DNS Zone Group for Storage
resource storageDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = {
  parent: storagePrivateEndpoint
  name: 'storage-dns-zone-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config1'
        properties: {
          privateDnsZoneId: privateDnsZoneIdStorage
        }
      }
    ]
  }
}

// Outputs
output redisId string = redisEnterprise.id
output redisName string = redisEnterprise.name
output redisHost string = redisEnterprise.properties.hostName
output redisPort int = 10000
@secure()
output redisPassword string = redisDatabase.listKeys().primaryKey

output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
@secure()
output storageConnectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
output secFilingsContainerName string = secFilingsContainer.name
output newsArticlesContainerName string = newsArticlesContainer.name
