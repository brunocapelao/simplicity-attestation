# SAP - Simplicity Attestation Protocol

## Sistema de Certificados On-Chain com Delegacao via Simplicity

**Versao:** 2.0
**Data:** 2026-01-06
**Status:** Especificacao Tecnica

---

## 1. Visao Geral

O SA e um sistema de certificados digitais on-chain que utiliza Simplicity na Liquid Network para:

1. **Admin** (Autoridade Raiz) cria vaults de delegacao
2. **Delegado** emite certificados gastando do vault
3. **Certificados** sao UTXOs que representam atestacoes validas
4. **Revogacao** ocorre quando o UTXO do certificado e gasto

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CADEIA DE CONFIANCA SA.                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ADMIN (Autoridade Raiz)                                                   │
│      │                                                                      │
│      │ Cria vault com funding                                               │
│      ▼                                                                      │
│   ┌─────────────────────────────────────────┐                              │
│   │         DELEGATION VAULT                │                              │
│   │         (Script Simplicity V)           │                              │
│   │         Balance: N sats                 │                              │
│   └─────────────────────────────────────────┘                              │
│      │                                                                      │
│      ├──► Admin gasta = DESATIVA delegado (vault vazio)                    │
│      │                                                                      │
│      └──► Delegado gasta = EMITE certificado                               │
│              │                                                              │
│              ├── Output 0: Troco → Vault V (ENFORCED pelo script)          │
│              ├── Output 1: Certificate UTXO → Script C                      │
│              ├── Output 2: OP_RETURN com CID IPFS                          │
│              └── Output 3: Fee                                              │
│                       │                                                     │
│                       ▼                                                     │
│              ┌─────────────────────────────────────────┐                   │
│              │       CERTIFICATE UTXO                  │                   │
│              │       (Script Simplicity C)             │                   │
│              │                                         │                   │
│              │   UTXO existe = Certificado VALIDO      │                   │
│              │   UTXO gasto  = Certificado REVOGADO    │                   │
│              └─────────────────────────────────────────┘                   │
│                       │                                                     │
│                       ├──► Admin gasta = REVOGA certificado                │
│                       └──► Delegado gasta = REVOGA certificado             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

  Resumo das Permissões

  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                           MATRIZ DE PERMISSÕES                              │
  ├─────────────────────────────────────────────────────────────────────────────┤
  │                                                                             │
  │  AÇÃO                              │  ADMIN  │  DELEGATE  │                │
  │  ──────────────────────────────────┼─────────┼────────────┤                │
  │  Emitir certificado (vault)        │   ✅    │     ✅     │                │
  │  Revogar certificado               │   ✅    │     ✅     │                │
  │  Desativar delegado (esvaziar)     │   ✅    │     ❌     │                │
  │  Gastar vault incondicionalmente   │   ✅    │     ❌     │                │
  │                                                                             │
  ├─────────────────────────────────────────────────────────────────────────────┤
  │                                                                             │
  │  CADEIA DE CONFIANÇA:                                                       │
  │                                                                             │
  │  Admin (Autoridade Máxima)                                                  │
  │    ├── Pode desativar Delegado a qualquer momento                          │
  │    ├── Pode revogar qualquer certificado                                   │
  │    └── Pode emitir certificados (com covenants)                            │
  │                                                                             │
  │  Delegado (Autoridade Delegada)                                             │
  │    ├── Pode emitir certificados (enquanto vault tiver fundos)              │
  │    ├── Pode revogar próprios certificados                                  │
  │    └── NÃO pode impedir Admin de desativá-lo                               │
  │                                                                             │
  └─────────────────────────────────────────────────────────────────────────────┘

  Fluxo Visual

                      ADMIN
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
     DESATIVAR     REVOGAR        (emite c/ covenant)
     DELEGADO    CERTIFICADO
          │             │
          ▼             ▼
     Vault vazio   Cert UTXO
                    gasto


                    DELEGADO
                        │
          ┌─────────────┼─────────────┐
          │             │             │
          ▼             ▼             ▼
       EMITIR       REVOGAR      (não desativa)
    CERTIFICADO   CERTIFICADO
          │             │
          ▼             ▼
     Novo Cert     Cert UTXO
       UTXO         gasto

---

## 2. Principio Fundamental

