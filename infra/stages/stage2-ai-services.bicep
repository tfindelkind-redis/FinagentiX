// Stage 2: AI Services - Azure OpenAI
targetScope = 'resourceGroup'

@description('Environment name')
param environmentName string

@description('Primary location for resources')
param location string = resourceGroup().location

@description('Unique resource token')
param resourceToken string

@description('Resource tags')
param tags object = {}

@description('VNet ID for private endpoints')
param vnetId string

@description('OpenAI subnet ID')
param openaiSubnetId string

@description('Private DNS Zone ID for OpenAI')
param privateDnsZoneIdOpenAI string

// Ensure we keep tags consistent and reference virtual network
var mergedTags = union(tags, {
  environment: environmentName
})

var vnetName = last(split(vnetId, '/'))
var subnetName = last(split(openaiSubnetId, '/'))

resource openaiVnet 'Microsoft.Network/virtualNetworks@2023-05-01' existing = {
  name: vnetName
}

resource openaiSubnet 'Microsoft.Network/virtualNetworks/subnets@2023-05-01' existing = {
  parent: openaiVnet
  name: subnetName
}

// Azure OpenAI Service
resource openai 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: 'openai-${resourceToken}'
  location: location
  tags: mergedTags
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: 'openai-${resourceToken}'
    publicNetworkAccess: 'Disabled'
    networkAcls: {
      defaultAction: 'Deny'
      ipRules: []
      virtualNetworkRules: []
    }
  }
}

// GPT-4o Deployment
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openai
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
  }
}

// Text Embedding Deployment
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openai
  name: 'text-embedding-3-large'
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: '1'
    }
  }
  dependsOn: [
    gpt4oDeployment
  ]
}

// Private Endpoint for OpenAI
resource openaiPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: 'pe-openai-${resourceToken}'
  location: location
  tags: mergedTags
  properties: {
    subnet: {
      id: openaiSubnet.id
    }
    privateLinkServiceConnections: [
      {
        name: 'openai-connection'
        properties: {
          privateLinkServiceId: openai.id
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

// Private DNS Zone Group for OpenAI
resource openaiDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = {
  parent: openaiPrivateEndpoint
  name: 'openai-dns-zone-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'config1'
        properties: {
          privateDnsZoneId: privateDnsZoneIdOpenAI
        }
      }
    ]
  }
}

// Outputs
output openaiId string = openai.id
output openaiName string = openai.name
output openaiEndpoint string = openai.properties.endpoint
@secure()
output openaiKey string = openai.listKeys().key1
output gpt4DeploymentName string = gpt4oDeployment.name
output embeddingDeploymentName string = embeddingDeployment.name
