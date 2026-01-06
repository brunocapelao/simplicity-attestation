#!/usr/bin/env python3
"""
DELEGATION VAULT - Delegate Spend Test

This script tests the Delegate (Bob) spending path from the delegation vault.
Delegate requires:
  1. Valid signature
  2. Timelock passed (block >= 2256000)
  3. OP_RETURN in output 1

IMPORTANT: This will only succeed after block 2256000 on Liquid Testnet.
"""

import subprocess
import json
import requests
from embit import ec

# Configuration
HAL = "/tmp/hal-simplicity-new/target/release/hal-simplicity"

# Update this UTXO before running
UTXO_TXID = "c968150de3da417b7d68834c20fe51460a0f7454c330770c5789393b88c8ca8b"
UTXO_VOUT = 0
UTXO_VALUE_BTC = "0.001"  # 100000 sats

# Compiled program (base64)
PROGRAM = "5gXQKEGJtN5gn38JDZrjk4Yg5zHtW7RGAZNixi+vDo15i+CoHlaiggTFBh9AoSQJOHM4qiEiuhMwARVwsGLwpYT2BhULrCX64qRkLLDgFbd+AIYBiQKEkH3m4CKD8BFAsmxhzXXcvB6E6noyBxnL/G3JXlGU+eypltVaey12jFEeKjEOGAYhNp+JAQDgIHDAnDAMQcRgcULTCu/pwKcKFF1hkNnJkCQr+9jQOFHALJHogDwYj0hOyCYOKQnFlkAETZAA4kCcNSQgwVeDmBd77UKPutD6OLpAkNFbS8SYUsZldxGEoA3o23T+XYAMMAxWQAAAACDWQKE2QAAAAACEChJBuBnG4KKBYvhrOYIi/1AcaRNMBhc3vyX09ErCRo/sv5CAbaGAJlp1bvfigwDEgUIMQKEkCRQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcz8FVrNkEyx2Bj+VLRZhxh+w1ElWaG0dCZ/89Ws0Q57jBgGJBiBQkgSN4nQwkcAz3xG8XPR4KsOjBRZ3weUhvfP91+qbUoSSjlgdgFJDANJIoA5FB4CBwokUAcjwcRAcYgcbhceAOSgORAXJMByXByOA5dA8kwOXwA=="

# Program info
CMR = "265e843c32c4c80bc53704829fbbe43e8efc411360dab659cd7001e560d58f1d"
VAULT_ADDRESS = "tex1pewrql3qrpzg5gc3ftdkhynz4mkmuaz7hj5ycdnwndl5jlhkxrd0qzygxjt"
TIMELOCK_HEIGHT = 2256000

# Fixed values
ASSET = "144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"
INTERNAL_KEY = "50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"

# Delegate keys (Bob)
DELEGATE_SECRET = "0f88f360602b68e02983c2e62a1cbd0e0d71a50f778f886abd1ccc3bc8b3ac9b"
DELEGATE_PUBKEY = "8577f4e053850a2eb0c86ce4c81215fdec681c28e01648f4401e0c47a4276413"

# Output configuration
RECIPIENT = "tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"
FEE_BTC = "0.00001"      # 1000 sats
CHANGE_BTC = "0.00098"   # 98000 sats (leaving room for OP_RETURN output)

# SAID Protocol OP_RETURN payload (type=0x02 for delegation attestation)
SAID_PAYLOAD = "534149440102cafebabe12345678cafebabe12345678cafebabe12345678cafebabe12345678"


def run_hal(args):
    """Run hal-simplicity command and return output."""
    cmd = [HAL] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"hal command failed: {result.stderr}")
    return result.stdout.strip()


def get_current_height():
    """Get current Liquid Testnet block height."""
    resp = requests.get("https://blockstream.info/liquidtestnet/api/blocks/tip/height")
    return int(resp.text)


def create_delegate_witness(signature_bytes):
    """
    Create witness for Right (Delegate) path.
    Right(sig) = bit 1 + 512 sig bits + 7 padding bits = 65 bytes
    """
    sig_bits = ''.join(format(b, '08b') for b in signature_bytes)
    witness_bits = '1' + sig_bits + '0000000'  # Right tag (1) + sig + padding
    witness_bytes = bytes(int(witness_bits[i:i+8], 2) for i in range(0, len(witness_bits), 8))
    return witness_bytes.hex()