### Estado do Certificado via UTXO

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                      REGRA DE VALIDADE DO CERTIFICADO                     ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║   Certificate UTXO NAO GASTO  ──►  Certificado VALIDO   ✓                 ║
║   Certificate UTXO GASTO      ──►  Certificado REVOGADO ✗                 ║
║                                                                           ║
║   A validade e verificada consultando a blockchain:                       ║
║   - Se o UTXO existe (unspent) = certificado ativo                        ║
║   - Se o UTXO foi gasto = certificado revogado                            ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

### Indexacao e Verificacao

Para verificar um certificado:

```python
def verificar_certificado(txid: str, vout: int) -> bool:
    """
    Verifica se um certificado e valido.

    Args:
        txid: Transaction ID onde o certificado foi emitido
        vout: Output index do certificate UTXO

    Returns:
        True se valido (UTXO nao gasto), False se revogado (UTXO gasto)
    """
    utxo_status = get_utxo_status(txid, vout)
    return utxo_status == "unspent"
```

---

## 3. Arquitetura Tecnica

### 3.1 Componentes do Sistema

| Componente | Tipo | Descricao |
|------------|------|-----------|
| **Delegation Vault (V)** | Script Simplicity | Pool de funding para emissao de certificados |
| **Certificate (C)** | Script Simplicity | UTXO que representa um certificado valido |
| **OP_RETURN** | Dados | Payload SAP com CID IPFS do certificado |
| **Admin Key** | Schnorr Pubkey | Autoridade raiz do sistema |
| **Delegate Key** | Schnorr Pubkey | Autoridade delegada para emitir certificados |

### 3.2 Delegation Vault (Script V)

O vault utiliza o **disconnect combinator** do Simplicity para garantir que o troco retorne ao mesmo endereco:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DELEGATION VAULT SCRIPT                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Witness: Either<AdminSig, (DelegateSig, OutputProof)>                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ LEFT PATH (Admin)                                                    │   │
│  │ ─────────────────                                                    │   │
│  │ 1. Verificar assinatura do Admin                                     │   │
│  │ 2. Pode gastar incondicionalmente                                    │   │
│  │    → DESATIVA o delegado (vault fica vazio)                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ RIGHT PATH (Delegate)                                                │   │
│  │ ──────────────────────                                               │   │
│  │ 1. Verificar assinatura do Delegado                                  │   │
│  │                                                                      │   │
│  │ 2. COVENANT: Verificar output[0] (Troco)                            │   │
│  │    - script_pubkey == VAULT_SCRIPT_PUBKEY (mesmo endereco)          │   │
│  │    - amount >= input_amount - cert_amount - fee                      │   │
│  │    *** ENFORCED PELO CODIGO, NAO POR INCENTIVO ***                  │   │
│  │                                                                      │   │
│  │ 3. COVENANT: Verificar output[1] (Certificate)                      │   │
│  │    - script_pubkey == CERTIFICATE_SCRIPT_PUBKEY                     │   │
│  │    - amount >= DUST_LIMIT (546 sats)                                │   │
│  │                                                                      │   │
│  │ 4. Verificar output[2] (OP_RETURN)                                  │   │
│  │    - Deve existir e conter dados                                     │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Certificate (Script C)

Script simples que permite Admin OU Delegado gastar (revogar):

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CERTIFICATE SCRIPT                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Witness: Either<AdminSig, DelegateSig>                                    │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ LEFT PATH (Admin) ou RIGHT PATH (Delegate)                          │   │
│  │ ─────────────────────────────────────────────                        │   │
│  │ 1. Verificar assinatura (Admin ou Delegate)                          │   │
│  │ 2. Pode gastar incondicionalmente                                    │   │
│  │    → REVOGA o certificado                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Nota: O ato de gastar este UTXO = revogar o certificado                   │
│  Opcionalmente pode incluir OP_RETURN com SAP tipo REVOKE                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Disconnect Combinator e Self-Reference

### O Problema da Self-Reference

Para garantir que o troco retorne ao mesmo vault, o script precisa verificar que o output vai para "si mesmo". Isso cria um problema circular:

```
Script precisa do script_pubkey → script_pubkey depende do CMR → CMR depende do script
```

### A Solucao: Disconnect Combinator

O Simplicity resolve isso com o `disconnect` combinator:

```
disconnect(committed_expr, disconnected_expr_cmr)
```

