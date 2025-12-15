#!/bin/bash
# Setup /etc/hosts entry for Azure OpenAI tunneling
# This allows SSL to work correctly through the SSH tunnel

OPENAI_HOST=$(python - <<'PY'
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

if [ -z "$OPENAI_HOST" ]; then
    echo "Unable to determine Azure OpenAI host."
    exit 1
fi

echo "This script will add an entry to /etc/hosts"
echo "Entry: 127.0.0.1 $OPENAI_HOST"
echo ""
echo "This requires sudo password."
echo ""

if grep -q "$OPENAI_HOST" /etc/hosts 2>/dev/null; then
    echo "✅ Entry already exists in /etc/hosts"
else
    echo "Adding entry to /etc/hosts..."
    echo "127.0.0.1 $OPENAI_HOST" | sudo tee -a /etc/hosts
    echo "✅ Added hosts entry"
fi

echo ""
echo "Now restart the SSH tunnel on port 443:"
echo "  sudo ssh -f -L 443:$OPENAI_HOST:443 -N azureuser@4.227.91.227"
