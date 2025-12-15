# Applying Featureform Definitions

## Quickstart (recommended)

Run the helper script from your workstation:

```bash
./infra/scripts/connect-and-apply.sh
```

The script retrieves Redis credentials, copies an execution script to the debug VM, and runs `featureform/definitions.py` from inside the VNet.

## Manual workflow

1. Retrieve the Redis password:
   ```bash
   export REDIS_PASSWORD=$(az redisenterprise database list-keys \
     -g finagentix-<env>-rg \
     --cluster-name redis-<resource-token> \
     --query primaryKey -o tsv)
   ```
2. SSH to the debug VM:
   ```bash
   ssh azureuser@<vm-public-ip>
   ```
3. On the VM, apply the definitions:
   ```bash
   cd /tmp
   if [ -d FinagentiX ]; then
     cd FinagentiX && git pull && cd ..
   else
     git clone https://github.com/tfindelkind-redis/FinagentiX.git
   fi
   cd FinagentiX

   export FEATUREFORM_HOST="featureform-<resource-token>.internal.<region>.azurecontainerapps.io"
   export REDIS_HOST="redis-<resource-token>.<region>.redisenterprise.cache.azure.net"
   export REDIS_PORT=10000
   export REDIS_PASSWORD=$REDIS_PASSWORD

   python featureform/definitions.py
   ```

## Verification

After the script finishes, verify the resources:

```bash
python <<'EOF2'
import featureform as ff
import os

client = ff.Client(host=os.getenv("FEATUREFORM_HOST"), insecure=True)
features = client.list_features()
print(f"Found {len(features)} features")
for feature in features:
    print(f" - {feature.name}")
EOF2
```

## Troubleshooting

- Check Featureform: `az containerapp logs show -g finagentix-<env>-rg -n featureform-<resource-token>`
- Validate Redis: `redis-cli -h redis-<resource-token>.<region>.redisenterprise.cache.azure.net -p 10000 --tls -a $REDIS_PASSWORD PING`
- Confirm DNS from VM: `dig featureform-<resource-token>.internal.<region>.azurecontainerapps.io`

```
