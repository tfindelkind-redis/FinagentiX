// Main Bicep orchestrator - Deploys all stages
targetScope = 'subscription'

@description('Environment name (dev, staging, prod)')
@minLength(1)
@maxLength(64)
param environmentName string

@description('Primary Azure region for resources')
param location string = deployment().location

@description('Resource naming prefix')
param prefix string = 'finagentix'

@description('Tags to apply to all resources')
param tags object = {
  environment: environmentName
  project: 'FinagentiX'
  managedBy: 'azd'
  owner: 'Thomas Findelkind'
}

@description('Redis SKU (E5 for dev, E10 for prod)')
@allowed(['Enterprise_E5', 'Enterprise_E10', 'Enterprise_E20'])
param redisSku string = 'Enterprise_E5'

@description('Deploy all stages or specific stages')
@allowed(['all', 'foundation', 'data-platform', 'ai-services', 'data-ingestion', 'agent-runtime'])
param deployStage string = 'all'

// Generate unique suffix for globally unique resource names
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var resourceGroupName = '${prefix}-${environmentName}-rg'

// Create resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// Stage 0: Foundation (Networking & Monitoring)
module foundation './stages/stage0-foundation.bicep' = if (deployStage == 'all' || deployStage == 'foundation') {
  scope: rg
  name: 'foundation-${resourceToken}'
  params: {
    environmentName: environmentName
    location: location
    resourceToken: resourceToken
    tags: tags
  }
}

// Stage 1: Data Platform (Redis + Storage)
module dataPlatform './stages/stage1-data-platform.bicep' = if (deployStage == 'all' || deployStage == 'data-platform') {
  scope: rg
  name: 'data-platform-${resourceToken}'
  params: {
    environmentName: environmentName
    location: location
    resourceToken: resourceToken
    tags: tags
    redisSku: redisSku
    vnetId: foundation.outputs.vnetId
    redisSubnetId: foundation.outputs.redisSubnetId
    storageSubnetId: foundation.outputs.storageSubnetId
    privateDnsZoneIdRedis: foundation.outputs.privateDnsZoneIdRedis
    privateDnsZoneIdStorage: foundation.outputs.privateDnsZoneIdStorage
  }
  dependsOn: [
    foundation
  ]
}

// Stage 2: AI Services (Azure OpenAI)
module aiServices './stages/stage2-ai-services.bicep' = if (deployStage == 'all' || deployStage == 'ai-services') {
  scope: rg
  name: 'ai-services-${resourceToken}'
  params: {
    environmentName: environmentName
    location: location
    resourceToken: resourceToken
    tags: tags
    vnetId: foundation.outputs.vnetId
    openaiSubnetId: foundation.outputs.openaiSubnetId
    privateDnsZoneIdOpenAI: foundation.outputs.privateDnsZoneIdOpenAI
  }
  dependsOn: [
    foundation
  ]
}

// Stage 3: Data Ingestion (Container App for batch load)
module dataIngestion './stages/stage3-data-ingestion.bicep' = if (deployStage == 'all' || deployStage == 'data-ingestion') {
  scope: rg
  name: 'data-ingestion-${resourceToken}'
  params: {
    environmentName: environmentName
    location: location
    resourceToken: resourceToken
    tags: tags
    containerAppsSubnetId: foundation.outputs.containerAppsSubnetId
    logAnalyticsWorkspaceId: foundation.outputs.logAnalyticsWorkspaceId
    applicationInsightsConnectionString: foundation.outputs.applicationInsightsConnectionString
    redisHost: dataPlatform.outputs.redisHost
    redisPort: dataPlatform.outputs.redisPort
    redisPassword: dataPlatform.outputs.redisPassword
    storageAccountName: dataPlatform.outputs.storageAccountName
    openaiEndpoint: aiServices.outputs.openaiEndpoint
    openaiKey: aiServices.outputs.openaiKey
  }
  dependsOn: [
    foundation
    dataPlatform
    aiServices
  ]
}

// Stage 4: Agent Runtime (Container App for agents/API)
module agentRuntime './stages/stage4-agent-runtime.bicep' = if (deployStage == 'all' || deployStage == 'agent-runtime') {
  scope: rg
  name: 'agent-runtime-${resourceToken}'
  params: {
    environmentName: environmentName
    location: location
    resourceToken: resourceToken
    tags: tags
    containerAppsSubnetId: foundation.outputs.containerAppsSubnetId
    logAnalyticsWorkspaceId: foundation.outputs.logAnalyticsWorkspaceId
    applicationInsightsConnectionString: foundation.outputs.applicationInsightsConnectionString
    redisHost: dataPlatform.outputs.redisHost
    redisPort: dataPlatform.outputs.redisPort
    redisPassword: dataPlatform.outputs.redisPassword
    openaiEndpoint: aiServices.outputs.openaiEndpoint
    openaiKey: aiServices.outputs.openaiKey
  }
  dependsOn: [
    foundation
    dataPlatform
    aiServices
  ]
}

// Outputs for azd environment variables
output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = resourceGroupName

// Stage 0 outputs
output VNET_ID string = foundation.outputs.vnetId
output LOG_ANALYTICS_WORKSPACE_ID string = foundation.outputs.logAnalyticsWorkspaceId

// Stage 1 outputs
output REDIS_HOST string = dataPlatform.outputs.redisHost
output REDIS_PORT int = dataPlatform.outputs.redisPort
output REDIS_PASSWORD string = dataPlatform.outputs.redisPassword
output STORAGE_ACCOUNT_NAME string = dataPlatform.outputs.storageAccountName
output STORAGE_CONNECTION_STRING string = dataPlatform.outputs.storageConnectionString

// Stage 2 outputs
output AZURE_OPENAI_ENDPOINT string = aiServices.outputs.openaiEndpoint
output AZURE_OPENAI_KEY string = aiServices.outputs.openaiKey
output AZURE_OPENAI_GPT4_DEPLOYMENT string = aiServices.outputs.gpt4DeploymentName
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = aiServices.outputs.embeddingDeploymentName

// Stage 3 outputs
output DATA_INGESTION_URL string = dataIngestion.outputs.ingestionUrl

// Stage 4 outputs
output AGENT_API_URL string = agentRuntime.outputs.agentApiUrl
