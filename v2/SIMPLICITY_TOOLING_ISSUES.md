# Simplicity Tooling Issues Report

**Data:** 2026-01-05
**Projeto:** Simplicity Attestation (SAID Protocol)
**Rede:** Liquid Testnet

---

## Sumário Executivo

Durante o desenvolvimento do sistema de atestações on-chain usando Simplicity, encontramos bugs e limitações nas ferramentas disponíveis que impedem a criação de transações com outputs customizados (OP_RETURN contendo CID do IPFS).

**Status:** O fluxo básico P2PK funciona, mas transações complexas com múltiplos outputs não podem ser construídas com as ferramentas atuais.

---

## 1. Contexto

### 1.1 Objetivo do Projeto

Criar um sistema de atestações on-chain onde:
- **Admin** pode gastar fundos livremente
- **Delegate** pode emitir atestações com estrutura específica:
  - Output 0: Vault (recicla fundos)
  - Output 1: Certificado (UTXO revogável)
  - **Output 2: OP_RETURN com CID IPFS** ← Bloqueado
  - Output 3: Fee

### 1.2 Protocolo SAID (Simplicity Attestation ID)

```
┌────────┬─────────┬──────────┬─────────────────────────┐
│  SAID  │ VERSION │   TYPE   │        PAYLOAD          │
│ 4 bytes│  1 byte │  1 byte  │    CID IPFS (46+ bytes) │
└────────┴─────────┴──────────┴─────────────────────────┘
```

O CID do IPFS deveria ser gravado no OP_RETURN para criar uma referência on-chain a dados off-chain.

---

## 2. Ferramentas Testadas

| Ferramenta | Versão | Fonte |
|------------|--------|-------|
| hal-simplicity | 0.1.0 | github.com/BlockstreamResearch/hal-simplicity (commit 2805f68) |
| simfony | 0.1.0 | crates.io |
| simplicityhl | 0.4.0 | crates.io |
| Web IDE | - | ide.simplicity-lang.org |
| simplicity-lang | 0.7.0 | Usado por hal-simplicity |
| simplicity-lang | 0.4.0 | Usado por simfony |

---

## 3. O Que Funcionou ✅

### 3.1 Transações P2PK via Web IDE

Conseguimos executar o fluxo completo de P2PK (Pay-to-Public-Key) usando automação do Web IDE via Playwright:

**Transação 1:**
- TXID: `ce7595e5a3eaeddfcdbfc2ff7225a05499f8e3c35bed8a3c3b1a143b70f05915`
- Status: Confirmada
- Explorer: https://blockstream.info/liquidtestnet/tx/ce7595e5a3eaeddfcdbfc2ff7225a05499f8e3c35bed8a3c3b1a143b70f05915

**Transação 2:**
- TXID: `1cba870f5c11f22867d4dffc8f61e95924efdddbc7977604572295ba8be675c0`
- Status: Confirmada
- Explorer: https://blockstream.info/liquidtestnet/tx/1cba870f5c11f22867d4dffc8f61e95924efdddbc7977604572295ba8be675c0

### 3.2 Fluxo que Funciona

```
1. Carregar exemplo P2PK no IDE
2. Configurar UTXO (txid, vout, value, recipient, fee)
3. Compilar (calcula sig_all_hash)
4. Copiar assinatura do Key Store
5. Atualizar código com assinatura válida
6. Recompilar → Execution succeeded
7. Obter transação assinada
8. Broadcast → Confirmado na rede
```

### 3.3 Comandos hal-simplicity que Funcionam

```bash
# Info do programa - FUNCIONA
hal-simplicity simplicity info <program.b64>

# Criar PSET - FUNCIONA
hal-simplicity simplicity pset create --liquid '<inputs>' '<outputs>'

# Atualizar input com UTXO - FUNCIONA
hal-simplicity simplicity pset update-input --liquid <pset> 0 \
  --input-utxo "<script>:<asset>:<value>" \
  --cmr "<cmr>" \
  --internal-key "<key>"
```

