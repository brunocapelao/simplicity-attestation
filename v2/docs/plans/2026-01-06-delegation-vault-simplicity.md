# Delegation Vault Simplicity Implementation Plan

> **For Agents:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task.

**Goal:** Implement a Simplicity vault contract where Admin (Alice) can spend unconditionally, while Delegate (Bob) can spend with conditions (timelock, OP_RETURN requirement).

**Architecture:** Single Simfony program with OR logic using `Either` type for witness. Admin path requires only signature verification. Delegate path requires signature + timelock verification + OP_RETURN data presence check. Both paths compiled into one program with unified CMR.

**Tech Stack:**
- Simfony (`.simf` files) compiled via `simc`
- `hal-simplicity` (corrected fork) for PSET operations
- Python with `embit` for Schnorr signing
- Liquid Testnet for testing

**Global Prerequisites:**
- Environment: macOS, Python 3.8+
- Tools: simc, hal-simplicity (corrected fork at `/tmp/hal-simplicity-new/target/release/hal-simplicity`)
- Access: Internet for Liquid Testnet faucet and API
- State: Working from `/Users/brunocapelao/Projects/satshack-3-main/v2/`

**Verification before starting:**
```bash
# Run ALL these commands and verify output:
/Users/brunocapelao/.cargo/bin/simc --version 2>&1 || echo "simc available (no --version flag)"
/tmp/hal-simplicity-new/target/release/hal-simplicity --version 2>&1 || echo "hal-simplicity available"
python3 -c "from embit import ec; print('embit OK')"
ls /Users/brunocapelao/Projects/satshack-3-main/v2/secrets.json  # Expected: file exists
```

---

## Phase 1: Simplified Delegation Vault Contract

### Task 1: Create the Simplified Delegation Vault Program

**Files:**
- Create: `/Users/brunocapelao/Projects/satshack-3-main/v2/delegation_vault_v1.simf`

**Prerequisites:**
- Tools: simc compiler
- Files must exist: `/Users/brunocapelao/Projects/satshack-3-main/v2/secrets.json`

**Step 1: Write the Simfony program**

Create the file `/Users/brunocapelao/Projects/satshack-3-main/v2/delegation_vault_v1.simf` with this content:

```rust
// ============================================================================
// DELEGATION VAULT v1 - Simplified
// ============================================================================
// Two spending paths:
// - LEFT: Admin (Alice) - unconditional spending
// - RIGHT: Delegate (Bob) - requires timelock + OP_RETURN
// ============================================================================

mod witness {
    // Either<AdminSig, DelegateSig>
    // Left = Admin signature
    // Right = Delegate signature
    const SPENDING_PATH: Either<Signature, Signature> = Left(0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000);
}

fn checksig(pk: Pubkey, sig: Signature) {
    let msg: u256 = jet::sig_all_hash();
    jet::bip_0340_verify((pk, msg), sig);
}

// ============================================================================
// ADMIN PATH - Unconditional Spending
// ============================================================================
fn admin_spend(admin_sig: Signature) {
    // Admin public key (Alice)
    let admin_pk: Pubkey = 0xbcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45;
    checksig(admin_pk, admin_sig);
}

// ============================================================================
// DELEGATE PATH - Conditional Spending
// ============================================================================
fn delegate_spend(delegate_sig: Signature) {
    // 1. Verify delegate signature
    let delegate_pk: Pubkey = 0x8577f4e053850a2eb0c86ce4c81215fdec681c28e01648f4401e0c47a4276413;
    checksig(delegate_pk, delegate_sig);

    // 2. Verify timelock - delegate can only spend after block 2256000
    // Current testnet height is ~2255256, so 2256000 is about 12 hours in the future
    let min_height: Height = 2256000;
    jet::check_lock_height(min_height);

    // 3. Verify OP_RETURN exists in output 1 (output 0 is recipient, output 1 is data)
    // We check that there's a null datum (OP_RETURN data) at output index 1
    let output_idx: u32 = 1;
    let datum_idx: u32 = 0;
    let maybe_datum: Option<Option<Either<(u2, u256), Either<u1, u4>>>> = jet::output_null_datum(output_idx, datum_idx);
    match maybe_datum {
        Some(inner: Option<Either<(u2, u256), Either<u1, u4>>>) => {
            match inner {
                Some(datum: Either<(u2, u256), Either<u1, u4>>) => {
                    // OP_RETURN data exists - OK
                },
                None => panic!(), // No data in OP_RETURN
            };
        },
        None => panic!(), // Output 1 doesn't exist or isn't OP_RETURN
    };
}

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================
fn main() {
    match witness::SPENDING_PATH {
        Left(admin_sig: Signature) => admin_spend(admin_sig),
        Right(delegate_sig: Signature) => delegate_spend(delegate_sig),
    }
}
```

**Step 2: Verify the file was created**

Run: `cat /Users/brunocapelao/Projects/satshack-3-main/v2/delegation_vault_v1.simf | head -20`

**Expected output:**
```
// ============================================================================
// DELEGATION VAULT v1 - Simplified
// ============================================================================
// Two spending paths:
// - LEFT: Admin (Alice) - unconditional spending
// - RIGHT: Delegate (Bob) - requires timelock + OP_RETURN
```

**If Task Fails:**
1. **File not created:** Check directory permissions with `ls -la /Users/brunocapelao/Projects/satshack-3-main/v2/`
2. **Rollback:** `rm /Users/brunocapelao/Projects/satshack-3-main/v2/delegation_vault_v1.simf`

---

### Task 2: Compile the Delegation Vault Program

**Files:**
- Read: `/Users/brunocapelao/Projects/satshack-3-main/v2/delegation_vault_v1.simf`
- Output: Base64 program and CMR (to be recorded)

**Prerequisites:**
- Task 1 completed
- simc compiler available

**Step 1: Compile the program**

Run:
```bash
cd /Users/brunocapelao/Projects/satshack-3-main/v2 && /Users/brunocapelao/.cargo/bin/simc delegation_vault_v1.simf
```

**Expected output:**
```
Program:
<base64-encoded-program>
```

