# Azure VNet Debugging Guide

This guide explains how to access and debug internal Azure resources (Featureform, Redis, Container Apps, etc.) that are only reachable from within the virtual network.

---

## The Challenge

Most platform components are deployed with private networking:
- Featureform: internal-only Container App endpoint
- Redis Enterprise: private endpoint
- Container Apps: internal ingress
- Storage accounts: private endpoints

Direct access from a developer laptop is blocked, making diagnostics and configuration changes difficult.

---

## Solution: Debug VM

The repository now standardizes on a small debug virtual machine that lives inside the same VNet as the application components. The VM:
- Runs Ubuntu 22.04 with common debugging tools pre-installed
- Exposes a public IP for SSH access (governed by Azure RBAC)
- Provides persistent storage between sessions
- Can be started and stopped on demand to control cost

The previous debug pod implementation has been removed. All workflows should use the debug VM instead.

---

## Quick Start

### 1. Deploy the debug VM

```bash
./infra/scripts/deploy-debug-vm.sh
```

The script provisions the VM, network security group rules, and required dependencies.

### 2. Configure passwordless SSH (one time per workstation)

```bash
./infra/scripts/setup-ssh-key.sh
```

This helper uploads your public SSH key and verifies connectivity. Skip it if you prefer to enter the VM password manually.

### 3. Connect to the VM

```bash
ssh azureuser@<vm-public-ip>
```

Retrieve the VM IP with:

```bash
az vm show \
  -g finagentix-<env>-rg \
  -n debug-vm-<resource-token> \
  -d --query publicIps -o tsv
```

### 4. Apply Featureform definitions from your workstation

```bash
./infra/scripts/connect-and-apply.sh
```

The helper script gathers Redis credentials, securely copies an execution script to the VM, and runs featureform/definitions.py inside the VNet boundary.

---

## Tools on the VM

The VM image includes:
- Python 3.11 and pip
- Featureform Python client
- Redis CLI
- Git and curl
- jq, dig, and netcat
- vim and nano

Install additional packages with apt or pip as needed.

---

## Common Debugging Tasks

Run these commands after connecting to the VM via SSH unless noted otherwise.

### Test Featureform connectivity

```bash
curl -v http://featureform-<resource-token>.internal.<region>.azurecontainerapps.io/health
```

Or via Python:

```bash
python <<'EOF2'
import featureform as ff
client = ff.Client(
    host="featureform-<resource-token>.internal.<region>.azurecontainerapps.io",
    insecure=True,
)
print("Connected to Featureform")
EOF2
```

### Apply Featureform definitions (manual method)

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
export REDIS_PASSWORD=<redis-password>

python featureform/definitions.py
```

Obtain the Redis password from your workstation with:

```bash
az redisenterprise database list-keys \
  -g finagentix-<env>-rg \
  --cluster-name redis-<resource-token> \
  --query primaryKey -o tsv
```

### Inspect Redis

```bash
redis-cli \
  -h redis-<resource-token>.<region>.redisenterprise.cache.azure.net \
  -p 10000 --tls --pass "$REDIS_PASSWORD"
```

Example commands:

```bash
PING
INFO
SELECT 0
KEYS ff:*
```

### Check Container App logs (run locally)

```bash
az containerapp logs show \
  -g finagentix-<env>-rg \
  -n featureform-<resource-token> \
  --tail 100 --follow
```

### Verify DNS resolution from inside the VNet

```bash
dig featureform-<resource-token>.internal.<region>.azurecontainerapps.io
dig redis-<resource-token>.<region>.redisenterprise.cache.azure.net
```

---

## File Transfer

Use scp from your local machine:

```bash
scp local-file.txt azureuser@<vm-public-ip>:/home/azureuser/
```

Copy files back:

```bash
scp azureuser@<vm-public-ip>:/home/azureuser/remote.log ./remote.log
```

For larger data sets consider mounting an Azure Files share or cloning the repository directly on the VM.

---

## Manage the Debug VM

Stop the VM to eliminate compute charges:

```bash
az vm deallocate -g finagentix-<env>-rg -n debug-vm-<resource-token>
```

Start it again when needed:

```bash
az vm start -g finagentix-<env>-rg -n debug-vm-<resource-token>
```

Delete the VM (and associated public IP) when finished:

```bash
az vm delete -g finagentix-<env>-rg -n debug-vm-<resource-token> --yes
az network public-ip delete -g finagentix-<env>-rg -n debug-vm-<resource-token>-pip
```

Approximate cost: Standard_B1s VM is roughly USD 8 per month when running; deallocated VMs only incur disk storage costs.

---

## Example Workflow

1. Deploy or start the debug VM.
2. Run ./infra/scripts/setup-ssh-key.sh if passwordless SSH is not configured.
3. Execute ./infra/scripts/connect-and-apply.sh to apply the latest Featureform definitions.
4. SSH into the VM for any additional diagnostics.
5. Stop the VM with az vm deallocate when you are done.

---

## Troubleshooting

### SSH fails with permission denied

- Verify the VM is running: az vm get-instance-view ... --query instanceView.statuses
- Ensure your public key was uploaded via setup-ssh-key.sh
- If necessary, reset credentials: az vm user reset-password

### Featureform endpoint unreachable from VM

- Confirm the Container App is running: az containerapp show --query properties.runningStatus
- Verify DNS resolution from the VM using dig
- Ensure the Container Apps environment static IP matches any hosts file overrides

### Redis authentication errors

- Regenerate keys: az redisenterprise database regenerate-key
- Update the REDIS_PASSWORD environment variable before rerunning definitions

---

## Security Notes

- Restrict SSH access to named Azure Active Directory users via RBAC.
- Use az vm deallocate when idle to limit attack surface and cost.
- Treat the VM as a privileged environment; avoid storing long-lived secrets in the home directory.

---

## Alternative Approaches (Reference)

- Azure Bastion plus a private VM: higher monthly cost but no public IPs.
- VPN Gateway with site-to-site or point-to-site connectivity: appropriate for larger teams.
- Azure Dev Tunnel to the debug VM for temporary access without exposing SSH.

These options remain valid if organizational policies prohibit public IP addresses, but the debug VM is the recommended path for this project.
