# 📜 Sistema de Certificados On-Chain com Simplicity

## Documentação Completa da Implementação

---

# Índice

1. [Visão Geral](#1-visão-geral)
2. [Caso de Uso](#2-caso-de-uso)
3. [Fundamentos Técnicos](#3-fundamentos-técnicos)
4. [Arquitetura do Sistema](#4-arquitetura-do-sistema)
5. [Contratos Simplicity](#5-contratos-simplicity)
6. [Fluxos Operacionais](#6-fluxos-operacionais)
7. [Armazenamento de Dados (IPFS)](#7-armazenamento-de-dados-ipfs)
8. [Guia de Implementação](#8-guia-de-implementação)
9. [Segurança](#9-segurança)
10. [Referências](#10-referências)

---

# 1. Visão Geral

## 1.1 O que é este sistema?

Este é um **sistema de certificados digitais on-chain** construído sobre a **Liquid Network** utilizando **Simplicity**, uma linguagem de smart contracts desenvolvida pela Blockstream especificamente para blockchains baseadas em Bitcoin.

O sistema permite:
- **Emissão de certificados** com dados armazenados no IPFS
- **Verificação on-chain** da validade dos certificados
- **Revogação on-chain** por autoridades autorizadas
- **Delegação de autoridade** com controle hierárquico

## 1.2 Por que Simplicity?

| Característica | Bitcoin Script | Ethereum/Solidity | Simplicity |
|----------------|----------------|-------------------|------------|
| **Segurança** | Alta (limitado) | Média (bugs comuns) | Alta (verificável formalmente) |
| **Expressividade** | Baixa | Alta | Média-Alta |
| **Custos** | Baixo | Alto (gas) | Baixo (weight) |
| **Análise Formal** | Limitada | Difícil | Projetado para isso |
| **Ataques conhecidos** | Poucos | Muitos (reentrancy, etc.) | Poucos |

## 1.3 Por que Liquid Network?

A **Liquid Network** é uma sidechain federada do Bitcoin que:
- ✅ Suporta **Simplicity** (ativado em Outubro 2024)
- ✅ Transações com **1-2 minutos** de confirmação
- ✅ **Confidential Transactions** nativas
- ✅ Suporte a **ativos digitais** (Issued Assets)
- ✅ **Testnet** disponível para desenvolvimento

---

# 2. Caso de Uso

## 2.1 Problema

Organizações precisam emitir certificados digitais que sejam:
- **Verificáveis** por qualquer pessoa
- **Imutáveis** após emissão
- **Revogáveis** quando necessário
- **Rastreáveis** em sua origem

Soluções tradicionais:
- ❌ **PDFs assinados**: Fáceis de falsificar, difíceis de revogar
- ❌ **Bancos de dados centralizados**: Ponto único de falha
- ❌ **Blockchain genérica**: Custos altos, complexidade

## 2.2 Solução

Um sistema onde:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   AUTORIDADE (Admin)                                                         │
│   ═══════════════════                                                        │
│   • Entidade raiz com controle total                                         │
│   • Pode delegar poderes a emissores                                         │
│   • Pode revogar qualquer certificado                                        │
│   • Pode cancelar delegações                                                 │
│                                                                              │
│                          │ delega                                            │
│                          ▼                                                   │
│                                                                              │
│   EMISSOR (Delegate)                                                         │
│   ═══════════════════                                                        │
│   • Autorizado pela Autoridade                                               │
│   • Pode emitir certificados                                                 │
│   • Pode revogar certificados que emitiu                                     │
│   • Não pode acessar fundos diretamente                                      │
│                                                                              │
│                          │ emite                                             │
│                          ▼                                                   │
│                                                                              │
│   CERTIFICADO                                                                │
│   ═══════════════                                                            │
│   • Representado por um UTXO na blockchain                                   │
│   • Dados armazenados no IPFS (referenciado via CID)                        │
│   • Verificável: UTXO existe = válido                                        │
│   • Revogável: UTXO gasto = inválido                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2.3 Exemplos de Aplicação

### 📚 Diplomas e Certificados Acadêmicos
```
Universidade (Admin) → Departamento (Delegate) → Diploma (Certificado)
```
- Universidade controla quais departamentos podem emitir
- Departamento emite diploma com dados do aluno
- Empregadores verificam on-chain
- Universidade pode revogar em caso de fraude

### 🏥 Certificações Profissionais
```
Conselho Profissional (Admin) → Regional (Delegate) → CRM/CRP/OAB (Certificado)
```
- Conselho nacional delega a regionais
- Regionais emitem registros profissionais
- Público pode verificar situação do profissional
- Cassação é revogação on-chain

### 🔐 Certificados de Conformidade
```
Órgão Certificador (Admin) → Auditor Autorizado (Delegate) → Selo ISO (Certificado)
```
- Órgão autoriza auditores
- Auditores emitem certificações
- Clientes verificam validade
- Certificações expiradas são revogadas

### 🏗️ Licenças e Alvarás
```
Prefeitura (Admin) → Secretaria (Delegate) → Alvará (Certificado)
```
- Prefeitura delega a secretarias específicas
- Secretarias emitem alvarás
- Fiscais verificam on-chain
- Cassação registrada permanentemente

---

# 3. Fundamentos Técnicos

## 3.1 Simplicity

**Simplicity** é uma linguagem de smart contracts criada pela Blockstream com foco em:

### Modelo Computacional
- Baseada em **combinadores funcionais**
- Sem loops (garantia de terminação)
- Tipagem estática forte
- Semântica formal definida

### Estrutura de um Programa
```
                    ┌─────────────────┐
                    │    SIMPLICITY   │
                    │     PROGRAM     │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │   Jets   │   │ Witness  │   │Environment│
        │(builtins)│   │  (input) │   │(tx data)  │
        └──────────┘   └──────────┘   └──────────┘
```

### Jets (Operações Otimizadas)
Jets são operações primitivas implementadas nativamente para eficiência:

| Categoria | Exemplos |
|-----------|----------|
| **Aritméticos** | `add_32`, `multiply_64`, `eq_256` |
| **Criptográficos** | `sha_256`, `bip_0340_verify` |
| **Transação** | `num_outputs`, `output_script_hash` |
| **Assinaturas** | `sig_all_hash`, `checksig` |

## 3.2 SimplicityHL (Linguagem de Alto Nível)

SimplicityHL é uma linguagem com sintaxe similar ao Rust que compila para Simplicity.

### Exemplo: Pay-to-Public-Key
```rust
fn main() {
    // Verificar assinatura com a chave pública esperada
    let pk: Pubkey = 0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798;
    let msg: u256 = jet::sig_all_hash();
    jet::bip_0340_verify((pk, msg), witness::SIG);
}
```

### Tipos Principais
```rust
// Tipos básicos
u1, u2, u4, u8, u16, u32, u64, u128, u256  // Inteiros sem sinal
bool                                         // Booleano

// Tipos compostos
(A, B)           // Produto (tupla)
Either<A, B>     // Soma (união discriminada)
Option<A>        // Opcional (Some/None)
[A; N]           // Array de tamanho fixo

// Aliases úteis
Pubkey = u256    // Chave pública x-only
Signature = [u8; 64]  // Assinatura Schnorr
```

## 3.3 Covenants

**Covenants** são restrições sobre como um UTXO pode ser gasto.

### Covenant Self-Referencial
```rust
// Força o output a ir para o mesmo contrato
let self_hash: u256 = jet::current_script_hash();
let output_hash: Option<u256> = jet::output_script_hash(0);
match output_hash {
    Some(hash: u256) => assert!(jet::eq_256(self_hash, hash)),
    None => panic!(),
};
```

### Covenant de Destino Específico
```rust
// Força o output a ir para um contrato específico
let expected_hash: u256 = 0x<HASH_DO_SCRIPT_DESTINO>;
let output_hash: Option<u256> = jet::output_script_hash(1);
match output_hash {
    Some(hash: u256) => assert!(jet::eq_256(expected_hash, hash)),
    None => panic!(),
};
```

## 3.4 CMR (Commitment Merkle Root)

O **CMR** é o identificador único de um programa Simplicity:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COMMITMENT MERKLE ROOT                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Programa Simplicity                                                        │
│          │                                                                   │
│          ▼                                                                   │
│   ┌─────────────────────┐                                                    │
│   │  Merkle Tree dos    │                                                    │
│   │  combinadores       │                                                    │
│   └──────────┬──────────┘                                                    │
│              │                                                               │
│              ▼                                                               │
│   ┌─────────────────────┐                                                    │
│   │   CMR (32 bytes)    │  ← Identifica o script                            │
│   │   0x7a3b...         │                                                    │
│   └─────────────────────┘                                                    │
│              │                                                               │
│              ▼                                                               │
│   ┌─────────────────────┐                                                    │
│   │  Taproot Tweak      │                                                    │
│   └──────────┬──────────┘                                                    │
│              │                                                               │
│              ▼                                                               │
│   ┌─────────────────────┐                                                    │
│   │ Endereço P2TR       │  ← tex1p83fxktk2usvxqslht92nna4tcfaw27pvy...      │
│   └─────────────────────┘                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Propriedades do CMR:**
- Determinístico: Mesmo código → Mesmo CMR
- Sem colisões: Códigos diferentes → CMRs diferentes
- Inclui apenas a estrutura, não os dados do witness

---

# 4. Arquitetura do Sistema

## 4.1 Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ARQUITETURA DO SISTEMA                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                          CAMADA ON-CHAIN                               │ │
│  │                        (Liquid Network)                                │ │
│  │                                                                        │ │
│  │   ┌─────────────────┐         ┌─────────────────┐                     │ │
│  │   │                 │ output  │                 │                     │ │
│  │   │   DELEGATION    │────────▶│   CERTIFICATE   │                     │ │
│  │   │     VAULT       │         │     (UTXO)      │                     │ │
│  │   │                 │         │                 │                     │ │
│  │   │ • Admin spend   │         │ • Admin revoke  │                     │ │
│  │   │ • Delegate emit │         │ • Delegate rev. │                     │ │
│  │   │                 │         │                 │                     │ │
│  │   └─────────────────┘         └─────────────────┘                     │ │
│  │            │                                                           │ │
│  │            │ OP_RETURN                                                │ │
│  │            ▼                                                           │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐ │ │
│  │   │                    CID do IPFS (46 bytes)                        │ │ │
│  │   │           QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG           │ │ │
│  │   └─────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      │ referencia                            │
│                                      ▼                                       │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         CAMADA OFF-CHAIN                               │ │
│  │                             (IPFS)                                     │ │
│  │                                                                        │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐ │ │
│  │   │                    DADOS DO CERTIFICADO                          │ │ │
│  │   │                                                                  │ │ │
│  │   │   {                                                              │ │ │
│  │   │     "version": "1.0",                                            │ │ │
│  │   │     "type": "academic_diploma",                                  │ │ │
│  │   │     "holder": {                                                  │ │ │
│  │   │       "name": "João da Silva",                                   │ │ │
│  │   │       "document": "123.456.789-00"                              │ │ │
│  │   │     },                                                           │ │ │
│  │   │     "credential": {                                              │ │ │
│  │   │       "title": "Bacharel em Ciência da Computação",             │ │ │
│  │   │       "institution": "Universidade Federal XYZ",                │ │ │
│  │   │       "date": "2025-12-15"                                      │ │ │
│  │   │     },                                                           │ │ │
│  │   │     "metadata": {                                                │ │ │
│  │   │       "issuer_pubkey": "0x9bef8d556d80e43ae7e0becb...",        │ │ │
│  │   │       "issued_at": "2026-01-05T18:00:00Z",                      │ │ │
│  │   │       "tx_id": "abc123..."                                      │ │ │
│  │   │     }                                                            │ │ │
│  │   │   }                                                              │ │ │
│  │   │                                                                  │ │ │
│  │   └─────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 4.2 Componentes

### Delegation Vault (`delegation_vault.simf`)

**Propósito:** Gerenciar a autoridade de emissão de certificados.

**Funcionalidades:**
- Admin pode gastar livremente (controle total)
- Delegate pode emitir certificados (poder limitado)

**Restrições do Delegate:**
- Deve criar exatamente 4 outputs
- Output 0: Deve voltar para o próprio vault
- Output 1: Deve ir para o contrato de certificado
- Output 2: Deve conter OP_RETURN com dados
- Output 3: Deve ser fee

### Certificate (`certificate.simf`)

**Propósito:** Representar um certificado válido.

**Funcionalidades:**
- Admin pode revogar (queimar para fee)
- Delegate pode revogar (queimar para fee)

**Verificação de Validade:**
- UTXO existe → Certificado válido
- UTXO gasto para fee → Certificado revogado

## 4.3 Modelo de Permissões

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MATRIZ DE PERMISSÕES                                 │
├──────────────────────────┬──────────────────┬──────────────────┬────────────┤
│          AÇÃO            │      ADMIN       │     DELEGATE     │  TERCEIROS │
├──────────────────────────┼──────────────────┼──────────────────┼────────────┤
│ Gastar vault livremente  │        ✅        │        ❌        │     ❌     │
│ Emitir certificado       │        ✅*       │        ✅        │     ❌     │
│ Revogar certificado      │        ✅        │        ✅        │     ❌     │
│ Cancelar delegação       │        ✅        │        ❌        │     ❌     │
│ Verificar certificado    │        ✅        │        ✅        │     ✅     │
│ Ler dados do IPFS        │        ✅        │        ✅        │     ✅     │
├──────────────────────────┴──────────────────┴──────────────────┴────────────┤
│ * Admin pode emitir usando o caminho do Delegate                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. Contratos Simplicity

## 5.1 Certificate (`v2/certificate.simf`)

```rust
// ═══════════════════════════════════════════════════════════════════════════
// CERTIFICATE - Certificado Revogável
// ═══════════════════════════════════════════════════════════════════════════

fn checksig(pk: Pubkey, sig: Signature) {
    let msg: u256 = jet::sig_all_hash();
    jet::bip_0340_verify((pk, msg), sig);
}

fn verify_single_fee_output() {
    // Deve haver exatamente 1 output (fee = burn)
    let num_outs: u32 = jet::num_outputs();
    assert!(jet::eq_32(num_outs, 1));
    
    let maybe_fee: Option<bool> = jet::output_is_fee(0);
    match maybe_fee {
        Some(is_fee: bool) => assert!(is_fee),
        None => panic!(),
    };
}

fn admin_revoke(admin_sig: Signature) {
    verify_single_fee_output();
    let admin_pk: Pubkey = 0x9bef8d556d80e43ae7e0becb3a7e6838b95defe45896ed6075bb9035d06c9964;
    checksig(admin_pk, admin_sig);
}

fn delegate_revoke(delegate_sig: Signature) {
    verify_single_fee_output();
    let delegate_pk: Pubkey = 0xe37d58a1aae4ba059fd2503712d998470d3a2522f7e2335f544ef384d2199e02;
    checksig(delegate_pk, delegate_sig);
}

fn main() {
    match witness::ADMIN_OR_DELEGATE {
        Left(admin_sig: Signature) => admin_revoke(admin_sig),
        Right(delegate_sig: Signature) => delegate_revoke(delegate_sig),
    }
}
```

### Explicação Linha por Linha

| Linha | Código | Explicação |
|-------|--------|------------|
| 5-8 | `fn checksig(...)` | Função auxiliar para verificar assinatura Schnorr |
| 6 | `jet::sig_all_hash()` | Obtém o hash da transação para assinatura |
| 7 | `jet::bip_0340_verify(...)` | Verifica assinatura BIP-340 (Schnorr) |
| 10-18 | `fn verify_single_fee_output()` | Valida que há exatamente 1 output de fee |
| 12 | `jet::num_outputs()` | Obtém número de outputs da transação |
| 15 | `jet::output_is_fee(0)` | Verifica se output 0 é fee |
| 20-24 | `fn admin_revoke(...)` | Caminho de revogação pelo Admin |
| 26-30 | `fn delegate_revoke(...)` | Caminho de revogação pelo Delegate |
| 32-37 | `fn main()` | Ponto de entrada - match no witness |

## 5.2 Delegation Vault (`v2/delegation_vault.simf`)

```rust
// ═══════════════════════════════════════════════════════════════════════════
// DELEGATION VAULT - Vault de Delegação
// ═══════════════════════════════════════════════════════════════════════════

fn checksig(pk: Pubkey, sig: Signature) {
    let msg: u256 = jet::sig_all_hash();
    jet::bip_0340_verify((pk, msg), sig);
}

// ADMIN: Pode gastar para qualquer destino
fn admin_spend(admin_sig: Signature) {
    let admin_pk: Pubkey = 0x9bef8d556d80e43ae7e0becb3a7e6838b95defe45896ed6075bb9035d06c9964;
    checksig(admin_pk, admin_sig);
}

// DELEGATE: Pode emitir certificado (4 outputs obrigatórios)
fn delegate_issue_certificate(delegate_sig: Signature) {
    // 1. Exatamente 4 outputs
    let num_outs: u32 = jet::num_outputs();
    assert!(jet::eq_32(num_outs, 4));

    // 2. Output 0 = próprio vault (self)
    let self_hash: u256 = jet::current_script_hash();
    let maybe_output0: Option<u256> = jet::output_script_hash(0);
    match maybe_output0 {
        Some(out_hash: u256) => assert!(jet::eq_256(self_hash, out_hash)),
        None => panic!(),
    };

    // 3. Output 1 = contrato de certificado
    let cert_script_hash: u256 = 0x0000000000000000000000000000000000000000000000000000000000000000; // TODO
    let maybe_output1: Option<u256> = jet::output_script_hash(1);
    match maybe_output1 {
        Some(cert_hash: u256) => assert!(jet::eq_256(cert_script_hash, cert_hash)),
        None => panic!(),
    };

    // 4. Output 2 = OP_RETURN com dados (CID IPFS)
    let output_idx: u32 = 2;
    let datum_idx: u32 = 0;
    let maybe_datum: Option<Option<Either<(u2, u256), Either<u1, u4>>>> = 
        jet::output_null_datum(output_idx, datum_idx);
    match maybe_datum {
        Some(inner_opt: Option<Either<(u2, u256), Either<u1, u4>>>) => {
            match inner_opt {
                Some(datum: Either<(u2, u256), Either<u1, u4>>) => { /* OK */ },
                None => panic!(),
            };
        },
        None => panic!(),
    };

    // 5. Output 3 = fee
    let maybe_fee: Option<bool> = jet::output_is_fee(3);
    match maybe_fee {
        Some(is_fee: bool) => assert!(is_fee),
        None => panic!(),
    };

    // 6. Verificar assinatura do Delegate
    let delegate_pk: Pubkey = 0xe37d58a1aae4ba059fd2503712d998470d3a2522f7e2335f544ef384d2199e02;
    checksig(delegate_pk, delegate_sig);
}

fn main() {
    match witness::ADMIN_OR_DELEGATE {
        Left(admin_sig: Signature) => admin_spend(admin_sig),
        Right(delegate_sig: Signature) => delegate_issue_certificate(delegate_sig),
    }
}
```

### Diagrama de Validação

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    VALIDAÇÃO DO DELEGATE_ISSUE_CERTIFICATE                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         TRANSAÇÃO                                    │   │
│   ├─────────────────────────────────────────────────────────────────────┤   │
│   │                                                                      │   │
│   │   INPUT: UTXO do Vault                                               │   │
│   │   WITNESS: Right(assinatura_delegate)                                │   │
│   │                                                                      │   │
│   ├─────────────────────────────────────────────────────────────────────┤   │
│   │                                                                      │   │
│   │   OUTPUT 0: Vault (self)                                             │   │
│   │   ┌─────────────────────────────────────────────────────────────┐   │   │
│   │   │  Validação: jet::current_script_hash() == output_script_hash│   │   │
│   │   │  Propósito: Preservar a capacidade de emitir mais certs     │   │   │
│   │   └─────────────────────────────────────────────────────────────┘   │   │
│   │                                                                      │   │
│   │   OUTPUT 1: Certificate                                              │   │
│   │   ┌─────────────────────────────────────────────────────────────┐   │   │
│   │   │  Validação: cert_script_hash == output_script_hash(1)       │   │   │
│   │   │  Propósito: Criar UTXO revogável que representa o cert      │   │   │
│   │   └─────────────────────────────────────────────────────────────┘   │   │
│   │                                                                      │   │
│   │   OUTPUT 2: OP_RETURN [CID]                                          │   │
│   │   ┌─────────────────────────────────────────────────────────────┐   │   │
│   │   │  Validação: output_null_datum(2, 0) retorna Some(Some(_))   │   │   │
│   │   │  Propósito: Armazenar referência aos dados no IPFS          │   │   │
│   │   └─────────────────────────────────────────────────────────────┘   │   │
│   │                                                                      │   │
│   │   OUTPUT 3: Fee                                                      │   │
│   │   ┌─────────────────────────────────────────────────────────────┐   │   │
│   │   │  Validação: output_is_fee(3) == true                        │   │   │
│   │   │  Propósito: Pagar taxa de rede                              │   │   │
│   │   └─────────────────────────────────────────────────────────────┘   │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 6. Fluxos Operacionais

## 6.1 Setup Inicial

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SETUP INICIAL                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   PASSO 1: Compilar Certificado                                              │
│   ════════════════════════════════                                           │
│                                                                              │
│   $ simply build --entrypoint v2/certificate.simf                            │
│                                                                              │
│   → Gera: target/certificate.json                                            │
│   → Extrair: CMR do certificado                                              │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 2: Atualizar Vault                                                   │
│   ════════════════════════════                                               │
│                                                                              │
│   Editar v2/delegation_vault.simf:                                           │
│                                                                              │
│   let cert_script_hash: u256 = 0x<CMR_DO_CERTIFICADO>;                       │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 3: Compilar Vault                                                    │
│   ═══════════════════════════                                                │
│                                                                              │
│   $ simply build --entrypoint v2/delegation_vault.simf                       │
│                                                                              │
│   → Gera: target/delegation_vault.json                                       │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 4: Obter Endereço do Vault                                           │
│   ═══════════════════════════════════                                        │
│                                                                              │
│   $ simply deposit --entrypoint v2/delegation_vault.simf                     │
│                                                                              │
│   → P2TR address: tex1p83fxktk2usvxqslht92nna4tcfaw27pvy...                  │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 5: Depositar Fundos (Admin)                                          │
│   ═══════════════════════════════════                                        │
│                                                                              │
│   Enviar L-BTC para o endereço P2TR do vault                                 │
│                                                                              │
│   → Vault ativo! Delegate pode emitir certificados.                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 6.2 Emissão de Certificado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EMISSÃO DE CERTIFICADO                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   PASSO 1: Preparar Dados                                                    │
│   ═══════════════════════════                                                │
│                                                                              │
│   Criar JSON com dados do certificado:                                       │
│                                                                              │
│   {                                                                          │
│     "version": "1.0",                                                        │
│     "holder": { "name": "João Silva", "id": "123.456.789-00" },             │
│     "credential": { "title": "Certificado XYZ", "date": "2026-01-05" },     │
│     "issuer": { "name": "Empresa ABC", "pubkey": "0x9bef..." }              │
│   }                                                                          │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 2: Upload para IPFS                                                  │
│   ═════════════════════════════                                              │
│                                                                              │
│   $ ipfs add certificate_data.json                                           │
│   added QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG                       │
│                                                                              │
│   → CID: QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG                      │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 3: Criar Arquivo Witness                                             │
│   ═══════════════════════════════════                                        │
│                                                                              │
│   {                                                                          │
│     "ADMIN_OR_DELEGATE": {                                                   │
│       "value": "Right(0x<ASSINATURA_DELEGATE>)",                             │
│       "type": "Either<Signature, Signature>"                                 │
│     }                                                                        │
│   }                                                                          │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 4: Construir e Broadcast Transação                                   │
│   ══════════════════════════════════════════════                             │
│                                                                              │
│   Criar transação com:                                                       │
│   • INPUT: UTXO do vault                                                     │
│   • OUTPUT 0: Vault (mesmo endereço)                                         │
│   • OUTPUT 1: Certificate (endereço do contrato certificate)                 │
│   • OUTPUT 2: OP_RETURN <CID>                                                │
│   • OUTPUT 3: Fee                                                            │
│                                                                              │
│   → TXID: abc123...def456                                                    │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 5: Registrar Referência                                              │
│   ═══════════════════════════════════                                        │
│                                                                              │
│   Guardar para verificação:                                                  │
│   • TXID da emissão                                                          │
│   • CID do IPFS                                                              │
│   • Índice do output do certificado (1)                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 6.3 Verificação de Certificado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VERIFICAÇÃO DE CERTIFICADO                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ENTRADA: TXID da emissão                                                   │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 1: Buscar Transação                                                  │
│   ═════════════════════════════                                              │
│                                                                              │
│   $ curl "https://blockstream.info/liquid/testnet/api/tx/{TXID}"            │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 2: Verificar Status do UTXO                                          │
│   ═════════════════════════════════════                                      │
│                                                                              │
│   $ curl "https://blockstream.info/liquid/testnet/api/tx/{TXID}/outspend/1" │
│                                                                              │
│   Resposta:                                                                  │
│   • { "spent": false } → Certificado VÁLIDO ✅                               │
│   • { "spent": true, ... } → Verificar destino                               │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 3: Se Gasto, Verificar Destino                                       │
│   ═══════════════════════════════════════                                    │
│                                                                              │
│   Se spent == true:                                                          │
│   • Verificar se foi para fee → REVOGADO 🔥                                  │
│   • Outro destino → ???                                                      │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 4: Obter Dados do Certificado                                        │
│   ═══════════════════════════════════════                                    │
│                                                                              │
│   Ler OP_RETURN (output 2) da transação de emissão:                         │
│   → CID: QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG                      │
│                                                                              │
│   $ ipfs cat QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG                  │
│   → Dados JSON do certificado                                                │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   RESULTADO FINAL                                                            │
│   ═════════════════                                                          │
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────┐     │
│   │  Status: VÁLIDO ✅                                                 │     │
│   │  Titular: João da Silva                                            │     │
│   │  Documento: 123.456.789-00                                         │     │
│   │  Credencial: Certificado XYZ                                       │     │
│   │  Data de Emissão: 2026-01-05                                       │     │
│   │  Emissor: Empresa ABC                                              │     │
│   │  TX de Emissão: abc123...def456                                    │     │
│   └───────────────────────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 6.4 Revogação de Certificado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        REVOGAÇÃO DE CERTIFICADO                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   PRÉ-REQUISITOS:                                                            │
│   • TXID do certificado a revogar                                            │
│   • Chave privada do Admin OU Delegate                                       │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 1: Obter SIGHASH                                                     │
│   ════════════════════════                                                   │
│                                                                              │
│   Construir transação de revogação:                                          │
│   • INPUT: UTXO do certificado  (TXID:1)                                     │
│   • OUTPUT 0: Fee (todo valor vai para mineradores)                          │
│                                                                              │
│   Calcular sighash da transação.                                             │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 2: Assinar                                                           │
│   ═════════════════                                                          │
│                                                                              │
│   $ simply sign --message <SIGHASH> --secret <PRIVATE_KEY>                   │
│                                                                              │
│   → Signature: 0xabc123...                                                   │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 3: Criar Witness                                                     │
│   ══════════════════════════                                                 │
│                                                                              │
│   // Para Admin revogar:                                                     │
│   { "ADMIN_OR_DELEGATE": { "value": "Left(0x<SIG>)", ... } }                 │
│                                                                              │
│   // Para Delegate revogar:                                                  │
│   { "ADMIN_OR_DELEGATE": { "value": "Right(0x<SIG>)", ... } }                │
│                                                                              │
│   ─────────────────────────────────────────────────────────────────────────  │
│                                                                              │
│   PASSO 4: Broadcast                                                         │
│   ═════════════════════                                                      │
│                                                                              │
│   $ simply withdraw \                                                        │
│       --entrypoint v2/certificate.simf \                                     │
│       --witness revoke.wit \                                                 │
│       --txid <CERT_TXID> \                                                   │
│       --destination ""  # Fee burn                                           │
│                                                                              │
│   → Certificado REVOGADO! 🔥                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 7. Armazenamento de Dados (IPFS)

## 7.1 Por que IPFS?

| Característica | IPFS | Blockchain | Banco de Dados |
|----------------|------|------------|----------------|
| **Custo** | Grátis* | Caro | Depende |
| **Imutabilidade** | Por hash | Total | Não |
| **Disponibilidade** | Distribuída | Alta | Centralizada |
| **Tamanho** | Ilimitado | ~80 bytes | Ilimitado |
| **Privacidade** | Opcional | Pública | Controlada |

*Requer pinning para garantir disponibilidade

## 7.2 Estrutura de Dados Recomendada

```json
{
  "version": "1.0",
  "schema": "certificate/v1",
  
  "holder": {
    "name": "Nome Completo do Titular",
    "document": {
      "type": "CPF",
      "value": "123.456.789-00"
    },
    "additional": {}
  },
  
  "credential": {
    "type": "diploma|certificate|license|permit",
    "title": "Título da Credencial",
    "description": "Descrição detalhada",
    "date": {
      "issued": "2026-01-05",
      "expires": null
    }
  },
  
  "issuer": {
    "name": "Nome da Entidade Emissora",
    "identifier": "CNPJ ou ID",
    "pubkey": "0x9bef8d556d80e43ae7e0becb3a7e6838b95defe45896ed6075bb9035d06c9964"
  },
  
  "metadata": {
    "tx_id": "TXID da transação de emissão",
    "block_height": 123456,
    "timestamp": "2026-01-05T18:00:00Z"
  },
  
  "attachments": [
    {
      "name": "documento.pdf",
      "cid": "QmXyz...",
      "hash": "sha256:abc123..."
    }
  ],
  
  "signature": {
    "algorithm": "BIP-340",
    "pubkey": "0x9bef8d...",
    "value": "0xabc123...",
    "message_hash": "0xdef456..."
  }
}
```

## 7.3 Fluxo de Armazenamento

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FLUXO DE ARMAZENAMENTO                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                 │
│   │   Dados     │      │    IPFS     │      │  Blockchain │                 │
│   │   JSON      │─────▶│   Storage   │─────▶│  OP_RETURN  │                 │
│   │             │ add  │   + pin     │ CID  │             │                 │
│   └─────────────┘      └─────────────┘      └─────────────┘                 │
│                                                                              │
│   O QUE FICA NO IPFS:                                                        │
│   • Todo o conteúdo do certificado                                           │
│   • Documentos anexos                                                        │
│   • Histórico de alterações (se aplicável)                                   │
│                                                                              │
│   O QUE FICA NA BLOCKCHAIN:                                                  │
│   • CID do IPFS (46 bytes para CIDv0)                                        │
│   • UTXO representando validade                                              │
│   • Histórico de transações                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

# 8. Guia de Implementação

## 8.1 Requisitos

### Software
```bash
# Rust (para compilar simply)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Simply CLI
cargo install --git https://github.com/starkware-bitcoin/simply simply

# IPFS (opcional, para armazenamento de dados)
# macOS
brew install ipfs
# Linux
snap install ipfs
```

### Chaves
```bash
# Gerar par de chaves para Admin
simply sign --message 00

# Output:
# Signature: 0x...
# Message: 00
# Public key: 0x9bef8d556d80e43ae7e0becb3a7e6838b95defe45896ed6075bb9035d06c9964
# Private key: 0x<GUARDAR_EM_SEGREDO>

# Gerar par de chaves para Delegate
simply sign --message 00
# ... similar
```

## 8.2 Configuração

### 1. Atualizar Chaves nos Contratos

Editar `v2/certificate.simf`:
```rust
// Substituir pelas chaves reais
let admin_pk: Pubkey = 0x<SUA_CHAVE_ADMIN>;
let delegate_pk: Pubkey = 0x<SUA_CHAVE_DELEGATE>;
```

Editar `v2/delegation_vault.simf`:
```rust
// Substituir pelas mesmas chaves
let admin_pk: Pubkey = 0x<SUA_CHAVE_ADMIN>;
let delegate_pk: Pubkey = 0x<SUA_CHAVE_DELEGATE>;
```

### 2. Compilar e Obter CMR

```bash
# Compilar certificado
simply build --entrypoint v2/certificate.simf

# Gerar endereço para obter info
simply deposit --entrypoint v2/certificate.simf
# P2TR address: tex1p...
```

### 3. Atualizar CMR no Vault

```rust
// Em delegation_vault.simf, substituir:
let cert_script_hash: u256 = 0x<CMR_REAL_DO_CERTIFICADO>;
```

### 4. Recompilar Vault

```bash
simply build --entrypoint v2/delegation_vault.simf
simply deposit --entrypoint v2/delegation_vault.simf
# P2TR address: tex1p... (endereço do vault)
```

## 8.3 Testnet

### Obter L-BTC de Teste
1. Acesse https://liquidtestnet.com/faucet
2. Cole o endereço P2TR do vault
3. Solicite fundos

### Verificar Saldo
```bash
# Via API Blockstream
curl "https://blockstream.info/liquid/testnet/api/address/{ENDEREÇO}/utxo"
```

---

# 9. Segurança

## 9.1 Modelo de Ameaças

| Ameaça | Mitigação |
|--------|-----------|
| **Roubo de chave do Admin** | Hardware wallet, multisig, backup seguro |
| **Roubo de chave do Delegate** | Rotação de chaves, limites de emissão |
| **Falsificação de certificado** | Verificação on-chain obrigatória |
| **Negação de serviço IPFS** | Múltiplos gateways, pinning services |
| **Replay attack** | Sighash único por transação |
| **Spam de certificados** | Custo de transação, limite de fundos no vault |

## 9.2 Boas Práticas

### Chaves
1. ✅ Use hardware wallet para chaves de produção
2. ✅ Faça backup em múltiplas localizações
3. ✅ Implemente rotação de chaves do Delegate periodicamente
4. ✅ Considere multisig para Admin

### Operações
1. ✅ Verifique transações antes de assinar
2. ✅ Mantenha logs de todas as emissões
3. ✅ Monitore o vault para gastos não autorizados
4. ✅ Tenha processo de revogação de emergência

### IPFS
1. ✅ Use serviços de pinning (Pinata, Infura, etc.)
2. ✅ Mantenha backup local dos dados
3. ✅ Considere criptografia para dados sensíveis

---

# 10. Referências

## Documentação Oficial

- [Simplicity Language](https://github.com/BlockstreamResearch/simplicity)
- [SimplicityHL Documentation](https://docs.simplicity-lang.org/simplicityhl-reference/)
- [Simply CLI](https://github.com/starkware-bitcoin/simply)
- [Liquid Network](https://liquid.net/)
- [IPFS Documentation](https://docs.ipfs.tech/)

## Papers

- [Simplicity: A New Language for Blockchains](https://blockstream.com/simplicity.pdf)
- [BIP-340: Schnorr Signatures](https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki)
- [BIP-341: Taproot](https://github.com/bitcoin/bips/blob/master/bip-0341.mediawiki)

## Recursos Adicionais

- [Liquid Testnet Faucet](https://liquidtestnet.com/faucet)
- [Liquid Testnet Explorer](https://blockstream.info/liquid/testnet/)
- [Pinata IPFS Pinning](https://www.pinata.cloud/)

---

# Apêndice A: Glossário

| Termo | Definição |
|-------|-----------|
| **CMR** | Commitment Merkle Root - hash único que identifica um programa Simplicity |
| **Covenant** | Restrição programática sobre como um UTXO pode ser gasto |
| **Delegate** | Entidade com poderes delegados pelo Admin |
| **Fee** | Taxa paga aos mineradores/validadores |
| **IPFS** | InterPlanetary File System - sistema de armazenamento distribuído |
| **Jet** | Operação otimizada nativa do Simplicity |
| **OP_RETURN** | Output de transação não gastável usado para armazenar dados |
| **P2TR** | Pay-to-Taproot - tipo de endereço Bitcoin/Liquid |
| **Simplicity** | Linguagem de smart contracts formal e verificável |
| **SimplicityHL** | Linguagem de alto nível que compila para Simplicity |
| **UTXO** | Unspent Transaction Output - "moeda" não gasta |
| **Vault** | Contrato que segura fundos com regras de gasto |
| **Witness** | Dados de entrada fornecidos em tempo de execução |

---

# Apêndice B: Comandos Rápidos

```bash
# ═══════════════════════════════════════════════════════════════════════════
# COMPILAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

# Compilar certificado
simply build --entrypoint v2/certificate.simf

# Compilar vault
simply build --entrypoint v2/delegation_vault.simf

# ═══════════════════════════════════════════════════════════════════════════
# ENDEREÇOS
# ═══════════════════════════════════════════════════════════════════════════

# Gerar endereço do certificado
simply deposit --entrypoint v2/certificate.simf

# Gerar endereço do vault
simply deposit --entrypoint v2/delegation_vault.simf

# ═══════════════════════════════════════════════════════════════════════════
# ASSINATURAS
# ═══════════════════════════════════════════════════════════════════════════

# Gerar nova chave
simply sign --message 00

# Assinar com chave existente
simply sign --message <SIGHASH_HEX> --secret <PRIVATE_KEY_HEX>

# ═══════════════════════════════════════════════════════════════════════════
# TRANSAÇÕES
# ═══════════════════════════════════════════════════════════════════════════

# Gastar de um contrato
simply withdraw \
    --entrypoint <ARQUIVO.simf> \
    --witness <ARQUIVO.wit> \
    --txid <TXID> \
    --destination <ENDERECO>

# Dry run (sem broadcast)
simply withdraw ... --dry-run

# ═══════════════════════════════════════════════════════════════════════════
# IPFS
# ═══════════════════════════════════════════════════════════════════════════

# Adicionar arquivo
ipfs add <ARQUIVO>

# Obter conteúdo
ipfs cat <CID>

# Pin para garantir disponibilidade
ipfs pin add <CID>
```

---

*Documentação criada em 2026-01-05*
*Versão 2.0*
