# SSH Tunnel Setup for Azure OpenAI Access

## Problem
Your local machine cannot reach Azure OpenAI endpoint due to network/DNS issues.

## Solution
Use SSH tunnel through the debug VM that's already running in the Azure VNet.

## Quick Setup

### Option 1: Manual SSH Tunnel (Recommended)

```bash
# 1. Test SSH connection first
ssh azureuser@4.227.91.227

# 2. If that works, create the tunnel (in a separate terminal):
ssh -L 8443:openai-545d8fdb508d4.openai.azure.com:443 -N azureuser@4.227.91.227

# 3. Keep this terminal open! The tunnel stays active.
```

**Password:** You'll need the VM password (check with infra team or Azure Portal)

### Option 2: Using the Helper Script

```bash
# Run the tunnel script (asks for password)
./setup_azure_tunnel.sh

# Keep this terminal open
```

## Update Configuration

Once the tunnel is running, update your `.env` file:

```bash
# Change from:
AZURE_OPENAI_ENDPOINT=https://openai-545d8fdb508d4.openai.azure.com/

# To:
AZURE_OPENAI_ENDPOINT=https://localhost:8443/
```

**Important:** You may need to disable SSL verification for localhost, or we can modify the code to accept self-signed certs.

## Alternative: SOCKS Proxy (More Complex)

If port forwarding doesn't work, use SOCKS proxy:

```bash
# 1. Create SOCKS proxy
ssh -D 8888 -N azureuser@4.227.91.227

# 2. Configure Python to use proxy:
export HTTP_PROXY=socks5://localhost:8888
export HTTPS_PROXY=socks5://localhost:8888
```

## Testing

Once tunnel is active:

```bash
# Terminal 1: Keep tunnel running
ssh -L 8443:openai-545d8fdb508d4.openai.azure.com:443 -N azureuser@4.227.91.227

# Terminal 2: Update .env and test
cat > .env << 'EOF'
AZURE_OPENAI_ENDPOINT=https://localhost:8443/
AZURE_OPENAI_API_KEY=a72469a7210c4c6286beddca96f37d62
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4o
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_SSL=false
LOG_LEVEL=INFO
ENVIRONMENT=development
EOF

# Test connection
python test_azure_connection.py
```

## VM Details

- **IP:** 4.227.91.227
- **User:** azureuser
- **Location:** westus3
- **Resource Group:** FINAGENTIX-DEV-RG
- **Name:** debug-vm-3ae172dc9e9da
- **Status:** Running ✅

## Get VM Password

If you don't have the password:

```bash
# Reset the password
az vm user update \
  -g FINAGENTIX-DEV-RG \
  -n debug-vm-3ae172dc9e9da \
  -u azureuser \
  -p 'YourNewPassword123!'
```

## Troubleshooting

### Can't connect to VM
```bash
# Check VM is running
az vm get-instance-view -g FINAGENTIX-DEV-RG -n debug-vm-3ae172dc9e9da --query instanceView.statuses
```

### SSH timeout
- Check network security group allows SSH (port 22)
- Verify your IP isn't blocked
- Try from different network

### SSL certificate errors with localhost
We'll need to modify the code to skip SSL verification for localhost. Let me know if you hit this.

## Next Steps

1. ✅ Get VM password (or reset it)
2. ✅ Test SSH connection: `ssh azureuser@4.227.91.227`
3. ✅ Create tunnel: `ssh -L 8443:openai-545d8fdb508d4.openai.azure.com:443 -N azureuser@4.227.91.227`
4. ✅ Update .env with `AZURE_OPENAI_ENDPOINT=https://localhost:8443/`
5. ✅ Test: `python test_azure_connection.py`
6. ✅ Run server and test agents!
