// Standalone Featureform deployment - references existing infrastructure
targetScope = 'resourceGroup'

param location string = resourceGroup().location
param resourceToken string

// Reference existing Redis
resource redisCluster 'Microsoft.Cache/redisEnterprise@2024-03-01-preview' existing = {
  name: 'redis-${resourceToken}'
}

resource redisDatabase 'Microsoft.Cache/redisEnterprise/databases@2024-03-01-preview' existing = {
  parent: redisCluster
  name: 'default'
}

// Get Redis connection details
var redisHost = '${redisCluster.properties.hostName}'
var redisPort = 10000
var redisPassword = redisDatabase.listKeys().primaryKey

// Create Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'acr${replace(resourceToken, '-', '')}'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
}

// Reference existing Log Analytics
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = {
  name: 'log-${resourceToken}'
}

// Reference existing VNet and subnet
resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' existing = {
  name: 'vnet-${resourceToken}'
}

resource containerAppsSubnet 'Microsoft.Network/virtualNetworks/subnets@2023-05-01' existing = {
  parent: vnet
  name: 'container-apps-subnet'
}

// Create Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'cae-${resourceToken}'
  location: location
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: containerAppsSubnet.id
    }
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// Create Postgres for Featureform metadata
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: 'postgres-ff-${resourceToken}'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '15'
    administratorLogin: 'ffadmin'
    administratorLoginPassword: redisPassword // Reuse Redis password
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

resource postgresFirewallAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  parent: postgresServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresServer
  name: 'featureform'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Deploy Featureform Container App
resource featureformApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'featureform-${resourceToken}'
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 7878
        transport: 'http2'
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      secrets: [
        {
          name: 'redis-password'
          value: redisPassword
        }
        {
          name: 'postgres-password'
          value: redisPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'featureform'
          image: 'featureformcom/featureform:latest'
          env: [
            {
              name: 'POSTGRES_HOST'
              value: postgresServer.properties.fullyQualifiedDomainName
            }
            {
              name: 'POSTGRES_PORT'
              value: '5432'
            }
            {
              name: 'POSTGRES_DB'
              value: 'featureform'
            }
            {
              name: 'POSTGRES_USER'
              value: 'ffadmin'
            }
            {
              name: 'POSTGRES_PASSWORD'
              secretRef: 'postgres-password'
            }
            {
              name: 'REDIS_HOST'
              value: redisHost
            }
            {
              name: 'REDIS_PORT'
              value: string(redisPort)
            }
            {
              name: 'REDIS_PASSWORD'
              secretRef: 'redis-password'
            }
            {
              name: 'REDIS_SSL'
              value: 'true'
            }
          ]
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// Outputs
output featureformUrl string = 'https://${featureformApp.properties.configuration.ingress.fqdn}'
output featureformHost string = featureformApp.properties.configuration.ingress.fqdn
output postgresHost string = postgresServer.properties.fullyQualifiedDomainName
output containerAppsEnvironmentId string = containerAppsEnvironment.id
output containerRegistryName string = containerRegistry.name
