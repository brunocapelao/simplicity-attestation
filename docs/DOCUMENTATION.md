# SAP - Simplicity Attestation Protocol

## On-Chain Certificate System with Delegation via Simplicity

**Version:** 2.0
**Date:** 2026-01-06
**Status:** Technical Specification

---

## 1. Overview

SAP is an on-chain digital certificate system that uses Simplicity on the Liquid Network to:

1. **Admin** (Root Authority) creates delegation vaults
2. **Delegate** issues certificates by spending from the vault
3. **Certificates** are UTXOs that represent valid attestations
4. **Revocation** occurs when the certificate UTXO is spent

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SAP CHAIN OF TRUST                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ADMIN (Root Authority)                                                    │
│      │                                                                      │
│      │ Creates vault with funding                                           │
│      ▼                                                                      │
│   ┌─────────────────────────────────────────┐                              │
│   │         DELEGATION VAULT                │                              │
│   │         (Simplicity Script V)           │                              │
│   │         Balance: N sats                 │                              │
│   └─────────────────────────────────────────┘                              │
│      │                                                                      │
│      ├──► Admin spends = DEACTIVATES delegate (empty vault)                │
│      │                                                                      │
│      └──► Delegate spends = ISSUES certificate                             │
│              │                                                              │
│              ├── Output 0: Change → Vault V (ENFORCED by script)           │
│              ├── Output 1: Certificate UTXO → Script C                     │
│              ├── Output 2: OP_RETURN with SAP payload (CID/identifier)     │
│              └── Output 3: Fee                                              │
│                       │                                                     │
│                       ▼                                                     │
│              ┌─────────────────────────────────────────┐                   │
│              │       CERTIFICATE UTXO                  │                   │
│              │       (Simplicity Script C)             │                   │
│              │                                         │                   │
│              │   UTXO exists = Certificate VALID       │                   │
│              │   UTXO spent  = Certificate REVOKED     │                   │
│              └─────────────────────────────────────────┘                   │
│                       │                                                     │
│                       ├──► Admin spends = REVOKES certificate              │
│                       └──► Delegate spends = REVOKES certificate           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

  Permissions Summary

  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                           PERMISSIONS MATRIX                                │
  ├─────────────────────────────────────────────────────────────────────────────┤
  │                                                                             │
  │  ACTION                              │  ADMIN  │  DELEGATE  │              │
  │  ──────────────────────────────────┼─────────┼────────────┤              │
  │  Issue certificate (vault)          │   ✅    │     ✅     │              │
  │  Revoke certificate                  │   ✅    │     ✅     │              │
  │  Deactivate delegate (drain)         │   ✅    │     ❌     │              │
  │  Spend vault unconditionally         │   ✅    │     ❌     │              │
  │                                                                             │
  ├─────────────────────────────────────────────────────────────────────────────┤
  │                                                                             │
  │  CHAIN OF TRUST:                                                            │
  │                                                                             │
  │  Admin (Supreme Authority)                                                  │
  │    ├── Can deactivate Delegate at any time                                 │
  │    ├── Can revoke any certificate                                          │
  │    └── Can issue certificates (with covenants via Right-Left path)         │
  │                                                                             │
  │  Delegate (Delegated Authority)                                             │
  │    ├── Can issue certificates (while vault has funds)                      │
  │    ├── Can revoke own certificates                                         │
  │    └── CANNOT prevent Admin from deactivating them                         │
  │                                                                             │
  └─────────────────────────────────────────────────────────────────────────────┘

  Visual Flow

                      ADMIN
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
     DEACTIVATE      REVOKE        ISSUE
     DELEGATE     CERTIFICATE   CERTIFICATE
          │             │        (w/covenants)
          ▼             ▼             │
     Empty vault   Cert UTXO          ▼
                    spent        New Cert
                                   UTXO


                    DELEGATE
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
       ISSUE        REVOKE       (no deactivate)
    CERTIFICATE   CERTIFICATE
          │             │
          ▼             ▼
     New Cert      Cert UTXO
       UTXO         spent

---

## 2. Fundamental Principle

### Certificate State via UTXO

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                      CERTIFICATE VALIDITY RULE                             ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║   Certificate UTXO NOT SPENT  ──►  Certificate VALID   ✓                  ║
║   Certificate UTXO SPENT      ──►  Certificate REVOKED ✗                  ║
║                                                                           ║
║   Validity is verified by querying the blockchain:                        ║
║   - If UTXO exists (unspent) = certificate active                         ║
║   - If UTXO was spent = certificate revoked                               ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

