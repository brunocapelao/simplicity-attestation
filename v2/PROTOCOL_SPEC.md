# 📋 SAID Protocol Specification

## Simplicity Attestation ID Protocol (SAID)

**Versão:** 1.0  
**Data:** 2026-01-05  
**Projeto:** Simplicity Attestation

---

## 1. Visão Geral

O protocolo SAID define um formato padronizado para armazenar referências a atestações (certificados) em outputs OP_RETURN de transações Liquid/Bitcoin. O formato permite que indexadores identifiquem rapidamente transações relacionadas ao sistema Simplicity Attestation.

---

## 2. Formato do OP_RETURN

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ESTRUTURA DO OP_RETURN                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌────────┬─────────┬──────────┬────────────────────────────────────────┐  │
│   │  TAG   │ VERSION │  TYPE    │              PAYLOAD                    │  │
│   │ 4 bytes│ 1 byte  │  1 byte  │           (variable)                    │  │
│   └────────┴─────────┴──────────┴────────────────────────────────────────┘  │
│                                                                              │
│   Total: 6 bytes de header + payload (CID)                                   │
│   Máximo OP_RETURN: ~80 bytes → ~74 bytes para payload                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 TAG (4 bytes)

**Magic bytes** para identificar o protocolo Simplicity Attestation:

```
ASCII:  "SAID"
HEX:    0x53414944
```

### 2.2 VERSION (1 byte)

Versão do protocolo para compatibilidade futura:

| Valor | Significado |
|-------|-------------|
| `0x01` | Versão 1.0 (atual) |
| `0x02-0xFF` | Reservado para futuras versões |

### 2.3 TYPE (1 byte)

Tipo de operação/dado:

| Valor | Tipo | Descrição |
|-------|------|-----------|
| `0x01` | ATTEST | Emissão de atestação (CID no payload) |
| `0x02` | REVOKE | Revogação (TXID da atestação no payload) |
| `0x03` | UPDATE | Atualização de metadados (novo CID) |
| `0x10` | DELEGATE | Delegação de autoridade |
| `0x11` | UNDELEGATE | Revogação de delegação |
| `0xFF` | RESERVED | Reservado |

### 2.4 PAYLOAD (variável)

Depende do TYPE:

| TYPE | Payload |
|------|---------|
| ATTEST | CID IPFS (46-59 bytes) |
| REVOKE | TXID:vout (34 bytes) |
| UPDATE | CID IPFS (46-59 bytes) |
| DELEGATE | Pubkey do delegate (32 bytes) |
| UNDELEGATE | Pubkey do delegate (32 bytes) |

---

## 3. Exemplos

### 3.1 Emissão de Atestação

```
OP_RETURN:
┌────────────┬─────┬──────┬─────────────────────────────────────────────────┐
│    SAID    │ 01  │  01  │ QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG │
├────────────┼─────┼──────┼─────────────────────────────────────────────────┤
│ 53414944   │ 01  │  01  │ (46 bytes - CIDv0 base58)                       │
└────────────┴─────┴──────┴─────────────────────────────────────────────────┘

HEX completo:
53414944 01 01 516d59774150...
```

### 3.2 Revogação de Atestação

```
OP_RETURN:
┌────────────┬─────┬──────┬─────────────────────────────────────────────────┐
│    SAID    │ 01  │  02  │ <TXID>:<vout>                                   │
├────────────┼─────┼──────┼─────────────────────────────────────────────────┤
│ 53414944   │ 01  │  02  │ (34 bytes - 32 bytes TXID + 2 bytes vout)       │
└────────────┴─────┴──────┴─────────────────────────────────────────────────┘
```

---

## 4. Algoritmo do Indexador

```python
def index_transaction(tx):
    for i, output in enumerate(tx.outputs):
        if not is_op_return(output):
            continue
            
        data = output.script_data
        
        # Verificar magic bytes
        if len(data) < 6:
            continue
        if data[0:4] != b'SAID':
            continue
            
        # Parse header
        version = data[4]
        op_type = data[5]
        payload = data[6:]
        
        if version != 0x01:
            log(f"Versão desconhecida: {version}")
            continue
            
        # Processar por tipo
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

## 5. Considerações

### 5.1 Versionamento

O campo VERSION permite evolução do protocolo mantendo compatibilidade:
- Indexadores devem ignorar versões que não entendem
- Novas versões podem adicionar campos ao header
- Payload pode mudar de estrutura entre versões

### 5.2 Validação On-chain

O contrato Simplicity pode opcionalmente validar o prefixo:

```rust
// Verificar que o OP_RETURN começa com "SAID"
let maybe_datum = jet::output_null_datum(2, 0);
// Extrair primeiros 4 bytes e comparar com 0x53414944
```

### 5.3 Tamanho

| Componente | Tamanho | Acumulado |
|------------|---------|-----------|
| OP_RETURN max | 80 bytes | - |
| TAG (SAID) | 4 bytes | 4 |
| VERSION | 1 byte | 5 |
| TYPE | 1 byte | 6 |
| CIDv0 | 46 bytes | 52 |
| **Sobra** | 28 bytes | - |

Para CIDv1 (mais longo), ainda cabe confortavelmente.

---

## 6. Registro de Tipos

### Tipos Reservados para Expansão

| Range | Uso |
|-------|-----|
| `0x01-0x0F` | Operações de atestação |
| `0x10-0x1F` | Operações de delegação |
| `0x20-0x2F` | Metadados e extensões |
| `0x30-0xEF` | Reservado para futuro |
| `0xF0-0xFE` | Uso privado/experimental |
| `0xFF` | Reservado (não usar) |

---

## 7. Implementação de Referência

### Encoder (Python)

```python
def encode_said_attest(cid: str) -> bytes:
    """Codifica um OP_RETURN de emissão de atestação."""
    tag = b'SAID'
    version = bytes([0x01])
    op_type = bytes([0x01])  # ATTEST
    payload = cid.encode('utf-8')
    
    return tag + version + op_type + payload


def encode_said_revoke(txid: bytes, vout: int) -> bytes:
    """Codifica um OP_RETURN de revogação."""
    tag = b'SAID'
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
class SAIDAttest:
    cid: str

@dataclass 
class SAIDRevoke:
    txid: bytes
    vout: int

def decode_said(data: bytes) -> Optional[Union[SAIDAttest, SAIDRevoke]]:
    """Decodifica um OP_RETURN SAID."""
    if len(data) < 6:
        return None
    if data[0:4] != b'SAID':
        return None
        
    version = data[4]
    op_type = data[5]
    payload = data[6:]
    
    if version != 0x01:
        return None
        
    if op_type == 0x01:  # ATTEST
        return SAIDAttest(cid=payload.decode('utf-8'))
    elif op_type == 0x02:  # REVOKE
        return SAIDRevoke(txid=payload[0:32], vout=int.from_bytes(payload[32:34], 'big'))
    
    return None
```

---

*Simplicity Attestation - SAID Protocol Specification v1.0*
