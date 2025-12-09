# Azure VNet Debugging Guide

This guide explains how to access and debug internal Azure resources (Featureform, Redis, Container Apps, etc.) that are only accessible within the VNet.

---

## 🎯 The Problem

Many Azure resources are deployed with private/internal networking for security:
- **Featureform**: Internal-only Container App (10.0.4.x)
- **Redis Enterprise**: Private endpoint (10.0.1.x)
- **Container Apps**: Internal ingress only
- **Storage**: Private endpoints

These cannot be accessed from your local machine for testing/debugging.

---

## ✅ Solution: Debug Pod

We've created a **lightweight "Debug Pod"** - a Container Instance that:
- Lives inside the Azure VNet
- Has all debugging tools pre-installed
- Costs ~$0.50/day when running, $0 when stopped
- Accessible via Azure CLI

---

## 🚀 Quick Start

### 1. Deploy the Debug Pod

```bash
./infra/scripts/deploy-debug-pod.sh
```

### 2. Connect to the Debug Pod

```bash
az container exec \
  -g finagentix-dev-rg \
  -n debug-pod-545d8fdb508d4 \
  --exec-command /bin/bash
```

You'll get a shell prompt inside the VNet! 🎉

---

## 🛠️ What's Pre-installed

The debug pod comes with:
- **Python 3.13** + pip
- **featureform** Python client
- **redis-cli** for Redis debugging
- **curl** for HTTP testing
- **git** for cloning repos
- **jq** for JSON parsing
- **dig, ping** for network debugging
- **vim, nano** for editing files

---

## 📋 Common Debugging Tasks

### Test Featureform Connection

```bash
# Inside debug pod:
curl -v http://featureform-545d8fdb508d4.internal.azurecontainerapps.io/health

# Or with Python:
python << 'EOF'
import featureform as ff
client = ff.Client(host="featureform-545d8fdb508d4.internal.azurecontainerapps.io", insecure=True)
print("✅ Connected to Featureform!")
EOF
```

### Apply Featureform Definitions

```bash
# Inside debug pod:
cd /tmp
git clone https://github.com/tfindelkind-redis/FinagentiX.git
cd FinagentiX

# Get Redis password from environment or Azure
export REDIS_PASSWORD="<your-redis-password>"

# Apply definitions
python featureform/definitions.py
```

### Test Redis Connection

```bash
# Inside debug pod:
redis-cli -h redis-545d8fdb508d4.eastus.redis.azure.net -p 10000 --tls

# With password:
redis-cli -h redis-545d8fdb508d4.eastus.redis.azure.net -p 10000 --tls --pass "<password>"

# Test commands:
PING  # Should return PONG
INFO
KEYS ff:*
```

### Check Container App Logs

```bash
# From your local machine (not inside debug pod):
az containerapp logs show \
  -g finagentix-dev-rg \
  -n featureform-545d8fdb508d4 \
  --tail 100 \
  --follow
```

### Test DNS Resolution

```bash
# Inside debug pod:
dig featureform-545d8fdb508d4.internal.azurecontainerapps.io
dig redis-545d8fdb508d4.eastus.redis.azure.net

# Or simple ping:
ping -c 3 featureform-545d8fdb508d4.internal.azurecontainerapps.io
```

### Network Connectivity Test

```bash
# Inside debug pod:
nc -zv featureform-545d8fdb508d4.internal.azurecontainerapps.io 80
nc -zv redis-545d8fdb508d4.eastus.redis.azure.net 10000
```

---

## 💾 Copy Files In/Out

### Copy files TO debug pod:

```bash
# Create a temporary storage in Azure Files (one-time setup)
az storage share create \
  --account-name st545d8fdb508d4 \
  --name debug-share

# Mount in debug pod and copy files
# (Or use git clone inside the pod)
```

### Copy files FROM debug pod:

```bash
# Option 1: Use Azure Files (if mounted)
# Option 2: Use git to push changes
# Option 3: Print to stdout and capture locally:
az container exec \
  -g finagentix-dev-rg \
  -n debug-pod-545d8fdb508d4 \
  --exec-command "cat /path/to/file.txt" > local-file.txt
```

---

## 🔄 Manage Debug Pod

### Stop (to save costs):
```bash
az container stop -g finagentix-dev-rg -n debug-pod-545d8fdb508d4
```

### Start again:
```bash
az container start -g finagentix-dev-rg -n debug-pod-545d8fdb508d4
```

### Delete (when done):
```bash
az container delete -g finagentix-dev-rg -n debug-pod-545d8fdb508d4 --yes
```

### Redeploy (if needed):
```bash
./infra/scripts/deploy-debug-pod.sh
```

---

## 💰 Costs

| State | Cost per Day | Cost per Month |
|-------|--------------|----------------|
| Running | ~$0.50 | ~$15 |
| Stopped | $0.00 | $0.00 |

**Recommendation**: Stop the pod when not in use!

---

## 🔍 Advanced Debugging Scenarios

### Scenario 1: Feature Store Integration Testing

```bash
# Inside debug pod:
python << 'EOF'
import featureform as ff
import os

# Connect to Featureform
client = ff.Client(
    host="featureform-545d8fdb508d4.internal.azurecontainerapps.io",
    insecure=True
)

# Register provider (if not already done)
redis = client.register_redis(
    name="azure-redis-online",
    host="redis-545d8fdb508d4.eastus.redis.azure.net",
    port=10000,
    password=os.getenv("REDIS_PASSWORD"),
    db=0
)

# List features
features = client.list_features()
print(f"✅ Found {len(features)} features")
for f in features:
    print(f"  - {f.name}")

# Get feature value
try:
    value = client.features([("sma_20", "AAPL")])
    print(f"✅ SMA 20 for AAPL: {value}")
except Exception as e:
    print(f"❌ Error: {e}")
EOF
```

### Scenario 2: Redis Data Inspection

```bash
# Inside debug pod:
redis-cli -h redis-545d8fdb508d4.eastus.redis.azure.net -p 10000 --tls --pass "$REDIS_PASSWORD" << 'EOF'
# Check Featureform metadata (DB 2)
SELECT 2
KEYS *
SCAN 0 MATCH ff:* COUNT 100

# Check online feature store (DB 0)
SELECT 0
KEYS ff:feature:*
GET ff:feature:AAPL:sma_20
EOF
```

### Scenario 3: Container App Health Check

```bash
# Inside debug pod:
curl -v http://featureform-545d8fdb508d4.internal.azurecontainerapps.io/health
curl -v http://featureform-545d8fdb508d4.internal.azurecontainerapps.io/api/v1/features
```

### Scenario 4: Network Latency Testing

```bash
# Inside debug pod:
# Install additional tools
apt-get install -y iperf3 mtr

# Test latency to Featureform
ping -c 10 featureform-545d8fdb508d4.internal.azurecontainerapps.io

# Trace route
mtr --report featureform-545d8fdb508d4.internal.azurecontainerapps.io
```

---

## 🎓 Workflow Example: Apply Feature Definitions

Here's the complete workflow to apply feature definitions:

```bash
# 1. Deploy debug pod (if not already done)
./infra/scripts/deploy-debug-pod.sh

# 2. Get Redis password
REDIS_PASSWORD=$(az redisenterprise database list-keys \
  -g finagentix-dev-rg \
  --cluster-name redis-545d8fdb508d4 \
  --query "primaryKey" -o tsv)

echo "Redis password: $REDIS_PASSWORD"

# 3. Connect to debug pod
az container exec \
  -g finagentix-dev-rg \
  -n debug-pod-545d8fdb508d4 \
  --exec-command /bin/bash

# 4. Inside debug pod, clone repo and apply definitions
git clone https://github.com/tfindelkind-redis/FinagentiX.git
cd FinagentiX

export FEATUREFORM_HOST="featureform-545d8fdb508d4.internal.azurecontainerapps.io"
export REDIS_HOST="redis-545d8fdb508d4.eastus.redis.azure.net"
export REDIS_PORT="10000"
export REDIS_PASSWORD="<paste-password-here>"

python featureform/definitions.py

# 5. Verify features were created
python << 'EOF'
import featureform as ff
client = ff.Client(host=os.getenv("FEATUREFORM_HOST"), insecure=True)
features = client.list_features()
print(f"✅ {len(features)} features registered")
EOF
```

