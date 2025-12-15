// Stage 5: Web Frontend - React SPA served via Nginx in Azure Container Apps
// Deploys the Vite-built frontend as a public-facing Container App

targetScope = 'resourceGroup'

@description('Environment name')
param environmentName string

@description('Primary location for resources')
param location string = resourceGroup().location

@description('Unique resource token shared across stages')
@minLength(5)
param resourceToken string

@description('Resource tags')
param tags object = {}

@description('Container Apps environment resource ID')
param containerAppsEnvironmentId string

@description('Container registry name hosting the frontend image')
@minLength(5)
param containerRegistryName string

@description('Container registry login server (e.g. myacr.azurecr.io)')
param containerRegistryLoginServer string

@description('Application Insights connection string')
@secure()
param applicationInsightsConnectionString string

@description('Public API base URL (https://...) used for routing traffic from the SPA')
param apiBaseUrl string

var containerAppsEnvironmentName = last(split(containerAppsEnvironmentId, '/'))
var frontendAppName = 'ca-frontend-${resourceToken}'

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' existing = {
  name: containerAppsEnvironmentName
}

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: containerRegistryName
}

resource frontendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: frontendAppName
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 80
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
          server: containerRegistryLoginServer
          username: containerRegistry.name
          passwordSecretRef: 'registry-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${containerRegistryLoginServer}/finagentix/frontend:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'ENVIRONMENT'
              value: environmentName
            }
            {
              name: 'PUBLIC_API_BASE_URL'
              value: apiBaseUrl
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              secretRef: 'appinsights-connection-string'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

output frontendAppId string = frontendApp.id
output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output frontendFqdn string = frontendApp.properties.configuration.ingress.fqdn