def main():
    print("=" * 60)
    print("DELEGATION VAULT - Delegate Spend Test")
    print("=" * 60)
    print()

    # Check current height
    current_height = get_current_height()
    blocks_remaining = TIMELOCK_HEIGHT - current_height

    print(f"Current block height: {current_height}")
    print(f"Timelock height: {TIMELOCK_HEIGHT}")

    if blocks_remaining > 0:
        print(f"Blocks remaining: {blocks_remaining} (~{blocks_remaining}min)")
        print()
        print("WARNING: Timelock not yet reached!")
        print("The delegate spend will FAIL until block", TIMELOCK_HEIGHT)
        proceed = input("Continue anyway for testing? (y/n) ").lower()
        if proceed != 'y':
            return
    else:
        print("Timelock PASSED!")

    print()
    print(f"Vault Address: {VAULT_ADDRESS}")
    print(f"UTXO: {UTXO_TXID}:{UTXO_VOUT}")
    print()

    # Step 1: Get script_pubkey
    print("=== Step 1: Get UTXO script_pubkey ===")
    utxo_resp = requests.get(f"https://blockstream.info/liquidtestnet/api/tx/{UTXO_TXID}")
    utxo_info = utxo_resp.json()
    script_pubkey = utxo_info["vout"][UTXO_VOUT]["scriptpubkey"]
    print(f"Script pubkey: {script_pubkey}")

    # Step 2: Create PSET with OP_RETURN
    print()
    print("=== Step 2: Create PSET with OP_RETURN ===")

    inputs_json = json.dumps([{"txid": UTXO_TXID, "vout": UTXO_VOUT}])
    outputs_json = json.dumps([
        {"address": RECIPIENT, "asset": ASSET, "amount": float(CHANGE_BTC)},
        {"address": f"data:{SAID_PAYLOAD}", "asset": ASSET, "amount": 0},
        {"address": "fee", "asset": ASSET, "amount": float(FEE_BTC)}
    ])

    pset_output = run_hal(["simplicity", "pset", "create", "--liquid", inputs_json, outputs_json])
    pset_json = json.loads(pset_output)
    pset = pset_json["pset"]
    print(f"PSET created: {pset[:50]}...")

    # Step 3: Update input
    print()
    print("=== Step 3: Update input ===")

    input_utxo = f"{script_pubkey}:{ASSET}:{UTXO_VALUE_BTC}"
    pset2_output = run_hal([
        "simplicity", "pset", "update-input", "--liquid", pset, "0",
        "--input-utxo", input_utxo,
        "--cmr", CMR,
        "--internal-key", INTERNAL_KEY
    ])
    pset2_json = json.loads(pset2_output)
    pset2 = pset2_json["pset"]
    print("PSET updated with input info")

    # Step 4: Get sig_all_hash with dummy witness
    print()
    print("=== Step 4: Get sig_all_hash ===")

    # Dummy witness for Right path: 1 bit + 512 zero bits + 7 padding = 65 bytes
    dummy_witness = "80" + "00" * 64  # 0x80 = 10000000 in binary (Right tag)

    run_output = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", PROGRAM, dummy_witness])
    run_json = json.loads(run_output)

    sig_all_hash = None
    for jet in run_json.get("jets", []):
        if jet["jet"] == "sig_all_hash":
            sig_all_hash = jet["output_value"].replace("0x", "")
            break

    if not sig_all_hash:
        print("ERROR: Could not extract sig_all_hash")
        print(run_output)
        return

    print(f"sig_all_hash: {sig_all_hash}")

    # Step 5: Sign with Delegate key
    print()
    print("=== Step 5: Sign with Delegate key ===")

    privkey = ec.PrivateKey(bytes.fromhex(DELEGATE_SECRET))
    signature = privkey.schnorr_sign(bytes.fromhex(sig_all_hash))
    sig_bytes = signature.serialize()
    print(f"Signature: {sig_bytes.hex()}")

    # Create delegate witness (Right path)
    delegate_witness = create_delegate_witness(sig_bytes)
    print(f"Delegate witness: {delegate_witness}")

    # Step 6: Verify
    print()
    print("=== Step 6: Verify signature ===")

    run_output = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", PROGRAM, delegate_witness])
    run_json = json.loads(run_output)
    success = run_json.get("success", False)

    print(f"Overall success: {success}")
    print("Jet results:")
    for jet in run_json.get("jets", []):
        jet_success = jet.get("success", "N/A")
        print(f"  {jet['jet']}: success={jet_success}")

    if not success:
        print()
        print("Verification FAILED (expected if timelock not reached)")

        # Check which condition failed
        for jet in run_json.get("jets", []):
            if jet["jet"] == "check_lock_height" and not jet.get("success", True):
                print(f">>> Timelock check failed - current height {current_height} < {TIMELOCK_HEIGHT}")
            if jet["jet"] == "output_null_datum" and not jet.get("success", True):
                print(">>> OP_RETURN check failed")
        return

    # Step 7: Finalize
    print()
    print("=== Step 7: Finalize PSET ===")

    final_output = run_hal(["simplicity", "pset", "finalize", "--liquid", pset2, "0", PROGRAM, delegate_witness])
    final_json = json.loads(final_output)
    final_pset = final_json["pset"]
    print("PSET finalized")

    # Step 8: Extract
    print()
    print("=== Step 8: Extract transaction ===")

    tx_hex = run_hal(["simplicity", "pset", "extract", "--liquid", final_pset])
    tx_hex = tx_hex.strip('"')
    print(f"Transaction hex length: {len(tx_hex)}")

    # Step 9: Broadcast
    print()
    print("=== Step 9: Broadcast ===")
    print("Transaction hex:")
    print(tx_hex[:100] + "...")
    print()

    broadcast = input("Broadcast transaction? (y/n) ").lower()
    if broadcast == 'y':
        resp = requests.post(
            "https://blockstream.info/liquidtestnet/api/tx",
            headers={"Content-Type": "text/plain"},
            data=tx_hex
        )
        result = resp.text
        print(f"Broadcast result: {result}")

        if len(result) == 64 and all(c in '0123456789abcdef' for c in result):
            print()
            print("=" * 60)
            print("*** DELEGATE SPEND SUCCESS! ***")
            print("=" * 60)
            print(f"TXID: {result}")
            print(f"Explorer: https://blockstream.info/liquidtestnet/tx/{result}")
    else:
        print("Broadcast skipped.")


if __name__ == "__main__":
    main()