**Funcionamento:**
1. O `committed_expr` (logica principal) e incluido no CMR
2. O `disconnected_expr` e fornecido no witness, mas seu CMR e passado como dado
3. Isso permite que o script conheca seu proprio CMR sem dependencia circular

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DISCONNECT COMBINATOR PATTERN                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  VaultScript = disconnect(                                                  │
│      MainLogic,           // Committed: verificacoes de output             │
│      SpendingRules_CMR    // Disconnected CMR: regras flexiveis            │
│  )                                                                          │
│                                                                             │
│  MainLogic = {                                                              │
│      // Pode acessar seu proprio CMR!                                       │
│      let my_cmr = get_cmr();                                               │
│      let expected_script = taproot_scriptpubkey(internal_key, my_cmr);     │
│                                                                             │
│      // Verificar que output[0] vai para o mesmo endereco                  │
│      let output_script = jet::output_script_hash(0);                       │
│      assert(output_script == sha256(expected_script));                     │
│  }                                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Jets de Introspection Disponiveis

| Jet | Descricao | Uso |
|-----|-----------|-----|
| `jet::output_script_hash(u32)` | Hash do scriptPubKey do output N | Verificar destino |
| `jet::output_amount(u32)` | Valor do output N | Verificar valor |
| `jet::output_asset(u32)` | Asset ID do output N (Liquid) | Verificar asset |
| `jet::output_null_datum(u32, u32)` | Dados do OP_RETURN | Verificar CID |
| `jet::current_index()` | Indice do input atual | Self-reference |
| `jet::input_script_hash(u32)` | Hash do script do input N | Comparacao |

---

## 5. Fluxo de Operacoes

### 5.1 Setup: Criacao do Sistema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SETUP INICIAL                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Admin gera par de chaves (admin_privkey, admin_pubkey)                 │
│  2. Delegado gera par de chaves (delegate_privkey, delegate_pubkey)        │
│                                                                             │
│  3. Compilar Certificate Script (C):                                        │
│     - Input: admin_pubkey, delegate_pubkey                                 │
│     - Output: CMR_C, CERTIFICATE_SCRIPT_PUBKEY                             │
│                                                                             │
│  4. Compilar Vault Script (V):                                              │
│     - Input: admin_pubkey, delegate_pubkey, CERTIFICATE_SCRIPT_PUBKEY      │
│     - Output: CMR_V, VAULT_SCRIPT_PUBKEY                                   │
│                                                                             │
│  5. Admin envia fundos para VAULT_ADDRESS                                   │
│     → Sistema ativo, Delegado pode emitir certificados                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Emissao de Certificado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EMISSAO DE CERTIFICADO                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  DELEGADO executa:                                                          │
│                                                                             │
│  1. Cria documento/certificado off-chain                                   │
│  2. Upload para IPFS → obtem CID                                           │
│  3. Constroi transacao:                                                     │
│                                                                             │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │ TX de Emissao                                                    │    │
│     ├─────────────────────────────────────────────────────────────────┤    │
│     │ Input 0: Vault UTXO (gasto com delegate path)                   │    │
│     │                                                                  │    │
│     │ Output 0: Troco → Vault Address (ENFORCED)                      │    │
│     │           Valor: input - cert_amount - fee                       │    │
│     │                                                                  │    │
│     │ Output 1: Certificate UTXO → Certificate Address                │    │
│     │           Valor: 546 sats (dust)                                │    │
│     │                                                                  │    │
│     │ Output 2: OP_RETURN                                             │    │
│     │           Dados: SAP 01 01 <CID_IPFS>                           │    │
│     │                                                                  │    │
│     │ Output 3: Fee                                                   │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  4. Assina e broadcast                                                      │
│  5. Certificado emitido! UTXO no Output 1 representa o certificado         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.3 Revogacao de Certificado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        REVOGACAO DE CERTIFICADO                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ADMIN ou DELEGADO executa:                                                 │
│                                                                             │
│  1. Identifica o Certificate UTXO a revogar (txid:vout)                    │
│  2. Constroi transacao gastando o Certificate UTXO                         │
│                                                                             │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │ TX de Revogacao                                                  │    │
│     ├─────────────────────────────────────────────────────────────────┤    │
│     │ Input 0: Certificate UTXO (gasto com admin ou delegate path)    │    │
│     │                                                                  │    │
│     │ Output 0: Destinatario opcional (se informado)                  │    │
│     │           Se omitido, valor vai para fee (queima)               │    │
│     │                                                                  │    │
│     │ Output 1: OP_RETURN (opcional)                                  │    │
│     │           Dados: SAP 01 02 <TXID:VOUT>[:REASON][:REPLACEMENT]   │    │
│     │                                                                  │    │
│     │ Output 2: Fee (se houver destinatario)                          │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  3. Assina e broadcast                                                      │
│  4. Certificado revogado! UTXO gasto = certificado invalido                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.4 Desativacao do Delegado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DESATIVACAO DO DELEGADO                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Apenas ADMIN pode executar:                                                │
│                                                                             │
│  1. Identifica o Vault UTXO                                                │
│  2. Gasta usando admin path (incondicional)                                │
│  3. Envia fundos para onde quiser                                          │
│                                                                             │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │ TX de Desativacao                                                │    │
│     ├─────────────────────────────────────────────────────────────────┤    │
│     │ Input 0: Vault UTXO (gasto com admin path)                      │    │
│     │                                                                  │    │
│     │ Output 0: Qualquer endereco (Admin recupera fundos)             │    │
│     │                                                                  │    │
│     │ Output 1: Fee                                                   │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  4. Vault vazio = Delegado nao pode mais emitir certificados               │
│                                                                             │
│  Nota: Certificados ja emitidos continuam validos!                         │
│  Para invalidar certificados existentes, Admin deve revogar cada um.       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.5 Ciclo completo (E2E)

