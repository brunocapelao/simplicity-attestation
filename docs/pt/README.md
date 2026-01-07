# SAP - Simplicity Attestation Protocol

Sistema de certificados on-chain com delegacao hierarquica usando Simplicity na Liquid Network.

Documentacao principal (Ingles): `docs/DOCUMENTATION.md`.

## Arquitetura

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
   Gasto livre              ┌─────────────────────────────────────┐
   (desativar               │         COVENANT ENFORCEMENT        │
    delegado)               │  Output 0: Troco → Vault (self-ref) │
                            │  Output 1: Cert → Certificate addr  │
                            │  Output 2: OP_RETURN com dados      │
                            │  Output 3: Fee                      │
                            └─────────────────────────────────────┘
                                             │
                                             ▼
                            ┌─────────────────────────────────────┐
                            │         CERTIFICATE UTXO            │
                            │   tex1pfeaa7eex2cxa9...8cvkka       │
                            │                                     │
                            │   Existencia = Certificado valido   │
                            │   Gasto = Certificado revogado      │
                            └─────────────────────────────────────┘
```

## Estrutura

```
contracts/
├── vault.simf              # Delegation vault (3 spending paths)
└── certificate.simf        # Certificate UTXO script

tests/
├── test_emit.py            # Emitir certificado (Admin ou Delegate)
├── test_certificate_revoke.py
└── test_edge_cases.py      # Testes de seguranca

docs/pt/
├── README.md               # Este guia (Portugues)
├── DOCUMENTACAO.md         # Documentacao completa (Portugues)
├── PROTOCOL_SPEC.md        # Especificacao SAP (Portugues)
└── SDK.md                  # Documentacao do SDK (Portugues)

secrets.json                # Chaves e enderecos (testnet)
```

## Spending Paths

| Path | Witness Encoding | Uso |
|------|------------------|-----|
| Left | `0` + sig + 7 pad | Admin drena vault (desativar delegado) |
| Right-Left | `10` + sig + 6 pad | Admin emite certificado |
| Right-Right | `11` + sig + 6 pad | Delegate emite certificado |

## Uso

### Emitir Certificado
```bash
cd tests
python test_emit.py --admin-issue          # Admin emite certificado
python test_emit.py --delegate-issue       # Delegate emite certificado
python test_emit.py --admin-unconditional  # Admin drena vault (desativar delegado)
```

### Revogar Certificado
```bash
python test_certificate_revoke.py --admin
python test_certificate_revoke.py --delegate
```

### SDK (E2E)

```python
from sdk import SAP

# 1) Criar vault (apenas chaves publicas)
config = SAP.create_vault(
    admin_pubkey="abc123...",
    delegate_pubkey="def456...",
    network="testnet"
)
config.save("vault_config.json")
print(f"Financiar: {config.vault_address}")

# 2) Operar como Admin
admin = SAP.as_admin(config="vault_config.json", private_key="admin_secret...")
result = admin.issue_certificate(cid="QmYwAPJzv5...")
admin.drain_vault(recipient="tex1...")  # Desativar delegado

# 3) Operar como Delegado (entidade diferente)
delegate = SAP.as_delegate(config="vault_config.json", private_key="delegate_secret...")
result = delegate.issue_certificate(cid="QmNewCert...")
delegate.revoke_certificate(result.txid, 1, reason_code=6)
```

### Execucao E2E recente (testnet)

Emissoes:
- Admin: https://blockstream.info/liquidtestnet/tx/5487ed018fa69105acc4ce525b865d25f8cb0ac92297a64539008b50243ed7bb
- Delegate: https://blockstream.info/liquidtestnet/tx/423efc36bb3112546324a91482681091dea6a9e83a94583fa5a80fe3cedef355

Revogacoes:
- Admin: https://blockstream.info/liquidtestnet/tx/07048a43fabae3b4ca3f10316b9241fdee5259e68c61056a89c66acac16c57e5
- Delegate: https://blockstream.info/liquidtestnet/tx/2601bb94fcb361ff34657804b7274ceb47a83f31eab7c3cce56b6a3eee718ef0

## Ferramentas

```bash
# hal-simplicity (fork com correcoes)
git clone https://github.com/brunocapelao/hal-simplicity-fork.git
cd hal-simplicity-fork && cargo build --release

# simc (Simfony Compiler)
git clone https://github.com/BlockstreamResearch/simfony.git
cd simfony && cargo build --release

# Python
pip install embit requests
```

## Protocolo SAP

```
OP_RETURN:
┌───────┬─────────┬──────┬──────────────────────────┐
│ "SAP" │ VERSION │ TYPE │        PAYLOAD (var)     │
│3 bytes│ 1 byte  │1 byte│        variable          │
└───────┴─────────┴──────┴──────────────────────────┘
```

REVOKE payload: `TXID:VOUT` + `reason_code` opcional + `replacement_txid` opcional.

## Chaves (Testnet)

| Papel | Public Key |
|-------|------------|
| Admin (Alice) | `bcc13efe...ad45` |
| Delegate (Bob) | `8577f4e0...6413` |

Chaves completas em `secrets.json`.

---

[English Version](../../README.md)
