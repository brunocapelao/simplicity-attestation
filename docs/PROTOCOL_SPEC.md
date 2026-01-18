# SAS - Simplicity Attestation Protocol

## Simplicity Attestation System (SAS)

**Version:** 1.0
**Date:** 2026-01-05
**Project:** Simplicity Attestation

---

## 1. Overview

The SAS protocol defines a standardized format for storing references to attestations (certificates) in OP_RETURN outputs of Liquid/Bitcoin transactions. The format allows indexers to quickly identify transactions related to the Simplicity Attestation system.

---

## 2. OP_RETURN Format

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          OP_RETURN STRUCTURE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌────────┬─────────┬──────────┬────────────────────────────────────────┐  │
│   │  TAG   │ VERSION │  TYPE    │              PAYLOAD                    │  │
│   │ 3 bytes│ 1 byte  │  1 byte  │           (variable)                    │  │
│   └────────┴─────────┴──────────┴────────────────────────────────────────┘  │
│                                                                              │
│   Total: 5 bytes header + payload (CID)                                      │
│   Maximum OP_RETURN: ~80 bytes → ~75 bytes for payload                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 TAG (3 bytes)

**Magic bytes** to identify the Simplicity Attestation protocol:

```
ASCII:  "SAS"
HEX:    0x534150
```

### 2.2 VERSION (1 byte)

Protocol version for future compatibility:

| Value | Meaning |
|-------|---------|
| `0x01` | Version 1.0 (current) |
| `0x02-0xFF` | Reserved for future versions |

### 2.3 TYPE (1 byte)

Operation/data type:

| Value | Type | Description |
|-------|------|-------------|
| `0x01` | ATTEST | Attestation issuance (CID in payload) |
| `0x02` | REVOKE | Revocation (attestation TXID in payload) |
| `0x03` | UPDATE | Metadata update (new CID) |
| `0x10` | DELEGATE | Authority delegation |
| `0x11` | UNDELEGATE | Delegation revocation |
| `0xFF` | RESERVED | Reserved |

### 2.4 PAYLOAD (variable)

Depends on TYPE:

| TYPE | Payload |
|------|---------|
| ATTEST | CID/identifier (variable, up to 75 bytes) |
| REVOKE | TXID:vout (34 bytes) |
| UPDATE | CID/identifier (variable, up to 75 bytes) |
| DELEGATE | Delegate pubkey (32 bytes) |
| UNDELEGATE | Delegate pubkey (32 bytes) |

---

## 3. Examples

### 3.1 Attestation Issuance

```
OP_RETURN:
┌────────────┬─────┬──────┬─────────────────────────────────────────────────┐
│    SAS     │ 01  │  01  │ QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG │
├────────────┼─────┼──────┼─────────────────────────────────────────────────┤
│ 534150     │ 01  │  01  │ (46 bytes - CIDv0 base58)                       │
└────────────┴─────┴──────┴─────────────────────────────────────────────────┘

Complete HEX:
534150 01 01 516d59774150...
```

Real Liquid testnet example (UTF-8 identifier payload):

- Issuance tx: `https://blockstream.info/liquidtestnet/tx/2785aac5ea950c54ece28b1fbfdeb5acf29903fed89ecbb78ba997fe0b927fcb`
- OP_RETURN (output `vout=2`): `534150010145582d4e45572d31373637373936313938` → `SAS|01|01|EX-NEW-1767796198`

### 3.2 Attestation Revocation

```
OP_RETURN:
┌────────────┬─────┬──────┬─────────────────────────────────────────────────┐
│    SAS     │ 01  │  02  │ <TXID>:<vout>                                   │
├────────────┼─────┼──────┼─────────────────────────────────────────────────┤
│ 534150     │ 01  │  02  │ (34 bytes - 32 bytes TXID + 2 bytes vout)       │
└────────────┴─────┴──────┴─────────────────────────────────────────────────┘
```

Real Liquid testnet example (reason + replacement):

