# Email Response Draft — Simplicity Developer

> **Subject:** RE: Certificate verification approach — architecture details & first production application

---

Hi [Developer],

Thank you so much for the thoughtful and detailed feedback. It was incredibly valuable — your concerns about Explorer API centralization are well-taken, and we've used them to refine our architecture and trust model.

I'd like to share how our system actually works in practice, because I think the full picture addresses most of the concerns raised. We also have our first real application built on top of the Simplicity Attestation System, which I'll describe below.

## Our Architecture: Not Just the Explorer

The key insight is that **we don't rely solely on the Explorer API**. Our system has its own indexer with a database that tracks certificate lifecycle independently. The Explorer API is one of multiple data sources, not the single source of truth.

Here's our system architecture:

### C4 Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SYSTEM CONTEXT                                 │
│                                                                         │
│  ┌──────────┐         ┌──────────────────────────┐                      │
│  │          │         │   SAS Indexer            │                      │
│  │  Admin / │ REST    │   (FastAPI Backend)      │     ┌──────────────┐ │
│  │ Delegate ├────────►│                          ├────►│ IPFS / Pinata│ │
│  │  (User)  │   API   │  - Certificate lifecycle │     │(Decentralized│ │
│  │          │         │  - DAO management        │     │   Storage)   │ │
│  └──────────┘         │  - Verification cache    │     └──────────────┘ │
│                       │  - Audit logging         │                      │
│       ┌──────────┐    └─────┬──────────┬─────────┘                      │
│       │ Frontend │          │          │                                │
│       │ React +  │          │          │                                │
│       │  Vite    │          │          │                                │
│       └──────────┘          │          │                                │
│                             │          │                                │
│                             ▼          ▼                                │
│                    ┌────────────┐  ┌──────────────────┐                 │
│                    │ PostgreSQL │  │ Liquid Network   │                 │
│                    │ (Indexer   │  │                  │                 │
│                    │  Database) │  │ ┌──────────────┐ │                 │
│                    │            │  │ │ Blockstream  │ │                 │
│                    │ - Records  │  │ │ Esplora API  │ │                 │
│                    │ - Versions │  │ └──────────────┘ │                 │
│                    │ - Audit    │  │                  │                 │
│                    └────────────┘  │ ┌──────────────┐ │                 │
│                                    │ │ Elements RPC │ │                 │
│                                    │ │ (future/prod)│ │                 │
│                                    │ └──────────────┘ │                 │
│                                    └──────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────┘
```

### C4 Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SAS INDEXER (Containers)                          │
│                                                                             │
│  ┌──────────────────┐    ┌───────────────────────────────────────────────┐  │
│  │    Frontend       │    │              Backend (FastAPI)                │  │
│  │    React + Vite   │    │                                              │  │
│  │                   │    │  ┌─────────────┐  ┌────────────────────────┐ │  │
│  │  - DAO Dashboard  │    │  │  DAO Module  │  │    Core Services       │ │  │
│  │  - Certificate    │    │  │             │  │                        │ │  │
│  │    Viewer         │    │  │ - CRUD API   │  │ ┌──────────────────┐  │ │  │
│  │  - Verification   ├───►│  │ - Versioning│  │ │  SAS Adapter     │  │ │  │
│  │    Status         │    │  │ - Replace   │  │ │  (SDK Wrapper)   │  │ │  │
│  │                   │    │  │ - Revoke    │  │ │                  │  │ │  │
│  └──────────────────┘    │  └──────┬──────┘  │ │ - prepare_cert() │  │ │  │
│                          │         │         │ │ - finalize()     │  │ │  │
│                          │         │         │ │ - verify()       │  │ │  │
│                          │         ▼         │ └────────┬─────────┘  │ │  │
│                          │  ┌──────────────┐ │          │            │ │  │
│                          │  │   Signing    │ │ ┌────────┴─────────┐  │ │  │
│                          │  │   Service    │ │ │  IPFS Client     │  │ │  │
│                          │  │             │ │ │  (Kubo / Pinata) │  │ │  │
│                          │  │ - Offline   │ │ └──────────────────┘  │ │  │
│                          │  │   signing   │ │                       │ │  │
│                          │  │ - No keys   │ │ ┌──────────────────┐  │ │  │
│                          │  │   on server │ │ │  Blockchain      │  │ │  │
│                          │  └─────────────┘ │ │  Provider        │  │ │  │
│                          │                  │ │  (Esplora API    │  │ │  │
│                          │                  │ │   or Elements    │  │ │  │
│                          │                  │ │   RPC)           │  │ │  │
│                          │                  │ └──────────────────┘  │ │  │
│                          │                  └────────────────────────┘ │  │
│                          └───────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────┐   ┌───────────┐   ┌───────────────┐   ┌───────────────┐  │
│  │ PostgreSQL   │   │  Redis    │   │  Background   │   │  Audit Log    │  │
│  │              │   │  Cache    │   │  Jobs         │   │               │  │
│  │ - dao_records│   │           │   │               │   │ - All state   │  │
│  │ - signing_   │   │ - Verify  │   │ - Reconcile   │   │   changes     │  │
│  │   requests   │   │   cache   │   │   blockchain  │   │ - Who/when/   │  │
│  │ - attestation│   │ - Rate    │   │ - Cleanup     │   │   what        │  │
│  │ - audit_log  │   │   limit   │   │   expired     │   │               │  │
│  └──────────────┘   └───────────┘   └───────────────┘   └───────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Certificate Lifecycle Flow

This is the complete flow from issuance to verification:

```
                        CERTIFICATE LIFECYCLE
                        =====================

  ┌──────────┐                                          ┌──────────────┐
  │  Admin/  │                                          │   Verifier   │
  │ Delegate │                                          │  (any user)  │
  └────┬─────┘                                          └──────┬───────┘
       │                                                       │
       │  1. Issue Certificate                                 │
       │  ─────────────────                                    │
       ▼                                                       │
  ┌─────────────────┐                                          │
  │ Upload doc to   │                                          │
  │ IPFS → get CID  │                                          │
  └────────┬────────┘                                          │
           │                                                   │
           ▼                                                   │
  ┌─────────────────┐     ┌──────────────┐                     │
  │ SAS SDK:        │     │ Liquid       │                     │
  │ prepare_cert()  ├────►│ Network      │                     │
  │ → sig_hash      │     │              │                     │
  └────────┬────────┘     │ Tx creates:  │                     │
           │              │ - Vault UTXO │                     │
           ▼              │   (change)   │                     │
  ┌─────────────────┐     │ - Cert UTXO  │                     │
  │ External signer │     │   (546 sats) │                     │
  │ signs sig_hash  │     │ - OP_RETURN  │                     │
  │ → signature     │     │   (SAS+CID)  │                     │
  └────────┬────────┘     │ - Fee        │                     │
           │              └──────┬───────┘                     │
           ▼                     │                             │
  ┌─────────────────┐            │                             │
  │ finalize() →    │            │                             │
  │ broadcast tx    ├────────────┘                             │
  └────────┬────────┘                                          │
           │                                                   │
           ▼                                                   │
  ┌─────────────────┐                                          │
  │ Store in DB:    │                                          │
  │ - txid, vout    │                                          │
  │ - ipfs_cid      │          5. Verify Certificate           │
  │ - dao_id        │          ────────────────────            │
  │ - version       │                                          │
  │ - status        │                                          ▼
  └─────────────────┘                                 ┌────────────────┐
                                                      │  GET /verify   │
                                                      │  ?txid=...     │
  2. Certificate is VALID                             └───────┬────────┘
  ───────────────────────                                     │
                                                              ▼
  ┌──────────────────────────────────────────┐        ┌────────────────┐
  │  UTXO exists at certificate address      │        │ Check DB first │
  │  ═══════════════════════════════════════ │        │ (cached state) │
  │                                          │        └───────┬────────┘
  │  Blockchain: cert UTXO is UNSPENT  ✓     │                │
  │  DB Indexer: status = "valid"      ✓     │                ▼
  │  IPFS: document retrievable        ✓     │        ┌────────────────┐
  │                                          │        │ Confirm on     │
  │  → Certificate is VALID                  │        │ blockchain     │
  └──────────────────────────────────────────┘        │ (Esplora or    │
                                                      │  Elements RPC) │
                                                      └───────┬────────┘
  3. Revoke Certificate                                       │
  ─────────────────────                                       ▼
                                                      ┌────────────────┐
  ┌─────────────────┐     ┌──────────────┐            │ Extract CID    │
  │ Admin/Delegate  │     │ Liquid       │            │ from OP_RETURN │
  │ spends cert     ├────►│ Network      │            │ Compare with   │
  │ UTXO            │     │              │            │ IPFS document  │
  └────────┬────────┘     │ Cert UTXO    │            └───────┬────────┘
           │              │ is now SPENT │                    │
           ▼              └──────┬───────┘                    ▼
  ┌─────────────────┐            │                   ┌─────────────────┐
  │ Update DB:      │            │                   │ Return result:  │
  │ revoked = true  │◄───────────┘                   │ - valid: bool   │
  │ revocation_tx   │                                │ - confirmations │
  │ reason_code     │                                │ - cid_match     │
  └─────────────────┘                                │ - status        │
                                                     └─────────────────┘

  4. Certificate is REVOKED
  ─────────────────────────

  ┌──────────────────────────────────────────┐
  │  UTXO spent at certificate address       │
  │  ═══════════════════════════════════════ │
  │                                          │
  │  Blockchain: cert UTXO is SPENT    ✗     │
  │  DB Indexer: revoked = true        ✗     │
  │  IPFS: document still exists       ✓     │
  │  (immutable history preserved)           │
  │                                          │
  │  → Certificate is REVOKED                │
  └──────────────────────────────────────────┘