**Step 2: Save the program output**

Record the base64 program string for use in subsequent tasks.

**If compilation fails with syntax error:**
- Check the error message for line number
- Common issues: missing semicolons, incorrect jet names, type mismatches
- The `jet::check_lock_height` uses `Height` type (not `u32`)
- The `jet::output_null_datum` returns a nested Option type

**If Task Fails:**
1. **Syntax error:** Review error message, fix the .simf file
2. **simc not found:** Verify path with `which simc` or use full path
3. **Rollback:** Not needed - compilation doesn't modify files

---

### Task 3: Get Program Info and Address

**Files:**
- Read: Compiled program from Task 2

**Prerequisites:**
- Task 2 completed (have base64 program)
- hal-simplicity available

**Step 1: Get program info**

Run (replace PROGRAM with the base64 from Task 2):
```bash
HAL=/tmp/hal-simplicity-new/target/release/hal-simplicity
PROGRAM="<paste-base64-from-task-2>"
$HAL simplicity info --liquid "$PROGRAM"
```

**Expected output (example):**
```json
{
  "jets": "elements",
  "commit_base64": "...",
  "type_arrow": "1 -> 1",
  "cmr": "<64-char-hex-cmr>",
  "liquid_testnet_address_unconf": "tex1p...",
  "is_redeem": false
}
```

**Step 2: Extract and record key values**

From the output, record:
- `cmr`: The Commitment Merkle Root (identifies the program)
- `liquid_testnet_address_unconf`: The testnet address (starts with `tex1p`)

**Step 3: Derive script_pubkey**

The script_pubkey for a Taproot address is `5120` + the 32-byte output key.
The output key is derived from the bech32m address.

Run this Python command to derive it:
```python
python3 << 'EOF'
import bech32m

address = "<paste-testnet-address-here>"
# Remove 'tex1p' prefix, decode remaining part
# The script_pubkey is: 5120 + <32-byte-hex>
# For now, use hal-simplicity's output or calculate manually
print("Script pubkey needs to be derived from address")
EOF
```

Alternatively, use the address directly with hal-simplicity (it handles conversion internally).

**If Task Fails:**
1. **"jets not supported":** The program may use jets not available in hal-simplicity
2. **Rollback:** Not needed - info command is read-only

---

### Task 4: Update secrets.json with Vault Info

**Files:**
- Modify: `/Users/brunocapelao/Projects/satshack-3-main/v2/secrets.json`

**Prerequisites:**
- Task 3 completed (have CMR and address)

**Step 1: Read current secrets.json**

Run: `cat /Users/brunocapelao/Projects/satshack-3-main/v2/secrets.json`

**Step 2: Add vault configuration**

Add a new section under `addresses` for the delegation vault. The exact values come from Task 3.

Add this structure (replace placeholders with actual values):
```json
"delegation_vault_v1": {
  "address": "<liquid_testnet_address_unconf from Task 3>",
  "cmr": "<cmr from Task 3>",
  "program": "<base64 program from Task 2>",
  "timelock_height": 2256000,
  "description": "Delegation vault: Admin unconditional, Delegate with timelock+OP_RETURN"
}
```

**Step 3: Verify JSON is valid**

Run: `cat /Users/brunocapelao/Projects/satshack-3-main/v2/secrets.json | python3 -m json.tool > /dev/null && echo "JSON valid"`

**Expected output:** `JSON valid`

**If Task Fails:**
1. **JSON invalid:** Use `python3 -m json.tool < secrets.json` to see error location
2. **Rollback:** `git checkout -- secrets.json`

---

### Task 5: Fund the Delegation Vault Address

**Files:**
- Read: `/Users/brunocapelao/Projects/satshack-3-main/v2/secrets.json` (for address)

**Prerequisites:**
- Task 4 completed (vault address known)

**Step 1: Request funds from faucet**

Open browser and go to: https://liquidtestnet.com/faucet

Enter the vault address from Task 4 and submit.

**Step 2: Record the funding transaction**

The faucet returns a TXID. Record it.

**Step 3: Verify the UTXO**

Run (replace TXID with the faucet response):
```bash
FAUCET_TXID="<paste-txid-here>"
curl -s "https://blockstream.info/liquidtestnet/api/tx/$FAUCET_TXID" | python3 -m json.tool | head -40
```

**Expected output:** JSON showing the transaction with an output to your vault address.

**Step 4: Identify the UTXO**

From the output, find:
- `vout` index where your address appears (usually 0)
- `value` in satoshis (usually 100000 = 0.001 BTC)

**If Task Fails:**
1. **Faucet rate limited:** Wait 24 hours or use a different IP
2. **Address not recognized:** Verify the address format starts with `tex1p`
3. **Rollback:** Not applicable - funding is on-chain

---

### Task 6: Run Code Review Checkpoint

1. **Dispatch all 3 reviewers in parallel:**
   - REQUIRED SUB-SKILL: Use requesting-code-review
   - All reviewers run simultaneously (code-reviewer, business-logic-reviewer, security-reviewer)
   - Wait for all to complete

2. **Handle findings by severity (MANDATORY):**

**Critical/High/Medium Issues:**
- Fix immediately (do NOT add TODO comments for these severities)
- Re-run all 3 reviewers in parallel after fixes
- Repeat until zero Critical/High/Medium issues remain

**Low Issues:**
- Add `TODO(review):` comments in code at the relevant location

3. **Proceed only when:**
   - Zero Critical/High/Medium issues remain
   - All Low issues have TODO(review): comments added

---

## Phase 2: Admin Spending Path (Unconditional)

### Task 7: Create Admin Spend Test Script

**Files:**
- Create: `/Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_admin_spend.sh`

**Prerequisites:**
- Task 5 completed (vault funded)
- Values from Tasks 2-4 recorded

**Step 1: Create the test script**

Create file `/Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_admin_spend.sh`:

