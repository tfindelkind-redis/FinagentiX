#!/bin/bash
# Simple SSH Port Forward to Azure OpenAI
# Forwards Azure OpenAI endpoint through the debug VM

set -e

VM_IP="4.227.91.227"
VM_USER="azureuser"
LOCAL_PORT=8443
AZURE_OPENAI_HOST=$(python - <<'PY'
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
if not endpoint:
	raise SystemExit("AZURE_OPENAI_ENDPOINT is not set. Update .env and re-run.")

host = urlparse(endpoint).netloc or endpoint.replace("https://", "").rstrip("/")
if not host:
	raise SystemExit("Unable to derive host from AZURE_OPENAI_ENDPOINT")

print(host)
PY
)
AZURE_OPENAI_PORT=443

echo "🔐 Setting up SSH port forward to Azure OpenAI..."
echo "VM: ${VM_USER}@${VM_IP}"
echo "Forwarding: localhost:${LOCAL_PORT} -> ${AZURE_OPENAI_HOST}:${AZURE_OPENAI_PORT}"
echo ""
echo "⚠️  Update your .env file to use: https://localhost:${LOCAL_PORT}/"
echo ""
echo "Press Ctrl+C to stop the tunnel."
echo ""

# Create SSH tunnel with port forwarding
# -L: Local port forwarding
# -N: Don't execute remote command
# -v: Verbose (remove for less output)
ssh -L ${LOCAL_PORT}:${AZURE_OPENAI_HOST}:${AZURE_OPENAI_PORT} -N ${VM_USER}@${VM_IP}
