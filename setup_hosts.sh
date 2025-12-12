#!/bin/bash
# Setup /etc/hosts entry for Azure OpenAI tunneling
# This allows SSL to work correctly through the SSH tunnel

echo "This script will add an entry to /etc/hosts"
echo "Entry: 127.0.0.1 openai-545d8fdb508d4.openai.azure.com"
echo ""
echo "This requires sudo password."
echo ""

# Check if entry already exists
if grep -q "openai-545d8fdb508d4.openai.azure.com" /etc/hosts 2>/dev/null; then
    echo "✅ Entry already exists in /etc/hosts"
else
    echo "Adding entry to /etc/hosts..."
    echo "127.0.0.1 openai-545d8fdb508d4.openai.azure.com" | sudo tee -a /etc/hosts
    echo "✅ Added hosts entry"
fi

echo ""
echo "Now restart the SSH tunnel on port 443:"
echo "  sudo ssh -f -L 443:openai-545d8fdb508d4.openai.azure.com:443 -N azureuser@4.227.91.227"