### Indexing and Verification

To verify a certificate:

```python
def verify_certificate(txid: str, vout: int) -> bool:
    """
    Verifies if a certificate is valid.

    Args:
        txid: Transaction ID where the certificate was issued
        vout: Output index of the certificate UTXO

    Returns:
        True if valid (UTXO not spent), False if revoked (UTXO spent)
    """
    utxo_status = get_utxo_status(txid, vout)
    return utxo_status == "unspent"
```

---

## 3. Technical Architecture

### 3.1 System Components

| Component | Type | Description |
|-----------|------|-------------|
| **Delegation Vault (V)** | Simplicity Script | Funding pool for certificate issuance |
| **Certificate (C)** | Simplicity Script | UTXO representing a valid certificate |
| **OP_RETURN** | Data | SAP payload with CID/identifier for the certificate |
| **Admin Key** | Schnorr Pubkey | Root authority of the system |
| **Delegate Key** | Schnorr Pubkey | Delegated authority to issue certificates |

### 3.2 Delegation Vault (Script V)

The vault uses Simplicity's **disconnect combinator** to ensure change returns to the same address:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DELEGATION VAULT SCRIPT                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Witness: Either<AdminSig, (DelegateSig, OutputProof)>                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ LEFT PATH (Admin)                                                    │   │
│  │ ─────────────────                                                    │   │
│  │ 1. Verify Admin signature                                            │   │
│  │ 2. Can spend unconditionally                                         │   │
│  │    → DEACTIVATES the delegate (vault becomes empty)                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ RIGHT PATH (Delegate)                                                │   │
│  │ ──────────────────────                                               │   │
│  │ 1. Verify Delegate signature                                         │   │
│  │                                                                      │   │
│  │ 2. COVENANT: Verify output[0] (Change)                              │   │
│  │    - script_pubkey == VAULT_SCRIPT_PUBKEY (same address)            │   │
│  │    - amount >= input_amount - cert_amount - fee                      │   │
│  │    *** ENFORCED BY CODE, NOT BY INCENTIVE ***                       │   │
│  │                                                                      │   │
│  │ 3. COVENANT: Verify output[1] (Certificate)                         │   │
│  │    - script_pubkey == CERTIFICATE_SCRIPT_PUBKEY                     │   │
│  │    - amount >= DUST_LIMIT (546 sats)                                │   │
│  │                                                                      │   │
│  │ 4. Verify output[2] (OP_RETURN)                                     │   │
│  │    - Must exist and contain data                                     │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Certificate (Script C)

Simple script that allows Admin OR Delegate to spend (revoke):

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CERTIFICATE SCRIPT                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Witness: Either<AdminSig, DelegateSig>                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ LEFT PATH (Admin) or RIGHT PATH (Delegate)                          │   │
│  │ ─────────────────────────────────────────────                        │   │
│  │ 1. Verify signature (Admin or Delegate)                              │   │
│  │ 2. Can spend unconditionally                                         │   │
│  │    → REVOKES the certificate                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Note: The act of spending this UTXO = revoking the certificate            │
│  Optionally may include OP_RETURN with SAP type REVOKE                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Disconnect Combinator and Self-Reference

### The Self-Reference Problem

To ensure change returns to the same vault, the script needs to verify that the output goes to "itself". This creates a circular problem:

```
Script needs script_pubkey → script_pubkey depends on CMR → CMR depends on script
```

### The Solution: Disconnect Combinator

Simplicity solves this with the `disconnect` combinator:

```
disconnect(committed_expr, disconnected_expr_cmr)
```

**How it works:**
1. The `committed_expr` (main logic) is included in the CMR
2. The `disconnected_expr` is provided in the witness, but its CMR is passed as data
3. This allows the script to know its own CMR without circular dependency

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DISCONNECT COMBINATOR PATTERN                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  VaultScript = disconnect(                                                  │
│      MainLogic,           // Committed: output verifications               │
│      SpendingRules_CMR    // Disconnected CMR: flexible rules              │
│  )                                                                          │
│                                                                             │
│  MainLogic = {                                                              │
│      // Can access its own CMR!                                             │
│      let my_cmr = get_cmr();                                               │
│      let expected_script = taproot_scriptpubkey(internal_key, my_cmr);     │
│                                                                             │
│      // Verify that output[0] goes to the same address                     │
│      let output_script = jet::output_script_hash(0);                       │
│      assert(output_script == sha256(expected_script));                     │
│  }                                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Available Introspection Jets

