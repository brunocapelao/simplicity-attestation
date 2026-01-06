#!/usr/bin/env python3
"""
SAP - Certificate Revocation Test

This script tests revoking a certificate by spending the certificate UTXO.
Both Admin and Delegate can revoke certificates.

The certificate is REVOKED when its UTXO is spent.

Usage:
    python test_certificate_revoke.py --admin    # Revoke with Admin key
    python test_certificate_revoke.py --delegate # Revoke with Delegate key

Before running:
    1. First emit a certificate using test_emit.py
    2. The script will find certificate UTXOs automatically
"""

import subprocess
import json
import requests
import sys
from embit import ec

# Configuration
HAL = "/tmp/hal-simplicity-new/target/release/hal-simplicity"

# Certificate v2 compiled program (from secrets.json)
CERT_PROGRAM = "46TabzBPv4SGzXHJwxBzmPat2iMAybFjF9eHRrzF8FQPK1FBCBQm0wrv6cCnChRdYZDZyZAkK/vY0DhRwCyR6IA8GI9ITsgmCECh0ChBhxyDBUkgScOZxVEJFdCZgAirhYMXhSwnsDCoXWEv1xUjIWWHAK278AQwDEgUJINwM43BRQfgZwqFobGHNddy8HoTqejIHGcv8bcleUZT57KmW1Vp7LXaMUR4qMQ4YBiE3n4rBAOBgcOG4lOE4iAxDiBxWBxeBxqA"

# Certificate v2 info
CERT_CMR = "5ab59e0758d47c302f04546d1c56b454b1bbbbc852d20d9e471497bfc8713955"
CERT_ADDRESS = "tex1pfeaa7eex2cxa923tehj5vd0emf779fp8v968mcx9uymm6q3gze6s8cvkka"
CERT_SCRIPT_PUBKEY = "51204e7bdf6726560dd2aa2bcde54635f9da7de2a42761747de0c5e137bd02281675"

# Fixed values
ASSET = "144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"
INTERNAL_KEY = "50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"

# Admin keys (Alice)
ADMIN_SECRET = "c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"
ADMIN_PUBKEY = "bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45"

# Delegate keys (Bob)
DELEGATE_SECRET = "0f88f360602b68e02983c2e62a1cbd0e0d71a50f778f886abd1ccc3bc8b3ac9b"
DELEGATE_PUBKEY = "8577f4e053850a2eb0c86ce4c81215fdec681c28e01648f4401e0c47a4276413"

# Recipient for revocation output (can be any address)
RECIPIENT = "tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"


def run_hal(args):
    """Run hal-simplicity command and return output."""
    cmd = [HAL] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"hal command failed: {result.stderr}\nstdout: {result.stdout}")
    return result.stdout.strip()


def get_certificate_utxos():
    """Get all UTXOs for certificate_v2 address."""
    resp = requests.get(f"https://blockstream.info/liquidtestnet/api/address/{CERT_ADDRESS}/utxo")
    if resp.status_code != 200:
        return []
    return resp.json()


def create_admin_witness(signature_bytes):
    """
    Create witness for Left (Admin) path.
    Left(sig) = bit 0 + 512 sig bits + 7 padding bits = 65 bytes
    """
    sig_bits = ''.join(format(b, '08b') for b in signature_bytes)
    witness_bits = '0' + sig_bits + '0000000'  # Left tag (0) + sig + padding
    witness_bytes = bytes(int(witness_bits[i:i+8], 2) for i in range(0, len(witness_bits), 8))
    return witness_bytes.hex()


def create_delegate_witness(signature_bytes):
    """
    Create witness for Right (Delegate) path.
    Right(sig) = bit 1 + 512 sig bits + 7 padding bits = 65 bytes
    """
    sig_bits = ''.join(format(b, '08b') for b in signature_bytes)
    witness_bits = '1' + sig_bits + '0000000'  # Right tag (1) + sig + padding
    witness_bytes = bytes(int(witness_bits[i:i+8], 2) for i in range(0, len(witness_bits), 8))
    return witness_bytes.hex()


def sats_to_btc(sats):
    """Convert satoshis to BTC string."""
    return f"{sats / 100_000_000:.8f}"


