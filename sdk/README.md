# SAS SDK (Python)

Python SDK for the Simplicity Attestation Protocol on Liquid Network.

## Features

- 🔐 **Secure by Design** - Vault creation with public keys only
- 🎭 **Role-based Access** - Separate Admin and Delegate operations
- 📜 **Certificate Lifecycle** - Issue, verify, and revoke certificates
- 🔗 **On-chain Verification** - UTXO-based certificate validity

## Installation

```bash
pip install embit requests
```

Requires `simc` and `hal-simplicity`. You can pass paths explicitly (recommended). See [docs/DOCUMENTATION.md](../docs/DOCUMENTATION.md) for setup.

## Quick Start

### 1. Create a Vault (Public Keys Only)

```python
from sdk import SAS

# Paths to required tools
HAL_PATH = "/path/to/hal-simplicity"
SIMC_PATH = "/path/to/simc"

# Admin creates vault with both public keys
config = SAS.create_vault(
    admin_pubkey="abc123...64hex...",
    delegate_pubkey="def456...64hex...",
    network="testnet",
    hal_path=HAL_PATH,
    simc_path=SIMC_PATH,
)

# Share config (safe - no private keys)
config.save("vault_config.json")
print(f"Fund this address: {config.vault_address}")
```

### 2. Operate as Admin

```python
from sdk import SAS

sap = SAS.as_admin(
    config="vault_config.json",
    private_key="admin_private_key...",
    hal_path=HAL_PATH,
)

# Issue certificate
result = sap.issue_certificate(cid="QmYwAPJzv5...")
print(f"Certificate TX: {result.txid}")

# Revoke any certificate
sap.revoke_certificate(txid, vout=1)

# Drain vault (deactivate delegate)
sap.drain_vault(recipient="tex1...")
```

### 3. Operate as Delegate

```python
from sdk import SAS

sap = SAS.as_delegate(
    config="vault_config.json",
    private_key="delegate_private_key...",
    hal_path=HAL_PATH,
)

# Issue certificate
result = sap.issue_certificate(cid="QmYwAPJzv5...")

# Revoke own certificates
sap.revoke_certificate(result.txid, vout=1)
```

### 4. Verify Certificates

```python
from sdk import CertificateStatus

status = sap.verify_certificate(txid, vout=1)
if status == CertificateStatus.VALID:
    print("Certificate is valid!")
else:
    print("Certificate has been revoked")
```

### 5. External Signing (Hardware Wallets / Multisig)

For scenarios where private keys are managed externally (hardware wallets, multisig, custody):

```python
from sdk import SAPClient, SASConfig
from sdk.infra.hal import HalSimplicity

client = SAPClient(
    config=SASConfig.from_file("config.json"),
    hal=HalSimplicity("/path/to/hal-simplicity", network="liquid"),
)

# Step 1: Prepare transaction (SDK builds it, returns hash to sign)
prepared = client.prepare_issue_certificate(cid="Qm...", issuer="admin")
print(f"Hash to sign: {prepared.sig_hash}")
print(f"Signer: {prepared.signer_role}")

# Step 2: Get signature from external source
signature = my_hardware_wallet.sign(prepared.sig_hash_bytes)  # 64-byte Schnorr

# Step 3: Finalize and broadcast
result = client.finalize_transaction(prepared, signature)
print(f"TX: {result.txid}")
```

**Available preparation methods:**
- `prepare_issue_certificate(cid, issuer)` — Issue certificate
- `prepare_revoke_certificate(txid, vout, revoker)` — Revoke certificate  
- `prepare_drain_vault(recipient)` — Drain vault (admin only)

## Legacy API

For backwards compatibility:

```python
from sdk import SAPClient

client = SAPClient.from_config("secrets.json")
result = client.issue_certificate(cid="Qm...")
```

## Documentation

- **English**: [docs/DOCUMENTATION.md](../docs/DOCUMENTATION.md)
- **Portuguese**: [docs/pt/SDK.md](../docs/pt/SDK.md)
- **Protocol Spec**: [docs/PROTOCOL_SPEC.md](../docs/PROTOCOL_SPEC.md)

## License

MIT - See [LICENSE](../LICENSE)
