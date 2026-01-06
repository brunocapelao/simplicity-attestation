# Simplicity Attestation

## Sistema de Atestacoes On-Chain via Simplicity

### Status: Delegation Vault v1 Funcionando na Liquid Testnet

**Implementacao completa do vault de delegacao com logica OR:**
- Admin (Alice) pode gastar incondicionalmente
- Delegate (Bob) pode gastar com timelock + OP_RETURN obrigatorio

**Transacoes Confirmadas:**

| Tipo | TXID | Descricao |
|------|------|-----------|
| P2PK Admin | `7fbdf242...9968` | Gasto simples com OP_RETURN SAID |
| P2PK Delegate | `a566fb03...fd3a` | Gasto simples com OP_RETURN SAID |
| Vault Admin | `c5609c2e...d8bc` | Admin gasto incondicional do vault |

---

## Estrutura de Arquivos

```
v2/
├── delegation_vault_v1.simf       # Vault com logica OR (Admin/Delegate)
├── test_vault_admin_spend.sh      # Script para gasto Admin
├── test_vault_delegate_spend.py   # Script para gasto Delegate (apos timelock)
├── admin_p2pk_final.simf          # Programa P2PK simples (Admin)
├── secrets.json                   # Chaves, enderecos e transacoes
├── SIMPLICITY_FLOW_GUIDE.md       # Documentacao detalhada do fluxo
├── PROTOCOL_SPEC.md               # Especificacao SAID Protocol
├── README.md                      # Esta documentacao
└── archive/                       # Arquivos experimentais arquivados
```

---

## Ferramentas Necessarias

### hal-simplicity (fork corrigido)
```bash
git clone https://github.com/brunocapelao/hal-simplicity-fork.git
cd hal-simplicity-fork
cargo build --release
```

O fork contem duas correcoes criticas:
1. **hex_or_base64()**: Digits nao eram reconhecidos como hex lowercase
2. **OP_RETURN**: Suporte adicionado ao `pset create`

### simc (Simfony Compiler)
```bash
cargo install simc
```

### Python com embit
```bash
pip install embit
```

---

## Fluxo Completo (Sem IDE)

### 1. Compilar Programa Simfony
```bash
simc compile admin_p2pk_final.simf
# Output: base64 do programa + CMR
```

### 2. Gerar Endereco P2TR
```bash
hal-simplicity simplicity address \
  --cmr <CMR> \
  --internal-key 50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0
```

### 3. Criar PSET com OP_RETURN
```bash
hal-simplicity simplicity pset create --liquid \
  '[{"txid":"...","vout":0}]' \
  '[
    {"address":"<recipient>","asset":"<asset>","amount":0.00099},
    {"address":"data:534149440101...","asset":"<asset>","amount":0},
    {"address":"fee","asset":"<asset>","amount":0.00001}
  ]'
```

### 4. Atualizar Input
```bash
hal-simplicity simplicity pset update-input --liquid <pset> 0 \
  --input-utxo "<script_pubkey>:<asset>:<value_btc>" \
  --cmr "<cmr>" \
  --internal-key "<internal_key>"
```

### 5. Obter sig_all_hash
```bash
hal-simplicity simplicity pset run --liquid <pset> 0 <program> <dummy_sig>
# Extrair sig_all_hash do output JSON
```

### 6. Assinar
```python
from embit import ec
privkey = ec.PrivateKey(bytes.fromhex(PRIVATE_KEY))
sig = privkey.schnorr_sign(bytes.fromhex(sig_all_hash))
```

### 7. Finalizar e Broadcast
```bash
hal-simplicity simplicity pset finalize --liquid <pset> 0 <program> <signature>
hal-simplicity simplicity pset extract --liquid <finalized_pset>
curl -X POST -d '<tx_hex>' https://blockstream.info/liquidtestnet/api/tx
```

Veja `SIMPLICITY_FLOW_GUIDE.md` para documentacao completa.

---

## Protocolo SAID

```
┌────────┬─────────┬──────────┬─────────────────────────────────────┐
│  TAG   │ VERSION │   TYPE   │             PAYLOAD                 │
│ "SAID" │  0x01   │  0x01    │   Hash 32 bytes (CID digest)        │
├────────┼─────────┼──────────┼─────────────────────────────────────┤
│ 4 bytes│ 1 byte  │  1 byte  │           32 bytes                  │
└────────┴─────────┴──────────┴─────────────────────────────────────┘
```

### Tipos de Operacao

| Byte | Tipo | Descricao |
|------|------|-----------|
| 0x01 | ATTEST | Emissao de atestacao |
| 0x02 | REVOKE | Revogacao de atestacao |

---

## Chaves (Testnet)

| Papel | Public Key (x-only) |
|-------|---------------------|
| Admin (Alice) | `bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45` |
| Delegate (Bob) | `8577f4e053850a2eb0c86ce4c81215fdec681c28e01648f4401e0c47a4276413` |

Chaves privadas em `secrets.json` (apenas testnet).

---

## Delegation Vault v1

**Implementacao: 100%**

O vault `delegation_vault_v1.simf` implementa:
- [x] Logica OR (Admin OU Delegate)
- [x] Admin: gasto incondicional (verificado on-chain)
- [x] Delegate: timelock (block 2256000) + OP_RETURN obrigatorio
- [x] Revogacao: Admin pode gastar a qualquer momento

### Arquitetura do Vault

```
┌─────────────────────────────────────────────────────────────────┐
│                    DELEGATION VAULT v1                          │
├─────────────────────────────────────────────────────────────────┤
│  Witness: Either<Signature, Signature>                          │
│  - Left(sig)  → Admin path (incondicional)                      │
│  - Right(sig) → Delegate path (timelock + OP_RETURN)            │
├─────────────────────────────────────────────────────────────────┤
│  ADMIN PATH                    │  DELEGATE PATH                 │
│  ─────────────                 │  ──────────────                │
│  1. Verificar assinatura       │  1. Verificar assinatura       │
│                                │  2. check_lock_height(2256000) │
│                                │  3. output_null_datum(1, 0)    │
└─────────────────────────────────────────────────────────────────┘
```

### Encoding do Witness (Simplicity)

```
Either<A, B> encoding:
  Left(x)  = bit 0 + x_bits + padding
  Right(x) = bit 1 + x_bits + padding

Signature = 512 bits
Witness total = 1 + 512 + 7 = 520 bits = 65 bytes
```

---

## Referencias

- [hal-simplicity-fork](https://github.com/brunocapelao/hal-simplicity-fork)
- [Simplicity Language](https://github.com/BlockstreamResearch/simplicity)
- [Simfony](https://github.com/BlockstreamResearch/simfony)

---

*Atualizado em 2026-01-06*