| Jet | Description | Usage |
|-----|-------------|-------|
| `jet::output_script_hash(u32)` | Hash of output N's scriptPubKey | Verify destination |
| `jet::output_amount(u32)` | Value of output N | Verify amount |
| `jet::output_asset(u32)` | Asset ID of output N (Liquid) | Verify asset |
| `jet::output_null_datum(u32, u32)` | OP_RETURN data | Verify CID |
| `jet::current_index()` | Current input index | Self-reference |
| `jet::input_script_hash(u32)` | Hash of input N's script | Comparison |

---

## 5. Operation Flows

### 5.1 Setup: System Creation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INITIAL SETUP                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Admin generates key pair (admin_privkey, admin_pubkey)                 │
│  2. Delegate generates key pair (delegate_privkey, delegate_pubkey)        │
│                                                                             │
│  3. Compile Certificate Script (C):                                         │
│     - Input: admin_pubkey, delegate_pubkey                                 │
│     - Output: CMR_C, CERTIFICATE_SCRIPT_PUBKEY                             │
│                                                                             │
│  4. Compile Vault Script (V):                                               │
│     - Input: admin_pubkey, delegate_pubkey, CERTIFICATE_SCRIPT_PUBKEY      │
│     - Output: CMR_V, VAULT_SCRIPT_PUBKEY                                   │
│                                                                             │
│  5. Admin sends funds to VAULT_ADDRESS                                      │
│     → System active, Delegate can issue certificates                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Certificate Issuance

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CERTIFICATE ISSUANCE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DELEGATE executes:                                                         │
│                                                                             │
│  1. Creates document/certificate off-chain                                 │
│  2. Uploads to IPFS (optional) → gets CID/identifier                        │
│  3. Builds transaction:                                                     │
│                                                                             │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │ Issuance TX                                                      │    │
│     ├─────────────────────────────────────────────────────────────────┤    │
│     │ Input 0: Vault UTXO (spent with delegate path)                  │    │
│     │                                                                  │    │
│     │ Output 0: Change → Vault Address (ENFORCED)                     │    │
│     │           Value: input - cert_amount - fee                       │    │
│     │                                                                  │    │
│     │ Output 1: Certificate UTXO → Certificate Address                │    │
│     │           Valor: 546 sats (dust)                                │    │
│     │                                                                  │    │
│     │ Output 2: OP_RETURN                                             │    │
│     │           Data: SAP 01 01 <CID_OR_IDENTIFIER>                    │    │
│     │                                                                  │    │
│     │ Output 3: Fee                                                   │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  4. Signs and broadcasts                                                    │
│  5. Certificate issued! UTXO at Output 1 represents the certificate        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Certificate Revocation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CERTIFICATE REVOCATION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ADMIN or DELEGATE executes:                                                │
│                                                                             │
│  1. Identifies the Certificate UTXO to revoke (txid:vout)                  │
│  2. Builds transaction spending the Certificate UTXO                       │
│                                                                             │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │ Revocation TX                                                    │    │
│     ├─────────────────────────────────────────────────────────────────┤    │
│     │ Input 0: Certificate UTXO (spent with admin or delegate path)   │    │
│     │                                                                  │    │
│     │ Output 0: Any address (recovers the sats)                       │    │
│     │                                                                  │    │
│     │ Output 1: OP_RETURN (optional)                                  │    │
│     │           Data: SAP 01 02 <ORIGINAL_TXID:VOUT>                  │    │
│     │                                                                  │    │
│     │ Output 2: Fee                                                   │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  3. Signs and broadcasts                                                    │
│  4. Certificate revoked! Spent UTXO = invalid certificate                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.4 Delegate Deactivation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DELEGATE DEACTIVATION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Only ADMIN can execute:                                                    │
│                                                                             │
│  1. Identifies the Vault UTXO                                              │
│  2. Spends using admin path (unconditional)                                │
│  3. Sends funds anywhere they want                                         │
│                                                                             │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │ Deactivation TX                                                  │    │
│     ├─────────────────────────────────────────────────────────────────┤    │
│     │ Input 0: Vault UTXO (spent with admin path)                     │    │
│     │                                                                  │    │
│     │ Output 0: Any address (Admin recovers funds)                    │    │
│     │                                                                  │    │
│     │ Output 1: Fee                                                   │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  4. Empty vault = Delegate can no longer issue certificates                │
│                                                                             │
│  Note: Already issued certificates remain valid!                           │
│  To invalidate existing certificates, Admin must revoke each one.          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. SAP Protocol (OP_RETURN)

