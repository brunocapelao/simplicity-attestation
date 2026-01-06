# Implementation Plan: Vault v2 with Enforced Covenants

**Date:** 2026-01-06
**Feature:** SAID Delegation Vault with Covenant-Enforced Outputs
**Status:** Ready for Implementation

---

## Goal

Implementar o sistema SAID completo com:
1. **Vault v2**: Covenant que ENFORCE troco volta para vault e certificate vai para script C
2. **Certificate Script**: Script simples para revogacao
3. **Scripts de Operacao**: Emissao, revogacao, desativacao

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SAID SYSTEM v2                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐        ┌─────────────────────┐                    │
│  │   Certificate (C)   │        │  Delegation Vault   │                    │
│  │   certificate.simf  │◄───────│     vault_v2.simf   │                    │
│  └─────────────────────┘        └─────────────────────┘                    │
│           │                              │                                  │
│           │                              │                                  │
│  CMR_C, CERT_ADDRESS            CMR_V, VAULT_ADDRESS                       │
│           │                              │                                  │
│           └──────────────┬───────────────┘                                  │
│                          │                                                  │
│                   Hardcoded no Vault:                                       │
│                   - CERT_SCRIPT_HASH                                        │
│                   - VAULT_SCRIPT_HASH (self-ref)                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- [x] hal-simplicity fork com OP_RETURN support
- [x] simc (Simfony compiler)
- [x] Python com embit
- [x] Chaves Admin/Delegate (secrets.json)

---

## Tasks

### Phase 1: Certificate Script (Dependency First)

#### Task 1.1: Create certificate.simf
**File:** `/v2/certificate.simf`
**Time:** 5 min

```rust
// Certificate Script - Admin ou Delegate podem revogar (gastar)
// Gastar este UTXO = revogar o certificado

mod witness {
    const SPENDING_PATH: Either<Signature, Signature> = Left(0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000);
}

fn checksig(pk: Pubkey, sig: Signature) {
    let msg: u256 = jet::sig_all_hash();
    jet::bip_0340_verify((pk, msg), sig);
}

fn main() {
    // Admin pubkey (Alice)
    let admin_pk: Pubkey = 0xbcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45;
    // Delegate pubkey (Bob)
    let delegate_pk: Pubkey = 0x8577f4e053850a2eb0c86ce4c81215fdec681c28e01648f4401e0c47a4276413;

    match witness::SPENDING_PATH {
        Left(admin_sig: Signature) => checksig(admin_pk, admin_sig),
        Right(delegate_sig: Signature) => checksig(delegate_pk, delegate_sig),
    }
}
```

**Verification:**
```bash
simc compile certificate.simf
# Expected: Compiles successfully, outputs CMR and program base64
```

#### Task 1.2: Get Certificate CMR and Address
**Time:** 3 min

```bash
# Compile
simc compile certificate.simf

# Get address
HAL=/tmp/hal-simplicity-new/target/release/hal-simplicity
INTERNAL_KEY="50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"
$HAL simplicity address --cmr <CMR_FROM_COMPILE> --internal-key $INTERNAL_KEY
```

**Output:** Save CMR_C and CERT_ADDRESS to secrets.json

---

### Phase 2: Vault v2 Script (With Covenants)

#### Task 2.1: Create vault_v2.simf
**File:** `/v2/vault_v2.simf`
**Time:** 15 min

**CRITICAL:** Este script precisa verificar:
1. Output 0 (troco) vai para VAULT_SCRIPT_HASH
2. Output 1 (certificate) vai para CERT_SCRIPT_HASH
3. Output 2 existe (OP_RETURN)

