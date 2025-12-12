#!/bin/bash
# SSH Tunnel to Azure OpenAI through Debug VM
# This creates a SOCKS proxy that routes traffic through the Azure VNet

set -e

VM_IP="4.227.91.227"
VM_USER="azureuser"
LOCAL_PORT=8888

echo "🔐 Setting up SSH tunnel to Azure..."
echo "VM: ${VM_USER}@${VM_IP}"
echo "Local SOCKS proxy: localhost:${LOCAL_PORT}"
echo ""
echo "This will create a SOCKS proxy that you can use to access Azure resources."
echo "Press Ctrl+C to stop the tunnel."
echo ""

# Create SSH tunnel with SOCKS proxy
# -D: Dynamic port forwarding (SOCKS proxy)
# -N: Don't execute remote command
# -v: Verbose (optional, remove for less output)
ssh -D ${LOCAL_PORT} -N ${VM_USER}@${VM_IP}
