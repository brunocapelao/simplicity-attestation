# SAP - Simplicity Attestation Protocol

On-chain certificate system with hierarchical delegation using Simplicity on Liquid Network.

Primary documentation is in English under `docs/DOCUMENTATION.md`. Portuguese is in `docs/pt/README.md`.

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │          DELEGATION VAULT           │
                    │   tex1pjycx6hckqcujaf...3pvtvd      │
                    └─────────────────────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
   ┌─────────┐              ┌─────────────────┐          ┌─────────────────┐
   │  LEFT   │              │   RIGHT-LEFT    │          │   RIGHT-RIGHT   │
   │  Admin  │              │  Admin + Cov.   │          │ Delegate + Cov. │
   │  Drain  │              │  Issue Cert     │          │   Issue Cert    │
   └─────────┘              └─────────────────┘          └─────────────────┘
        │                            │                            │
        ▼                            ▼                            ▼
   Free spend              ┌─────────────────────────────────────┐
   (deactivate             │         COVENANT ENFORCEMENT        │
    delegate)              │  Output 0: Change → Vault (self-ref)│
                           │  Output 1: Cert → Certificate addr  │
                           │  Output 2: OP_RETURN with data      │
                           │  Output 3: Fee                      │
                           └─────────────────────────────────────┘
                                            │
                                            ▼
                           ┌─────────────────────────────────────┐
                           │         CERTIFICATE UTXO            │
                           │   tex1pfeaa7eex2cxa9...8cvkka       │
                           │                                     │
                           │   Existence = Valid certificate     │
                           │   Spent = Revoked certificate       │
                           └─────────────────────────────────────┘
```

## Structure

```
contracts/
├── vault.simf              # Delegation vault (3 spending paths)
└── certificate.simf        # Certificate UTXO script

tests/
├── test_emit.py            # Issue certificate (Admin or Delegate)
├── test_certificate_revoke.py
└── test_edge_cases.py      # Security tests

docs/
├── DOCUMENTATION.md        # Full documentation (English)
├── PROTOCOL_SPEC.md        # SAP specification (English)
└── pt/
    ├── README.md           # Guia em Portugues
    ├── DOCUMENTACAO.md     # Documentacao completa (Portugues)
    ├── PROTOCOL_SPEC.md    # SAP specification (Portugues)
    └── SDK.md              # SDK documentation (Portugues)

secrets.json                # Keys and addresses (testnet)
```

## Spending Paths

| Path | Witness Encoding | Usage |
|------|------------------|-------|
| Left | `0` + sig + 7 pad | Admin drains vault (deactivate delegate) |
| Right-Left | `10` + sig + 6 pad | Admin issues certificate |
| Right-Right | `11` + sig + 6 pad | Delegate issues certificate |

## Usage

### Issue Certificate
```bash
cd tests
python test_emit.py --admin-issue          # Admin issues certificate
python test_emit.py --delegate-issue       # Delegate issues certificate
python test_emit.py --admin-unconditional  # Admin drains vault (deactivate delegate)
```

### Revoke Certificate
```bash
python test_certificate_revoke.py --admin
python test_certificate_revoke.py --delegate
```

### SDK (E2E)
```python
from sdk.sap import SAP
from sdk import SAPClient

# 1) Create vault config (public)
config = SAP.create_vault(admin_pubkey, delegate_pubkey, network="testnet")
config.save("network_config.json")

# 2) Fund vault address (external)
# 3) Issue certificate
client = SAPClient.from_config("secrets.json")
issue = client.issue_certificate(cid="Qm...", issuer="delegate")

# 4) Revoke with reason and replacement
revoke = client.revoke_certificate(
    issue.txid, 1,
    reason_code=6,
    replacement_txid="new_txid..."
)
```

### Recent E2E (testnet)

Issuance:
- Admin: https://blockstream.info/liquidtestnet/tx/5487ed018fa69105acc4ce525b865d25f8cb0ac92297a64539008b50243ed7bb
- Delegate: https://blockstream.info/liquidtestnet/tx/423efc36bb3112546324a91482681091dea6a9e83a94583fa5a80fe3cedef355

Revocation:
- Admin: https://blockstream.info/liquidtestnet/tx/07048a43fabae3b4ca3f10316b9241fdee5259e68c61056a89c66acac16c57e5
- Delegate: https://blockstream.info/liquidtestnet/tx/2601bb94fcb361ff34657804b7274ceb47a83f31eab7c3cce56b6a3eee718ef0

## Tools

```bash
# hal-simplicity (fork with fixes)
git clone https://github.com/brunocapelao/hal-simplicity-fork.git
cd hal-simplicity-fork && cargo build --release

# simc (Simfony Compiler)
git clone https://github.com/BlockstreamResearch/simfony.git
cd simfony && cargo build --release

# Python
pip install embit requests
```

## SAP Protocol

```
OP_RETURN:
┌───────┬─────────┬──────┬──────────────────────────┐
│ "SAP" │ VERSION │ TYPE │        PAYLOAD (var)     │
│3 bytes│ 1 byte  │1 byte│        variable          │
└───────┴─────────┴──────┴──────────────────────────┘
```

REVOKE payload: `TXID:VOUT` + optional `reason_code` + optional `replacement_txid`.

## Keys (Testnet)

| Role | Public Key |
|------|------------|
| Admin (Alice) | `bcc13efe...ad45` |
| Delegate (Bob) | `8577f4e0...6413` |

Full keys in `secrets.json`.

---

[Documentação em Português](docs/pt/README.md)
