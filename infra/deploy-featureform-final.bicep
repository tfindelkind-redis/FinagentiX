// Simplified Featureform deployment - uses parameters instead of listKeys()
targetScope = 'resourceGroup'

param location string = resourceGroup().location
param resourceToken string
@secure()
param redisPassword string

// Redis connection details - dynamically built based on region
var redisHost = 'redis-${resourceToken}.${location}.redisenterprise.cache.azure.net'
var redisPort = 10000

// Reference existing Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' existing = {
  name: 'cae-${resourceToken}'
}

// Deploy Featureform Container App (using Redis for both metadata and online store)
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
      ]
    }
    template: {
      containers: [
        {
          name: 'featureform'
          image: 'featureformcom/featureform:latest'
          env: [
            // Use Redis for metadata store (database 2)
            {
              name: 'METADATA_BACKEND'
              value: 'redis'
            }
            {
              name: 'METADATA_REDIS_HOST'
              value: redisHost
            }
            {
              name: 'METADATA_REDIS_PORT'
              value: string(redisPort)
            }
            {
              name: 'METADATA_REDIS_PASSWORD'
              secretRef: 'redis-password'
            }
            {
              name: 'METADATA_REDIS_DB'
              value: '2'
            }
            {
              name: 'METADATA_REDIS_SSL'
              value: 'true'
            }
            // Online store Redis (database 0)
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
output containerAppsEnvironmentId string = containerAppsEnvironment.id