```bash
#!/bin/bash
set -e

# ============================================================================
# DELEGATION VAULT - Admin Spend Test
# ============================================================================
# This script tests the Admin (Alice) spending path from the delegation vault.
# Admin can spend unconditionally - no timelock or OP_RETURN required.
# ============================================================================

HAL=/tmp/hal-simplicity-new/target/release/hal-simplicity

# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES FROM YOUR TASKS
# ============================================================================

# From Task 5: UTXO info
UTXO_TXID="REPLACE_WITH_FAUCET_TXID"
UTXO_VOUT=0
UTXO_VALUE_BTC="0.001"  # 100000 sats in BTC format

# From Task 2: Compiled program (base64)
PROGRAM="REPLACE_WITH_BASE64_PROGRAM"

# From Task 3: Program info
CMR="REPLACE_WITH_CMR"
VAULT_ADDRESS="REPLACE_WITH_VAULT_ADDRESS"

# Derive script_pubkey from CMR and internal key
# This is calculated: taptweak(internal_key, cmr)
# For simplicity, we'll derive it during PSET update

# Fixed values
ASSET="144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"
INTERNAL_KEY="50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"

# Admin keys
ADMIN_SECRET="c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"
ADMIN_PUBKEY="bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45"

# Output configuration
RECIPIENT="tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"  # Random testnet address
FEE_BTC="0.00001"        # 1000 sats
CHANGE_BTC="0.00099"     # 99000 sats

echo "=============================================="
echo "DELEGATION VAULT - Admin Spend Test"
echo "=============================================="
echo ""
echo "Vault Address: $VAULT_ADDRESS"
echo "UTXO: $UTXO_TXID:$UTXO_VOUT"
echo ""

# ============================================================================
# STEP 1: Get script_pubkey from vault address
# ============================================================================
echo "=== Step 1: Get script_pubkey ==="

# Use hal-simplicity to get the script_pubkey
SCRIPT_PUBKEY=$($HAL simplicity info --liquid "$PROGRAM" | python3 -c "
import json, sys
data = json.load(sys.stdin)
# The cmr gives us the output key via taptweak
# script_pubkey = 5120 + tweaked_output_key
# For now, we need to get this from the address
addr = data.get('liquid_testnet_address_unconf', '')
print('5120' + '00' * 32)  # Placeholder - will be derived
" 2>/dev/null || echo "SCRIPT_PUBKEY_NEEDED")

# If we need to derive manually, the PSET update will fail with the correct script_pubkey
# For now, let's use the address directly and let hal-simplicity handle it
echo "CMR: $CMR"

# ============================================================================
# STEP 2: Create PSET (Admin spends to simple address)
# ============================================================================
echo ""
echo "=== Step 2: Create PSET ==="

PSET_JSON=$($HAL simplicity pset create --liquid \
  "[{\"txid\":\"$UTXO_TXID\",\"vout\":$UTXO_VOUT}]" \
  "[
    {\"address\":\"$RECIPIENT\",\"asset\":\"$ASSET\",\"amount\":$CHANGE_BTC},
    {\"address\":\"fee\",\"asset\":\"$ASSET\",\"amount\":$FEE_BTC}
  ]")

PSET=$(echo "$PSET_JSON" | jq -r '.pset')
echo "PSET created: ${PSET:0:50}..."

# ============================================================================
# STEP 3: Get script_pubkey from UTXO
# ============================================================================
echo ""
echo "=== Step 3: Get UTXO script_pubkey ==="

UTXO_INFO=$(curl -s "https://blockstream.info/liquidtestnet/api/tx/$UTXO_TXID")
SCRIPT_PUBKEY=$(echo "$UTXO_INFO" | jq -r ".vout[$UTXO_VOUT].scriptpubkey")
echo "Script pubkey from chain: $SCRIPT_PUBKEY"

# ============================================================================
# STEP 4: Update input with UTXO info
# ============================================================================
echo ""
echo "=== Step 4: Update input ==="

PSET2_JSON=$($HAL simplicity pset update-input --liquid "$PSET" 0 \
  --input-utxo "$SCRIPT_PUBKEY:$ASSET:$UTXO_VALUE_BTC" \
  --cmr "$CMR" \
  --internal-key "$INTERNAL_KEY")

PSET2=$(echo "$PSET2_JSON" | jq -r '.pset')
echo "PSET updated with input info"

# ============================================================================
# STEP 5: Create Admin witness (Left path)
# ============================================================================
echo ""
echo "=== Step 5: Prepare Admin witness ==="

# For the Either<Signature, Signature> witness:
# Left(sig) = 0x00 prefix + signature
# Right(sig) = 0x01 prefix + signature
#
# Admin uses Left path, so witness format is:
# 00 + 64-byte-signature

# First, we need to get sig_all_hash with a dummy signature
# Dummy witness: 00 + 64-byte zeros
DUMMY_WITNESS="000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"

echo "Running with dummy witness to get sig_all_hash..."
RUN_OUTPUT=$($HAL simplicity pset run --liquid "$PSET2" 0 "$PROGRAM" "$DUMMY_WITNESS" 2>&1)
echo "$RUN_OUTPUT" | jq . 2>/dev/null || echo "$RUN_OUTPUT"

# Extract sig_all_hash
SIG_ALL_HASH=$(echo "$RUN_OUTPUT" | jq -r '.jets[] | select(.jet == "sig_all_hash") | .output_value' 2>/dev/null | sed 's/0x//')

if [ -z "$SIG_ALL_HASH" ] || [ "$SIG_ALL_HASH" = "null" ]; then
    echo "ERROR: Could not extract sig_all_hash"
    echo "Run output: $RUN_OUTPUT"
    exit 1
fi

echo "sig_all_hash: $SIG_ALL_HASH"

# ============================================================================
# STEP 6: Sign with Admin key
# ============================================================================
echo ""
echo "=== Step 6: Sign with Admin key ==="

SIGNATURE=$(python3 << EOF
from embit import ec
privkey = ec.PrivateKey(bytes.fromhex("$ADMIN_SECRET"))
sig = privkey.schnorr_sign(bytes.fromhex("$SIG_ALL_HASH"))
print(sig.serialize().hex())
EOF
)
echo "Signature: $SIGNATURE"

# Create full witness: 00 (Left tag) + signature
ADMIN_WITNESS="00${SIGNATURE}"
echo "Full witness: $ADMIN_WITNESS"

# ============================================================================
# STEP 7: Verify signature
# ============================================================================
echo ""
echo "=== Step 7: Verify signature ==="

RUN_OUTPUT=$($HAL simplicity pset run --liquid "$PSET2" 0 "$PROGRAM" "$ADMIN_WITNESS" 2>&1)
SUCCESS=$(echo "$RUN_OUTPUT" | jq -r '.success' 2>/dev/null)
echo "Verification result: $SUCCESS"

if [ "$SUCCESS" != "true" ]; then
    echo "ERROR: Signature verification failed!"
    echo "$RUN_OUTPUT"
    exit 1
fi

# ============================================================================
# STEP 8: Finalize PSET
# ============================================================================
echo ""
echo "=== Step 8: Finalize PSET ==="

FINAL_OUTPUT=$($HAL simplicity pset finalize --liquid "$PSET2" 0 "$PROGRAM" "$ADMIN_WITNESS" 2>&1)
FINAL_PSET=$(echo "$FINAL_OUTPUT" | jq -r '.pset')
echo "PSET finalized"

# ============================================================================
# STEP 9: Extract raw transaction
# ============================================================================
echo ""
echo "=== Step 9: Extract transaction ==="

TX_HEX=$($HAL simplicity pset extract --liquid "$FINAL_PSET" | tr -d '"')
echo "Transaction hex length: ${#TX_HEX}"

# ============================================================================
# STEP 10: Broadcast
# ============================================================================
echo ""
echo "=== Step 10: Broadcast ==="
echo "To broadcast manually:"
echo "curl -X POST -H 'Content-Type: text/plain' -d '$TX_HEX' https://blockstream.info/liquidtestnet/api/tx"
echo ""

read -p "Broadcast transaction? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    RESULT=$(curl -s -X POST -H 'Content-Type: text/plain' -d "$TX_HEX" https://blockstream.info/liquidtestnet/api/tx 2>&1)
    echo "Broadcast result: $RESULT"

    if [[ ${#RESULT} == 64 ]] && [[ $RESULT =~ ^[0-9a-f]+$ ]]; then
        echo ""
        echo "============================================"
        echo "*** ADMIN SPEND SUCCESS! ***"
        echo "============================================"
        echo "TXID: $RESULT"
        echo "Explorer: https://blockstream.info/liquidtestnet/tx/$RESULT"
    fi
else
    echo "Broadcast skipped. Transaction hex saved above."
fi
```