### 6.1 Format

```
┌───────┬─────────┬──────────┬─────────────────────────────────────┐
│  TAG  │ VERSION │   TYPE   │             PAYLOAD                 │
│ "SAP" │  0x01   │  0x01    │   CID/identifier (≤75 bytes)       │
├───────┼─────────┼──────────┼─────────────────────────────────────┤
│3 bytes│ 1 byte  │  1 byte  │           variable                  │
└───────┴─────────┴──────────┴─────────────────────────────────────┘
```

### 6.2 Operation Types

| Type | Byte | Description | Payload |
|------|------|-------------|---------|
| ATTEST | `0x01` | Certificate issuance | CID/identifier (UTF-8 or raw bytes) |
| REVOKE | `0x02` | Certificate revocation | TXID:VOUT (34 bytes) |
| UPDATE | `0x03` | Metadata update | New CID/identifier |

### 6.3 Examples

**Issuance:**
```
5341500101516d59774150...
│     │ │ └── CID: QmYwAP...
│     │ └──── Type: ATTEST (0x01)
│     └────── Version: 1
└──────────── Magic: "SAP"
```

**Revocation:**
```
534150010212ab34cd56ef...0001
│     │ │ └── Referenced TXID:VOUT
│     │ └──── Type: REVOKE (0x02)
│     └────── Version: 1
└──────────── Magic: "SAP"
```

---

## 7. Security Considerations

### 7.1 System Guarantees

| Property | Guarantee | Mechanism |
|----------|-----------|-----------|
| **Change goes to vault** | Enforced by code | Covenant with script_pubkey verification |
| **Certificate goes to script C** | Enforced by code | Hardcoded covenant |
| **Only Admin deactivates** | Enforced by code | Signature verification |
| **Admin OR Delegate revoke** | Enforced by code | Either path in certificate |
| **Certificate valid if UTXO exists** | UTXO property | Bitcoin model |

### 7.2 Mitigated Attack Vectors

1. **Delegate diverts change**: Impossible - covenant verifies destination
2. **Delegate creates fake certificate**: Impossible - script_pubkey verified
3. **Third party revokes certificate**: Impossible - requires Admin or Delegate signature
4. **Double-spend of certificate**: Impossible - UTXO model prevents this

### 7.3 Known Limitations

1. **Admin can revoke any certificate**: By design - Admin is root authority
2. **Delegate can revoke own certificates**: By design - allows error correction
3. **Certificates persist after deactivation**: By design - revocation is separate

---

## 8. Implementation

### 8.1 Dependencies

| Tool | Version | Usage |
|------|---------|-------|
| simc | latest | Simfony → Simplicity compiler |
| hal-simplicity | fork | CLI for PSET and broadcast |
| embit | latest | Schnorr signatures (Python) |

### 8.2 System Files

```
contracts/
├── vault.simf              # Delegation Vault with covenants
└── certificate.simf        # Certificate script

tests/
├── test_emit.py            # Certificate emission test
├── test_certificate_revoke.py  # Revocation test
└── test_edge_cases.py      # Security tests

docs/
├── DOCUMENTATION.md        # This specification (English)
├── PROTOCOL_SPEC.md        # SAP protocol specification (English)
└── pt/
    ├── DOCUMENTACAO.md     # Specification (Portuguese)
    ├── PROTOCOL_SPEC.md    # SAP protocol specification (Portuguese)
    └── SDK.md              # SDK documentation (Portuguese)
```

### 8.3 External Signing (Hardware Wallets / Multisig / Custody)

The SDK supports **external signing** for scenarios where private keys are managed outside the SDK:

- **Hardware Wallets** (Ledger, Trezor, Coldcard)
- **Multisig Ceremonies** (multiple signers required)
- **Custodial Services** (keys held by third party)
- **HSM Integration** (Hardware Security Modules)

#### Workflow: Prepare → Sign Externally → Finalize

