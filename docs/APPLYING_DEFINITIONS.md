# Applying Featureform Definitions

## Quickstart - One Command

```bash
# Get Redis password and store it
export REDIS_PASSWORD=$(az redisenterprise database list-keys \
  -g finagentix-dev-rg \
  --cluster-name redis-545d8fdb508d4 \
  --query "primaryKey" -o tsv)

# Connect to debug pod
az container exec -g finagentix-dev-rg -n debug-pod-545d8fdb508d4 --exec-command /bin/bash
```

## Inside the Debug Pod

Once connected, run these commands:

```bash
# Install dependencies
pip3 install -q featureform redis python-dotenv requests

# Clone repository
git clone https://github.com/tfindelkind-redis/FinagentiX.git /tmp/FinagentiX
cd /tmp/FinagentiX

# Set environment variables
export FEATUREFORM_HOST="featureform-545d8fdb508d4.internal.azurecontainerapps.io"
export REDIS_HOST="redis-545d8fdb508d4.eastus.redis.azure.net"
export REDIS_PORT="10000"
export REDIS_PASSWORD="<paste-the-password-from-your-terminal>"

# Apply definitions
python3 featureform/definitions.py
```

## Why Not Fully Automated?

The debug pod runs **inside Azure's VNet** (private IP: 10.0.6.4), so:
- SSH from your local machine → ❌ Can't reach private IP
- `az container exec` with piping → ❌ Command parsing issues
- **Interactive `az container exec`** → ✅ **Works perfectly**

For CI/CD, you can use Azure DevOps agents or GitHub Actions runners **inside the VNet**.

## Verification

After applying definitions, verify they were registered:

```bash
# Inside debug pod
python3 << 'EOF'
import featureform as ff
import os

client = ff.Client(host=os.getenv("FEATUREFORM_HOST"), insecure=True)
features = client.list_features()
print(f"✅ Registered {len(features)} features:")
for f in features:
    print(f"  - {f.name}")
EOF
```

## Next Steps

1. **Apply Definitions**: Run the commands above
2. **Verify Features**: Check that features were registered
3. **Update Agents**: Modify agent code to use Featureform client
4. **Test Retrieval**: Fetch features from agents

## Troubleshooting

If definitions fail to apply:
- Check Featureform server logs: `az containerapp logs show -g finagentix-dev-rg -n featureform-545d8fdb508d4`
- Verify Redis connectivity: `redis-cli -h redis-545d8fdb508d4.eastus.redis.azure.net -p 10000 --tls -a $REDIS_PASSWORD PING`
- Test Featureform connectivity: `curl http://featureform-545d8fdb508d4.internal.azurecontainerapps.io`