**Step 2: Make script executable**

Run: `chmod +x /Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_admin_spend.sh`

**Step 3: Verify script created**

Run: `head -30 /Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_admin_spend.sh`

**Expected output:** First 30 lines of the script showing header comments.

**If Task Fails:**
1. **Permission denied:** Check directory permissions
2. **Rollback:** `rm /Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_admin_spend.sh`

---

### Task 8: Update Admin Spend Script with Actual Values

**Files:**
- Modify: `/Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_admin_spend.sh`

**Prerequisites:**
- Task 7 completed
- Values from Tasks 2-5 available

**Step 1: Update configuration values**

Edit the script to replace placeholders with actual values:

Replace:
- `REPLACE_WITH_FAUCET_TXID` with the TXID from Task 5
- `REPLACE_WITH_BASE64_PROGRAM` with the base64 program from Task 2
- `REPLACE_WITH_CMR` with the CMR from Task 3
- `REPLACE_WITH_VAULT_ADDRESS` with the address from Task 3

**Step 2: Verify replacements**

Run: `grep "REPLACE" /Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_admin_spend.sh`

**Expected output:** (empty - no REPLACE placeholders remaining)

**If placeholders remain:** Edit the file to replace them.

**If Task Fails:**
1. **Values not available:** Complete previous tasks first
2. **Rollback:** `git checkout -- test_vault_admin_spend.sh`

---

### Task 9: Test Admin Spend Path (Dry Run)

**Files:**
- Execute: `/Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_admin_spend.sh`

**Prerequisites:**
- Task 8 completed
- Vault funded (Task 5)

**Step 1: Run the script in test mode**

Run:
```bash
cd /Users/brunocapelao/Projects/satshack-3-main/v2 && ./test_vault_admin_spend.sh
```

When prompted "Broadcast transaction? (y/n)", enter `n` for dry run.

**Expected output:**
```
=== Step 7: Verify signature ===
Verification result: true

=== Step 8: Finalize PSET ===
PSET finalized

=== Step 9: Extract transaction ===
Transaction hex length: <some number>
```

**Step 2: Analyze any failures**

If verification fails, check:
- Is the witness format correct? (00 prefix for Left path)
- Is the CMR matching the script_pubkey?
- Are values in BTC format (not satoshis)?

**If Task Fails:**
1. **sig_all_hash extraction fails:** Check PSET is correctly formed
2. **Signature verification fails:** Check witness format (00 + signature for Left path)
3. **CMR mismatch:** Verify the program was compiled correctly
4. **Rollback:** Not needed - dry run doesn't modify anything on-chain

---

### Task 10: Execute Admin Spend (Live)

**Files:**
- Execute: `/Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_admin_spend.sh`

**Prerequisites:**
- Task 9 completed successfully (dry run passed)

**Step 1: Run and broadcast**

Run:
```bash
cd /Users/brunocapelao/Projects/satshack-3-main/v2 && ./test_vault_admin_spend.sh
```

When prompted "Broadcast transaction? (y/n)", enter `y`.

**Expected output:**
```
============================================
*** ADMIN SPEND SUCCESS! ***
============================================
TXID: <64-char-hex-txid>
Explorer: https://blockstream.info/liquidtestnet/tx/<txid>
```

**Step 2: Verify on explorer**

Open the explorer link and verify:
- Transaction is confirmed
- Input was from the vault address
- Output went to recipient address

**Step 3: Update secrets.json with transaction record**

Add to `transactions` section:
```json
"vault_admin_spend": {
  "txid": "<paste-txid>",
  "explorer": "https://blockstream.info/liquidtestnet/tx/<paste-txid>",
  "description": "Admin (Alice) unconditional spend from delegation vault",
  "signer": "admin",
  "status": "confirmed"
}
```

