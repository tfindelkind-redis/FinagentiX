// Stage 1a: Storage Account Only (simplified for debugging)
targetScope = 'resourceGroup'

@description('Primary location for resources')
param location string = resourceGroup().location

@description('Unique resource token')
param resourceToken string

@description('Storage subnet ID from Stage 0')
param storageSubnetId string

@description('Private DNS Zone ID for Storage from Stage 0')
param privateDnsZoneIdStorage string

@description('Virtual Network ID')
param vnetId string

@description('Resource tags')
param tags object = {}

// Storage Account
var storageAccountName = 'st${replace(resourceToken, '-', '')}'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    networkAcls: {
      defaultAction: 'Deny'
      bypass: 'AzureServices'
    }
    publicNetworkAccess: 'Disabled'
  }
}

// Blob Service
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

// Containers
var containers = [
  'stock-data'
  'news-articles'
  'sec-filings'
  'embeddings'
  'feature-store'
]

resource storageContainers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [
  for container in containers: {
    parent: blobService
    name: container
    properties: {
      publicAccess: 'None'
    }
  }
]

// Private Endpoint for Blob
resource storagePrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: 'pe-${storageAccountName}-blob'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: storageSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: 'storage-blob'
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

// Private DNS Zone Group
resource storageDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = {
  parent: storagePrivateEndpoint
  name: 'default'
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
output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
output storageAccountPrimaryEndpoints object = storageAccount.properties.primaryEndpoints
