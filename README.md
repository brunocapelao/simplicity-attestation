# SAP - Simplicity Attestation Protocol

Sistema de certificados on-chain com delegacao hierarquica usando Simplicity na Liquid Network.

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

docs/
├── PROTOCOL_SPEC.md        # Especificacao SAP
└── DOCUMENTACAO.md         # Documentacao completa

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
python test_emit.py --admin      # Admin emite
python test_emit.py --delegate   # Delegate emite
```

### Revogar Certificado
```bash
python test_certificate_revoke.py --admin
python test_certificate_revoke.py --delegate
```

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
│ "SAP" │ VERSION │ TYPE │     HASH/CID (32 bytes)  │
│3 bytes│ 1 byte  │1 byte│        32 bytes          │
└───────┴─────────┴──────┴──────────────────────────┘
```

## Chaves (Testnet)

| Papel | Public Key |
|-------|------------|
| Admin (Alice) | `bcc13efe...ad45` |
| Delegate (Bob) | `8577f4e0...6413` |

Chaves completas em `secrets.json`.