1. **Criacao do vault** (Admin): compila contratos com chaves publicas, gera CMRs e enderecos.
2. **Funding do vault**: enviar L-BTC para o endereco do vault.
3. **Emissao** (Admin ou Delegado): gasta o vault e cria o Certificate UTXO + OP_RETURN.
4. **Revogacao** (Admin ou Delegado): gasta o Certificate UTXO.
5. **Substituicao (opcional)**:
   - Revoga com `reason_code=REISSUE_REPLACEMENT` e `replacement_txid`.
   - Emite novo certificado com o CID atualizado.

O estado do certificado e definido pelo UTXO:
- **Unspent**: valido.
- **Spent**: revogado.

### 5.6 Exemplo E2E (testnet)

Emissao:
- TXID: `49f10e4899029104aa875d11df82e2f1acfb10360a6268d13b5fe10c787dcb48`
- Output 1 (certificate UTXO): `vout=1` na `tex1pfeaa7eex2cxa923tehj5vd0emf779fp8v968mcx9uymm6q3gze6s8cvkka`

Revogacao com substituicao:
- TXID: `b73da760d3ac4b5c893a43a359c55cf657a770bd1cb49893e4aad7c9e6329f88`
- OP_RETURN inclui:
  - `TXID:VOUT` revogado: `1650b3ffe11d591d918c5c5b55d7a4bf70874ab526be28206e51d441aba2a6b9:1`
  - `reason_code=6` (REISSUE_REPLACEMENT)
  - `replacement_txid=49f10e4899029104aa875d11df82e2f1acfb10360a6268d13b5fe10c787dcb48`
Explorer:
- Emissao: https://blockstream.info/liquidtestnet/tx/49f10e4899029104aa875d11df82e2f1acfb10360a6268d13b5fe10c787dcb48
- Revogacao: https://blockstream.info/liquidtestnet/tx/b73da760d3ac4b5c893a43a359c55cf657a770bd1cb49893e4aad7c9e6329f88

### 5.7 Execucao E2E recente (testnet)

Emissoes:
- Admin: `5487ed018fa69105acc4ce525b865d25f8cb0ac92297a64539008b50243ed7bb`
- Delegate: `423efc36bb3112546324a91482681091dea6a9e83a94583fa5a80fe3cedef355`
- Edge cases (emitido pelo script): `2bf4e71f5c9c081a93e1599fe45e324e7a8670e1eb104eec7507955109d1d507`

Explorer:
- Admin: https://blockstream.info/liquidtestnet/tx/5487ed018fa69105acc4ce525b865d25f8cb0ac92297a64539008b50243ed7bb
- Delegate: https://blockstream.info/liquidtestnet/tx/423efc36bb3112546324a91482681091dea6a9e83a94583fa5a80fe3cedef355
- Edge cases: https://blockstream.info/liquidtestnet/tx/2bf4e71f5c9c081a93e1599fe45e324e7a8670e1eb104eec7507955109d1d507