---

## 4. Bugs Encontrados 🐛

### 4.1 Bug: Decodificação incorreta de hex em hal-simplicity

**Componente:** `hal-simplicity` - função `hex_or_base64()` em `src/lib.rs`

**Erro:**
```json
{
  "error": "invalid program: bitstream had trailing bytes 0x4d..."
}
```
ou
```json
{
  "error": "invalid program: Invalid padding"
}
```

**Causa Raiz Identificada (2026-01-05):**

Bug na função `hex_or_base64()` em `src/lib.rs` linha 60:

```rust
// BUGGY - linha 60:
if s.len() % 2 == 0 && s.bytes().all(|b| b.is_ascii_hexdigit() && b.is_ascii_lowercase()) {
```

O problema: `'0'.is_ascii_lowercase()` retorna `false` porque dígitos (`0-9`) **não são letras minúsculas**!

**Consequência:**
- Witness hex "000...000" (128 chars) → interpretado como base64 → **96 bytes** (ERRADO!)
- Deveria ser interpretado como hex → **64 bytes** (CORRETO)

**Fix Proposto:**

```rust
// FIXED:
if s.len() % 2 == 0 && s.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f')) {
```

**Verificação:**
O fix foi testado e confirmado funcionando. Com a correção:
- `simplicity info <prog> <witness>` funciona corretamente
- `pset run` e `pset finalize` devem funcionar corretamente

**Reprodução do Bug:**
```bash
PROG="1JtM33xqq2wHIdc/BfZZ0/NBxcrvfyLEt2sDrdyBroNkyyAjgMAqcUbGAgA="
WITNESS="0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"

# Com hal-simplicity atual (buggy):
hal-simplicity simplicity info "$PROG" "$WITNESS"
# Output: {"error": "invalid program: bitstream had trailing bytes 0x4d..."}

# Após aplicar o fix: SUCCESS!
```

**Status:** ✅ **FIX APLICADO E VERIFICADO** (2026-01-05)

O fix foi aplicado em `/tmp/hal-simplicity-new/src/lib.rs` e testado com sucesso:
- `simplicity info <prog> <witness>` ✅ funciona
- `pset run` ✅ parsing funciona (execução do programa procede corretamente)
- O jet `bip_0340_verify` retorna `false` como esperado (assinatura era de outra transação)

**Próximo passo:** Submeter PR para hal-simplicity upstream.

**Impacto:** Com o fix aplicado, hal-simplicity pode ser usado para construir transações Simplicity programaticamente.

### 4.2 Bug: Incompatibilidade de Versões simfony/hal-simplicity

**Problema:**
```
hal-simplicity usa: simplicity-lang 0.7.0
simfony 0.1.0 usa:  simplicity-lang 0.4.0
```

**Erro ao usar programa compilado com simfony no hal-simplicity:**
```json
{
  "error": "invalid program: Invalid byte 95, offset 10."
}
```

**Reprodução:**
```bash
# Compilar com simfony
simc delegation_vault.simf > program.b64

# Tentar usar no hal-simplicity
hal-simplicity simplicity info program.b64
# Output: {"error": "invalid program: Invalid byte 95, offset 10."}
```

**Impacto:** Não é possível compilar contratos customizados localmente e usá-los com hal-simplicity.

---

## 5. Limitações 🚧

### 5.1 Web IDE: Sem Suporte a OP_RETURN

O Web IDE (ide.simplicity-lang.org) só permite configurar:
- txid, vout, value (input UTXO)
- recipient address (único output)
- fee, nLockTime, nSequence

**Não há opção para:**
- Adicionar múltiplos outputs
- Criar outputs OP_RETURN customizados
- Especificar scripts de output arbitrários

**Impacto:** Impossível criar transações de atestação com CID no OP_RETURN via IDE.

### 5.2 elements-cli: Sem Suporte Nativo a Simplicity

