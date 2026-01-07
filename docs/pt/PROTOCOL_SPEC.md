# 📋 SAP - Simplicity Attestation Protocol

## Simplicity Attestation Protocol (SAP)

**Versão:** 1.0  
**Data:** 2026-01-05  
**Projeto:** Simplicity Attestation

---

## 1. Visão Geral

O protocolo SAP define um formato padronizado para armazenar referências a atestações (certificados) em outputs OP_RETURN de transações Liquid/Bitcoin. O formato permite que indexadores identifiquem rapidamente transações relacionadas ao sistema Simplicity Attestation.

---

## 2. Formato do OP_RETURN

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ESTRUTURA DO OP_RETURN                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌────────┬─────────┬──────────┬────────────────────────────────────────┐  │
│   │  TAG   │ VERSION │  TYPE    │              PAYLOAD                    │  │
│   │ 3 bytes│ 1 byte  │  1 byte  │           (variable)                    │  │
│   └────────┴─────────┴──────────┴────────────────────────────────────────┘  │
│                                                                              │
│   Total: 5 bytes de header + payload (CID)                                   │
│   Máximo OP_RETURN: ~80 bytes → ~75 bytes para payload                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 TAG (3 bytes)

**Magic bytes** para identificar o protocolo Simplicity Attestation:

```
ASCII:  "SAP"
HEX:    0x534150
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
| ATTEST | CID/identificador (variável, até 75 bytes) |
| REVOKE | TXID:vout (+ reason_code opcional + replacement_txid opcional) |
| UPDATE | CID/identificador (variável, até 75 bytes) |
| DELEGATE | Pubkey do delegate (32 bytes) |
| UNDELEGATE | Pubkey do delegate (32 bytes) |

---

## 3. Exemplos

### 3.1 Emissão de Atestação

```
OP_RETURN:
┌────────────┬─────┬──────┬─────────────────────────────────────────────────┐
│    SAP     │ 01  │  01  │ QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG │
├────────────┼─────┼──────┼─────────────────────────────────────────────────┤
│ 534150     │ 01  │  01  │ (46 bytes - CIDv0 base58)                       │
└────────────┴─────┴──────┴─────────────────────────────────────────────────┘

HEX completo:
534150 01 01 516d59774150...
```

Exemplo real (Liquid testnet) com payload UTF-8:

- TX de emissão: `https://blockstream.info/liquidtestnet/tx/2785aac5ea950c54ece28b1fbfdeb5acf29903fed89ecbb78ba997fe0b927fcb`
- OP_RETURN (output `vout=2`): `534150010145582d4e45572d31373637373936313938` → `SAP|01|01|EX-NEW-1767796198`

### 3.2 Revogação de Atestação

```
OP_RETURN:
┌────────────┬─────┬──────┬─────────────────────────────────────────────────┐
│    SAP     │ 01  │  02  │ <TXID>:<vout>[:reason_code][:replacement_txid]  │
├────────────┼─────┼──────┼─────────────────────────────────────────────────┤
│ 534150     │ 01  │  02  │ (34 bytes - 32 bytes TXID + 2 bytes vout)       │
└────────────┴─────┴──────┴─────────────────────────────────────────────────┘
```

Se presente, `reason_code` é 1 byte adicional ao final do payload. `replacement_txid` (32 bytes) só pode aparecer junto com `reason_code`.

Exemplo real (reason + replacement):

- TX de revogação: `https://blockstream.info/liquidtestnet/tx/625dcfdac2ca7a2ddfb857254459c46e17939c7785c3e20c21f3ea33fb5be729`
- Decodificado: `txid=912a79b929e331cfaf02727cd9f3282c8f87dd4a7af502c2ccf765feb5c12444`, `vout=1`, `reason_code=6 (REISSUE_REPLACEMENT)`, `replacement_txid=2785aac5ea950c54ece28b1fbfdeb5acf29903fed89ecbb78ba997fe0b927fcb`

### 3.3 Códigos de revogação (reason_code)

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

## 4. Algoritmo do Indexador

```python
def index_transaction(tx):
    for i, output in enumerate(tx.outputs):
        if not is_op_return(output):
            continue
            
        data = output.script_data
        
        # Verificar magic bytes
        if len(data) < 5:
            continue
        if data[0:3] != b'SAP':
            continue
            
        # Parse header
        version = data[3]
        op_type = data[4]
        payload = data[5:]
        
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
// Verificar que o OP_RETURN começa com "SAP"
let maybe_datum = jet::output_null_datum(2, 0);
// Extrair primeiros 4 bytes e comparar com 0x53414944
```

### 5.3 Tamanho

| Componente | Tamanho | Acumulado |
|------------|---------|-----------|
| OP_RETURN max | 80 bytes | - |
| TAG (SAP) | 3 bytes | 3 |
| VERSION | 1 byte | 4 |
| TYPE | 1 byte | 5 |
| CIDv0 | 46 bytes | 51 |
| **Sobra** | 29 bytes | - |

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
def encode_sap_attest(cid: str) -> bytes:
    """Codifica um OP_RETURN de emissão de atestação."""
    tag = b'SAP'
    version = bytes([0x01])
    op_type = bytes([0x01])  # ATTEST
    payload = cid.encode('utf-8')
    
    return tag + version + op_type + payload


def encode_sap_revoke(txid: bytes, vout: int) -> bytes:
    """Codifica um OP_RETURN de revogação."""
    tag = b'SAP'
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
class SAPAttest:
    cid: str

@dataclass
class SAPRevoke:
    txid: bytes
    vout: int

def decode_sap(data: bytes) -> Optional[Union[SAPAttest, SAPRevoke]]:
    """Decodifica um OP_RETURN SAP."""
    if len(data) < 5:
        return None
    if data[0:3] != b'SAP':
        return None

    version = data[3]
    op_type = data[4]
    payload = data[5:]

    if version != 0x01:
        return None

    if op_type == 0x01:  # ATTEST
        return SAPAttest(cid=payload.decode('utf-8'))
    elif op_type == 0x02:  # REVOKE
        return SAPRevoke(txid=payload[0:32], vout=int.from_bytes(payload[32:34], 'big'))
    
    return None
```

---

*Simplicity Attestation Protocol (SAP) - Specification v1.0*

---

[English Version](../PROTOCOL_SPEC.md)
