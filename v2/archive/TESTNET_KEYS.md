# 🔐 Simplicity Attestation - Chaves de Teste

**⚠️ ATENÇÃO: Estas são chaves de TESTNET apenas! Nunca use em produção!**

---

## 📍 Endereços dos Contratos

| Contrato | Endereço P2TR (Testnet) |
|----------|-------------------------|
| **Vault** | `tex1p7qvajg5kc2agzj9fn4gc623dmr5hdvetvngqteckz042f86tcuds3lh3m5` |
| **Attestation** | `tex1py5a2suf0vr02dxxm8094wqaumwn67u4z5zwayflr33hwxjzkpqpqt34rzt` |

---

## 🔑 Chaves

### Admin (Alice)

| Campo | Valor |
|-------|-------|
| **Public Key** | `bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45` |
| **Private Key** | `c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379` |

### Delegate (Bob)

| Campo | Valor |
|-------|-------|
| **Public Key** | `8577f4e053850a2eb0c86ce4c81215fdec681c28e01648f4401e0c47a4276413` |
| **Private Key** | `0f88f360602b68e02983c2e62a1cbd0e0d71a50f778f886abd1ccc3bc8b3ac9b` |

---

## 🧪 Comandos de Teste

### 1. Depositar L-BTC no Vault

Acesse: https://liquidtestnet.com/faucet

Cole o endereço do Vault:
```
tex1p7qvajg5kc2agzj9fn4gc623dmr5hdvetvngqteckz042f86tcuds3lh3m5
```

### 2. Verificar UTXO

```bash
curl -s "https://blockstream.info/liquidtestnet/api/address/tex1p7qvajg5kc2agzj9fn4gc623dmr5hdvetvngqteckz042f86tcuds3lh3m5/utxo" | python3 -m json.tool
```

### 3. Gastar do Vault (como Admin)

```bash
# O simply withdraw precisa:
# - TXID do depósito
# - Arquivo witness com a assinatura
# - Endereço de destino

simply withdraw \
    --entrypoint delegation_vault.simf \
    --witness admin_spend.wit \
    --txid <TXID_DO_DEPOSITO> \
    --destination <SEU_ENDERECO>
```

### 4. Assinar com Chave do Admin

```bash
simply sign \
    --message <SIGHASH_32_BYTES_HEX> \
    --secret c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379
```

---

## 📄 Witness Files

### admin_spend.wit (Admin gastando do Vault)

```json
{
    "ADMIN_OR_DELEGATE": {
        "value": "Left(0x<ASSINATURA_AQUI>)",
        "type": "Either<Signature, Signature>"
    }
}
```

### delegate_issue.wit (Delegate emitindo atestação)

```json
{
    "ADMIN_OR_DELEGATE": {
        "value": "Right(0x<ASSINATURA_AQUI>)",
        "type": "Either<Signature, Signature>"
    }
}
```

---

*Gerado em: 2026-01-05T19:38:35-03:00*
