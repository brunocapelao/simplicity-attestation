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
  │  Emitir certificado (vault)        │   ❌    │     ✅     │                │
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
  │    └── NÃO pode emitir certificado (by design)                             │
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
     DESATIVAR     REVOGAR        (não emite)
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
│     │           Valor: 1000 sats (minimo)                             │    │
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
│     │ Output 0: Qualquer endereco (recupera os sats)                  │    │
│     │                                                                  │    │
│     │ Output 1: OP_RETURN (opcional)                                  │    │
│     │           Dados: SAP 01 02 <TXID_ORIGINAL:VOUT>                 │    │
│     │                                                                  │    │
│     │ Output 2: Fee                                                   │    │
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
| REVOKE | `0x02` | Revogacao de certificado | TXID:VOUT (34 bytes) |
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

**Revogacao:**
```
534150010212ab34cd56ef...0001
│     │ │ └── TXID:VOUT referenciado
│     │ └──── Tipo: REVOKE (0x02)
│     └────── Versao: 1
└──────────── Magic: "SAP"
```

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
v2/
├── DOCUMENTACAO.md              # Esta especificacao
├── vault_v2.simf                # Delegation Vault com covenants
├── certificate.simf             # Certificate script
├── scripts/
│   ├── setup_system.py          # Setup inicial (compilar, gerar enderecos)
│   ├── emit_certificate.py      # Emissao de certificado
│   ├── revoke_certificate.py    # Revogacao de certificado
│   └── deactivate_delegate.py   # Desativacao de delegado
└── secrets.json                 # Chaves e enderecos (testnet)
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

*SA Protocol - Simplicity Attestation*
