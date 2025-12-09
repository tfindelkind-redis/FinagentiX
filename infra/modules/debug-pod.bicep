// Debug Pod - Lightweight container for VNet access and debugging
// This provides a way to access internal resources like Featureform, Redis, etc.

targetScope = 'resourceGroup'

param location string = resourceGroup().location
param resourceToken string
param subnetId string

// Debug pod configuration
resource debugPod 'Microsoft.ContainerInstance/containerGroups@2023-05-01' = {
  name: 'debug-pod-${resourceToken}'
  location: location
  properties: {
    containers: [
      {
        name: 'debug'
        properties: {
          image: 'mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04:latest'
          command: [
            '/bin/bash'
            '-c'
            '''
            set -e
            echo "Installing packages..."
            apt-get update -qq && apt-get install -y -qq openssh-server curl redis-tools dnsutils iputils-ping vim nano git jq
            
            echo "Installing Python packages..."
            pip install --no-cache-dir featureform redis python-dotenv requests azure-identity
            
            echo "Configuring SSH..."
            mkdir -p /run/sshd /root/.ssh
            echo "root:debugpod2024" | chpasswd
            sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
            sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
            
            echo "Starting SSH server..."
            /usr/sbin/sshd -D
            '''
          ]
          ports: [
            {
              port: 22
              protocol: 'TCP'
            }
          ]
          resources: {
            requests: {
              cpu: 1
              memoryInGB: 2
            }
          }
          environmentVariables: [
            {
              name: 'FEATUREFORM_HOST'
              value: 'featureform-${resourceToken}.internal.azurecontainerapps.io'
            }
            {
              name: 'REDIS_HOST'
              value: 'redis-${resourceToken}.${location}.redisenterprise.cache.azure.net'
            }
            {
              name: 'REDIS_PORT'
              value: '10000'
            }
            {
              name: 'PYTHONUNBUFFERED'
              value: '1'
            }
          ]
        }
      }
    ]
    osType: 'Linux'
    restartPolicy: 'Always'
    ipAddress: {
      type: 'Private'
      ports: [
        {
          port: 22
          protocol: 'TCP'
        }
      ]
    }
    subnetIds: [
      {
        id: subnetId
      }
    ]
  }
  tags: {
    purpose: 'debugging'
    environment: 'dev'
  }
}

output containerGroupName string = debugPod.name
output privateIp string = debugPod.properties.ipAddress.ip
output execCommand string = 'az container exec -g ${resourceGroup().name} -n ${debugPod.name} --exec-command /bin/bash'
