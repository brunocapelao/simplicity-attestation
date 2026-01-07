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

### Key Innovation: The Self-Reference Problem

SAP solves a challenge previously considered impossible: a script that verifies outputs go back to *itself*:

```simplicity
// The script obtains its own hash at runtime
let self_hash: u256 = jet::current_script_hash();

// And cryptographically enforces change returns to itself
let output0_hash: u256 = unwrap(jet::output_script_hash(0));
assert!(jet::eq_256(self_hash, output0_hash));
```

This enables true **recursive covenant enforcement** — impossible in Bitcoin Script.

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
git clone https://github.com/your-repo/sap.git
cd sap

# Install Python dependencies
pip install embit requests

# Install Simplicity tools (required for contract compilation)
# hal-simplicity
git clone https://github.com/brunocapelao/hal-simplicity.git
cd hal-simplicity && cargo build --release

# simc (Simfony Compiler)
git clone https://github.com/BlockstreamResearch/simfony.git
cd simfony && cargo build --release
```

### SDK Usage

```python
from sdk import SAP

# =============================================================================
# OPTION 1: Simple Mode — Just provide keys
# =============================================================================

sap = SAP(
    admin_private_key="your_admin_key...",
    delegate_private_key="your_delegate_key...",
    network="testnet"
)

# Fund the vault
print(f"Fund vault: {sap.vault_address}")

# Issue a certificate
result = sap.issue_certificate(cid="QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG")
print(f"Certificate: {result.txid}:{result.vout}")

# Revoke when needed
sap.revoke_certificate(result.txid, vout=1)

# =============================================================================
# OPTION 2: Multi-Party Mode — Role separation
# =============================================================================

# Admin creates vault configuration (public keys only)
config = SAP.create_vault(
    admin_pubkey="abc123...",
    delegate_pubkey="def456...",
    network="testnet"
)
config.save("vault_config.json")

# Admin operates with their private key
admin = SAP.as_admin(config="vault_config.json", private_key="admin_secret...")
result = admin.issue_certificate(cid="QmYwAPJzv5...")
admin.drain_vault(recipient="tex1...")  # Deactivate delegate if needed

# Delegate operates independently
delegate = SAP.as_delegate(config="vault_config.json", private_key="delegate_secret...")
result = delegate.issue_certificate(cid="QmNewCert...")
delegate.revoke_certificate(result.txid, 1, reason_code=6)

# =============================================================================
# OPTION 3: Hardware Wallet / HSM Mode — External signing
# =============================================================================

sap = SAP(
    admin_pubkey="abc123...",
    delegate_pubkey="def456...",
    signer=my_hardware_wallet,
    network="testnet"
)

# Prepare transaction (no signature yet)
prepared = sap.prepare_issue_certificate(cid="Qm...")

# Sign externally
signature = my_hardware_wallet.sign(prepared.sig_hash)

# Finalize and broadcast
result = sap.finalize_transaction(prepared, signature)
```

### CLI Usage

```bash
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
│ "SAP"  │  0x01   │  0x01    │   IPFS CID (46-59 bytes)          │
├────────┼─────────┼──────────┼────────────────────────────────────┤
│ 3 bytes│ 1 byte  │  1 byte  │          variable                  │
└────────┴─────────┴──────────┴────────────────────────────────────┘
```

### Operation Types

| Type | Byte | Description | Payload |
|:-----|:-----|:------------|:--------|
| ATTEST | `0x01` | Certificate issuance | IPFS CID |
| REVOKE | `0x02` | Certificate revocation | `TXID:VOUT` (+ optional reason) |
| UPDATE | `0x03` | Metadata update | New IPFS CID |

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

| Attack | Result | Protection |
|:-------|:------:|:-----------|
| Delegate diverts change | ❌ Blocked | Self-ref covenant |
| Non-standard certificate | ❌ Blocked | Script hash check |
| Third party forgery | ❌ Blocked | Schnorr signature |
| Unauthorized revocation | ❌ Blocked | Schnorr signature |
| Delegate drains vault | ❌ Blocked | Admin-only path |
| Invalid output count | ❌ Blocked | num_outputs check |

---

## Project Structure

```
sap/
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
│   └── test_edge_cases.py      # Security tests
│
├── docs/
│   ├── DOCUMENTATION.md        # Technical specification (EN)
│   ├── PROTOCOL_SPEC.md        # SAP protocol spec (EN)
│   └── pt/                     # Portuguese documentation
│
└── secrets.json                # Testnet keys/addresses
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

[Documentation](docs/DOCUMENTATION.md) • [Protocol Spec](docs/PROTOCOL_SPEC.md) • [Blockstream Report](BLOCKSTREAM_REPORT.md)

</div>
