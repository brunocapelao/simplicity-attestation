# Guia Completo: Transações Simplicity com OP_RETURN na Liquid Testnet

Este documento descreve o fluxo completo para criar, assinar e transmitir transações Simplicity com dados OP_RETURN na Liquid Testnet, **sem utilizar o IDE web**.

## Sumário

1. [Pré-requisitos](#1-pré-requisitos)
2. [Configuração do Ambiente](#2-configuração-do-ambiente)
3. [Geração de Chaves](#3-geração-de-chaves)
4. [Criação do Programa Simplicity (P2PK)](#4-criação-do-programa-simplicity-p2pk)
5. [Obtenção do Endereço](#5-obtenção-do-endereço)
6. [Financiamento do Endereço](#6-financiamento-do-endereço)
7. [Criação da Transação com OP_RETURN](#7-criação-da-transação-com-op_return)
8. [Assinatura da Transação](#8-assinatura-da-transação)
9. [Broadcast da Transação](#9-broadcast-da-transação)
10. [Verificação](#10-verificação)
11. [Correções Necessárias no hal-simplicity](#11-correções-necessárias-no-hal-simplicity)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Pré-requisitos

### Ferramentas necessárias

| Ferramenta | Descrição | Instalação |
|------------|-----------|------------|
| `hal-simplicity` | CLI para manipulação de Simplicity/PSET | Compilar do fonte |
| `simc` | Compilador Simfony → Simplicity | `cargo install simfony` |
| Python 3 | Para assinatura Schnorr | Sistema |
| `embit` | Biblioteca Python para BIP-340 | `pip install embit` |
| `jq` | Processamento JSON | `brew install jq` |
| `curl` | Requisições HTTP | Sistema |

### Instalação do hal-simplicity

```bash
# Clonar repositório
git clone https://github.com/apoelstra/hal-simplicity.git /tmp/hal-simplicity
cd /tmp/hal-simplicity

# Aplicar correções (ver seção 11)
# ... editar src/lib.rs e src/actions/simplicity/pset/create.rs

# Compilar
cargo build --release

# O binário estará em:
# /tmp/hal-simplicity/target/release/hal-simplicity
```

### Instalação do simc (Simfony Compiler)

```bash
cargo install simfony
# Ou compilar do fonte:
git clone https://github.com/BlockstreamResearch/simfony.git
cd simfony
cargo build --release
```

### Instalação das dependências Python

```bash
pip install embit
```

---

## 2. Configuração do Ambiente

### Variáveis de ambiente

```bash
# Caminho para hal-simplicity
export HAL=/tmp/hal-simplicity/target/release/hal-simplicity

# Rede
export NETWORK="liquidtestnet"

# Asset ID da Liquid Testnet (L-BTC)
export ASSET="144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"

# Internal key (unspendable - BIP-341)
export INTERNAL_KEY="50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"
```

---

## 3. Geração de Chaves

### Gerar par de chaves Schnorr (32 bytes cada)

```python
#!/usr/bin/env python3
"""generate_keys.py - Gera par de chaves Schnorr"""

import secrets
from embit import ec

# Gerar chave privada (32 bytes aleatórios)
private_key_bytes = secrets.token_bytes(32)
private_key = ec.PrivateKey(private_key_bytes)

# Derivar chave pública (x-only, 32 bytes)
public_key = private_key.get_public_key()
public_key_xonly = public_key.xonly()

print(f"Private Key: {private_key_bytes.hex()}")
print(f"Public Key:  {public_key_xonly.hex()}")
```

### Exemplo de chaves geradas

```json
{
  "admin": {
    "private_key": "c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379",
    "public_key": "bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45"
  },
  "delegate": {
    "private_key": "0f88f360602b68e02983c2e62a1cbd0e0d71a50f778f886abd1ccc3bc8b3ac9b",
    "public_key": "8577f4e053850a2eb0c86ce4c81215fdec681c28e01648f4401e0c47a4276413"
  }
}
```

---

## 4. Criação do Programa Simplicity (P2PK)

### Código Simfony para P2PK

Criar arquivo `p2pk.simf`:

```rust
mod witness {
    // Assinatura será fornecida no momento do gasto
    const SIG: Signature = 0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000;
}

fn main() {
    // 1. Obter o hash da transação (sig_all_hash)
    let msg: u256 = jet::sig_all_hash();

    // 2. Definir a chave pública autorizada (SUBSTITUIR pela sua chave)
    let pk: Pubkey = 0xbcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45;

    // 3. Verificar assinatura Schnorr BIP-340
    jet::bip_0340_verify((pk, msg), witness::SIG);
}
```

### Compilar o programa

```bash
simc p2pk.simf
```

**Saída:**
```
Program:
4jSQJOHM4qiEiuhMwARVwsGLwpYT2BhULrCX64qRkLLDgFbd+AIYBiQKE2m8wT7+Ehs1xycMQc5j2rdojAMmxYxfXh0a8xfBUDytRQQgUJIQYaHCpxQLQ2MOa67l4PQnU9GQOM5f425K8oynz2VMtqrT2Wu0YojxUYhwwDEJvPwcEA4GBwkA
```

O programa compilado está em formato **base64**.

---

## 5. Obtenção do Endereço

### Obter informações do programa

```bash
PROGRAM="4jSQJOHM4qiEiuhMwARVwsGLwpYT2BhULrCX64qRkLLDgFbd+AIYBiQKE2m8wT7+Ehs1xycMQc5j2rdojAMmxYxfXh0a8xfBUDytRQQgUJIQYaHCpxQLQ2MOa67l4PQnU9GQOM5f425K8oynz2VMtqrT2Wu0YojxUYhwwDEJvPwcEA4GBwkA"

$HAL simplicity info --liquid "$PROGRAM"
```

**Saída:**
```json
{
  "jets": "core",
  "commit_base64": "4jSQJOHM4qiEiuhMwARVwsGLwpYT2BhULrCX64qRkLLDgFbd...",
  "commit_decode": "(((false & unit); assertl drop jet_sig_all_hash ) & iden); ...",
  "type_arrow": "1 → 1",
  "cmr": "2f4199e55c870456428dc7b822c2c98297607d1781c83124d6b816353ed0cac0",
  "liquid_address_unconf": "ex1pz28yevfp9f3nhgsqzxermr5w5zdrdxaxdltmpuptx5p36n7hutqqejwprs",
  "liquid_testnet_address_unconf": "tex1pz28yevfp9f3nhgsqzxermr5w5zdrdxaxdltmpuptx5p36n7hutqqctuxjl",
  "is_redeem": false
}
```

### Informações importantes extraídas

| Campo | Valor | Descrição |
|-------|-------|-----------|
| `cmr` | `2f4199e55c...` | Commitment Merkle Root (identifica o programa) |
| `liquid_testnet_address_unconf` | `tex1pz28ye...` | Endereço Taproot na Liquid Testnet |

### Derivar script_pubkey

O `script_pubkey` para um endereço Taproot é:
```
5120 + <32-byte-output-key>
```

Para o endereço `tex1pz28yevfp9f3nhgsqzxermr5w5zdrdxaxdltmpuptx5p36n7hutqqctuxjl`:
```
script_pubkey: 5120128e4cb1212a633ba20011b23d8e8ea09a369ba66fd7b0f02b35031d4fd7e2c0
```

---

## 6. Financiamento do Endereço

### Usando o Faucet da Liquid Testnet

1. Acessar: https://liquidtestnet.com/faucet
2. Inserir o endereço: `tex1pz28yevfp9f3nhgsqzxermr5w5zdrdxaxdltmpuptx5p36n7hutqqctuxjl`
3. Clicar em "Send"
4. Anotar o TXID retornado

### Verificar UTXO

```bash
FAUCET_TXID="38ff3f17073233ba3ad0254fe79745c675e9ac9c667811aee0f366abc26281ec"

curl -s "https://blockstream.info/liquidtestnet/api/tx/$FAUCET_TXID" | jq '.vout[0]'
```

**Saída:**
```json
{
  "scriptpubkey": "5120128e4cb1212a633ba20011b23d8e8ea09a369ba66fd7b0f02b35031d4fd7e2c0",
  "scriptpubkey_address": "tex1pz28yevfp9f3nhgsqzxermr5w5zdrdxaxdltmpuptx5p36n7hutqqctuxjl",
  "value": 100000,
  "asset": "144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"
}
```

---

## 7. Criação da Transação com OP_RETURN

### 7.1. Definir variáveis

```bash
# UTXO de entrada
UTXO_TXID="38ff3f17073233ba3ad0254fe79745c675e9ac9c667811aee0f366abc26281ec"
UTXO_VOUT=0
UTXO_VALUE_BTC="0.001"  # 100000 sats - IMPORTANTE: em BTC, não satoshis!

# Programa e CMR
PROGRAM="4jSQJOHM4qiEiuhMwARVwsGLwpYT2BhULrCX64qRkLLDgFbd+AIYBiQKE2m8wT7+Ehs1xycMQc5j2rdojAMmxYxfXh0a8xfBUDytRQQgUJIQYaHCpxQLQ2MOa67l4PQnU9GQOM5f425K8oynz2VMtqrT2Wu0YojxUYhwwDEJvPwcEA4GBwkA"
CMR="2f4199e55c870456428dc7b822c2c98297607d1781c83124d6b816353ed0cac0"
SCRIPT_PUBKEY="5120128e4cb1212a633ba20011b23d8e8ea09a369ba66fd7b0f02b35031d4fd7e2c0"

# Saídas
RECIPIENT="tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"
FEE_BTC="0.00001"      # 1000 sats
CHANGE_BTC="0.00099"   # 99000 sats

# Payload OP_RETURN (formato SAID)
# SAID (4 bytes) + version (1 byte) + type (1 byte) + hash (32 bytes)
SAID_PAYLOAD="534149440101deadbeefcafebabedeadbeefcafebabedeadbeefcafebabedeadbeefcafebabe"
```

### 7.2. Criar PSET (Partially Signed Elements Transaction)

```bash
PSET_JSON=$($HAL simplicity pset create --liquid \
  "[{\"txid\":\"$UTXO_TXID\",\"vout\":$UTXO_VOUT}]" \
  "[
    {\"address\":\"$RECIPIENT\",\"asset\":\"$ASSET\",\"amount\":$CHANGE_BTC},
    {\"address\":\"data:$SAID_PAYLOAD\",\"asset\":\"$ASSET\",\"amount\":0},
    {\"address\":\"fee\",\"asset\":\"$ASSET\",\"amount\":$FEE_BTC}
  ]")

PSET=$(echo "$PSET_JSON" | jq -r '.pset')
echo "PSET criado: ${PSET:0:50}..."
```

**Nota sobre outputs:**
- `address`: endereço de destino normal
- `data:<hex>`: cria output OP_RETURN com os dados hex
- `fee`: output de taxa (script vazio)

### 7.3. Atualizar input com dados do UTXO

```bash
PSET2_JSON=$($HAL simplicity pset update-input --liquid "$PSET" 0 \
  --input-utxo "$SCRIPT_PUBKEY:$ASSET:$UTXO_VALUE_BTC" \
  --cmr "$CMR" \
  --internal-key "$INTERNAL_KEY")

PSET2=$(echo "$PSET2_JSON" | jq -r '.pset')
echo "PSET atualizado"
```

**Formato do `--input-utxo`:**
```
<script_pubkey>:<asset_id>:<value_in_btc>
```

⚠️ **IMPORTANTE**: O valor deve estar em BTC (ex: `0.001`), não em satoshis!

### 7.4. Obter sig_all_hash

Para obter o hash que precisa ser assinado, executamos o programa com uma assinatura dummy:

```bash
# Assinatura dummy de 64 bytes (128 hex chars)
DUMMY_SIG="00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001"

RUN_OUTPUT=$($HAL simplicity pset run --liquid "$PSET2" 0 "$PROGRAM" "$DUMMY_SIG")

# Extrair sig_all_hash do output
SIG_ALL_HASH=$(echo "$RUN_OUTPUT" | jq -r '.jets[] | select(.jet == "sig_all_hash") | .output_value' | sed 's/0x//')

echo "sig_all_hash: $SIG_ALL_HASH"
```

**Saída esperada:**
```json
{
  "success": false,
  "jets": [
    {
      "jet": "sig_all_hash",
      "success": true,
      "output_value": "0x4d7555f67deba3af0cd4f6e6ac5d67702dc4e8a4781e8495f293f9352c006439"
    },
    {
      "jet": "bip_0340_verify",
      "success": false
    }
  ]
}
```

O `sig_all_hash` é o hash que precisa ser assinado.

---

## 8. Assinatura da Transação

### 8.1. Assinar com chave privada (Python/embit)

```python
#!/usr/bin/env python3
"""sign_transaction.py - Assina o sig_all_hash com Schnorr BIP-340"""

from embit import ec

# Chave privada (32 bytes hex)
PRIVATE_KEY = "c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"

# sig_all_hash obtido do pset run
SIG_ALL_HASH = "4d7555f67deba3af0cd4f6e6ac5d67702dc4e8a4781e8495f293f9352c006439"

# Criar objeto de chave privada
privkey = ec.PrivateKey(bytes.fromhex(PRIVATE_KEY))

# Assinar (Schnorr BIP-340)
signature = privkey.schnorr_sign(bytes.fromhex(SIG_ALL_HASH))

# Serializar assinatura (64 bytes)
sig_hex = signature.serialize().hex()
print(f"Signature: {sig_hex}")
```

Ou via bash com heredoc:

```bash
SIGNATURE=$(python3 << EOF
from embit import ec
privkey = ec.PrivateKey(bytes.fromhex("$PRIVATE_KEY"))
sig = privkey.schnorr_sign(bytes.fromhex("$SIG_ALL_HASH"))
print(sig.serialize().hex())
EOF
)
echo "Signature: $SIGNATURE"
```

### 8.2. Verificar assinatura

```bash
RUN_OUTPUT=$($HAL simplicity pset run --liquid "$PSET2" 0 "$PROGRAM" "$SIGNATURE")
SUCCESS=$(echo "$RUN_OUTPUT" | jq -r '.success')

echo "Verificação: $SUCCESS"
```

**Se `success: true`**, a assinatura é válida!

### 8.3. Finalizar PSET

```bash
FINAL_JSON=$($HAL simplicity pset finalize --liquid "$PSET2" 0 "$PROGRAM" "$SIGNATURE")
FINAL_PSET=$(echo "$FINAL_JSON" | jq -r '.pset')

echo "PSET finalizado"
```

### 8.4. Extrair transação raw

```bash
TX_HEX=$($HAL simplicity pset extract --liquid "$FINAL_PSET" | tr -d '"')

echo "TX hex length: ${#TX_HEX}"
echo "TX: ${TX_HEX:0:100}..."
```

---

## 9. Broadcast da Transação

### Via API Blockstream

```bash
RESULT=$(curl -s -X POST \
  -H 'Content-Type: text/plain' \
  -d "$TX_HEX" \
  https://blockstream.info/liquidtestnet/api/tx)

echo "Result: $RESULT"
```

**Se sucesso**, retorna o TXID (64 caracteres hex).

### Verificar se é TXID válido

```bash
if [[ ${#RESULT} == 64 ]] && [[ $RESULT =~ ^[0-9a-f]+$ ]]; then
    echo "TXID: $RESULT"
    echo "Explorer: https://blockstream.info/liquidtestnet/tx/$RESULT"
else
    echo "Erro: $RESULT"
fi
```

---

## 10. Verificação

### Verificar transação no explorer

```bash
TXID="7fbdf242634b6bb83a01090706628728308e1185e6defdc59e4a46ad8cfe9968"

curl -s "https://blockstream.info/liquidtestnet/api/tx/$TXID" | jq '{
  txid: .txid,
  status: .status,
  fee: .fee,
  outputs: [.vout[] | {type: .scriptpubkey_type, value: .value, address: .scriptpubkey_address}]
}'
```

### Verificar OP_RETURN

```bash
curl -s "https://blockstream.info/liquidtestnet/api/tx/$TXID" | \
  jq '.vout[] | select(.scriptpubkey_type == "op_return") | .scriptpubkey_asm'
```

**Saída esperada:**
```
"OP_RETURN OP_PUSHBYTES_38 534149440101deadbeefcafebabedeadbeefcafebabedeadbeefcafebabedeadbeefcafebabe"
```

---

## 11. Correções Necessárias no hal-simplicity

### 11.1. Bug no hex_or_base64()

**Arquivo:** `src/lib.rs`

**Problema:** A função `hex_or_base64()` usava `b.is_ascii_lowercase()` que retorna `false` para dígitos (0-9), causando erro "Invalid padding" ou "trailing bytes".

**Correção:**

```rust
// ANTES (bugado):
if s.len() % 2 == 0 && s.bytes().all(|b| b.is_ascii_hexdigit() && b.is_ascii_lowercase()) {

// DEPOIS (corrigido):
if s.len() % 2 == 0 && s.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f')) {
```

### 11.2. Adicionar suporte a OP_RETURN

**Arquivo:** `src/actions/simplicity/pset/create.rs`

**Adicionar ao enum de erros:**

```rust
#[derive(Debug, thiserror::Error)]
pub enum PsetCreateError {
    // ... outros erros ...

    #[error("invalid OP_RETURN hex data: {0}")]
    OpReturnHexParse(String),
}
```

**Adicionar ao match de address:**

```rust
let script_pubkey = match output_spec.address.as_str() {
    "fee" => elements::Script::new(),

    // NOVO: Suporte a OP_RETURN
    x if x.starts_with("data:") => {
        let hex_data = &x[5..];
        let data = hex::decode(hex_data)
            .map_err(|e| PsetCreateError::OpReturnHexParse(e.to_string()))?;
        elements::script::Builder::new()
            .push_opcode(elements::opcodes::all::OP_RETURN)
            .push_slice(&data)
            .into_script()
    }

    x => {
        let addr = x.parse::<Address>().map_err(PsetCreateError::AddressParse)?;
        if addr.is_blinded() {
            return Err(PsetCreateError::ConfidentialAddressNotSupported);
        }
        addr.script_pubkey()
    }
};
```

### 11.3. Recompilar

```bash
cd /tmp/hal-simplicity
cargo build --release
```

---

## 12. Troubleshooting

### Erro: "Invalid padding" ou "trailing bytes 0x..."

**Causa:** Bug no `hex_or_base64()` - dígitos não reconhecidos como hex.

**Solução:** Aplicar correção da seção 11.1.

### Erro: "value in != value out"

**Causa:** Valores passados em satoshis em vez de BTC.

**Solução:** Usar formato BTC decimal:
- ❌ `100000` (satoshis)
- ✅ `0.001` (BTC)

### Erro: "Assertion failed inside jet"

**Causa:** sig_all_hash calculado incorretamente (geralmente por valor errado no input-utxo).

**Solução:** Verificar que o valor no `--input-utxo` está em BTC e corresponde ao UTXO real.

### Erro: "program does not have a redeem node"

**Causa:** Programa compilado é CommitNode, precisa de witness para virar RedeemNode.

**Solução:** Sempre passar uma assinatura (mesmo dummy) para `pset run`.

### Erro: "CMR and internal key imply output key X, which does not match input scriptPubKey Y"

**Causa:** CMR ou internal_key incorretos para o endereço.

**Solução:** Verificar que está usando o CMR correto do programa compilado.

---

## Script Completo

Veja o arquivo `complete_op_return.sh` para um script bash completo que executa todo o fluxo.

---

## Transações de Exemplo

### Admin (Alice)
- **TXID:** `7fbdf242634b6bb83a01090706628728308e1185e6defdc59e4a46ad8cfe9968`
- **Explorer:** https://blockstream.info/liquidtestnet/tx/7fbdf242634b6bb83a01090706628728308e1185e6defdc59e4a46ad8cfe9968

### Delegate (Bob)
- **TXID:** `a566fb037a27a5604ab03bb3bdd60c09d635285570f013d21b18c83436e6fd3a`
- **Explorer:** https://blockstream.info/liquidtestnet/tx/a566fb037a27a5604ab03bb3bdd60c09d635285570f013d21b18c83436e6fd3a

---

## Referências

- [Simplicity Language](https://github.com/BlockstreamResearch/simplicity)
- [Simfony (High-level Simplicity)](https://github.com/BlockstreamResearch/simfony)
- [hal-simplicity](https://github.com/apoelstra/hal-simplicity)
- [Liquid Testnet Faucet](https://liquidtestnet.com/faucet)
- [Liquid Testnet Explorer](https://blockstream.info/liquidtestnet/)
- [BIP-340 (Schnorr Signatures)](https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki)