```python
from sdk import SAPClient, SAPConfig
from sdk.infra.hal import HalSimplicity

client = SAPClient(
    config=SAPConfig.from_file("config.json"),
    hal=HalSimplicity("/path/to/hal-simplicity", network="liquid"),
)

# ============================================
# STEP 1: Prepare Transaction (SDK builds it)
# ============================================
prepared = client.prepare_issue_certificate(
    cid="QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
    issuer="admin"  # or "delegate"
)

# Display information for approval
print(prepared.summary())
"""
=== ISSUE_CERTIFICATE ===
Signer: admin
Hash to sign: a1b2c3d4...e5f6g7h8
cid: QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG
vault_utxo: abc123:0
vault_balance: 50000
"""

# Get the hash that needs to be signed
sig_hash = prepared.sig_hash           # Hex string
sig_hash_bytes = prepared.sig_hash_bytes  # 32-byte bytes

# ============================================
# STEP 2: Sign Externally
# ============================================
# Send sig_hash to your external signer:
# - Hardware wallet via USB
# - Multisig ceremony via PSBT sharing
# - Custody API call
# - HSM signing service

signature = my_external_signer.sign(sig_hash_bytes)  # Returns 64-byte Schnorr sig

# ============================================
# STEP 3: Finalize and Broadcast
# ============================================
result = client.finalize_transaction(prepared, signature)

if result.success:
    print(f"Transaction broadcast: {result.txid}")
else:
    print(f"Error: {result.error}")
```

#### Available Preparation Methods

| Method | Description | Signer |
|--------|-------------|--------|
| `prepare_issue_certificate(cid, issuer)` | Prepare certificate issuance | Admin or Delegate |
| `prepare_revoke_certificate(txid, vout, revoker)` | Prepare revocation | Admin or Delegate |
| `prepare_drain_vault(recipient)` | Prepare vault drain | Admin only |

#### PreparedTransaction Object

```python
prepared.tx_type           # TransactionType enum (ISSUE, REVOKE, DRAIN)
prepared.sig_hash          # 32-byte hash as hex string
prepared.sig_hash_bytes    # 32-byte hash as bytes
prepared.signer_role       # "admin" or "delegate"
prepared.required_pubkey   # Expected signer's public key
prepared.details           # Dict with human-readable operation details
prepared.is_expired        # Check if transaction expired (optional timeout)
prepared.summary()         # Human-readable summary for approval UI
prepared.to_json()         # JSON serialization for API transport
```

#### Implementing an External Signer

```python
from sdk.prepared import ExternalSignerProtocol

class MyHardwareWallet(ExternalSignerProtocol):
    """Example external signer implementation."""
    
    def sign(self, message_hash: bytes) -> bytes:
        """
        Sign a 32-byte message hash.
        
        Args:
            message_hash: 32-byte hash to sign (sig_hash from PreparedTransaction)
        
        Returns:
            64-byte Schnorr signature
        """
        # Connect to hardware wallet
        # Display message for user confirmation
        # Return signature
        return self.device.schnorr_sign(message_hash)
    
    def get_public_key(self) -> str:
        """Get the signer's x-only public key (64 hex chars)."""
        return self.device.get_public_key()
```

### 8.4 Simfony Pseudo-code

**vault.simf:**
```rust
// Delegation Vault - With Enforced Covenants

mod witness {
    // Either<AdminSig, DelegateSig>
    const SPENDING_PATH: Either<Signature, Signature>;
}

// Constants (hardcoded at compilation)
const ADMIN_PUBKEY: Pubkey = 0x...;
const DELEGATE_PUBKEY: Pubkey = 0x...;
const CERTIFICATE_SCRIPT_HASH: u256 = 0x...; // Hash of certificate script
const VAULT_SCRIPT_HASH: u256 = 0x...;       // Hash of own script (self-ref)
const CERT_MIN_AMOUNT: u64 = 1000;           // Minimum for certificate

fn checksig(pk: Pubkey, sig: Signature) {
    let msg: u256 = jet::sig_all_hash();
    jet::bip_0340_verify((pk, msg), sig);
}

fn admin_spend(admin_sig: Signature) {
    // Admin can spend unconditionally
    checksig(ADMIN_PUBKEY, admin_sig);
}

fn delegate_spend(delegate_sig: Signature) {
    // 1. Verify delegate signature
    checksig(DELEGATE_PUBKEY, delegate_sig);

    // 2. COVENANT: Output 0 must go to vault (change)
    let output0_script: u256 = jet::output_script_hash(0);
    assert!(output0_script == VAULT_SCRIPT_HASH);

    // 3. COVENANT: Output 1 must go to certificate script
    let output1_script: u256 = jet::output_script_hash(1);
    assert!(output1_script == CERTIFICATE_SCRIPT_HASH);

    // 4. Verify minimum certificate amount
    let output1_amount: u64 = jet::output_amount(1);
    assert!(output1_amount >= CERT_MIN_AMOUNT);

    // 5. Verify that OP_RETURN exists (output 2)
    let maybe_datum = jet::output_null_datum(2, 0);
    match maybe_datum {
        Some(_) => { /* OK */ },
        None => panic!(),
    };
}

fn main() {
    match witness::SPENDING_PATH {
        Left(admin_sig) => admin_spend(admin_sig),
        Right(delegate_sig) => delegate_spend(delegate_sig),
    }
}
```