**If Task Fails:**
1. **Broadcast rejected:** Check error message from API
2. **"bad-txns-inputs-missingorspent":** UTXO already spent
3. **Rollback:** Cannot rollback on-chain transaction
4. **If UTXO spent:** Fund the vault again (Task 5) and retry

---

## Phase 3: Delegate Spending Path (Conditional)

### Task 11: Re-fund the Delegation Vault

**Files:**
- Read: `/Users/brunocapelao/Projects/satshack-3-main/v2/secrets.json`

**Prerequisites:**
- Vault address known from Task 4

**Step 1: Request funds from faucet**

Open: https://liquidtestnet.com/faucet
Enter the vault address and submit.

**Step 2: Record new UTXO**

Record the new TXID for delegate spending test.

**Step 3: Verify the UTXO**

Run:
```bash
NEW_TXID="<paste-new-txid>"
curl -s "https://blockstream.info/liquidtestnet/api/tx/$NEW_TXID" | python3 -m json.tool | head -40
```

**If Task Fails:**
1. **Faucet rate limited:** Wait 24 hours
2. **Rollback:** Not applicable

---

### Task 12: Create Delegate Spend Test Script

**Files:**
- Create: `/Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_delegate_spend.sh`

**Prerequisites:**
- Task 11 completed (vault re-funded)
- Values from Phase 1 available

**Step 1: Create the test script**

Create file `/Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_delegate_spend.sh`:

