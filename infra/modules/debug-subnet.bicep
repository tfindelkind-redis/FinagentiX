// Debug Subnet for Container Instances
// Separate from Container Apps subnet which is delegated

param vnetName string

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' existing = {
  name: vnetName
}

resource debugSubnet 'Microsoft.Network/virtualNetworks/subnets@2023-05-01' = {
  parent: vnet
  name: 'debug-subnet'
  properties: {
    addressPrefix: '10.0.6.0/28'  // Small subnet, 16 IPs (11 usable)
    serviceEndpoints: []
    delegations: [
      {
        name: 'Microsoft.ContainerInstance/containerGroups'
        properties: {
          serviceName: 'Microsoft.ContainerInstance/containerGroups'
        }
      }
    ]
  }
}

output subnetId string = debugSubnet.id
output subnetName string = debugSubnet.name
