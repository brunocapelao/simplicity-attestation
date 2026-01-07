# SAP — Simplicity Attestation Protocol

<div align="center">

**On-chain certificate system with hierarchical delegation using Simplicity on Liquid Network**

[![Simplicity](https://img.shields.io/badge/Simplicity-Powered-8B5CF6?style=flat-square)](https://simplicity-lang.org)
[![Liquid Network](https://img.shields.io/badge/Liquid-Testnet-00AAFF?style=flat-square)](https://liquid.net)
[![SDK](https://img.shields.io/badge/SDK-v0.6.0-green?style=flat-square)](./sdk)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](./LICENSE)

[Documentation (EN)](docs/DOCUMENTATION.md) • [Documentação (PT)](docs/pt/README.md) • [Protocol Spec](docs/PROTOCOL_SPEC.md)

</div>

---

## Overview

SAP is a **decentralized digital certificate system** that leverages Simplicity's unique capabilities on Liquid Network to provide:

- **Trustless Verification** — Certificate validity is determined by UTXO existence, not trusted third parties
- **Instant Revocation** — Spend the UTXO = certificate revoked (no CRL/OCSP delays)
- **Hierarchical Delegation** — Admin delegates authority to issuers with cryptographic restrictions
- **Self-Referential Covenants** — Change always returns to the vault (enforced by code, not incentives)


## 🌟 Why Simplicity?

### The Simplicity Launch Context

On **July 31, 2025**, Blockstream launched Simplicity—culminating 8 years of research into a language that promises:

> *"If adopted on Bitcoin in the future, Simplicity could position Bitcoin as a programmable settlement layer for all institutional-grade finance."*
> — **Andrew Poelstra**, Director of Research at Blockstream

| 🎯 Simplicity Feature | SAP Implementation | Status |
|:---------------------|:-------------------|:------:|
| **Covenants** | Self-referential vault with enforced output constraints | ✅ Production |
| **Vaults** | Delegation Vault with 3 spending paths | ✅ Production |
| **Delegation Schemes** | Admin→Delegate hierarchy with cryptographic restrictions | ✅ Production |

---

## How It Works

```
                              ADMIN (Root Authority)
                                       │
                    Deposits L-BTC to Delegation Vault
                                       │
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            DELEGATION VAULT                                   │
│                     Simplicity Contract with Covenants                        │
│                                                                               │
│   ┌─────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐  │
│   │   LEFT PATH     │   │   RIGHT-LEFT PATH    │   │  RIGHT-RIGHT PATH    │  │
│   │   Admin Drain   │   │   Admin + Covenants  │   │ Delegate + Covenants │  │
│   │                 │   │                      │   │                      │  │
│   │  Unconditional  │   │   Issue Certificate  │   │  Issue Certificate   │  │
│   │  (Deactivate)   │   │   (with restrictions)│   │  (with restrictions) │  │
│   └────────┬────────┘   └──────────┬───────────┘   └──────────┬───────────┘  │
│            │                       │                          │               │
│            ▼                       └────────────┬─────────────┘               │
│      Free Spend                                 │                             │
│    (Recover funds)              ┌───────────────▼──────────────────┐          │
│                                 │     COVENANT ENFORCEMENT         │          │
│                                 │                                  │          │
│                                 │  ✓ Output 0 → Vault (self-ref)  │          │
│                                 │  ✓ Output 1 → Certificate Script│          │
│                                 │  ✓ Output 2 → OP_RETURN (SAP)   │          │
│                                 │  ✓ Output 3 → Fee               │          │
│                                 └──────────────────────────────────┘          │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────────┐
                    │          CERTIFICATE UTXO            │
                    │                                      │
                    │   UTXO EXISTS  → Certificate VALID   │
                    │   UTXO SPENT   → Certificate REVOKED │
                    │                                      │
                    │   Can be revoked by Admin or Delegate│
                    └──────────────────────────────────────┘
```

### Permission Matrix

| Action | Admin | Delegate |
|:-------|:-----:|:--------:|
| Issue certificate (via vault) | ✅ | ✅ |
| Revoke certificate | ✅ | ✅ |
| Drain vault (deactivate delegate) | ✅ | ❌ |
| Unconditional spend | ✅ | ❌ |

---

## Verified Testnet Transactions

All operations have been successfully tested on Liquid Testnet:

### Issuance
| Actor | Transaction |
|:------|:------------|
| Admin | [`5487ed01...`](https://blockstream.info/liquidtestnet/tx/5487ed018fa69105acc4ce525b865d25f8cb0ac92297a64539008b50243ed7bb) |
| Delegate | [`423efc36...`](https://blockstream.info/liquidtestnet/tx/423efc36bb3112546324a91482681091dea6a9e83a94583fa5a80fe3cedef355) |

### Revocation
| Actor | Transaction |
|:------|:------------|
| Admin | [`07048a43...`](https://blockstream.info/liquidtestnet/tx/07048a43fabae3b4ca3f10316b9241fdee5259e68c61056a89c66acac16c57e5) |
| Delegate | [`2601bb94...`](https://blockstream.info/liquidtestnet/tx/2601bb94fcb361ff34657804b7274ceb47a83f31eab7c3cce56b6a3eee718ef0) |

---

## Quick Start

### Installation

> **Important / Importante:** For SAP to work correctly, use the patched `hal-simplicity` from https://github.com/brunocapelao/hal-simplicity (includes required fixes).

```bash
# Clone the repository
git clone https://github.com/brunocapelao/simplicity-attestation.git
cd simplicity-attestation

# Install Python dependencies
pip install embit requests

# Install Simplicity tools (required for contract compilation)
# hal-simplicity
git clone https://github.com/brunocapelao/hal-simplicity.git
(cd hal-simplicity && cargo build --release)

# simc (Simfony Compiler)
git clone https://github.com/BlockstreamResearch/simfony.git
(cd simfony && cargo build --release)

# Optional: make tools available in PATH
export PATH="$PWD/hal-simplicity/target/release:$PWD/simfony/target/release:$PATH"
```

### SDK Usage

```python
from sdk import SAP, SAPClient, SAPConfig
from sdk.infra.hal import HalSimplicity

# =============================================================================
# OPTION 1 (Recommended): Multi-Party Mode — Role separation
# =============================================================================

HAL_PATH = "./hal-simplicity/target/release/hal-simplicity"
SIMC_PATH = "./simfony/target/release/simc"

# Admin creates vault configuration (public keys only)
config = SAP.create_vault(
    admin_pubkey="abc123...",
    delegate_pubkey="def456...",
    network="testnet",
    hal_path=HAL_PATH,
    simc_path=SIMC_PATH,
)
config.save("vault_config.json")
print(f"Fund vault: {config.vault_address}")

# Admin operates with their private key
admin = SAP.as_admin(config="vault_config.json", private_key="admin_secret...", hal_path=HAL_PATH)
result = admin.issue_certificate(cid="QmYwAPJzv5...")
print(f"Issued certificate tx: {result.txid}")

# Delegate operates independently
delegate = SAP.as_delegate(config="vault_config.json", private_key="delegate_secret...", hal_path=HAL_PATH)
result = delegate.issue_certificate(cid="QmNewCert...")
delegate.revoke_certificate(result.txid, 1, reason_code=6)

# Admin can deactivate delegate if needed
# admin.drain_vault(recipient="tex1...")

# =============================================================================
# OPTION 2: External Signing (Hardware Wallets / Multisig / Custody)
# =============================================================================
# Use this when private keys are managed externally (HSM, hardware wallet,
# multisig ceremony, or custody provider). SDK builds the transaction and
# provides the sig_hash for external signing.

client = SAPClient(
    config=SAPConfig.from_file("secrets.json"),
    hal=HalSimplicity(HAL_PATH, network="liquid"),
)

# Step 1: Prepare transaction (SDK builds it, returns hash to sign)
prepared = client.prepare_issue_certificate(cid="Qm...", issuer="admin")
print(f"Sign this hash: {prepared.sig_hash}")
print(f"Required signer: {prepared.signer_role}")

# Step 2: Get signature from external source
signature = my_hardware_wallet.sign(prepared.sig_hash_bytes)  # 64-byte Schnorr

# Step 3: Finalize and broadcast
result = client.finalize_transaction(prepared, signature)
```

### CLI Usage

```bash
export SAP_ADMIN_PRIVATE_KEY="<64-hex>"
export SAP_DELEGATE_PRIVATE_KEY="<64-hex>"
export SAP_HAL_PATH="./hal-simplicity/target/release/hal-simplicity"
export SAP_SIMC_PATH="./simfony/target/release/simc"

cd tests

# Issue certificate
python test_emit.py --admin-issue          # Admin issues certificate
python test_emit.py --delegate-issue       # Delegate issues certificate
python test_emit.py --admin-unconditional  # Admin drains vault

# Revoke certificate
python test_certificate_revoke.py --admin
python test_certificate_revoke.py --delegate
```

---

## SAP Protocol (OP_RETURN)

Standardized format for certificate metadata stored on-chain:

```
┌────────┬─────────┬──────────┬────────────────────────────────────┐
│  TAG   │ VERSION │   TYPE   │            PAYLOAD                 │
│ "SAP"  │  0x01   │  0x01    │   CID/identifier (≤75 bytes)      │
├────────┼─────────┼──────────┼────────────────────────────────────┤
│ 3 bytes│ 1 byte  │  1 byte  │          variable                  │
└────────┴─────────┴──────────┴────────────────────────────────────┘
```

### Operation Types

| Type | Byte | Description | Payload |
|:-----|:-----|:------------|:--------|
| ATTEST | `0x01` | Certificate issuance | CID/identifier (UTF-8 or raw bytes) |
| REVOKE | `0x02` | Certificate revocation | `TXID:VOUT` (+ optional `reason_code` + optional `replacement_txid`) |
| UPDATE | `0x03` | Metadata update | New CID/identifier |

---

## Explorer Examples (Didactic)

- Valid certificate (issuance creates the certificate UTXO at `vout=1`): `https://blockstream.info/liquidtestnet/tx/2785aac5ea950c54ece28b1fbfdeb5acf29903fed89ecbb78ba997fe0b927fcb`
  - OP_RETURN (issuance is enforced at `vout=2` by the vault covenant): `534150010145582d4e45572d31373637373936313938` → `SAP|01|01|EX-NEW-1767796198`
- Revoked + replacement (revoke includes `reason_code=6` and points to a new issuance txid): `https://blockstream.info/liquidtestnet/tx/625dcfdac2ca7a2ddfb857254459c46e17939c7785c3e20c21f3ea33fb5be729`
  - OP_RETURN (`vout=1` in this example): `5341500102` + `<old_txid>` + `0001` + `06` + `<replacement_txid>`
  - Decoded: `old_txid=912a79b929e331cfaf02727cd9f3282c8f87dd4a7af502c2ccf765feb5c12444`, `vout=1`, `reason_code=6 (REISSUE_REPLACEMENT)`, `replacement_txid=2785aac5ea950c54ece28b1fbfdeb5acf29903fed89ecbb78ba997fe0b927fcb`

---

## Simplicity Jets Used

| Jet | Purpose | SAP Usage |
|:----|:--------|:----------|
| `jet::sig_all_hash()` | Compute transaction sighash | Signature verification |
| `jet::bip_0340_verify()` | Verify Schnorr signature | Authentication |
| `jet::current_script_hash()` | Get CMR of current script | **Self-reference covenant** |
| `jet::output_script_hash()` | Get hash of output script | Destination enforcement |
| `jet::output_null_datum()` | Read OP_RETURN data | SAP protocol data |
| `jet::output_is_fee()` | Check if output is fee | Structure validation |
| `jet::num_outputs()` | Count transaction outputs | Structure validation |

---

## Security

### Guarantees

| Property | Mechanism | Strength |
|:---------|:----------|:---------|
| Change returns to vault | Self-referential covenant | Cryptographic |
| Certificate format enforced | Hardcoded script hash | Cryptographic |
| Only authorized signers | Schnorr verification | Cryptographic |
| Certificate validity | UTXO existence | Consensus |
| No double-spend | UTXO model | Consensus |

### Attack Vectors Tested

| Attack | Result | Protection | Test |
|:-------|:------:|:-----------|:-----|
| Delegate diverts change | ❌ Blocked | Self-ref covenant | `tests/test_attack_vectors.py` |
| Non-standard certificate | ❌ Blocked | Script hash check | `tests/test_attack_vectors.py` |
| Missing OP_RETURN | ❌ Blocked | output_null_datum check | `tests/test_attack_vectors.py` |
| Invalid output count | ❌ Blocked | num_outputs check | `tests/test_attack_vectors.py` |
| Delegate drains vault | ❌ Blocked | Admin-only path | `tests/test_edge_cases.py` |
| Third party forgery | ❌ Blocked | Schnorr signature + key checks | `tests/test_attack_vectors.py` |

---

## Project Structure

```
.
├── contracts/
│   ├── vault.simf              # Delegation Vault (3 spending paths)
│   └── certificate.simf        # Certificate UTXO script
│
├── sdk/                        # Python SDK v0.6.0
│   ├── sap.py                  # Main SAP class
│   ├── client.py               # Legacy client
│   ├── config.py               # Configuration management
│   ├── prepared.py             # External signing support
│   ├── providers.py            # Key providers
│   ├── roles.py                # Role-based access
│   ├── confirmation.py         # Transaction tracking
│   ├── fees.py                 # Fee estimation
│   └── errors.py               # Error handling
│
├── tests/
│   ├── test_emit.py            # Issuance tests
│   ├── test_certificate_revoke.py  # Revocation tests
│   ├── test_edge_cases.py      # Security tests
│   └── test_attack_vectors.py  # Offline covenant/attack tests
│
├── docs/
│   ├── DOCUMENTATION.md        # Technical specification (EN)
│   ├── PROTOCOL_SPEC.md        # SAP protocol spec (EN)
│   └── pt/                     # Portuguese documentation
│
└── secrets.example.json        # Template (do not commit real keys)
```

---

## Spending Paths Reference

| Path | Witness Encoding | Usage |
|:-----|:-----------------|:------|
| Left | `0` + sig + 7 pad | Admin drains vault (deactivate delegate) |
| Right-Left | `10` + sig + 6 pad | Admin issues certificate (with covenants) |
| Right-Right | `11` + sig + 6 pad | Delegate issues certificate (with covenants) |

---

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

---

<div align="center">

**Built with [Simplicity](https://simplicity-lang.org) on [Liquid Network](https://liquid.net)**

[Documentation](docs/DOCUMENTATION.md) • [Protocol Spec](docs/PROTOCOL_SPEC.md)

</div>