```bash
#!/bin/bash
set -e

# ============================================================================
# DELEGATION VAULT - Delegate Spend Test
# ============================================================================
# This script tests the Delegate (Bob) spending path from the delegation vault.
# Delegate must satisfy:
# 1. Signature verification
# 2. Timelock (block height >= 2256000)
# 3. OP_RETURN in output 1
# ============================================================================

HAL=/tmp/hal-simplicity-new/target/release/hal-simplicity

# ============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# ============================================================================

# From Task 11: New UTXO info
UTXO_TXID="REPLACE_WITH_NEW_FAUCET_TXID"
UTXO_VOUT=0
UTXO_VALUE_BTC="0.001"  # 100000 sats in BTC format

# From Phase 1: Compiled program
PROGRAM="REPLACE_WITH_BASE64_PROGRAM"
CMR="REPLACE_WITH_CMR"
VAULT_ADDRESS="REPLACE_WITH_VAULT_ADDRESS"

# Fixed values
ASSET="144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"
INTERNAL_KEY="50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"

# Delegate keys
DELEGATE_SECRET="0f88f360602b68e02983c2e62a1cbd0e0d71a50f778f886abd1ccc3bc8b3ac9b"
DELEGATE_PUBKEY="8577f4e053850a2eb0c86ce4c81215fdec681c28e01648f4401e0c47a4276413"

# Output configuration
RECIPIENT="tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"
FEE_BTC="0.00001"        # 1000 sats
CHANGE_BTC="0.00099"     # 99000 sats

# SAID Protocol payload for OP_RETURN
# Format: "SAID" (4 bytes) + version (1 byte) + type (1 byte) + hash (32 bytes)
SAID_PAYLOAD="534149440102aabbccdd11223344aabbccdd11223344aabbccdd11223344aabbccdd11223344"

echo "=============================================="
echo "DELEGATION VAULT - Delegate Spend Test"
echo "=============================================="
echo ""
echo "Vault Address: $VAULT_ADDRESS"
echo "UTXO: $UTXO_TXID:$UTXO_VOUT"
echo "Timelock: Block >= 2256000"
echo ""

# Check current block height
CURRENT_HEIGHT=$(curl -s "https://blockstream.info/liquidtestnet/api/blocks/tip/height")
echo "Current block height: $CURRENT_HEIGHT"
echo "Timelock height: 2256000"

if [ "$CURRENT_HEIGHT" -lt 2256000 ]; then
    echo ""
    echo "WARNING: Current height ($CURRENT_HEIGHT) is below timelock (2256000)"
    echo "Delegate spending will FAIL until block 2256000"
    echo ""
    read -p "Continue anyway (to see the failure)? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. Wait for block 2256000."
        exit 0
    fi
fi

# ============================================================================
# STEP 1: Get script_pubkey from UTXO
# ============================================================================
echo ""
echo "=== Step 1: Get UTXO script_pubkey ==="

UTXO_INFO=$(curl -s "https://blockstream.info/liquidtestnet/api/tx/$UTXO_TXID")
SCRIPT_PUBKEY=$(echo "$UTXO_INFO" | jq -r ".vout[$UTXO_VOUT].scriptpubkey")
echo "Script pubkey: $SCRIPT_PUBKEY"

# ============================================================================
# STEP 2: Create PSET with OP_RETURN (required for delegate path)
# ============================================================================
echo ""
echo "=== Step 2: Create PSET with OP_RETURN ==="

# Output 0: Recipient (change)
# Output 1: OP_RETURN with SAID payload (REQUIRED for delegate)
# Output 2: Fee

PSET_JSON=$($HAL simplicity pset create --liquid \
  "[{\"txid\":\"$UTXO_TXID\",\"vout\":$UTXO_VOUT}]" \
  "[
    {\"address\":\"$RECIPIENT\",\"asset\":\"$ASSET\",\"amount\":$CHANGE_BTC},
    {\"address\":\"data:$SAID_PAYLOAD\",\"asset\":\"$ASSET\",\"amount\":0},
    {\"address\":\"fee\",\"asset\":\"$ASSET\",\"amount\":$FEE_BTC}
  ]")

PSET=$(echo "$PSET_JSON" | jq -r '.pset')
echo "PSET created with OP_RETURN in output 1"

# ============================================================================
# STEP 3: Update input with UTXO info
# ============================================================================
echo ""
echo "=== Step 3: Update input ==="

PSET2_JSON=$($HAL simplicity pset update-input --liquid "$PSET" 0 \
  --input-utxo "$SCRIPT_PUBKEY:$ASSET:$UTXO_VALUE_BTC" \
  --cmr "$CMR" \
  --internal-key "$INTERNAL_KEY")

PSET2=$(echo "$PSET2_JSON" | jq -r '.pset')
echo "PSET updated"

# ============================================================================
# STEP 4: Create Delegate witness (Right path)
# ============================================================================
echo ""
echo "=== Step 4: Prepare Delegate witness ==="

# For the Either<Signature, Signature> witness:
# Left(sig) = 0x00 prefix + signature
# Right(sig) = 0x01 prefix + signature
#
# Delegate uses Right path, so witness format is:
# 01 + 64-byte-signature

# First, get sig_all_hash with dummy signature
DUMMY_WITNESS="010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"

echo "Running with dummy witness to get sig_all_hash..."
RUN_OUTPUT=$($HAL simplicity pset run --liquid "$PSET2" 0 "$PROGRAM" "$DUMMY_WITNESS" 2>&1)

# Check for jet failures
if echo "$RUN_OUTPUT" | grep -q "check_lock_height"; then
    echo ""
    echo "Jet output:"
    echo "$RUN_OUTPUT" | jq '.jets[] | select(.jet == "check_lock_height")' 2>/dev/null || echo "$RUN_OUTPUT"
fi

# Extract sig_all_hash
SIG_ALL_HASH=$(echo "$RUN_OUTPUT" | jq -r '.jets[] | select(.jet == "sig_all_hash") | .output_value' 2>/dev/null | sed 's/0x//')

if [ -z "$SIG_ALL_HASH" ] || [ "$SIG_ALL_HASH" = "null" ]; then
    echo "ERROR: Could not extract sig_all_hash"
    echo "This might be because timelock check failed early."
    echo "Run output:"
    echo "$RUN_OUTPUT" | jq . 2>/dev/null || echo "$RUN_OUTPUT"
    exit 1
fi

echo "sig_all_hash: $SIG_ALL_HASH"

# ============================================================================
# STEP 5: Sign with Delegate key
# ============================================================================
echo ""
echo "=== Step 5: Sign with Delegate key ==="

SIGNATURE=$(python3 << EOF
from embit import ec
privkey = ec.PrivateKey(bytes.fromhex("$DELEGATE_SECRET"))
sig = privkey.schnorr_sign(bytes.fromhex("$SIG_ALL_HASH"))
print(sig.serialize().hex())
EOF
)
echo "Signature: $SIGNATURE"

# Create full witness: 01 (Right tag) + signature
DELEGATE_WITNESS="01${SIGNATURE}"
echo "Full witness: $DELEGATE_WITNESS"

# ============================================================================
# STEP 6: Verify signature and conditions
# ============================================================================
echo ""
echo "=== Step 6: Verify signature and conditions ==="

RUN_OUTPUT=$($HAL simplicity pset run --liquid "$PSET2" 0 "$PROGRAM" "$DELEGATE_WITNESS" 2>&1)
SUCCESS=$(echo "$RUN_OUTPUT" | jq -r '.success' 2>/dev/null)
echo "Verification result: $SUCCESS"

# Show jet results
echo ""
echo "Jet execution results:"
echo "$RUN_OUTPUT" | jq '.jets[]' 2>/dev/null || echo "$RUN_OUTPUT"

if [ "$SUCCESS" != "true" ]; then
    echo ""
    echo "ERROR: Verification failed!"
    echo ""
    echo "Possible causes:"
    echo "1. Timelock not satisfied (current height < 2256000)"
    echo "2. OP_RETURN missing or in wrong position"
    echo "3. Signature invalid"
    echo ""
    echo "Full output:"
    echo "$RUN_OUTPUT"
    exit 1
fi

# ============================================================================
# STEP 7: Finalize and extract
# ============================================================================
echo ""
echo "=== Step 7: Finalize PSET ==="

FINAL_OUTPUT=$($HAL simplicity pset finalize --liquid "$PSET2" 0 "$PROGRAM" "$DELEGATE_WITNESS" 2>&1)
FINAL_PSET=$(echo "$FINAL_OUTPUT" | jq -r '.pset')
echo "PSET finalized"

echo ""
echo "=== Step 8: Extract transaction ==="

TX_HEX=$($HAL simplicity pset extract --liquid "$FINAL_PSET" | tr -d '"')
echo "Transaction hex length: ${#TX_HEX}"

# ============================================================================
# STEP 8: Broadcast
# ============================================================================
echo ""
echo "=== Step 9: Broadcast ==="
echo ""

read -p "Broadcast transaction? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    RESULT=$(curl -s -X POST -H 'Content-Type: text/plain' -d "$TX_HEX" https://blockstream.info/liquidtestnet/api/tx 2>&1)
    echo "Broadcast result: $RESULT"

    if [[ ${#RESULT} == 64 ]] && [[ $RESULT =~ ^[0-9a-f]+$ ]]; then
        echo ""
        echo "============================================"
        echo "*** DELEGATE SPEND SUCCESS! ***"
        echo "============================================"
        echo "TXID: $RESULT"
        echo "Explorer: https://blockstream.info/liquidtestnet/tx/$RESULT"
    fi
else
    echo "Broadcast skipped."
fi
```

**Step 2: Make script executable**

Run: `chmod +x /Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_delegate_spend.sh`

**Step 3: Verify script created**

Run: `head -30 /Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_delegate_spend.sh`

**If Task Fails:**
1. **Rollback:** `rm /Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_delegate_spend.sh`

---

### Task 13: Update Delegate Spend Script with Values

**Files:**
- Modify: `/Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_delegate_spend.sh`

**Prerequisites:**
- Task 12 completed
- Task 11 TXID available
- Phase 1 values available

**Step 1: Update placeholders**

Replace:
- `REPLACE_WITH_NEW_FAUCET_TXID` with TXID from Task 11
- `REPLACE_WITH_BASE64_PROGRAM` with program from Task 2
- `REPLACE_WITH_CMR` with CMR from Task 3
- `REPLACE_WITH_VAULT_ADDRESS` with address from Task 3

**Step 2: Verify no placeholders remain**

Run: `grep "REPLACE" /Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_delegate_spend.sh`