```

## Trust Model — Addressing Your Concerns

Here's how our trust model works across different deployment scenarios:

```
TRUST MODEL COMPARISON
══════════════════════

  Concern raised              MVP (current)             Production (planned)
  ─────────────────────────   ───────────────────────   ──────────────────────

  "Explorer API could        DB Indexer is primary      Elements RPC replaces
   hide revocations"         source; Esplora is         Esplora entirely.
                             secondary confirmation.    Direct UTXO set query.
                             Two independent sources    Zero third-party trust.
                             must agree.

  "Explorer API could        System continues to        Elements node is self-
   be discontinued"          function from DB alone.    hosted. No external
                             Degraded but operational.  dependency.

  "Why blockchain if         Blockchain provides:       Same guarantees, plus:
   centralized?"             - Immutable issuance       - Trustless verification
                             - Covenant enforcement     - No API dependency
                             - Public auditability      - Full sovereignty
                             DB provides:
                             - Fast queries
                             - Version chains
                             - Revocation metadata
```

### Verification: Defense in Depth

```
┌─────────────────────────────────────────────────────────────────┐
│                    VERIFICATION LAYERS                           │
│                                                                  │
│  Layer 1: Database (fastest, always available)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SELECT * FROM dao_records                               │   │
│  │  WHERE tx = ? AND vout = ? AND revoked = false           │   │
│  │                                                          │   │
│  │  → Instant response, works even if blockchain is slow    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  Layer 2: Blockchain confirmation (authoritative)                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  MVP:   Esplora API  →  GET /address/{addr}/utxo         │   │
│  │  Prod:  Elements RPC →  gettxout(txid, vout)             │   │
│  │                                                          │   │
│  │  → Confirms DB state against actual UTXO set             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  Layer 3: Content verification (integrity)                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Extract CID from OP_RETURN → Fetch from IPFS            │   │
│  │  Compare document hash with on-chain CID                  │   │
│  │                                                          │   │
│  │  → Proves document hasn't been tampered with              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  Result: VALID only if ALL layers agree                          │
└─────────────────────────────────────────────────────────────────┘
```

## First Application: Wyoming DAO LLC Registry

Our first production application is a **DAO Attestation and Registry System** for Wyoming DAO LLCs. Here's how it uses the Simplicity Attestation System:

```
┌──────────────────────────────────────────────────────────────────┐
│                   WYOMING DAO LLC REGISTRY                        │
│                                                                   │
│   What it does:                                                   │
│   - Issues blockchain-backed certificates for DAO registrations   │
│   - Stores DAO operating agreements on IPFS                       │
│   - Manages certificate versioning (governance changes)           │
│   - Handles revocation with reason codes                          │
│   - Provides public verification API                              │
│                                                                   │
│   Certificate lifecycle for a DAO:                                │
│                                                                   │
│   v1: Initial registration                                        │
│   ┌────────────────────────────────┐                              │
│   │ dao_id: da1df5k3q00h7m9p       │                              │
│   │ name: "Wyoming Tech DAO LLC"   │                              │
│   │ tx: abc123...  (cert UTXO)     │  ← VALID (UTXO unspent)     │
│   │ ipfs: QmXyz... (agreement)     │                              │
│   │ version: 1                     │                              │
│   └────────────────────────────────┘                              │
│                    │                                              │
│                    │  Governance change                           │
│                    ▼                                              │
│   v2: Updated governance                                          │
│   ┌────────────────────────────────┐                              │
│   │ dao_id: da1df5k3q00h7m9p       │                              │
│   │ name: "Wyoming Tech DAO LLC"   │                              │
│   │ tx: def456...  (new cert UTXO) │  ← VALID (UTXO unspent)     │
│   │ ipfs: QmAbc... (new agreement) │                              │
│   │ version: 2                     │                              │
│   │ replaces: v1 (abc123...)       │                              │
│   └────────────────────────────────┘                              │
│                                                                   │
│   v1 is now REVOKED:                                              │
│   ┌────────────────────────────────┐                              │
│   │ tx: abc123...  (cert UTXO)     │  ← REVOKED (UTXO spent)     │
│   │ reason_code: 6 (REPLACEMENT)   │                              │
│   │ replacement_tx: def456...      │                              │
│   └────────────────────────────────┘                              │
│                                                                   │
│   Complete version chain is queryable:                            │
│   GET /api/v1/daos/da1df5k3q00h7m9p/chain                       │
│   → Returns [v1 (revoked), v2 (valid)]                           │
│                                                                   │
│   Key features:                                                   │
│   - Offline signing (no private keys on server)                   │
│   - Atomic replace (new cert + revoke old in sequence)            │
│   - 12 revocation reason codes (standard)                         │
│   - Background reconciliation with blockchain                     │
│   - Bech32-style DAO identifiers (da1...)                        │
└──────────────────────────────────────────────────────────────────┘
```

### Offline Signing Architecture

One important design decision: **the server never holds private keys**. This is the signing flow:

```
┌──────────┐      ┌──────────────┐      ┌──────────────┐      ┌─────────┐
│  Admin   │      │  SAS Indexer │      │  SAS SDK     │      │ Liquid  │
│ (signer) │      │  (server)    │      │  (read-only) │      │ Network │
└────┬─────┘      └──────┬───────┘      └──────┬───────┘      └────┬────┘
     │                   │                     │                    │
     │  1. Request       │                     │                    │
     │  certificate      │                     │                    │
     ├──────────────────►│                     │                    │
     │                   │  2. Prepare         │                    │
     │                   │  transaction        │                    │
     │                   ├────────────────────►│                    │
     │                   │                     │  3. Build PSET,    │
     │                   │                     │  get sig_hash      │
     │                   │  4. Return          │                    │
     │                   │◄────────────────────┤                    │
     │  5. Return        │                     │                    │
     │  sig_hash         │                     │                    │
     │◄──────────────────┤                     │                    │
     │                   │                     │                    │
     │  6. Sign locally  │                     │                    │
     │  (never leaves    │                     │                    │
     │   admin's device) │                     │                    │
     │                   │                     │                    │
     │  7. Submit        │                     │                    │
     │  signature        │                     │                    │
     ├──────────────────►│                     │                    │
     │                   │  8. Finalize        │                    │
     │                   ├────────────────────►│                    │
     │                   │                     │  9. Inject sig,    │
     │                   │                     │  extract tx        │
     │                   │  10. Broadcast      │                    │
     │                   ├─────────────────────┼───────────────────►│
     │                   │                     │                    │
     │  11. Return txid  │                     │                    │
     │◄──────────────────┤                     │                    │
     │                   │                     │                    │
```

## Regarding the Specific Concerns

### Concern (1): No UTXO introspection in smart contracts

You're absolutely right that Simplicity contracts can't check whether external UTXOs are spent. However, **our use case doesn't require this**. We verify certificates off-chain (humans and applications checking status), not on-chain (smart contracts reacting to certificate state). The covenants we use are purely for structural enforcement (vault self-reference, output format, authorized signers).

### Concerns (2), (3), (4): Explorer centralization

For our MVP, we use the Blockstream Esplora API as **one of two sources** (the other being our own database with reconciliation). For production, we plan to run our own Elements node, which makes the architecture fully trustless:

```
MVP path:     App  →  DB + Esplora API  →  Liquid Network    (practical, sufficient)
Prod path:    App  →  DB + Elements RPC  →  Liquid Network   (trustless, sovereign)
```

The code change is minimal — the SAS SDK already accepts a custom `base_url`, and the verification logic (`UTXO exists = valid`) is identical regardless of the data source.

### Regarding recursive covenants

We appreciate the suggestion, and it's something we'll keep in mind for future use cases where on-chain automated decisions based on certificate status become necessary. For our current use case (human/application verification of DAO certificates), the UTXO-as-certificate model is elegant and sufficient.

## Summary

| What | How |
|------|-----|
| **Certificate issuance** | Simplicity covenants enforce structure (trustless) |
| **Certificate revocation** | Spend the UTXO (instant, on-chain) |
| **Verification (MVP)** | DB indexer + Esplora API (two sources) |
| **Verification (prod)** | DB indexer + Elements RPC (trustless) |
| **Document integrity** | IPFS CID embedded in OP_RETURN (immutable) |
| **Key management** | Offline signing — server never holds keys |
| **Version management** | Replacement chains with reason codes |
| **First application** | Wyoming DAO LLC Registry |

I'd love to continue this conversation and hear your thoughts on this architecture. If there are aspects of Simplicity that could better serve our use case, or if you see any issues with our approach, I'm very open to feedback.

Best regards,
Bruno

---

*Attachments: This document contains ASCII diagrams. For rendered versions, see the project documentation.*
