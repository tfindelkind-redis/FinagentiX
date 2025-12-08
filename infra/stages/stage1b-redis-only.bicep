// Stage 1b: Azure Managed Redis Only
targetScope = 'resourceGroup'

@description('Primary location for resources')
param location string = resourceGroup().location

@description('Unique resource token')
param resourceToken string

@description('Redis SKU for Azure Managed Redis')
@allowed(['Balanced_B1', 'Balanced_B5', 'Balanced_B10', 'MemoryOptimized_M1', 'MemoryOptimized_M5', 'ComputeOptimized_C1'])
param redisSku string = 'Balanced_B5'

@description('Redis subnet ID from Stage 0')
param redisSubnetId string

@description('Private DNS Zone ID for Redis from Stage 0')
param privateDnsZoneIdRedis string

@description('Resource tags')
param tags object = {}

// Azure Managed Redis Cluster
var redisClusterName = 'redis-${resourceToken}'

resource redisCluster 'Microsoft.Cache/redisEnterprise@2024-09-01-preview' = {
  name: redisClusterName
  location: location
  tags: tags
  sku: {
    name: redisSku
  }
  properties: {
    minimumTlsVersion: '1.2'
  }
}

// Redis Database with modules (Azure Managed Redis includes RediSearch, RedisJSON, RedisTimeSeries, RedisBloom by default)
resource redisDatabase 'Microsoft.Cache/redisEnterprise/databases@2024-09-01-preview' = {
  parent: redisCluster
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
  name: 'pe-${redisClusterName}'
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
          privateLinkServiceId: redisCluster.id
          groupIds: [
            'redisEnterprise'
          ]
        }
      }
    ]
  }
}

// Private DNS Zone Group
resource redisDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = {
  parent: redisPrivateEndpoint
  name: 'default'
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

// Outputs
output redisClusterId string = redisCluster.id
output redisClusterName string = redisCluster.name
output redisDatabaseId string = redisDatabase.id
output redisHostName string = redisCluster.properties.hostName
output redisPort int = redisDatabase.properties.port