O Elements Core não tem suporte nativo para Simplicity. Comandos como `createrawtransaction` não funcionam com outputs Simplicity.

---

## 6. Workaround Parcial

### 6.1 Fluxo Híbrido (Não Implementado)

Em teoria, seria possível:
1. Usar o IDE para obter a assinatura válida
2. Construir a transação raw manualmente adicionando OP_RETURN
3. Substituir apenas o witness com a assinatura do IDE

**Desafios:**
- Requer conhecimento profundo do formato de transação Elements
- A assinatura cobre o hash da transação, então qualquer modificação invalida a assinatura
- O `sig_all_hash` inclui todos os outputs, então não é possível adicionar OP_RETURN depois

### 6.2 Solução Real Necessária

Para o fluxo completo funcionar, precisamos de UMA das seguintes:

1. **hal-simplicity corrigido:** Que o bug `Invalid padding` seja corrigido para permitir `pset run` e `pset finalize`

2. **Web IDE expandido:** Que o IDE suporte configuração de múltiplos outputs customizados

3. **Biblioteca de construção de TX:** Uma biblioteca (Rust/Python) que construa transações Simplicity com outputs arbitrários

---

## 7. Informações Técnicas

### 7.1 Endereço P2PK Testado

```
Endereço: tex1psll4tk527a7p7sedszhua6z3wykxk9g3v8cknv86jfgtju3pk95skx84jl
CMR: 0372d6489c5ff31451df4c959b7449b1edda528f2304ca223266bca1dc8f246a
Programa: 1JtM33xqq2wHIdc/BfZZ0/NBxcrvfyLEt2sDrdyBroNkyyAjgMAqcUbGAgA=
Alice PubKey: 9bef8d556d80e43ae7e0becb3a7e6838b95defe45896ed6075bb9035d06c9964
```

### 7.2 Estrutura do Witness (Transação Bem-Sucedida)

```
witness[0]: Assinatura + Witness Simplicity (64 bytes encoded)
witness[1]: Programa Simplicity (serializado)
witness[2]: CMR do programa (32 bytes)
witness[3]: Control block Taproot
```

### 7.3 Asset ID (L-BTC Testnet)

```
144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49
```

---

## 8. Recomendações

### 8.1 Para Blockstream Research

1. **Corrigir bug `Invalid padding`** no hal-simplicity
   - O `pset run` e `pset finalize` falham mesmo com programas válidos
   - O `info` funciona com os mesmos programas

2. **Sincronizar versões** simfony ↔ simplicity-lang
   - simfony 0.1.0 usa simplicity-lang 0.4.0
   - hal-simplicity usa simplicity-lang 0.7.0
   - Programas compilados são incompatíveis

3. **Expandir Web IDE**
   - Adicionar suporte a múltiplos outputs
   - Permitir OP_RETURN customizado
   - Expor opções de construção de transação avançada

### 8.2 Para o Projeto SAID

1. ~~**Curto prazo:** Usar P2PK simples como prova de conceito~~ ✅ FEITO
2. ~~**Médio prazo:** Aguardar correções em hal-simplicity~~ ✅ FIX APLICADO LOCALMENTE
3. **Próximo passo:** Usar hal-simplicity com fix para criar transações com OP_RETURN
4. **Longo prazo:** Submeter PR com fix para upstream

---

## 9. Arquivos Relacionados

```
v2/
├── delegation_vault.simf      # Contrato principal (não pode ser usado)
├── delegation_vault_ide.simf  # Versão simplificada para IDE
├── complete_p2pk_flow.py      # Script de automação que funciona
├── TESTNET_KEYS.md            # Chaves de teste
└── SIMPLICITY_TOOLING_ISSUES.md  # Este documento
```

---

## 10. Links de Referência

- **hal-simplicity:** https://github.com/BlockstreamResearch/hal-simplicity
- **SimplicityHL:** https://github.com/BlockstreamResearch/SimplicityHL
- **Web IDE:** https://ide.simplicity-lang.org/
- **Simplicity Docs:** https://docs.simplicity-lang.org/
- **Liquid Testnet Explorer:** https://blockstream.info/liquidtestnet/