Revogacoes:
- Admin: `07048a43fabae3b4ca3f10316b9241fdee5259e68c61056a89c66acac16c57e5`
- Delegate: `2601bb94fcb361ff34657804b7274ceb47a83f31eab7c3cce56b6a3eee718ef0`

Explorer:
- Admin: https://blockstream.info/liquidtestnet/tx/07048a43fabae3b4ca3f10316b9241fdee5259e68c61056a89c66acac16c57e5
- Delegate: https://blockstream.info/liquidtestnet/tx/2601bb94fcb361ff34657804b7274ceb47a83f31eab7c3cce56b6a3eee718ef0

---

## 6. Protocolo SAP (OP_RETURN)

### 6.1 Formato

```
┌───────┬─────────┬──────────┬─────────────────────────────────────┐
│  TAG  │ VERSION │   TYPE   │             PAYLOAD                 │
│ "SAP" │  0x01   │  0x01    │   CID IPFS (46-59 bytes)           │
├───────┼─────────┼──────────┼─────────────────────────────────────┤
│3 bytes│ 1 byte  │  1 byte  │           variavel                  │
└───────┴─────────┴──────────┴─────────────────────────────────────┘
```

### 6.2 Tipos de Operacao

| Tipo | Byte | Descricao | Payload |
|------|------|-----------|---------|
| ATTEST | `0x01` | Emissao de certificado | CID IPFS |
| REVOKE | `0x02` | Revogacao de certificado | TXID:VOUT (+ reason_code + replacement_txid) |
| UPDATE | `0x03` | Atualizacao de metadados | Novo CID IPFS |

### 6.3 Exemplos

**Emissao:**
```
5341500101516d59774150...
│     │ │ └── CID: QmYwAP...
│     │ └──── Tipo: ATTEST (0x01)
│     └────── Versao: 1
└──────────── Magic: "SAP"
```

**Revogacao (minima):**
```
534150010212ab34cd56ef...0001
│     │ │ └── TXID:VOUT referenciado
│     │ └──── Tipo: REVOKE (0x02)
│     └────── Versao: 1
└──────────── Magic: "SAP"
```

**Revogacao com motivo e substituicao:**
```
5341500102 <TXID> <VOUT> <REASON> <REPLACEMENT_TXID>
```

`REASON` e `REPLACEMENT_TXID` sao opcionais, mas `REPLACEMENT_TXID` so pode aparecer se `REASON` estiver presente.

### 6.4 Codigos de revogacao (reason_code)

| Codigo | Constante | Uso | Descricao curta | Quando usar (exemplos praticos) |
| --- | --- | --- | --- | --- |
| **1** | `DATA_ERROR` | MVP | Erro na emissao/conteudo. | Campo trocado, pessoa errada, data invalida; revogue e reemita correto. |
| **2** | `DUPLICATE` | MVP | Registro duplicado (mesmo emissor). | Duas emissoes do mesmo objeto; manter apenas a via correta. |
| **3** | `FRAUD_SUSPECTED` | MVP | Indicios de fraude (em apuracao). | Sinais de falsificacao/uso indevido; pode evoluir para 4. |
| **4** | `FRAUD_CONFIRMED` | MVP | Fraude confirmada com evidencia. | Documento/VC falsa, identidade forjada. |
| **5** | `HOLDER_REQUEST` | MVP | Pedido do titular. | Retirada de consentimento, exposicao indevida, necessidade de cancelamento. |
| **6** | `REISSUE_REPLACEMENT` | MVP | Substituicao por reemissao. | Nova via corrigida/atualizada substitui a anterior. |
| **7** | `ADMINISTRATIVE` | MVP | Decisao/regra administrativa. | Encerramento de vinculo, programa/politica encerrada, obito. |
| **8** | `LEGAL_ORDER` | MVP | Ordem judicial/regulatoria. | Determinacao externa obrigatoria. |
| **9** | `KEY_COMPROMISE` | MVP | Comprometimento de chaves/dispositivo. | Carteira do titular perdida/comprometida; chave do emissor exposta. |
| **10** | `SUSPENDED` | Futuro (V2) | Suspensao temporaria (nao-terminal). | Bloqueio enquanto dura investigacao/cumprimento de requisito. |
| **11** | `CRYPTO_DEPRECATED` | Futuro | Algoritmo/curva obsoleta ou vulneravel. | Revogacao/reemissao em massa por obsolescencia criptografica. |
| **12** | `PROCESS_ERROR` | Futuro | Falha sistemica de processo/lote. | Template/ETL/regra aplicados incorretamente a um lote; recall. |
| **13** | **RESERVED** | Futuro | Reservado. | Mantido para extensoes padronizadas. |
| **14** | **RESERVED** | Futuro | Reservado. | Mantido para extensoes padronizadas. |
| **15** | **RESERVED** | Futuro | Reservado. | Mantido para extensoes padronizadas. |

