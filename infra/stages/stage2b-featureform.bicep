// Stage 2b: Featureform Feature Store on Azure Container Apps
// Deploys Featureform server to Azure Container Apps with Redis Enterprise as online store

@description('Environment name (dev, staging, prod)')
param environmentName string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Unique resource token')
param resourceToken string

@description('Virtual Network ID')
param vnetId string

@description('Container Apps subnet ID')
param containerAppsSubnetId string

@description('Redis Enterprise hostname')
param redisHost string

@description('Redis Enterprise port')
param redisPort int = 10000

@description('Redis Enterprise access key')
@secure()
param redisPassword string

@description('Container Apps Environment ID')
param containerAppsEnvironmentId string

// Variables
var featureformAppName = 'featureform-${resourceToken}'
var postgresServerName = 'postgres-ff-${resourceToken}'
var postgresDatabaseName = 'featureform'
var postgresAdminUser = 'ffadmin'

// Reference existing Container Apps Environment (created in Stage 3)
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' existing = {
  name: split(containerAppsEnvironmentId, '/')[8]  // Extract name from resource ID
}

// Featureform requires Postgres for metadata store
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: postgresServerName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '15'
    administratorLogin: postgresAdminUser
    administratorLoginPassword: redisPassword // Reuse Redis password for simplicity
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

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresServer
  name: postgresDatabaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Featureform Container App
resource featureformApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: featureformAppName
  location: location
  tags: {
    environment: environmentName
    service: 'featureform'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 7878
        transport: 'http'
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
      registries: []
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
              value: postgresDatabaseName
            }
            {
              name: 'POSTGRES_USER'
              value: postgresAdminUser
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
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

// Outputs
output featureformUrl string = 'https://${featureformApp.properties.configuration.ingress.fqdn}'
output featureformHost string = featureformApp.properties.configuration.ingress.fqdn
output postgresHost string = postgresServer.properties.fullyQualifiedDomainName
output postgresDatabaseName string = postgresDatabaseName
