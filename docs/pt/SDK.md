# SAP SDK v0.6.0 - Documentação Completa

SDK Python para o Simplicity Attestation Protocol na rede Liquid.

---

## Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Início Rápido](#início-rápido)
3. [Arquitetura de Segurança](#arquitetura-de-segurança)
4. [SAPClient](#sapclient)
5. [Assinatura Externa](#assinatura-externa)
6. [Criação de Vault](#criação-de-vault)
7. [Controle de Acesso](#controle-de-acesso)
8. [Modelos de Dados](#modelos-de-dados)
9. [Features de Produção](#features-de-produção)
10. [Protocolo SAP](#protocolo-sap)

---

## Pré-requisitos

### Dependências Python

```bash
pip install embit requests
```

### Ferramentas Externas (Rust)

O SDK requer duas ferramentas compiladas em Rust:

#### 1. simc (Simfony Compiler)

Compila contratos Simfony para Simplicity.

```bash
# Clone o repositório
git clone https://github.com/BlockstreamResearch/simfony.git
cd simfony

# Compile
cargo build --release

# Instale
cp target/release/simc ~/.cargo/bin/
# ou
sudo cp target/release/simc /usr/local/bin/

# Verifique
simc
# Output: Usage: simc PROGRAM_FILE
```

#### 2. hal-simplicity

Ferramenta PSET para transações Simplicity na Liquid.

```bash
# Clone o fork com suporte completo
git clone https://github.com/brunocapelao/hal-simplicity.git
cd hal-simplicity

# Compile
cargo build --release

# Instale
cp target/release/hal-simplicity ~/.cargo/bin/
# ou
sudo cp target/release/hal-simplicity /usr/local/bin/

# Verifique
hal-simplicity --help
```

> **Nota**: Você precisa do Rust instalado. [Instale via rustup](https://rustup.rs/).

---

## Início Rápido

### Modo Simples (Legado)

```python
from sdk import SAPClient

# Arquivo local (NÃO comite):
# copie `secrets.example.json` → `secrets.json` e preencha chaves/contratos.
client = SAPClient.from_config("secrets.json")

# Emitir certificado
result = client.issue_certificate(cid="QmYwAPJzv5...")
print(f"TX: {result.txid}")

# Verificar
is_valid = client.verify_certificate(result.txid, 1)

# Revogar
client.revoke_certificate(result.txid, 1)
```

### Modo Seguro (Recomendado)

```python
import os
from sdk import SAP

HAL_PATH = "./hal-simplicity/target/release/hal-simplicity"
SIMC_PATH = "./simfony/target/release/simc"

# Config pública (pode estar no git)
config = SAP.create_vault(
    admin_pubkey="abc123...",
    delegate_pubkey="def456...",
    network="testnet",
    hal_path=HAL_PATH,
    simc_path=SIMC_PATH,
)
config.save("vault_config.json")

# Chaves privadas fora do git (ex.: env vars)
admin = SAP.as_admin("vault_config.json", private_key=os.environ["SAP_ADMIN_PRIVATE_KEY"], hal_path=HAL_PATH)
delegate = SAP.as_delegate("vault_config.json", private_key=os.environ["SAP_DELEGATE_PRIVATE_KEY"], hal_path=HAL_PATH)

result = delegate.issue_certificate(cid="Qm...")
```

### Ciclo Completo (E2E)

```python
from sdk import SAP

# 1) Criar vault (publico)
HAL_PATH = "./hal-simplicity/target/release/hal-simplicity"
SIMC_PATH = "./simfony/target/release/simc"

config = SAP.create_vault(
    admin_pubkey="abc123...",
    delegate_pubkey="def456...",
    network="testnet",
    hal_path=HAL_PATH,
    simc_path=SIMC_PATH,
)
config.save("vault_config.json")

# 2) Financiar vault externamente (L-BTC)
# 3) Emitir certificado
delegate = SAP.as_delegate("vault_config.json", private_key="delegate_secret...", hal_path=HAL_PATH)
issue = delegate.issue_certificate(cid="Qm...")

# 4) Revogar (com motivo + substituicao)
revoke = delegate.revoke_certificate(issue.txid, vout=1, reason_code=6, replacement_txid="new_txid...")
```

---

## Arquitetura de Segurança

### Separação de Dados

| Tipo | Onde Armazenar | Exemplos |
|------|----------------|----------|
| **Público** | Git, config files | Endereços, CMRs, asset_id |
| **Privado** | Env vars, KMS, HSM | Chaves privadas |

### KeyProviders

```python
from sdk import EnvKeyProvider, MemoryKeyProvider, FileKeyProvider

# Produção: variável de ambiente
provider = EnvKeyProvider("SAP_PRIVATE_KEY")

# Desenvolvimento: em memória
provider = MemoryKeyProvider("abc123...64 hex chars...")

# Assinatura
signature = provider.sign(message_bytes)  # 64-byte Schnorr
pubkey = provider.public_key  # x-only pubkey
```

### NetworkConfig vs SAPConfig

```python
# NOVO: Config pública (segura para git)
from sdk import NetworkConfig
config = NetworkConfig.from_file("network_config.json")

# LEGADO: Config com chaves (NÃO comitar)
from sdk import SAPConfig
# copie `secrets.example.json` → `secrets.json` e preencha chaves/contratos.
config = SAPConfig.from_file("secrets.json")
```

---

## SAPClient

### Construtores

```python
# Legado (chaves no arquivo; NÃO comite)
client = SAPClient.from_config("secrets.json")

# Com logging
import logging
from sdk import SAPConfig
client = SAPClient(config=SAPConfig.from_file("secrets.json"), logger=logging.getLogger("sap"))
```

### Operações do Vault

```python
# Estado do vault
vault = client.get_vault()
vault.address       # Endereço
vault.balance       # Saldo em sats
vault.can_issue     # True se >= 1046 sats
vault.utxos         # Lista de UTXOs

# Drenar vault (admin only)
result = client.drain_vault(recipient="tex1...")
```

### Operações de Certificado

```python
# Emitir
result = client.issue_certificate(
    cid="QmYwAPJzv5...",      # CID ou hash
    issuer="delegate",         # "admin" ou "delegate"
    broadcast=True             # Enviar para rede
)

# Verificar
status = client.verify_certificate(txid, vout=1)
# Retorna: CertificateStatus.VALID ou REVOKED

# Obter detalhes
cert = client.get_certificate(txid, vout=1)
cert.cid        # CID original
cert.status     # VALID/REVOKED
cert.issued_at  # Block height

# Listar todos
certs = client.list_certificates()

# Revogar
result = client.revoke_certificate(
    txid="abc123...",
    vout=1,
    revoker="admin",
    recipient="tex1..."  # Opcional, senão queima como fee
)
```

---

## Assinatura Externa

Para multisig, hardware wallets, ou workflows de aprovação.

### Fluxo Completo

```python
# 1. PREPARAR (SDK monta transação)
prepared = client.prepare_issue_certificate(cid="Qm...")

# Dados para aprovação
print(prepared.summary())
print(f"Hash: {prepared.sig_hash}")
print(f"Papel: {prepared.signer_role}")
print(f"Pubkey esperada: {prepared.required_pubkey}")

# 2. ASSINAR (externamente)
# Hardware wallet, multisig ceremony, custodian API...
signature = external_signer.sign(prepared.sig_hash_bytes)

# 3. FINALIZAR (SDK broadcasta)
result = client.finalize_transaction(prepared, signature)
```

### Métodos de Preparação

```python
# Issue
prepared = client.prepare_issue_certificate(cid, issuer="delegate")

# Revoke
prepared = client.prepare_revoke_certificate(txid, vout, revoker="admin")

# Drain
prepared = client.prepare_drain_vault(recipient)
```

### PreparedTransaction

```python
prepared.tx_type           # ISSUE_CERTIFICATE, REVOKE, DRAIN
prepared.sig_hash          # Hash para assinar (hex)
prepared.sig_hash_bytes    # Hash como bytes
prepared.signer_role       # "admin" ou "delegate"
prepared.required_pubkey   # Pubkey que deve assinar
prepared.is_expired        # Verificar expiração
prepared.details           # Dados para UI
prepared.summary()         # Resumo human-readable
```

---

## Criação de Vault

### VaultBuilder

```python
from sdk import VaultBuilder

builder = VaultBuilder(
    simc_path="simc",           # Simfony compiler
    hal_path="/path/to/hal",    # hal-simplicity
    contracts_dir="./contracts"  # Diretório .simf
)

# Criar vault
setup = builder.create_vault(
    admin_public_key="abc123...",
    delegate_public_key="def456...",
    network="liquidtestnet"
)

# Salvar config (pública, sem chaves)
setup.save("network_config.json")
print(f"Deposit: {setup.vault.address}")
```

### VaultFunder

```python
from sdk import VaultFunder

funder = VaultFunder(network="testnet")

# Instruções de depósito
instruction = funder.get_deposit_instruction(vault_address)
print(f"Balance: {instruction['current_balance']}")
print(f"Min deposit: {instruction['min_deposit']}")
print(f"Can issue: {instruction['can_issue_certificates']}")

# Aguardar depósito
balance = funder.wait_for_deposit(
    vault_address,
    min_amount=10000,
    timeout=600
)
```

---

## Controle de Acesso

### Roles

```python
from sdk import Role, RoleContext, Permissions, PermissionError

# Verificar permissões
ctx = RoleContext(Role.DELEGATE)
ctx.can_issue          # True
ctx.can_drain_vault    # False
ctx.can_revoke_any     # False

# Validar operação
try:
    ctx.require(Permissions.VAULT_DRAIN, "drain_vault")
except PermissionError as e:
    print(f"Negado: {e}")
```

### Permissões por Role

| Permissão | Admin | Delegate |
|-----------|-------|----------|
| `VAULT_READ` | ✅ | ✅ |
| `VAULT_DRAIN` | ✅ | ❌ |
| `CERT_ISSUE` | ✅ | ✅ |
| `CERT_REVOKE_OWN` | ✅ | ✅ |
| `CERT_REVOKE_ANY` | ✅ | ❌ |

---

## Modelos de Dados

### Certificate

```python
@dataclass
class Certificate:
    txid: str
    vout: int
    cid: Optional[str]
    status: CertificateStatus  # VALID, REVOKED, UNKNOWN
    issued_at: Optional[int]   # Block height
    revoked_at: Optional[int]
```

### Vault

```python
@dataclass
class Vault:
    address: str
    balance: int
    utxos: List[UTXO]
    can_issue: bool
    available_utxo: Optional[UTXO]
```

### TransactionResult

```python
@dataclass
class TransactionResult:
    success: bool
    txid: Optional[str]
    raw_hex: Optional[str]
    error: Optional[str]
```

---

## Features de Produção

### Confirmação de Transação

```python
from sdk import ConfirmationTracker, TxStatus

# Esperar confirmação
status = client.wait_for_confirmation(txid, confirmations=1, timeout=600)
print(f"Confirmações: {status.confirmations}")

# Callback assíncrono
client.on_confirmation(txid, lambda s: print(f"Confirmado: {s.txid}"))
```

### Estimativa de Taxas

```python
from sdk import FeePriority

fee = client.estimate_fee("issue_certificate", FeePriority.HIGH)
print(f"{fee.total_sats} sats ({fee.sat_per_vbyte} sat/vB)")
```

### Eventos

```python
from sdk import EventType

@client.on(EventType.AFTER_ISSUE)
def on_issue(event):
    print(f"Emitido: {event.data['txid']}")

@client.on(EventType.ON_ERROR)
def on_error(event):
    print(f"Erro: {event.data['error']}")
```

### Logging Estruturado

```python
from sdk import StructuredLogger, create_file_logger

# JSON logging
logger = StructuredLogger(json_output=True)
logger.info("Operação", txid="abc123")

# File logger
logger = create_file_logger("/var/log/sap.log")
```

---

## Protocolo SAP

### Formato OP_RETURN

```
[SAP] [VERSION] [TYPE] [PAYLOAD]
 3B      1B       1B    Variable
```

### Tipos de Operação

| Tipo | Código | Payload |
|------|--------|---------|
| ATTEST | 0x01 | CID/hash (até 75 bytes) |
| REVOKE | 0x02 | txid:vout (+ reason_code + replacement_txid) |
| UPDATE | 0x03 | CID/hash |
| DELEGATE | 0x10 | pubkey |
| UNDELEGATE | 0x11 | pubkey |

### Encoding/Decoding

```python
from sdk.protocols import SAPProtocol

# Encode
payload_hex = SAPProtocol.encode_attest("QmYwAPJzv5...")

# Decode
sap = SAPProtocol.decode_hex(payload_hex)
print(type(sap).__name__)  # SAPAttest / SAPRevoke / SAPUpdate
if hasattr(sap, "cid"):
    print(sap.cid)
```

### Códigos de revogação (reason_code)

Opcionalmente, a revogação pode carregar um código de motivo (1 byte) no payload `REVOKE`.

```python
result = client.revoke_certificate(txid, vout=1, reason_code=3)
```

Com substituição (referência ao novo certificado):
```python
result = client.revoke_certificate(
    txid, vout=1,
    reason_code=6,
    replacement_txid=new_txid
)
```

| Código | Constante | Uso | Descrição curta | Quando usar (exemplos práticos) |
| --- | --- | --- | --- | --- |
| **1** | `DATA_ERROR` | MVP | Erro na emissão/conteúdo. | Campo trocado, pessoa errada, data inválida; revogue e reemita correto. |
| **2** | `DUPLICATE` | MVP | Registro duplicado (mesmo emissor). | Duas emissões do mesmo objeto; manter apenas a via correta. |
| **3** | `FRAUD_SUSPECTED` | MVP | Indícios de fraude (em apuração). | Sinais de falsificação/uso indevido; pode evoluir para 4. |
| **4** | `FRAUD_CONFIRMED` | MVP | Fraude confirmada com evidência. | Documento/VC falsa, identidade forjada. |
| **5** | `HOLDER_REQUEST` | MVP | Pedido do titular. | Retirada de consentimento, exposição indevida, necessidade de cancelamento. |
| **6** | `REISSUE_REPLACEMENT` | MVP | Substituição por reemissão. | Nova via corrigida/atualizada substitui a anterior. |
| **7** | `ADMINISTRATIVE` | MVP | Decisão/regra administrativa. | Encerramento de vínculo, programa/política encerrada, óbito. |
| **8** | `LEGAL_ORDER` | MVP | Ordem judicial/regulatória. | Determinação externa obrigatória. |
| **9** | `KEY_COMPROMISE` | MVP | Comprometimento de chaves/dispositivo. | Carteira do titular perdida/comprometida; chave do emissor exposta. |
| **10** | `SUSPENDED` | Futuro (V2) | Suspensão temporária (não-terminal). | Bloqueio enquanto dura investigação/cumprimento de requisito. |
| **11** | `CRYPTO_DEPRECATED` | Futuro | Algoritmo/curva obsoleta ou vulnerável. | Revogação/reemissão em massa por obsolescência criptográfica. |
| **12** | `PROCESS_ERROR` | Futuro | Falha sistêmica de processo/lote. | Template/ETL/regra aplicados incorretamente a um lote; recall. |
| **13** | **RESERVED** | Futuro | Reservado. | Mantido para extensões padronizadas. |
| **14** | **RESERVED** | Futuro | Reservado. | Mantido para extensões padronizadas. |
| **15** | **RESERVED** | Futuro | Reservado. | Mantido para extensões padronizadas. |

---

## Erros

```python
from sdk import (
    SAPError,               # Base
    InsufficientFundsError, # Vault sem fundos
    CertificateNotFoundError,
    VaultEmptyError,
    BroadcastError,
    ConfirmationTimeoutError,
    PayloadTooLargeError,   # CID > 75 bytes
    HalSimplicityError,
)

try:
    prepared = client.prepare_issue_certificate(cid)
except InsufficientFundsError as e:
    print(f"Precisa {e.required}, tem {e.available}")
```

---

## Changelog

### v0.6.0 (Current)
- **Unified SAP API** with `SAP.create_vault()`, `SAP.as_admin()`, `SAP.as_delegate()`
- Vault creation requires only PUBLIC keys
- Role-based operation (Admin vs Delegate)
- Automatic contract compilation with key injection
- VaultConfig for sharing vault setup

### v0.5.0
- Modelo de assinatura externa (prepare/finalize)
- PreparedTransaction para multisig/HW wallets

### v0.4.0
- VaultBuilder e VaultFunder
- Criação e funding de vaults

### v0.3.0
- KeyProvider abstraction
- Role-based access control
- NetworkConfig (config pública)

### v0.2.0
- Tipos de erro específicos
- Confirmação de transações
- Estimativa de fees
- Sistema de eventos
- Logging estruturado

### v0.1.0
- Versão inicial
- SAPClient básico
- PSET workflow