```rust
// Delegation Vault v2 - Com Covenants Enforced
// Admin: gasto incondicional (desativa delegado)
// Delegate: emite certificado com covenants verificados

mod witness {
    const SPENDING_PATH: Either<Signature, Signature> = Left(0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000);
}

fn checksig(pk: Pubkey, sig: Signature) {
    let msg: u256 = jet::sig_all_hash();
    jet::bip_0340_verify((pk, msg), sig);
}

fn admin_spend(admin_sig: Signature) {
    // Admin pode gastar incondicionalmente - DESATIVA delegado
    let admin_pk: Pubkey = 0xbcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45;
    checksig(admin_pk, admin_sig);
}

fn delegate_spend(delegate_sig: Signature) {
    // 1. Verificar assinatura do delegado
    let delegate_pk: Pubkey = 0x8577f4e053850a2eb0c86ce4c81215fdec681c28e01648f4401e0c47a4276413;
    checksig(delegate_pk, delegate_sig);

    // 2. COVENANT: Verificar que output 0 (troco) vai para o vault
    // NOTA: VAULT_SCRIPT_HASH sera calculado apos compilacao inicial
    // Por ora usamos placeholder - sera atualizado na Task 2.3
    let expected_vault_script: u256 = 0x_VAULT_SCRIPT_HASH_PLACEHOLDER_;
    let output0_script: u256 = jet::output_script_hash(0);
    assert!(output0_script == expected_vault_script);

    // 3. COVENANT: Verificar que output 1 (certificate) vai para certificate script
    let expected_cert_script: u256 = 0x_CERT_SCRIPT_HASH_PLACEHOLDER_;
    let output1_script: u256 = jet::output_script_hash(1);
    assert!(output1_script == expected_cert_script);

    // 4. Verificar que existe OP_RETURN em output 2
    let output_idx: u32 = 2;
    let datum_idx: u32 = 0;
    let maybe_datum: Option<Option<Either<(u2, u256), Either<u1, u4>>>> = jet::output_null_datum(output_idx, datum_idx);
    match maybe_datum {
        Some(inner: Option<Either<(u2, u256), Either<u1, u4>>>) => {
            match inner {
                Some(datum: Either<(u2, u256), Either<u1, u4>>) => {
                    // OP_RETURN existe - OK
                },
                None => panic!(),
            };
        },
        None => panic!(),
    };
}

fn main() {
    match witness::SPENDING_PATH {
        Left(admin_sig: Signature) => admin_spend(admin_sig),
        Right(delegate_sig: Signature) => delegate_spend(delegate_sig),
    }
}
```

#### Task 2.2: Investigate jet::output_script_hash availability
**Time:** 10 min

**CRITICAL RESEARCH:** Verificar se `jet::output_script_hash` existe em Simfony/Simplicity.

```bash
# Check Simfony documentation
simc --help
# Search in simfony repo for output_script_hash

# Alternative jets to investigate:
# - jet::output_script_sig_hash
# - jet::output_script_pubkey
# - jet::tap_leaf_hash
```

Se `output_script_hash` NAO existir, alternativas:
1. Usar `jet::output_amounts_hash` + verificacao de estrutura
2. Usar verificacao via sighash modes
3. Redesenhar usando disconnect combinator explicitamente

#### Task 2.3: Resolve Self-Reference (Vault Script Hash)
**Time:** 20 min

**O Problema:**
```
vault_v2.simf precisa do VAULT_SCRIPT_HASH
→ VAULT_SCRIPT_HASH depende do CMR
→ CMR depende do codigo
→ Codigo contem VAULT_SCRIPT_HASH (circular!)
```

**Solucao A: Two-Pass Compilation**
1. Compilar vault_v2.simf com placeholder
2. Calcular script_pubkey do vault
3. Calcular hash do script_pubkey
4. Atualizar vault_v2.simf com o hash correto
5. Recompilar - verificar se CMR permanece igual (NAO vai permanecer!)

**Solucao B: Parametrizacao via Witness**
```rust
mod witness {
    const VAULT_SCRIPT_HASH: u256 = 0x...;  // Fornecido no witness
    const SPENDING_PATH: Either<Signature, Signature>;
}
```
Problema: Delegado poderia fornecer hash falso.

**Solucao C: Verificacao Indireta**
Ao inves de verificar script_hash exato, verificar propriedades:
```rust
// Verificar que output 0 tem o mesmo asset e valor minimo
let output0_asset = jet::output_asset(0);
let input_asset = jet::current_input_asset();
assert!(output0_asset == input_asset);
// ... mais verificacoes
```

**Solucao D: Aceitar Limitacao**
Para MVP, aceitar que o troco pode ir para qualquer lugar, mas:
- Certificate output DEVE ir para CERT_ADDRESS (enforced)
- OP_RETURN DEVE existir (enforced)
- Isso ja e melhor que v1!

**Decision Point:** Implementar Solucao D para MVP, evoluir para C ou B depois.

#### Task 2.4: Final vault_v2.simf (MVP)
**File:** `/v2/vault_v2.simf`
**Time:** 10 min

Versao simplificada que enforce:
- Certificate output vai para CERT_ADDRESS
- OP_RETURN existe
- (Troco: incentivo economico por ora)

