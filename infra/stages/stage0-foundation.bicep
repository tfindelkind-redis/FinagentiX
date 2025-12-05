// Stage 0: Foundation - Networking and Shared Resources
targetScope = 'resourceGroup'

@description('Environment name')
param environmentName string

@description('Primary location for resources')
param location string = resourceGroup().location

@description('Unique resource token')
param resourceToken string

@description('Resource tags')
param tags object = {}

// Virtual Network Configuration
var vnetName = 'vnet-${resourceToken}'
var addressPrefix = '10.0.0.0/16'

var subnets = [
  {
    name: 'redis-subnet'
    addressPrefix: '10.0.1.0/24'
    privateEndpointNetworkPolicies: 'Disabled'
  }
  {
    name: 'openai-subnet'
    addressPrefix: '10.0.2.0/24'
    privateEndpointNetworkPolicies: 'Disabled'
  }
  {
    name: 'storage-subnet'
    addressPrefix: '10.0.3.0/24'
    privateEndpointNetworkPolicies: 'Disabled'
  }
  {
    name: 'container-apps-subnet'
    addressPrefix: '10.0.4.0/23'
    delegations: [
      {
        name: 'Microsoft.App/environments'
        properties: {
          serviceName: 'Microsoft.App/environments'
        }
      }
    ]
  }
]

// Virtual Network
resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        addressPrefix
      ]
    }
    subnets: [for subnet in subnets: {
      name: subnet.name
      properties: {
        addressPrefix: subnet.addressPrefix
        privateEndpointNetworkPolicies: subnet.?privateEndpointNetworkPolicies ?? 'Enabled'
        delegations: subnet.?delegations ?? []
      }
    }]
  }
}

// Network Security Group for Container Apps
resource nsgContainerApps 'Microsoft.Network/networkSecurityGroups@2023-05-01' = {
  name: 'nsg-container-apps-${resourceToken}'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'AllowHttpsInbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
        }
      }
    ]
  }
}

// Private DNS Zones
resource privateDnsZoneRedis 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.redisenterprise.cache.azure.net'
  location: 'global'
  tags: tags
}

resource privateDnsZoneOpenAI 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.openai.azure.com'
  location: 'global'
  tags: tags
}

resource privateDnsZoneStorage 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.blob.${environment().suffixes.storage}'
  location: 'global'
  tags: tags
}

// Link Private DNS Zones to VNet
resource vnetLinkRedis 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZoneRedis
  name: '${vnetName}-redis-link'
  location: 'global'
  properties: {
    virtualNetwork: {
      id: vnet.id
    }
    registrationEnabled: false
  }
}

resource vnetLinkOpenAI 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZoneOpenAI
  name: '${vnetName}-openai-link'
  location: 'global'
  properties: {
    virtualNetwork: {
      id: vnet.id
    }
    registrationEnabled: false
  }
}

resource vnetLinkStorage 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZoneStorage
  name: '${vnetName}-storage-link'
  location: 'global'
  properties: {
    virtualNetwork: {
      id: vnet.id
    }
    registrationEnabled: false
  }
}

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: 'log-${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
  }
}

// Application Insights
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${resourceToken}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    RetentionInDays: 30
  }
}

// Outputs
output vnetId string = vnet.id
output vnetName string = vnet.name

output redisSubnetId string = vnet.properties.subnets[0].id
output openaiSubnetId string = vnet.properties.subnets[1].id
output storageSubnetId string = vnet.properties.subnets[2].id
output containerAppsSubnetId string = vnet.properties.subnets[3].id

output privateDnsZoneIdRedis string = privateDnsZoneRedis.id
output privateDnsZoneIdOpenAI string = privateDnsZoneOpenAI.id
output privateDnsZoneIdStorage string = privateDnsZoneStorage.id

output logAnalyticsWorkspaceId string = logAnalytics.id
output logAnalyticsWorkspaceName string = logAnalytics.name
output applicationInsightsId string = applicationInsights.id
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
output applicationInsightsInstrumentationKey string = applicationInsights.properties.InstrumentationKey
