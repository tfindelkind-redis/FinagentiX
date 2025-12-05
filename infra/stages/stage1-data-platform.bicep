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

@description('Redis SKU')
@allowed(['Enterprise_E5', 'Enterprise_E10', 'Enterprise_E20'])
param redisSku string = 'Enterprise_E5'

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
resource redisEnterprise 'Microsoft.Cache/redisEnterprise@2023-11-01' = {
  name: 'redis-${resourceToken}'
  location: location
  tags: tags
  sku: {
    name: redisSku
    capacity: 2
  }
  properties: {
    minimumTlsVersion: '1.2'
  }
}

// Redis Database with required modules
resource redisDatabase 'Microsoft.Cache/redisEnterprise/databases@2023-11-01' = {
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
      rdbEnabled: true
      rdbFrequency: '1h'
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
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
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
