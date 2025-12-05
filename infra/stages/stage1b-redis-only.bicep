// Stage 1b: Azure Managed Redis Only
targetScope = 'resourceGroup'

@description('Primary location for resources')
param location string = resourceGroup().location

@description('Unique resource token')
param resourceToken string

@description('Redis SKU')
@allowed(['Enterprise_E5', 'Enterprise_E10', 'Enterprise_E20'])
param redisSku string = 'Enterprise_E5'

@description('Redis subnet ID from Stage 0')
param redisSubnetId string

@description('Private DNS Zone ID for Redis from Stage 0')
param privateDnsZoneIdRedis string

@description('Resource tags')
param tags object = {}

// Redis Enterprise Cluster
var redisClusterName = 'redis-${resourceToken}'

resource redisCluster 'Microsoft.Cache/redisEnterprise@2023-11-01' = {
  name: redisClusterName
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

// Redis Database with modules
resource redisDatabase 'Microsoft.Cache/redisEnterprise/databases@2023-11-01' = {
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
        args: ''
      }
      {
        name: 'RedisJSON'
        args: ''
      }
      {
        name: 'RedisTimeSeries'
        args: ''
      }
      {
        name: 'RedisBloom'
        args: ''
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
