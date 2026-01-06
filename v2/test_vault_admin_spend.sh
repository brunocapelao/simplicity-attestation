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
# CONFIGURATION
# ============================================================================

# UTXO info (update UTXO_TXID for each test)
UTXO_TXID="0c639a24a0507387fc0e22a836cad97ddaa09fcacb6036abff39241da8406b15"
UTXO_VOUT=0
UTXO_VALUE_BTC="0.001"  # 100000 sats in BTC format

# Compiled program (base64)
PROGRAM="5gXQKEGJtN5gn38JDZrjk4Yg5zHtW7RGAZNixi+vDo15i+CoHlaiggTFBh9AoSQJOHM4qiEiuhMwARVwsGLwpYT2BhULrCX64qRkLLDgFbd+AIYBiQKEkH3m4CKD8BFAsmxhzXXcvB6E6noyBxnL/G3JXlGU+eypltVaey12jFEeKjEOGAYhNp+JAQDgIHDAnDAMQcRgcULTCu/pwKcKFF1hkNnJkCQr+9jQOFHALJHogDwYj0hOyCYOKQnFlkAETZAA4kCcNSQgwVeDmBd77UKPutD6OLpAkNFbS8SYUsZldxGEoA3o23T+XYAMMAxWQAAAACDWQKE2QAAAAACEChJBuBnG4KKBYvhrOYIi/1AcaRNMBhc3vyX09ErCRo/sv5CAbaGAJlp1bvfigwDEgUIMQKEkCRQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcz8FVrNkEyx2Bj+VLRZhxh+w1ElWaG0dCZ/89Ws0Q57jBgGJBiBQkgSN4nQwkcAz3xG8XPR4KsOjBRZ3weUhvfP91+qbUoSSjlgdgFJDANJIoA5FB4CBwokUAcjwcRAcYgcbhceAOSgORAXJMByXByOA5dA8kwOXwA=="

# Program info
CMR="265e843c32c4c80bc53704829fbbe43e8efc411360dab659cd7001e560d58f1d"
VAULT_ADDRESS="tex1pewrql3qrpzg5gc3ftdkhynz4mkmuaz7hj5ycdnwndl5jlhkxrd0qzygxjt"

# Fixed values
ASSET="144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"
INTERNAL_KEY="50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"

# Admin keys
ADMIN_SECRET="c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"
ADMIN_PUBKEY="bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45"

# Output configuration
RECIPIENT="tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"
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
# STEP 1: Get script_pubkey from UTXO
# ============================================================================
echo "=== Step 1: Get UTXO script_pubkey ==="

UTXO_INFO=$(curl -s "https://blockstream.info/liquidtestnet/api/tx/$UTXO_TXID")
SCRIPT_PUBKEY=$(echo "$UTXO_INFO" | jq -r ".vout[$UTXO_VOUT].scriptpubkey")
echo "Script pubkey from chain: $SCRIPT_PUBKEY"

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
# STEP 3: Update input with UTXO info
# ============================================================================
echo ""
echo "=== Step 3: Update input ==="

PSET2_JSON=$($HAL simplicity pset update-input --liquid "$PSET" 0 \
  --input-utxo "$SCRIPT_PUBKEY:$ASSET:$UTXO_VALUE_BTC" \
  --cmr "$CMR" \
  --internal-key "$INTERNAL_KEY")

PSET2=$(echo "$PSET2_JSON" | jq -r '.pset')
echo "PSET updated with input info"

# ============================================================================
# STEP 4: Create Admin witness (Left path)
# ============================================================================
echo ""
echo "=== Step 4: Prepare Admin witness ==="

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
# STEP 5: Sign with Admin key
# ============================================================================
echo ""
echo "=== Step 5: Sign with Admin key ==="

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
# STEP 6: Verify signature
# ============================================================================
echo ""
echo "=== Step 6: Verify signature ==="

RUN_OUTPUT=$($HAL simplicity pset run --liquid "$PSET2" 0 "$PROGRAM" "$ADMIN_WITNESS" 2>&1)
SUCCESS=$(echo "$RUN_OUTPUT" | jq -r '.success' 2>/dev/null)
echo "Verification result: $SUCCESS"

if [ "$SUCCESS" != "true" ]; then
    echo "ERROR: Signature verification failed!"
    echo "$RUN_OUTPUT"
    exit 1
fi

# ============================================================================
# STEP 7: Finalize PSET
# ============================================================================
echo ""
echo "=== Step 7: Finalize PSET ==="

FINAL_OUTPUT=$($HAL simplicity pset finalize --liquid "$PSET2" 0 "$PROGRAM" "$ADMIN_WITNESS" 2>&1)
FINAL_PSET=$(echo "$FINAL_OUTPUT" | jq -r '.pset')
echo "PSET finalized"

# ============================================================================
# STEP 8: Extract raw transaction
# ============================================================================
echo ""
echo "=== Step 8: Extract transaction ==="

TX_HEX=$($HAL simplicity pset extract --liquid "$FINAL_PSET" | tr -d '"')
echo "Transaction hex length: ${#TX_HEX}"

# ============================================================================
# STEP 9: Broadcast
# ============================================================================
echo ""
echo "=== Step 9: Broadcast ==="
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