**Expected output:** (empty)

**If Task Fails:**
1. **Rollback:** `git checkout -- test_vault_delegate_spend.sh`

---

### Task 14: Test Delegate Spend (Expect Failure Before Timelock)

**Files:**
- Execute: `/Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_delegate_spend.sh`

**Prerequisites:**
- Task 13 completed
- Current block height < 2256000

**Step 1: Run and observe timelock failure**

Run:
```bash
cd /Users/brunocapelao/Projects/satshack-3-main/v2 && ./test_vault_delegate_spend.sh
```

**Expected output:**
```
WARNING: Current height (2255xxx) is below timelock (2256000)
Delegate spending will FAIL until block 2256000

Continue anyway (to see the failure)? (y/n)
```

Enter `y` to observe the failure.

**Expected failure:**
```
ERROR: Verification failed!

Possible causes:
1. Timelock not satisfied (current height < 2256000)
```

**Step 2: Document the expected behavior**

This failure PROVES the timelock is working. Delegate CANNOT spend until block 2256000.

**If Task Fails:**
1. **Script crashes before timelock check:** Check PSET creation and witness format
2. **Timelock not enforced:** Review the delegation_vault_v1.simf for correct jet usage

---

### Task 15: Wait for Timelock and Test Delegate Spend (Success)

**Files:**
- Execute: `/Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_delegate_spend.sh`

**Prerequisites:**
- Task 14 completed
- Current block height >= 2256000

**Step 1: Check current height**

Run:
```bash
curl -s "https://blockstream.info/liquidtestnet/api/blocks/tip/height"
```

**Expected output:** A number >= 2256000

If not, wait. Liquid Testnet produces blocks approximately every minute.

**Step 2: Run delegate spend**

Run:
```bash
cd /Users/brunocapelao/Projects/satshack-3-main/v2 && ./test_vault_delegate_spend.sh
```

When prompted, enter `y` to broadcast.

**Expected output:**
```
============================================
*** DELEGATE SPEND SUCCESS! ***
============================================
TXID: <64-char-hex-txid>
Explorer: https://blockstream.info/liquidtestnet/tx/<txid>
```

**Step 3: Verify on explorer**

Open the explorer link and verify:
- Transaction is confirmed
- Input was from the vault address
- Output 1 contains OP_RETURN with SAID payload
- Signer was delegate (Bob)

**Step 4: Update secrets.json**

Add to `transactions` section:
```json
"vault_delegate_spend": {
  "txid": "<paste-txid>",
  "explorer": "https://blockstream.info/liquidtestnet/tx/<paste-txid>",
  "description": "Delegate (Bob) conditional spend with timelock + OP_RETURN",
  "signer": "delegate",
  "op_return_payload": "534149440102aabbccdd11223344aabbccdd11223344aabbccdd11223344aabbccdd11223344",
  "timelock_satisfied": true,
  "status": "confirmed"
}
```

**If Task Fails:**
1. **Timelock still failing:** Verify block height with curl command
2. **OP_RETURN check failing:** Verify output 1 has OP_RETURN data
3. **Rollback:** Cannot rollback on-chain

---

### Task 16: Run Code Review Checkpoint

1. **Dispatch all 3 reviewers in parallel:**
   - REQUIRED SUB-SKILL: Use requesting-code-review
   - All reviewers run simultaneously
   - Wait for all to complete

2. **Handle findings by severity:**
   - Fix Critical/High/Medium immediately
   - Add TODO(review): for Low issues

3. **Proceed when:** Zero Critical/High/Medium issues remain

---

## Phase 4: Revocation Test (Admin Revokes Delegation)

### Task 17: Create Revocation Scenario

**Files:**
- Read: secrets.json
- Fund vault again

**Prerequisites:**
- Phase 3 completed

**Step 1: Fund vault for revocation test**

Use faucet: https://liquidtestnet.com/faucet

Record new TXID.

**Step 2: Document revocation scenario**

Revocation works by Admin spending the vault before Delegate can. Since Admin has no timelock, Admin can always "beat" Delegate by spending first.

This is effectively a revocation - the delegate's authority is removed by spending the vault.

**If Task Fails:**
1. **Faucet rate limited:** Wait or use different approach

---

### Task 18: Update and Run Admin Revocation Spend

**Files:**
- Modify: `/Users/brunocapelao/Projects/satshack-3-main/v2/test_vault_admin_spend.sh`

**Prerequisites:**
- Task 17 completed (vault funded)

**Step 1: Update UTXO_TXID in admin spend script**

Edit the script to use the new TXID from Task 17.

**Step 2: Run admin spend to revoke**

Run:
```bash
cd /Users/brunocapelao/Projects/satshack-3-main/v2 && ./test_vault_admin_spend.sh
```

Broadcast when prompted.

**Expected output:** Admin spend succeeds, vault is now empty.

**Step 3: Document revocation**

This proves: Admin can revoke delegation at any time by spending the vault unconditionally.

**If Task Fails:**
1. **UTXO already spent:** Verify TXID is correct
2. **Rollback:** Not applicable

---

## Phase 5: Documentation and Cleanup

### Task 19: Create Comprehensive Documentation

**Files:**
- Create: `/Users/brunocapelao/Projects/satshack-3-main/v2/DELEGATION_VAULT_GUIDE.md`

**Prerequisites:**
- All tests completed

**Step 1: Write documentation**

Create file with content:

