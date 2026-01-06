#!/bin/bash
set -e

cd /Users/brunocapelao/Projects/satshack-3-main/v2

HAL=/tmp/hal-simplicity-new/target/release/hal-simplicity

# UTXO
UTXO_TXID="a6e83d005bb5bbbd738e92cea13306cf45b5aeb0ac7d86e692c8e20cd73f20b4"
UTXO_VOUT="0"
UTXO_VALUE="100000"
ASSET="144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"

# P2PK program
PROGRAM_B64="1JtM33xqq2wHIdc/BfZZ0/NBxcrvfyLEt2sDrdyBroNkyyAjgMAqcUbGAgA="
CMR="0372d6489c5ff31451df4c959b7449b1edda528f2304ca223266bca1dc8f246a"
P2PK_SCRIPT="512087ff55da8af77c1f432d80afcee851712c6b151161f169b0fa9250b97221b169"

# Alice's public key (we don't have private key, so this is just for testing the flow)
ALICE_PUBKEY="9bef8d556d80e43ae7e0becb3a7e6838b95defe45896ed6075bb9035d06c9964"

echo "=== Step 1: Create PSET ==="
INPUTS="[{\"txid\":\"${UTXO_TXID}\",\"vout\":${UTXO_VOUT}}]"
OUTPUTS="[{\"address\":\"tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0\",\"asset\":\"${ASSET}\",\"amount\":99000}]"

PSET_JSON=$($HAL simplicity pset create --liquid "$INPUTS" "$OUTPUTS")
PSET=$(echo "$PSET_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['pset'])")
echo "PSET created (${#PSET} chars)"

echo ""
echo "=== Step 2: Update input with UTXO ==="
INPUT_UTXO="${P2PK_SCRIPT}:${ASSET}:${UTXO_VALUE}"
echo "Input UTXO: $INPUT_UTXO"

PSET2_JSON=$($HAL simplicity pset update-input --liquid "$PSET" 0 --input-utxo "$INPUT_UTXO" --cmr "$CMR")
PSET2=$(echo "$PSET2_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin)['pset'])")
echo "PSET updated"

echo ""
echo "=== Step 3: Run program (dry run) ==="
# For run, we need a witness. Let's use a dummy signature first to see the error
DUMMY_WITNESS="0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"

echo "Running with dummy witness to check if PSET is valid..."
$HAL simplicity pset run --liquid "$PSET2" 0 "$PROGRAM_B64" "$DUMMY_WITNESS" 2>&1 || true

echo ""
echo "=== Step 4: Extract raw tx to compute sighash ==="
# First finalize with dummy then extract to get raw tx
$HAL simplicity pset finalize --liquid "$PSET2" 0 "$PROGRAM_B64" "$DUMMY_WITNESS" 2>&1 || true

echo ""
echo "=== Testing complete ==="