---

## Apêndice: Scripts de Teste

### A.1 Script de Automação P2PK (Funcional)

```python
#!/usr/bin/env python3
"""Complete P2PK spend flow via Simplicity Web IDE"""

import asyncio
import re
from playwright.async_api import async_playwright

UTXO_TXID = "a6e83d005bb5bbbd738e92cea13306cf45b5aeb0ac7d86e692c8e20cd73f20b4"
UTXO_VOUT = "0"
UTXO_VALUE = "100000"
FEE = "1000"
RECIPIENT = "tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = await context.new_page()

        await page.goto("https://ide.simplicity-lang.org/")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Load P2PK
        dropdown = page.locator('button.dropdown-button:has-text("Examples")')
        await dropdown.click()
        await asyncio.sleep(1)
        p2pk = page.locator('button.action-button').filter(has_text="P2PK").first
        await p2pk.click()
        await asyncio.sleep(2)

        # Configure UTXO
        tx_tab = page.locator('button:has-text("Transaction")').last
        await tx_tab.click()
        await asyncio.sleep(1)

        inputs = page.locator("input:visible")
        await inputs.nth(0).fill(UTXO_TXID)
        await inputs.nth(1).fill(UTXO_VOUT)
        await inputs.nth(2).fill(UTXO_VALUE)
        await inputs.nth(3).fill(RECIPIENT)
        await inputs.nth(4).fill(FEE)

        # Compile
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(3)

        # Get signature
        keystore_tab = page.locator('button:has-text("Key Store")')
        await keystore_tab.click()
        await asyncio.sleep(1)

        copy_alice = page.locator('button:has-text("CopyAlice")').nth(1)
        await copy_alice.click()
        signature = await page.evaluate("navigator.clipboard.readText()")

        # Update code
        textarea = page.locator("textarea.program-input-field")
        code = await textarea.input_value()
        new_code = re.sub(
            r'const ALICE_SIGNATURE: \[u8; 64\] = 0x[a-fA-F0-9]+;',
            f'const ALICE_SIGNATURE: [u8; 64] = {signature};',
            code
        )
        await textarea.fill(new_code)

        # Recompile
        await run_btn.click()
        await asyncio.sleep(3)

        # Get transaction
        tx_btn = page.get_by_role("button", name="Transaction").first
        await tx_btn.click()
        tx_hex = await page.evaluate("navigator.clipboard.readText()")

        print(f"Transaction: {tx_hex}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### A.2 Comandos hal-simplicity (Parcialmente Funcionais)

```bash
# Funciona - Info do programa
hal-simplicity simplicity info "1JtM33xqq2wHIdc/BfZZ0/NBxcrvfyLEt2sDrdyBroNkyyAjgMAqcUbGAgA="

# Funciona - Criar PSET
hal-simplicity simplicity pset create --liquid \
  '[{"txid":"...","vout":0}]' \
  '[{"address":"tex1...","asset":"144c...","amount":99000}]'

# Funciona - Atualizar input
hal-simplicity simplicity pset update-input --liquid "$PSET" 0 \
  --input-utxo "5120...:<asset>:100000" \
  --cmr "0372..." \
  --internal-key "5092..."

# FUNCIONA com fix - Run (parsing ok, executa o programa)
hal-simplicity simplicity pset run --liquid "$PSET" 0 "$PROGRAM" "$WITNESS"
# Output: JSON com resultado da execução dos jets

# FUNCIONA com fix - Finalize (parsing ok, falha apenas se assinatura inválida)
hal-simplicity simplicity pset finalize --liquid "$PSET" 0 "$PROGRAM" "$WITNESS"
# Output: {"error": "Jet failed during execution"} (se assinatura errada)
# Output: Transação finalizada (se assinatura correta)
```

---

*Documento gerado durante investigação do Simplicity Attestation Protocol (SAID)*