```markdown
# Delegation Vault Guide

## Overview

The Delegation Vault is a Simplicity smart contract that implements hierarchical spending authority:

- **Admin (Alice)**: Full control, can spend unconditionally
- **Delegate (Bob)**: Limited authority, can only spend when:
  1. Timelock has passed (block height >= threshold)
  2. Transaction includes OP_RETURN with attestation data

## Contract Structure

```
delegation_vault_v1.simf
├── witness::SPENDING_PATH: Either<Signature, Signature>
├── admin_spend(sig): Unconditional signature check
└── delegate_spend(sig): Signature + Timelock + OP_RETURN check
```

## Spending Paths

### Admin Path (Left)
- Witness format: `00` + 64-byte Schnorr signature
- Requirements: Valid signature from Admin public key
- Use case: Normal spending, revocation, emergency access

### Delegate Path (Right)
- Witness format: `01` + 64-byte Schnorr signature
- Requirements:
  1. Valid signature from Delegate public key
  2. Block height >= 2256000
  3. Output 1 must be OP_RETURN with data
- Use case: Issuing attestations with on-chain data

## Revocation

Admin can revoke delegation at any time by spending the vault using the Admin path. Since Admin has no timelock restriction, Admin can always spend before Delegate.

## Transactions

| Transaction | Path | Status |
|-------------|------|--------|
| Admin Spend | Left | [link] |
| Delegate Spend | Right | [link] |
| Admin Revocation | Left | [link] |

## Technical Details

- **Network**: Liquid Testnet
- **Timelock**: Block 2256000
- **Asset**: L-BTC (144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49)
- **CMR**: [from secrets.json]

## Files

- `delegation_vault_v1.simf`: Simfony source code
- `test_vault_admin_spend.sh`: Admin spending test script
- `test_vault_delegate_spend.sh`: Delegate spending test script
- `secrets.json`: Keys and transaction records
```

**Step 2: Verify documentation created**

Run: `head -30 /Users/brunocapelao/Projects/satshack-3-main/v2/DELEGATION_VAULT_GUIDE.md`

**If Task Fails:**
1. **Rollback:** `rm DELEGATION_VAULT_GUIDE.md`

---

### Task 20: Update README with Delegation Vault Status

**Files:**
- Modify: `/Users/brunocapelao/Projects/satshack-3-main/v2/README.md`

**Prerequisites:**
- Task 19 completed

**Step 1: Add delegation vault section**

Add to README after existing content:

```markdown
---

## Delegation Vault - COMPLETED

The delegation vault feature is now fully implemented:

- [x] Vault with OR logic (Admin OR Delegate)
- [x] Timelock condition for delegate spending
- [x] OP_RETURN requirement for delegate spending
- [x] Admin revocation capability

See `DELEGATION_VAULT_GUIDE.md` for full documentation.

### Test Transactions

| Transaction | Type | Status |
|-------------|------|--------|
| Admin unconditional spend | Admin Path | Confirmed |
| Delegate conditional spend | Delegate Path | Confirmed |
| Admin revocation | Admin Path | Confirmed |
```

**Step 2: Verify README updated**

Run: `tail -20 /Users/brunocapelao/Projects/satshack-3-main/v2/README.md`

**If Task Fails:**
1. **Rollback:** `git checkout -- README.md`

---

### Task 21: Final Code Review

1. **Dispatch all 3 reviewers in parallel:**
   - REQUIRED SUB-SKILL: Use requesting-code-review
   - Review all new files
   - Wait for all to complete

2. **Handle findings by severity**

3. **Final verification:**
   - All tests pass
   - All documentation complete
   - No Critical/High/Medium issues remain

---

### Task 22: Commit All Changes

**Files:**
- All new and modified files

**Prerequisites:**
- Task 21 completed (code review passed)

**Step 1: Stage all changes**

Run:
```bash
cd /Users/brunocapelao/Projects/satshack-3-main/v2
git add delegation_vault_v1.simf
git add test_vault_admin_spend.sh
git add test_vault_delegate_spend.sh
git add secrets.json
git add DELEGATION_VAULT_GUIDE.md
git add README.md
git add docs/plans/
```

**Step 2: Commit**

Run:
```bash
git commit -m "feat: implement delegation vault with conditional spending

- Add delegation_vault_v1.simf with Admin/Delegate OR logic
- Admin path: unconditional signature verification
- Delegate path: signature + timelock (block 2256000) + OP_RETURN
- Add test scripts for both spending paths
- Document in DELEGATION_VAULT_GUIDE.md
- All test transactions confirmed on Liquid Testnet"
```

**Step 3: Verify commit**

Run: `git log -1`

**Expected output:** Shows the commit with message.

**If Task Fails:**
1. **Nothing to commit:** Verify files are staged
2. **Rollback:** `git reset HEAD~1` (if commit was made incorrectly)

---

## Appendix A: Troubleshooting

### Issue: "jets not supported"

**Cause:** hal-simplicity may not support all Simplicity jets.

**Solution:** Use only core jets:
- `jet::sig_all_hash()`
- `jet::bip_0340_verify()`
- `jet::check_lock_height()`
- `jet::num_outputs()`
- `jet::output_null_datum()`

### Issue: Witness format incorrect

**Cause:** Either type encoding not correct.

**Solution:**
- Left(sig) = `00` + 64-byte signature hex
- Right(sig) = `01` + 64-byte signature hex

### Issue: CMR mismatch

**Cause:** Script pubkey doesn't match CMR + internal key.

**Solution:**
1. Get fresh script_pubkey from funded UTXO via API
2. Verify CMR matches compiled program
3. Use standard internal key: `50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0`

### Issue: Timelock not enforced

**Cause:** Height type vs u32 confusion.

**Solution:** Use `Height` type for timelock values:
```rust
let min_height: Height = 2256000;
jet::check_lock_height(min_height);
```

---

## Appendix B: Future Enhancements

1. **Spend Limits**: Add amount checking with `jet::output_amounts_hash()`
2. **Multiple Delegates**: Extend Either to handle multiple delegate keys
3. **Threshold Signatures**: Require M-of-N delegate signatures
4. **Revocation UTXO**: Create explicit revocation mechanism instead of just spending
5. **Certificate Contract**: Chain vault to certificate issuance contract

---

## Summary

This plan implements a complete delegation vault system with:
- 22 bite-sized tasks (2-5 minutes each)
- Full test coverage for Admin and Delegate paths
- Timelock verification (expected failure before, success after)
- OP_RETURN enforcement for delegate spending
- Revocation capability via Admin spending
- Comprehensive documentation

**Estimated total time:** 2-3 hours
**Network:** Liquid Testnet
**Tools:** simc, hal-simplicity (corrected fork), Python/embit

---

*Plan created: 2026-01-06*
*Feature: delegation-vault-simplicity*