---

## 7. Consideracoes de Seguranca

### 7.1 Garantias do Sistema

| Propriedade | Garantia | Mecanismo |
|-------------|----------|-----------|
| **Troco vai para vault** | Enforced pelo codigo | Covenant com verificacao de script_pubkey |
| **Certificate vai para script C** | Enforced pelo codigo | Covenant hardcoded |
| **Apenas Admin desativa** | Enforced pelo codigo | Verificacao de assinatura |
| **Admin OU Delegate revogam** | Enforced pelo codigo | Either path no certificate |
| **Certificado valido se UTXO existe** | Propriedade UTXO | Modelo Bitcoin |

### 7.2 Vetores de Ataque Mitigados

1. **Delegado desvia troco**: Impossivel - covenant verifica destino
2. **Delegado cria certificate falso**: Impossivel - script_pubkey verificado
3. **Terceiro revoga certificado**: Impossivel - requer assinatura Admin ou Delegate
4. **Double-spend de certificado**: Impossivel - modelo UTXO previne

### 7.3 Limitacoes Conhecidas

1. **Admin pode revogar qualquer certificado**: By design - Admin e autoridade raiz
2. **Delegado pode revogar proprios certificados**: By design - permite correcao de erros
3. **Certificados persistem apos desativacao**: By design - revogacao e separada

---

## 8. Implementacao

### 8.1 Dependencias

| Ferramenta | Versao | Uso |
|------------|--------|-----|
| simc | latest | Compilador Simfony → Simplicity |
| hal-simplicity | fork | CLI para PSET e broadcast |
| embit | latest | Assinaturas Schnorr (Python) |

### 8.2 Arquivos do Sistema

```
contracts/
├── vault.simf              # Delegation Vault com covenants
└── certificate.simf        # Certificate script

tests/
├── test_emit.py            # Teste de emissao de certificado
├── test_certificate_revoke.py  # Teste de revogacao
└── test_edge_cases.py      # Testes de seguranca

docs/
├── DOCUMENTATION.md        # Esta especificacao (Ingles)
├── DOCUMENTACAO.md         # Esta especificacao (Portugues)
└── PROTOCOL_SPEC.md        # Especificacao do protocolo SAP

secrets.json                # Chaves e enderecos (testnet)
```

### 8.3 Pseudo-codigo Simfony

**vault_v2.simf:**
```rust
// Delegation Vault v2 - Com Covenants Enforced

mod witness {
    // Either<AdminSig, DelegateSig>
    const SPENDING_PATH: Either<Signature, Signature>;
}

// Constantes (hardcoded na compilacao)
const ADMIN_PUBKEY: Pubkey = 0x...;
const DELEGATE_PUBKEY: Pubkey = 0x...;
const CERTIFICATE_SCRIPT_HASH: u256 = 0x...; // Hash do script do certificate
const VAULT_SCRIPT_HASH: u256 = 0x...;       // Hash do proprio script (self-ref)
const CERT_MIN_AMOUNT: u64 = 1000;           // Minimo para certificate

fn checksig(pk: Pubkey, sig: Signature) {
    let msg: u256 = jet::sig_all_hash();
    jet::bip_0340_verify((pk, msg), sig);
}

fn admin_spend(admin_sig: Signature) {
    // Admin pode gastar incondicionalmente
    checksig(ADMIN_PUBKEY, admin_sig);
}

fn delegate_spend(delegate_sig: Signature) {
    // 1. Verificar assinatura do delegado
    checksig(DELEGATE_PUBKEY, delegate_sig);

    // 2. COVENANT: Output 0 deve ir para o vault (troco)
    let output0_script: u256 = jet::output_script_hash(0);
    assert!(output0_script == VAULT_SCRIPT_HASH);

    // 3. COVENANT: Output 1 deve ir para certificate script
    let output1_script: u256 = jet::output_script_hash(1);
    assert!(output1_script == CERTIFICATE_SCRIPT_HASH);

    // 4. Verificar valor minimo do certificate
    let output1_amount: u64 = jet::output_amount(1);
    assert!(output1_amount >= CERT_MIN_AMOUNT);

    // 5. Verificar que existe OP_RETURN (output 2)
    let maybe_datum = jet::output_null_datum(2, 0);
    match maybe_datum {
        Some(_) => { /* OK */ },
        None => panic!(),
    };
}

fn main() {
    match witness::SPENDING_PATH {
        Left(admin_sig) => admin_spend(admin_sig),
        Right(delegate_sig) => delegate_spend(delegate_sig),
    }
}
```