**certificate.simf:**
```rust
// Certificate Script - Admin or Delegate can revoke

mod witness {
    const SPENDING_PATH: Either<Signature, Signature>;
}

const ADMIN_PUBKEY: Pubkey = 0x...;
const DELEGATE_PUBKEY: Pubkey = 0x...;

fn checksig(pk: Pubkey, sig: Signature) {
    let msg: u256 = jet::sig_all_hash();
    jet::bip_0340_verify((pk, msg), sig);
}

fn main() {
    match witness::SPENDING_PATH {
        Left(admin_sig) => checksig(ADMIN_PUBKEY, admin_sig),
        Right(delegate_sig) => checksig(DELEGATE_PUBKEY, delegate_sig),
    }
}
```

---

## 9. Certificate Verification

### 9.1 On-Chain Query

```python
def verify_certificate(cert_txid: str, cert_vout: int = 1) -> dict:
    """
    Verifies the status of a certificate.

    Returns:
        {
            "valid": bool,
            "cid": str,            # CID/identifier (UTF-8 or hex)
            "issued_at": int,      # Block height
            "revoked_at": int,     # Block height (if revoked)
            "issued_by": str,      # Delegate pubkey
        }
    """
    # 1. Check if UTXO exists (not spent)
    utxo = get_utxo(cert_txid, cert_vout)

    # 2. Get OP_RETURN data from issuance TX
    tx = get_transaction(cert_txid)
    op_return_data = parse_op_return(tx.outputs[2])

    # 3. Decode SAP
    sap = decode_sap(op_return_data)

    return {
        "valid": utxo is not None,
        "cid": sap.cid,
        "issued_at": tx.block_height,
        "revoked_at": None if utxo else get_spend_height(cert_txid, cert_vout),
    }
```

### 9.2 Indexer API

```
GET /api/v1/certificate/{txid}/{vout}

Response:
{
    "status": "valid" | "revoked",
    "cid": "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
    "issuer": "tex1...",
    "issued_at": 2256100,
    "revoked_at": null,
    "vault_address": "tex1pewrql3..."
}
```

---

## 10. Roadmap

### Phase 1: MVP (Current)
- [x] Basic P2PK with OP_RETURN
- [x] Vault v1 (without change covenant)
- [x] Vault with enforced covenants
- [x] Certificate script
- [x] Emission/revocation scripts

### Phase 2: Production
- [ ] Certificate indexer
- [ ] Verification API
- [ ] Web interface

### Phase 3: Extensions
- [ ] Multi-delegate
- [ ] Spend limits per delegate
- [ ] Delegation expiration

---

## 11. References

- [Disconnecting Simplicity Expressions](https://blog.blockstream.com/disconnecting-simplicity-expressions/)
- [Simplicity: Taproot and Universal Sighashes](https://blog.blockstream.com/simplicity-taproot-and-universal-sighashes/)
- [Covenants in Production on Liquid](https://blog.blockstream.com/covenants-in-production-on-liquid/)
- [Elements Introspection Opcodes](https://github.com/ElementsProject/elements/blob/master/doc/tapscript_opcodes.md)
- [BlockstreamResearch/simplicity](https://github.com/BlockstreamResearch/simplicity)
- [BlockstreamResearch/simfony](https://github.com/BlockstreamResearch/simfony)

---

*SAP - Simplicity Attestation Protocol - Specification v2.0*
