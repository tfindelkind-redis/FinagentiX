// Stage 4: Agent Runtime - Container App for agents/API
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

@description('OpenAI endpoint')
param openaiEndpoint string

@description('OpenAI key')
@secure()
param openaiKey string

@description('Azure OpenAI GPT-4 deployment name')
param openaiGpt4Deployment string

@description('Azure OpenAI embedding deployment name')
param openaiEmbeddingDeployment string

@description('Azure OpenAI API version')
param openaiApiVersion string = '2024-08-01-preview'

// Get existing Container Apps Environment (created in Stage 3)
resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' existing = {
  name: 'cae-${resourceToken}'
}

// Get existing Container Registry (created in Stage 3)
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: 'acr${replace(resourceToken, '-', '')}'
}

// Agent API Container App
resource agentApiApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'ca-agent-api-${resourceToken}'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
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
          name: 'agent-api'
          image: '${containerRegistry.properties.loginServer}/finagentix/agent-api:latest'
          resources: {
            cpu: json('2.0')
            memory: '4Gi'
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
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'openai-key'
            }
            {
              name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
              value: openaiGpt4Deployment
            }
            {
              name: 'AZURE_OPENAI_GPT4_DEPLOYMENT'
              value: openaiGpt4Deployment
            }
            {
              name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
              value: openaiEmbeddingDeployment
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: openaiApiVersion
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
        minReplicas: 1
        maxReplicas: 10
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
}

// Outputs
output agentApiAppId string = agentApiApp.id
output agentApiUrl string = 'https://${agentApiApp.properties.configuration.ingress.fqdn}'
output agentApiFqdn string = agentApiApp.properties.configuration.ingress.fqdn
