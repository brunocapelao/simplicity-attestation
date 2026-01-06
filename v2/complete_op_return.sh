#!/bin/bash
set -e

HAL=/tmp/hal-simplicity-new/target/release/hal-simplicity

# Configuration from secrets.json
UTXO_TXID="38ff3f17073233ba3ad0254fe79745c675e9ac9c667811aee0f366abc26281ec"
UTXO_VOUT=0
UTXO_VALUE_BTC="0.001"  # 100000 sats in BTC format

ASSET="144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"
RECIPIENT="tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"
FEE_BTC="0.00001"        # 1000 sats in BTC
CHANGE_BTC="0.00099"     # 99000 sats in BTC

# SAID Protocol payload: "SAID" + v1 + type01 + 32-byte test hash
SAID_PAYLOAD="534149440101deadbeefcafebabedeadbeefcafebabedeadbeefcafebabedeadbeefcafebabe"

# Program info
PROG="4jSQJOHM4qiEiuhMwARVwsGLwpYT2BhULrCX64qRkLLDgFbd+AIYBiQKE2m8wT7+Ehs1xycMQc5j2rdojAMmxYxfXh0a8xfBUDytRQQgUJIQYaHCpxQLQ2MOa67l4PQnU9GQOM5f425K8oynz2VMtqrT2Wu0YojxUYhwwDEJvPwcEA4GBwkA"
CMR="2f4199e55c870456428dc7b822c2c98297607d1781c83124d6b816353ed0cac0"
SCRIPT_PUBKEY="5120128e4cb1212a633ba20011b23d8e8ea09a369ba66fd7b0f02b35031d4fd7e2c0"

# Taproot keys
INTERNAL_KEY="50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"

# Admin keys
ADMIN_SECRET="c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"
ADMIN_PUBKEY="bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45"

echo "=============================================="
echo "SAID Protocol - OP_RETURN Transaction"
echo "=============================================="

echo ""
echo "=== Step 1: Create PSET with OP_RETURN ==="
PSET_JSON=$($HAL simplicity pset create --liquid \
  "[{\"txid\":\"$UTXO_TXID\",\"vout\":$UTXO_VOUT}]" \
  "[
    {\"address\":\"$RECIPIENT\",\"asset\":\"$ASSET\",\"amount\":$CHANGE_BTC},
    {\"address\":\"data:$SAID_PAYLOAD\",\"asset\":\"$ASSET\",\"amount\":0},
    {\"address\":\"fee\",\"asset\":\"$ASSET\",\"amount\":$FEE_BTC}
  ]")

PSET=$(echo "$PSET_JSON" | jq -r '.pset')
echo "PSET created"

echo ""
echo "=== Step 2: Update input with UTXO info ==="
# IMPORTANT: input-utxo value must be in BTC, not satoshis!
PSET2_JSON=$($HAL simplicity pset update-input --liquid "$PSET" 0 \
  --input-utxo "$SCRIPT_PUBKEY:$ASSET:$UTXO_VALUE_BTC" \
  --cmr "$CMR" \
  --internal-key "$INTERNAL_KEY")

PSET2=$(echo "$PSET2_JSON" | jq -r '.pset')
echo "PSET updated with input info"

echo ""
echo "=== Step 3: Calculate sig_all_hash ==="
# Use a 64-byte dummy signature (128 hex chars) to get the sig_all_hash
DUMMY_SIG="00000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000001"

RUN_OUTPUT=$($HAL simplicity pset run --liquid "$PSET2" 0 "$PROG" "$DUMMY_SIG" 2>&1)
echo "$RUN_OUTPUT" | jq . || echo "$RUN_OUTPUT"

# Extract sig_all_hash from jet output
SIG_ALL_HASH=$(echo "$RUN_OUTPUT" | jq -r '.jets[] | select(.jet == "sig_all_hash") | .output_value' 2>/dev/null | sed 's/0x//')

if [ -n "$SIG_ALL_HASH" ] && [ "$SIG_ALL_HASH" != "null" ]; then
    echo ""
    echo "*** sig_all_hash: $SIG_ALL_HASH ***"

    echo ""
    echo "=== Step 4: Sign with Admin key ==="
    # Use Python with embit to sign
    SIGNATURE=$(python3 << EOF
from embit import ec
privkey = ec.PrivateKey(bytes.fromhex("$ADMIN_SECRET"))
sig = privkey.schnorr_sign(bytes.fromhex("$SIG_ALL_HASH"))
print(sig.serialize().hex())
EOF
)
    echo "Signature: $SIGNATURE"

    echo ""
    echo "=== Step 5: Verify signature ==="
    RUN_OUTPUT=$($HAL simplicity pset run --liquid "$PSET2" 0 "$PROG" "$SIGNATURE" 2>&1)
    SUCCESS=$(echo "$RUN_OUTPUT" | jq -r '.success')
    echo "Verification: $SUCCESS"

    if [ "$SUCCESS" = "true" ]; then
        echo ""
        echo "=== Step 6: Finalize PSET ==="
        FINAL_OUTPUT=$($HAL simplicity pset finalize --liquid "$PSET2" 0 "$PROG" "$SIGNATURE" 2>&1)
        FINAL_PSET=$(echo "$FINAL_OUTPUT" | jq -r '.pset')
        echo "PSET finalized"

        echo ""
        echo "=== Step 7: Extract raw transaction ==="
        TX_HEX=$($HAL simplicity pset extract --liquid "$FINAL_PSET" | tr -d '"')
        echo "Transaction hex length: ${#TX_HEX}"

        echo ""
        echo "=== Step 8: Broadcast ==="
        echo "To broadcast:"
        echo "curl -X POST -H 'Content-Type: text/plain' -d '$TX_HEX' https://blockstream.info/liquidtestnet/api/tx"

        # Auto-broadcast
        RESULT=$(curl -s -X POST -H 'Content-Type: text/plain' -d "$TX_HEX" https://blockstream.info/liquidtestnet/api/tx 2>&1)
        echo ""
        echo "Broadcast result: $RESULT"

        if [[ ${#RESULT} == 64 ]] && [[ $RESULT =~ ^[0-9a-f]+$ ]]; then
            echo ""
            echo "============================================"
            echo "*** TRANSACTION BROADCAST SUCCESS! ***"
            echo "============================================"
            echo "TXID: $RESULT"
            echo "Explorer: https://blockstream.info/liquidtestnet/tx/$RESULT"
        fi
    else
        echo "Signature verification failed!"
        echo "$RUN_OUTPUT"
    fi
else
    echo "Failed to extract sig_all_hash from run output"
    echo "Run output: $RUN_OUTPUT"
fi