---

### Phase 3: Integration Scripts

#### Task 3.1: Setup Script
**File:** `/v2/scripts/setup_system.py`
**Time:** 15 min

```python
#!/usr/bin/env python3
"""
Setup do sistema SAID v2.
Compila scripts, gera enderecos, atualiza secrets.json
"""

import subprocess
import json

def compile_simfony(simf_file):
    """Compila arquivo .simf e retorna CMR e programa."""
    result = subprocess.run(
        ["simc", "compile", simf_file],
        capture_output=True, text=True
    )
    # Parse output...
    return cmr, program_base64

def get_address(cmr, internal_key):
    """Gera endereco P2TR a partir do CMR."""
    result = subprocess.run([
        HAL, "simplicity", "address",
        "--cmr", cmr,
        "--internal-key", internal_key
    ], capture_output=True, text=True)
    # Parse output...
    return address, script_pubkey

def main():
    # 1. Compilar Certificate script
    cert_cmr, cert_program = compile_simfony("certificate.simf")
    cert_address, cert_script_pubkey = get_address(cert_cmr, INTERNAL_KEY)

    # 2. Atualizar vault_v2.simf com CERT_SCRIPT_HASH
    # ...

    # 3. Compilar Vault script
    vault_cmr, vault_program = compile_simfony("vault_v2.simf")
    vault_address, vault_script_pubkey = get_address(vault_cmr, INTERNAL_KEY)

    # 4. Atualizar secrets.json
    # ...

    print(f"Certificate Address: {cert_address}")
    print(f"Vault Address: {vault_address}")
```

#### Task 3.2: Emit Certificate Script
**File:** `/v2/scripts/emit_certificate.py`
**Time:** 20 min

Script para delegado emitir certificado:
1. Cria PSET com outputs corretos
2. Assina com delegate key
3. Broadcast

#### Task 3.3: Revoke Certificate Script
**File:** `/v2/scripts/revoke_certificate.py`
**Time:** 15 min

Script para revogar certificado (Admin ou Delegate):
1. Gasta o Certificate UTXO
2. Opcionalmente inclui OP_RETURN REVOKE

---

### Phase 4: Testing

#### Task 4.1: Test Certificate Compilation
```bash
cd /Users/brunocapelao/Projects/satshack-3-main/v2
simc compile certificate.simf
```

#### Task 4.2: Test Vault Compilation
```bash
simc compile vault_v2.simf
```

#### Task 4.3: Test Certificate Spend (Revocation)
- Fund certificate address
- Spend with Admin key
- Verify UTXO is spent

#### Task 4.4: Test Vault Delegate Spend (Certificate Emission)
- Fund vault address
- Spend with Delegate key
- Verify outputs: troco, certificate, OP_RETURN

#### Task 4.5: Test Vault Admin Spend (Deactivation)
- Fund vault address
- Spend with Admin key
- Verify vault is empty

---

## Code Review Checkpoint

After Phase 2, run code review to verify:
1. Covenant logic is correct
2. Script_hash verification (if implemented)
3. No security vulnerabilities

---

## Key Decisions

### Decision 1: Self-Reference Approach
**Options:**
- A: Two-pass compilation (complex, may not converge)
- B: Witness parametrization (security concern)
- C: Property verification (partial enforcement)
- D: Certificate-only enforcement (MVP) ✅

**Chosen:** D for MVP - Enforce certificate destination, accept troco goes by incentive.

### Decision 2: jet::output_script_hash Availability
**Needs Investigation:** Verify jet exists in current Simfony/Simplicity.
If not available, use alternative verification methods.

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| output_script_hash jet not available | Use alternative jets or property verification |
| Self-reference not solvable | Accept partial enforcement for MVP |
| Compilation errors | Test each script incrementally |

---

## Success Criteria

1. [ ] certificate.simf compiles and generates valid address
2. [ ] vault_v2.simf compiles with covenant logic
3. [ ] Delegate can emit certificate with enforced outputs
4. [ ] Admin can revoke certificate
5. [ ] Admin can deactivate delegate
6. [ ] All operations verified on Liquid Testnet

---

## Next Steps After This Plan

1. Execute Phase 1 (Certificate script)
2. Investigate jet availability (Task 2.2)
3. Decide on self-reference approach
4. Complete vault_v2.simf
5. Test on Liquid Testnet