- Revoke tx: `https://blockstream.info/liquidtestnet/tx/625dcfdac2ca7a2ddfb857254459c46e17939c7785c3e20c21f3ea33fb5be729`
- Decoded: `txid=912a79b929e331cfaf02727cd9f3282c8f87dd4a7af502c2ccf765feb5c12444`, `vout=1`, `reason_code=6`, `replacement_txid=2785aac5ea950c54ece28b1fbfdeb5acf29903fed89ecbb78ba997fe0b927fcb`

---

## 4. Indexer Algorithm

```python
def index_transaction(tx):
    for i, output in enumerate(tx.outputs):
        if not is_op_return(output):
            continue

        data = output.script_data

        # Check magic bytes
        if len(data) < 5:
            continue
        if data[0:3] != b'SAS':
            continue

        # Parse header
        version = data[3]
        op_type = data[4]
        payload = data[5:]

        if version != 0x01:
            log(f"Unknown version: {version}")
            continue

        # Process by type
        if op_type == 0x01:  # ATTEST
            cid = decode_cid(payload)
            index_attestation(tx.txid, i, cid)

        elif op_type == 0x02:  # REVOKE
            ref_txid = payload[0:32]
            ref_vout = int.from_bytes(payload[32:34], 'big')
            mark_revoked(ref_txid, ref_vout)

        elif op_type == 0x03:  # UPDATE
            cid = decode_cid(payload)
            update_attestation(tx.txid, i, cid)
```

---

## 5. Considerations

### 5.1 Versioning

The VERSION field allows protocol evolution while maintaining compatibility:
- Indexers should ignore versions they don't understand
- New versions can add fields to the header
- Payload structure can change between versions

### 5.2 On-chain Validation

The Simplicity contract can optionally validate the prefix:

```rust
// Verify that OP_RETURN starts with "SAS"
let maybe_datum = jet::output_null_datum(2, 0);
// Extract first 3 bytes and compare with 0x534150
```

### 5.3 Size

| Component | Size | Cumulative |
|-----------|------|------------|
| OP_RETURN max | 80 bytes | - |
| TAG (SAS) | 3 bytes | 3 |
| VERSION | 1 byte | 4 |
| TYPE | 1 byte | 5 |
| CIDv0 | 46 bytes | 51 |
| **Remaining** | 29 bytes | - |

For CIDv1 (longer), it still fits comfortably.

---

## 6. Type Registry

### Types Reserved for Expansion

| Range | Usage |
|-------|-------|
| `0x01-0x0F` | Attestation operations |
| `0x10-0x1F` | Delegation operations |
| `0x20-0x2F` | Metadata and extensions |
| `0x30-0xEF` | Reserved for future |
| `0xF0-0xFE` | Private/experimental use |
| `0xFF` | Reserved (do not use) |

---

## 7. Reference Implementation

### Encoder (Python)

```python
def encode_sas_attest(cid: str) -> bytes:
    """Encodes an attestation issuance OP_RETURN."""
    tag = b'SAS'
    version = bytes([0x01])
    op_type = bytes([0x01])  # ATTEST
    payload = cid.encode('utf-8')

    return tag + version + op_type + payload


def encode_sas_revoke(txid: bytes, vout: int) -> bytes:
    """Encodes a revocation OP_RETURN."""
    tag = b'SAS'
    version = bytes([0x01])
    op_type = bytes([0x02])  # REVOKE
    payload = txid + vout.to_bytes(2, 'big')

    return tag + version + op_type + payload
```

### Decoder (Python)

```python
from dataclasses import dataclass
from typing import Optional, Union

@dataclass
class SAPAttest:
    cid: str

@dataclass
class SAPRevoke:
    txid: bytes
    vout: int

def decode_sap(data: bytes) -> Optional[Union[SAPAttest, SAPRevoke]]:
    """Decodes a SAS OP_RETURN."""
    if len(data) < 5:
        return None
    if data[0:3] != b'SAS':
        return None

    version = data[3]
    op_type = data[4]
    payload = data[5:]

    if version != 0x01:
        return None

    if op_type == 0x01:  # ATTEST
        return SAPAttest(cid=payload.decode('utf-8'))
    elif op_type == 0x02:  # REVOKE
        return SAPRevoke(txid=payload[0:32], vout=int.from_bytes(payload[32:34], 'big'))

    return None
```

---

*Simplicity Attestation System (SAS) - Specification v1.0*