**certificate.simf:**
```rust
// Certificate Script - Admin ou Delegate podem revogar

mod witness {
    const SPENDING_PATH: Either<Signature, Signature>;
}

const ADMIN_PUBKEY: Pubkey = 0x...;
const DELEGATE_PUBKEY: Pubkey = 0x...;

fn checksig(pk: Pubkey, sig: Signature) {
    let msg: u256 = jet::sig_all_hash();
    jet::bip_0340_verify((pk, msg), sig);
}

fn main() {
    match witness::SPENDING_PATH {
        Left(admin_sig) => checksig(ADMIN_PUBKEY, admin_sig),
        Right(delegate_sig) => checksig(DELEGATE_PUBKEY, delegate_sig),
    }
}
```

---

## 9. Verificacao de Certificados

### 9.1 Consulta On-Chain

```python
def verificar_certificado(cert_txid: str, cert_vout: int = 1) -> dict:
    """
    Verifica o status de um certificado.

    Returns:
        {
            "valido": bool,
            "cid": str,           # CID do IPFS
            "emitido_em": int,    # Block height
            "revogado_em": int,   # Block height (se revogado)
            "emitido_por": str,   # Delegate pubkey
        }
    """
    # 1. Verificar se UTXO existe (nao gasto)
    utxo = get_utxo(cert_txid, cert_vout)

    # 2. Obter dados do OP_RETURN da TX de emissao
    tx = get_transaction(cert_txid)
    op_return_data = parse_op_return(tx.outputs[2])

    # 3. Decodificar SAP
    sap = decode_sap(op_return_data)

    return {
        "valido": utxo is not None,
        "cid": sap.cid,
        "emitido_em": tx.block_height,
        "revogado_em": None if utxo else get_spend_height(cert_txid, cert_vout),
    }
```

### 9.2 API do Indexador

```
GET /api/v1/certificate/{txid}/{vout}

Response:
{
    "status": "valid" | "revoked",
    "cid": "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
    "issuer": "tex1...",
    "issued_at": 2256100,
    "revoked_at": null,
    "vault_address": "tex1pewrql3..."
}
```

---

## 10. Roadmap

### Fase 1: MVP (Atual)
- [x] P2PK basico com OP_RETURN
- [x] Vault v1 (sem covenant de troco)
- [ ] **Vault v2 com covenants enforced**
- [ ] Certificate script
- [ ] Scripts de emissao/revogacao

### Fase 2: Producao
- [ ] Indexador de certificados
- [ ] API de verificacao
- [ ] Interface web

### Fase 3: Extensoes
- [ ] Multi-delegate
- [ ] Spend limits por delegado
- [ ] Expiracao de delegacao

---

## 11. Referencias

- [Disconnecting Simplicity Expressions](https://blog.blockstream.com/disconnecting-simplicity-expressions/)
- [Simplicity: Taproot and Universal Sighashes](https://blog.blockstream.com/simplicity-taproot-and-universal-sighashes/)
- [Covenants in Production on Liquid](https://blog.blockstream.com/covenants-in-production-on-liquid/)
- [Elements Introspection Opcodes](https://github.com/ElementsProject/elements/blob/master/doc/tapscript_opcodes.md)
- [BlockstreamResearch/simplicity](https://github.com/BlockstreamResearch/simplicity)
- [BlockstreamResearch/simfony](https://github.com/BlockstreamResearch/simfony)

---

*SAP - Simplicity Attestation Protocol - Especificacao v2.0*

---

[English Version](DOCUMENTATION.md)