def main():
    # Parse arguments
    use_admin = "--admin" in sys.argv
    use_delegate = "--delegate" in sys.argv

    if not use_admin and not use_delegate:
        print("Usage: python test_certificate_revoke.py --admin|--delegate")
        print()
        print("  --admin    Revoke certificate with Admin (Alice) key")
        print("  --delegate Revoke certificate with Delegate (Bob) key")
        return

    signer_name = "Admin (Alice)" if use_admin else "Delegate (Bob)"
    signer_secret = ADMIN_SECRET if use_admin else DELEGATE_SECRET
    create_witness = create_admin_witness if use_admin else create_delegate_witness

    print("=" * 70)
    print(f"CERTIFICATE REVOCATION - Using {signer_name}")
    print("=" * 70)
    print()

    # Check for available certificate UTXOs
    print("=== Checking for certificate UTXOs ===")
    utxos = get_certificate_utxos()

    if not utxos:
        print(f"No certificate UTXOs found at: {CERT_ADDRESS}")
        print()
        print("First emit a certificate using test_emit.py")
        return

    print(f"Found {len(utxos)} certificate UTXO(s):")
    for i, utxo in enumerate(utxos):
        print(f"  [{i}] {utxo['txid']}:{utxo['vout']} = {utxo['value']} sats")

    # Select UTXO
    if len(utxos) == 1:
        selected = utxos[0]
    else:
        idx = int(input("\nSelect certificate UTXO to revoke: "))
        selected = utxos[idx]

    utxo_txid = selected["txid"]
    utxo_vout = selected["vout"]
    utxo_value_sats = selected["value"]

    print()
    print(f"Revoking certificate: {utxo_txid}:{utxo_vout}")
    print(f"Value: {utxo_value_sats} sats")
    print()

    # Calculate outputs
    FEE_SATS = 300
    output_sats = utxo_value_sats - FEE_SATS

    if output_sats < 546:
        # If value too small, just burn as fee
        FEE_SATS = utxo_value_sats
        output_sats = 0
        print(f"Certificate value too small, burning as fee: {FEE_SATS} sats")
    else:
        print(f"Output: {output_sats} sats to {RECIPIENT}")
        print(f"Fee: {FEE_SATS} sats")

    # Step 1: Create PSET
    print()
    print("=== Step 1: Create PSET ===")

    inputs_json = json.dumps([{"txid": utxo_txid, "vout": utxo_vout}])

    if output_sats > 0:
        outputs_json = json.dumps([
            {"address": RECIPIENT, "asset": ASSET, "amount": float(sats_to_btc(output_sats))},
            {"address": "fee", "asset": ASSET, "amount": float(sats_to_btc(FEE_SATS))}
        ])
    else:
        outputs_json = json.dumps([
            {"address": "fee", "asset": ASSET, "amount": float(sats_to_btc(FEE_SATS))}
        ])

    pset_output = run_hal(["simplicity", "pset", "create", "--liquid", inputs_json, outputs_json])
    pset_json = json.loads(pset_output)
    pset = pset_json["pset"]
    print(f"PSET created: {pset[:60]}...")

    # Step 2: Update input
    print()
    print("=== Step 2: Update input ===")

    input_utxo = f"{CERT_SCRIPT_PUBKEY}:{ASSET}:{sats_to_btc(utxo_value_sats)}"
    pset2_output = run_hal([
        "simplicity", "pset", "update-input", "--liquid", pset, "0",
        "--input-utxo", input_utxo,
        "--cmr", CERT_CMR,
        "--internal-key", INTERNAL_KEY
    ])
    pset2_json = json.loads(pset2_output)
    pset2 = pset2_json["pset"]
    print("PSET updated")

    # Step 3: Get sig_all_hash
    print()
    print("=== Step 3: Get sig_all_hash ===")

    # Dummy witness
    if use_admin:
        dummy_witness = "00" + "00" * 64  # Left (Admin)
    else:
        dummy_witness = "80" + "00" * 64  # Right (Delegate)

    run_output = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", CERT_PROGRAM, dummy_witness])
    run_json = json.loads(run_output)

    sig_all_hash = None
    for jet in run_json.get("jets", []):
        if jet["jet"] == "sig_all_hash":
            sig_all_hash = jet["output_value"].replace("0x", "")
            break

    if not sig_all_hash:
        print("ERROR: Could not extract sig_all_hash")
        return

    print(f"sig_all_hash: {sig_all_hash}")

    # Step 4: Sign
    print()
    print(f"=== Step 4: Sign with {signer_name} key ===")

    privkey = ec.PrivateKey(bytes.fromhex(signer_secret))
    signature = privkey.schnorr_sign(bytes.fromhex(sig_all_hash))
    sig_bytes = signature.serialize()
    print(f"Signature: {sig_bytes.hex()}")

    witness = create_witness(sig_bytes)
    print(f"Witness: {witness[:40]}...")

    # Step 5: Verify
    print()
    print("=== Step 5: Verify ===")

    run_output = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", CERT_PROGRAM, witness])
    run_json = json.loads(run_output)
    success = run_json.get("success", False)

    print(f"Verification: {'SUCCESS' if success else 'FAILED'}")

    if not success:
        print("Jet results:")
        for jet in run_json.get("jets", []):
            print(f"  {jet['jet']}: success={jet.get('success', 'N/A')}")
        return

    # Step 6: Finalize
    print()
    print("=== Step 6: Finalize ===")

    final_output = run_hal(["simplicity", "pset", "finalize", "--liquid", pset2, "0", CERT_PROGRAM, witness])
    final_json = json.loads(final_output)
    final_pset = final_json["pset"]
    print("PSET finalized")

    # Step 7: Extract
    print()
    print("=== Step 7: Extract transaction ===")

    tx_hex = run_hal(["simplicity", "pset", "extract", "--liquid", final_pset])
    tx_hex = tx_hex.strip('"')
    print(f"Transaction hex length: {len(tx_hex)} chars")

    # Step 8: Broadcast
    print()
    print("=== Step 8: Ready to broadcast ===")
    print()
    print("This will REVOKE the certificate by spending its UTXO!")
    print()

    broadcast = input("Broadcast revocation? (y/n) ").lower()
    if broadcast == 'y':
        resp = requests.post(
            "https://blockstream.info/liquidtestnet/api/tx",
            headers={"Content-Type": "text/plain"},
            data=tx_hex
        )
        result = resp.text

        if len(result) == 64 and all(c in '0123456789abcdef' for c in result):
            print()
            print("=" * 70)
            print("*** CERTIFICATE REVOKED! ***")
            print("=" * 70)
            print()
            print(f"Revocation TXID: {result}")
            print(f"Explorer: https://blockstream.info/liquidtestnet/tx/{result}")
            print()
            print(f"Certificate {utxo_txid}:{utxo_vout} is now INVALID")
            print(f"Revoked by: {signer_name}")
        else:
            print(f"Broadcast failed: {result}")
    else:
        print("Broadcast skipped.")
        print()
        print("Transaction hex (for manual broadcast):")
        print(tx_hex)


if __name__ == "__main__":
    main()