---

## 🔐 Security Considerations

1. **Debug pod is internal-only**: Cannot be accessed from internet
2. **No public IP**: Only accessible via Azure CLI
3. **VNet isolation**: Can only reach internal resources
4. **Temporary by design**: Should be deleted when not needed
5. **No persistent storage**: All data is lost when container restarts

---

## 🆘 Troubleshooting

### Can't connect to debug pod

```bash
# Check if it's running
az container show -g finagentix-dev-rg -n debug-pod-545d8fdb508d4 --query "{State:properties.instanceView.state, IP:properties.ipAddress.ip}"

# Check logs
az container logs -g finagentix-dev-rg -n debug-pod-545d8fdb508d4 --tail 100

# Restart if needed
az container restart -g finagentix-dev-rg -n debug-pod-545d8fdb508d4
```

### Can't reach Featureform from debug pod

```bash
# Check DNS resolution
dig featureform-545d8fdb508d4.internal.azurecontainerapps.io

# Check if Featureform is running
az containerapp show -g finagentix-dev-rg -n featureform-545d8fdb508d4 --query "properties.runningStatus"

# Check Featureform logs
az containerapp logs show -g finagentix-dev-rg -n featureform-545d8fdb508d4 --tail 50
```

### Package installation fails inside debug pod

```bash
# Update package lists
apt-get update

# Install with verbose output
pip install --verbose <package-name>

# Check Python version
python --version
```

---

## 📚 Alternative Approaches (For Reference)

### Option A: Azure Bastion + VM
- **Cost**: ~$150/month
- **Use case**: If you need persistent desktop environment
- **Setup**: More complex, requires VM management

### Option B: VPN Gateway
- **Cost**: ~$150/month  
- **Use case**: If entire team needs VNet access
- **Setup**: Complex certificate management

### Option C: App Service SSH
- **Cost**: ~$15/month
- **Use case**: Always-on debugging environment
- **Setup**: Similar to debug pod but persistent

### Option D: Azure CLI Container Extension
- **Cost**: Free (uses your local Docker)
- **Use case**: Run commands without deploying resources
- **Limitation**: Still can't reach internal VNet resources

---

## ✅ Why Debug Pod is Best

1. **Cost-effective**: Only pay when running (~$0.50/day)
2. **Zero maintenance**: No OS updates, no SSH keys
3. **Pre-configured**: Everything you need is pre-installed
4. **Secure**: No public access, internal-only
5. **Disposable**: Delete when done, redeploy in seconds
6. **Modern workflow**: Use familiar Azure CLI commands

---

## 🎯 Next Steps

1. **Deploy the debug pod**: `./infra/scripts/deploy-debug-pod.sh`
2. **Apply feature definitions** (see workflow above)
3. **Test Featureform integration** with your agents
4. **Stop the pod** when done: `az container stop -g finagentix-dev-rg -n debug-pod-545d8fdb508d4`

---

**Quick Reference**:

```bash
# Deploy
./infra/scripts/deploy-debug-pod.sh

# Connect
az container exec -g finagentix-dev-rg -n debug-pod-545d8fdb508d4 --exec-command /bin/bash

# Stop (save costs)
az container stop -g finagentix-dev-rg -n debug-pod-545d8fdb508d4

# Delete
az container delete -g finagentix-dev-rg -n debug-pod-545d8fdb508d4 --yes
```
