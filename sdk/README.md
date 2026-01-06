# SAP SDK v0.5.0 - Documentação Completa

SDK Python para o Simplicity Attestation Protocol na rede Liquid.

---

## Índice

1. [Início Rápido](#início-rápido)
2. [Arquitetura de Segurança](#arquitetura-de-segurança)
3. [SAPClient](#sapclient)
4. [Assinatura Externa](#assinatura-externa)
5. [Criação de Vault](#criação-de-vault)
6. [Controle de Acesso](#controle-de-acesso)
7. [Modelos de Dados](#modelos-de-dados)
8. [Features de Produção](#features-de-produção)
9. [Protocolo SAP](#protocolo-sap)

---

## Início Rápido

### Instalação

```bash
pip install embit requests
```

### Modo Simples (Legado)

```python
from sdk import SAPClient

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
from sdk import SAPClient, NetworkConfig, EnvKeyProvider, Role

# Config pública (pode estar no git)
config = NetworkConfig.from_file("network_config.json")

# Chave do ambiente (segura)
provider = EnvKeyProvider("SAP_PRIVATE_KEY")

# Preparar → Assinar → Finalizar
client = SAPClient.from_config("network_config.json")
prepared = client.prepare_issue_certificate(cid="Qm...")
signature = provider.sign(prepared.sig_hash_bytes)
result = client.finalize_transaction(prepared, signature)
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
config = SAPConfig.from_file("secrets.json")
```

---

## SAPClient

### Construtores

```python
# Legado (chaves no arquivo)
client = SAPClient.from_config("secrets.json")

# Com logging
import logging
client = SAPClient.from_config("secrets.json", logger=logging.getLogger())
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
from sdk import Role, RoleContext, Permissions

# Verificar permissões
ctx = RoleContext(Role.DELEGATE)
ctx.can_issue          # True
ctx.can_drain_vault    # False
ctx.can_revoke_any     # False

# Validar operação
try:
    ctx.require(Permissions.VAULT_DRAIN, "drain_vault")
except PermissionError as e:
    print(f"Negado: {e.message}")
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
| REVOKE | 0x02 | txid:vout |
| UPDATE | 0x03 | CID/hash |
| DELEGATE | 0x04 | pubkey |
| UNDELEGATE | 0x05 | pubkey |

### Encoding/Decoding

```python
from sdk.protocols import SAPProtocol

# Encode
payload = SAPProtocol.encode_attest("QmYwAPJzv5...")

# Decode
sap = SAPProtocol.decode_hex(op_return_hex)
print(sap.type)  # ATTEST
print(sap.cid)   # QmYwAPJzv5...
```

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
    result = client.issue_certificate(cid)
except InsufficientFundsError as e:
    print(f"Precisa {e.required}, tem {e.available}")
except PayloadTooLargeError as e:
    print(f"CID muito grande: {e.size} bytes")
```

---

## Changelog

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
