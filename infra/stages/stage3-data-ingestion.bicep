// Stage 3: Data Ingestion - Container App for batch data load
targetScope = 'resourceGroup'

@description('Environment name')
param environmentName string

@description('Primary location for resources')
param location string = resourceGroup().location

@description('Unique resource token')
param resourceToken string

@description('Resource tags')
param tags object = {}

@description('Container Apps subnet ID')
param containerAppsSubnetId string

@description('Log Analytics Workspace ID')
param logAnalyticsWorkspaceId string

@description('Application Insights Connection String')
@secure()
param applicationInsightsConnectionString string

@description('Redis host')
param redisHost string

@description('Redis port')
param redisPort int

@description('Redis password')
@secure()
param redisPassword string

@description('Storage Account name')
param storageAccountName string

@description('OpenAI endpoint')
param openaiEndpoint string

@description('OpenAI key')
@secure()
param openaiKey string

// Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'acr${resourceToken}'
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
}

// Container Apps Environment
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'cae-${resourceToken}'
  location: location
  tags: tags
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: containerAppsSubnetId
    }
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey
      }
    }
  }
}

// Data Ingestion Container App
resource dataIngestionApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-data-ingestion-${resourceToken}'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: [
        {
          name: 'redis-password'
          value: redisPassword
        }
        {
          name: 'openai-key'
          value: openaiKey
        }
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
        {
          name: 'appinsights-connection-string'
          value: applicationInsightsConnectionString
        }
      ]
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.name
          passwordSecretRef: 'registry-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'data-ingestion'
          image: '${containerRegistry.properties.loginServer}/finagentix/data-ingestion:latest'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
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
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: openaiEndpoint
            }
            {
              name: 'AZURE_OPENAI_KEY'
              secretRef: 'openai-key'
            }
            {
              name: 'AZURE_STORAGE_ACCOUNT_NAME'
              value: storageAccountName
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              secretRef: 'appinsights-connection-string'
            }
            {
              name: 'ENVIRONMENT'
              value: environmentName
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

// Outputs
output containerRegistryId string = containerRegistry.id
output containerRegistryName string = containerRegistry.name
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
@secure()
output containerRegistryPassword string = containerRegistry.listCredentials().passwords[0].value

output containerAppsEnvironmentId string = containerAppsEnvironment.id
output dataIngestionAppId string = dataIngestionApp.id
output ingestionUrl string = 'https://${dataIngestionApp.properties.configuration.ingress.fqdn}'
