#!/usr/bin/env python3
"""
VAULT V3 - Certificate Emission Test

Vault v3 has 3 spending paths:
  1. Admin Unconditional (Left) - Can drain vault
  2. Admin Issue Certificate (Right-Left) - Admin emits with covenants
  3. Delegate Issue Certificate (Right-Right) - Delegate emits with covenants

Usage:
    python test_vault_v3_emit.py --admin-unconditional  # Drain vault
    python test_vault_v3_emit.py --admin-issue          # Admin emits certificate
    python test_vault_v3_emit.py --delegate-issue       # Delegate emits certificate
"""

import subprocess
import json
import requests
import sys
from embit import ec

# Configuration
HAL = "/tmp/hal-simplicity-new/target/release/hal-simplicity"

# Vault v3 info
VAULT_V3_PROGRAM = "5wXQKEGJtN5gn38JDZrjk4Yg5zHtW7RGAZNixi+vDo15i+CoHlaiggTFBh9AoTwEIFB9BtQoPqFGxgISKD8KBANgHAgnAgMQcJA4cQYgUG4kT8MQQJxUgxNkAAAACAgWDNuIIwCPhwQGkgUJsgAAAAAEfDUCEChBiBQlQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACDcfnHG5BCjNugEAcLDpA2k2kAwIh2DXnooOXhFRPJ7/G404jHA8jbuSHGx6nuNx/8CgQJwJNkAAAAAggDhiBQbhaBQkDhR+DHG5NCgDhAHGQcwNRNkAAAABAgTekDjNAoNyFONyHFHw1ghAoQYgUJA44QYgUJA4+SGAYkigDleHaBwAmyAAAAAwR8NgIE4OgxAoSBySQYBynDgBmSKAOYUG8LgwDmIBxYBxqBx0Fx+A5jQcjgOSoXJoBzIg5WgctQuXQDmVBzDAc1oTmSA5mQcxy0wrv6cCnChRdYZDZyZAkK/vY0DhRwCyR6IA8GI9ITsgmDmyCc2oHMyLQA5oAcyoOgDmYB5nQOb4A="
VAULT_V3_CMR = "f5f369b46047361c7d7803e20e8cbaf4252adea7f9030fc7dba3d3788aa3f688"
VAULT_V3_ADDRESS = "tex1pjycx6hckqcujafu6rqydr5p4k6xzqzxtq3vpj4sjjn75r3z46dyq3pvtvd"

# We need to calculate the script_pubkey from the address
# Address: tex1pjycx6hckqcujafu6rqydr5p4k6xzqzxtq3vpj4sjjn75r3z46dyq3pvtvd
# This is a P2TR address, so scriptPubKey = 5120 + <32-byte tweaked pubkey>
# For now, let's derive it from the address using Python

def bech32m_decode(addr):
    """Decode bech32m address to get the witness program."""
    CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"

    # Remove prefix
    if addr.startswith("tex1p"):
        data_part = addr[5:]
    elif addr.startswith("ex1p"):
        data_part = addr[4:]
    else:
        raise ValueError("Unknown prefix")

    # Decode characters
    values = [CHARSET.index(c) for c in data_part]

    # Remove checksum (last 6 chars)
    values = values[:-6]

    # Convert from 5-bit to 8-bit
    acc = 0
    bits = 0
    result = []
    for v in values:
        acc = (acc << 5) | v
        bits += 5
        while bits >= 8:
            bits -= 8
            result.append((acc >> bits) & 0xff)

    return bytes(result)

# Derive script_pubkey
witness_program = bech32m_decode(VAULT_V3_ADDRESS)
VAULT_V3_SCRIPT_PUBKEY = "5120" + witness_program.hex()

# Certificate v2 info (same as before)
CERT_ADDRESS = "tex1pfeaa7eex2cxa923tehj5vd0emf779fp8v968mcx9uymm6q3gze6s8cvkka"

# Fixed values
ASSET = "144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"
INTERNAL_KEY = "50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"

# Keys
ADMIN_SECRET = "c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"
DELEGATE_SECRET = "0f88f360602b68e02983c2e62a1cbd0e0d71a50f778f886abd1ccc3bc8b3ac9b"

SAID_PAYLOAD = "534149440103a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"


def run_hal(args):
    """Run hal-simplicity command and return output."""
    cmd = [HAL] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.stderr
    return result.stdout.strip(), None


def create_witness_admin_unconditional(signature_bytes):
    """
    Create witness for Admin Unconditional (Left path).
    Either<Sig, Either<Sig, Sig>>
    Left(sig) = 0 + sig(512 bits) + 7 padding = 65 bytes
    """
    sig_bits = ''.join(format(b, '08b') for b in signature_bytes)
    # Left tag (0) + signature + padding
    witness_bits = '0' + sig_bits + '0000000'
    witness_bytes = bytes(int(witness_bits[i:i+8], 2) for i in range(0, len(witness_bits), 8))
    return witness_bytes.hex()


def create_witness_admin_issue(signature_bytes):
    """
    Create witness for Admin Issue Certificate (Right-Left path).
    Either<Sig, Either<Sig, Sig>>
    Right(Left(sig)) = 1 + 0 + sig(512 bits) + 6 padding = 65 bytes
    """
    sig_bits = ''.join(format(b, '08b') for b in signature_bytes)
    # Right tag (1) + Left tag (0) + signature + padding
    witness_bits = '10' + sig_bits + '000000'
    witness_bytes = bytes(int(witness_bits[i:i+8], 2) for i in range(0, len(witness_bits), 8))
    return witness_bytes.hex()


def create_witness_delegate_issue(signature_bytes):
    """
    Create witness for Delegate Issue Certificate (Right-Right path).
    Either<Sig, Either<Sig, Sig>>
    Right(Right(sig)) = 1 + 1 + sig(512 bits) + 6 padding = 65 bytes
    """
    sig_bits = ''.join(format(b, '08b') for b in signature_bytes)
    # Right tag (1) + Right tag (1) + signature + padding
    witness_bits = '11' + sig_bits + '000000'
    witness_bytes = bytes(int(witness_bits[i:i+8], 2) for i in range(0, len(witness_bits), 8))
    return witness_bytes.hex()


def sats_to_btc(sats):
    return f"{sats / 100_000_000:.8f}"


def get_vault_utxos():
    """Get all UTXOs for vault_v3 address."""
    resp = requests.get(f"https://blockstream.info/liquidtestnet/api/address/{VAULT_V3_ADDRESS}/utxo")
    if resp.status_code != 200:
        return []
    return resp.json()


def main():
    # Parse arguments
    admin_unconditional = "--admin-unconditional" in sys.argv
    admin_issue = "--admin-issue" in sys.argv
    delegate_issue = "--delegate-issue" in sys.argv

    if not any([admin_unconditional, admin_issue, delegate_issue]):
        print("Usage:")
        print("  python test_vault_v3_emit.py --admin-unconditional  # Drain vault")
        print("  python test_vault_v3_emit.py --admin-issue          # Admin emits certificate")
        print("  python test_vault_v3_emit.py --delegate-issue       # Delegate emits certificate")
        return

    if admin_unconditional:
        mode = "Admin Unconditional"
        create_witness = create_witness_admin_unconditional
        secret_key = ADMIN_SECRET
        needs_covenants = False
    elif admin_issue:
        mode = "Admin Issue Certificate"
        create_witness = create_witness_admin_issue
        secret_key = ADMIN_SECRET
        needs_covenants = True
    else:
        mode = "Delegate Issue Certificate"
        create_witness = create_witness_delegate_issue
        secret_key = DELEGATE_SECRET
        needs_covenants = True

    print("=" * 70)
    print(f"VAULT V3 - {mode}")
    print("=" * 70)
    print()
    print(f"Vault V3 Address: {VAULT_V3_ADDRESS}")
    print(f"Script Pubkey: {VAULT_V3_SCRIPT_PUBKEY}")
    print()

    # Get UTXOs
    utxos = get_vault_utxos()
    if not utxos:
        print("No UTXOs found. Please fund the vault first:")
        print(f"  Address: {VAULT_V3_ADDRESS}")
        print("  Faucet: https://liquidtestnet.com/faucet")
        return

    print(f"Found {len(utxos)} UTXO(s):")
    for i, utxo in enumerate(utxos):
        print(f"  [{i}] {utxo['txid']}:{utxo['vout']} = {utxo['value']} sats")

    selected = utxos[0]
    utxo_txid = selected["txid"]
    utxo_vout = selected["vout"]
    utxo_value = selected["value"]

    print()
    print(f"Using UTXO: {utxo_txid}:{utxo_vout} ({utxo_value} sats)")
    print()

    # Calculate outputs
    FEE_SATS = 500

    if needs_covenants:
        # Certificate emission - 4 outputs required
        CERT_SATS = 546
        troco_sats = utxo_value - FEE_SATS - CERT_SATS

        if troco_sats < 546:
            print("ERROR: UTXO value too small for certificate emission")
            return

        print("=== Output Plan (Certificate Emission) ===")
        print(f"  Output 0 (Troco to Vault): {troco_sats} sats")
        print(f"  Output 1 (Certificate):   {CERT_SATS} sats")
        print(f"  Output 2 (OP_RETURN):     0 sats")
        print(f"  Output 3 (Fee):           {FEE_SATS} sats")

        inputs_json = json.dumps([{"txid": utxo_txid, "vout": utxo_vout}])
        outputs_json = json.dumps([
            {"address": VAULT_V3_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(troco_sats))},
            {"address": CERT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(CERT_SATS))},
            {"address": f"data:{SAID_PAYLOAD}", "asset": ASSET, "amount": 0},
            {"address": "fee", "asset": ASSET, "amount": float(sats_to_btc(FEE_SATS))}
        ])
    else:
        # Admin unconditional - simple spend
        output_sats = utxo_value - FEE_SATS
        recipient = "tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"

        print("=== Output Plan (Unconditional Spend) ===")
        print(f"  Output 0 (Recipient): {output_sats} sats")
        print(f"  Output 1 (Fee):       {FEE_SATS} sats")

        inputs_json = json.dumps([{"txid": utxo_txid, "vout": utxo_vout}])
        outputs_json = json.dumps([
            {"address": recipient, "asset": ASSET, "amount": float(sats_to_btc(output_sats))},
            {"address": "fee", "asset": ASSET, "amount": float(sats_to_btc(FEE_SATS))}
        ])

    print()

    # Create PSET
    print("=== Step 1: Create PSET ===")
    pset_out, err = run_hal(["simplicity", "pset", "create", "--liquid", inputs_json, outputs_json])
    if err:
        print(f"ERROR: {err}")
        return
    pset = json.loads(pset_out)["pset"]
    print(f"PSET created: {pset[:60]}...")

    # Update input
    print()
    print("=== Step 2: Update input ===")
    input_utxo = f"{VAULT_V3_SCRIPT_PUBKEY}:{ASSET}:{sats_to_btc(utxo_value)}"
    pset2_out, err = run_hal([
        "simplicity", "pset", "update-input", "--liquid", pset, "0",
        "--input-utxo", input_utxo,
        "--cmr", VAULT_V3_CMR,
        "--internal-key", INTERNAL_KEY
    ])
    if err:
        print(f"ERROR: {err}")
        return
    pset2 = json.loads(pset2_out)["pset"]
    print("PSET updated")

    # Get sig_all_hash with dummy witness
    print()
    print("=== Step 3: Get sig_all_hash ===")

    # Create appropriate dummy witness based on path
    if admin_unconditional:
        dummy_witness = "00" + "00" * 64  # Left path
    elif admin_issue:
        dummy_witness = "80" + "00" * 64  # Right-Left (0x80 = 10000000)
    else:
        dummy_witness = "c0" + "00" * 64  # Right-Right (0xC0 = 11000000)

    run_out, err = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", VAULT_V3_PROGRAM, dummy_witness])
    if err:
        print(f"ERROR: {err}")
        return

    run_json = json.loads(run_out)
    sig_all_hash = None
    for jet in run_json.get("jets", []):
        if jet["jet"] == "sig_all_hash":
            sig_all_hash = jet["output_value"].replace("0x", "")
            break

    if not sig_all_hash:
        print("ERROR: Could not extract sig_all_hash")
        print("Jets:", [j["jet"] for j in run_json.get("jets", [])])
        return

    print(f"sig_all_hash: {sig_all_hash}")

    # Sign
    print()
    print(f"=== Step 4: Sign with {'Admin' if secret_key == ADMIN_SECRET else 'Delegate'} key ===")
    privkey = ec.PrivateKey(bytes.fromhex(secret_key))
    signature = privkey.schnorr_sign(bytes.fromhex(sig_all_hash))
    witness = create_witness(signature.serialize())
    print(f"Witness: {witness[:40]}...")

    # Verify
    print()
    print("=== Step 5: Verify ===")
    run_out, err = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", VAULT_V3_PROGRAM, witness])
    if err:
        print(f"ERROR: {err}")
        return

    run_json = json.loads(run_out)
    success = run_json.get("success", False)

    print(f"Verification: {'SUCCESS' if success else 'FAILED'}")

    if not success:
        print("Failed jets:")
        for jet in run_json.get("jets", []):
            if not jet.get("success", True):
                print(f"  - {jet['jet']}")
        return

    # Finalize and extract
    print()
    print("=== Step 6: Finalize ===")
    final_out, err = run_hal(["simplicity", "pset", "finalize", "--liquid", pset2, "0", VAULT_V3_PROGRAM, witness])
    if err:
        print(f"ERROR: {err}")
        return
    final_pset = json.loads(final_out)["pset"]
    print("PSET finalized")

    print()
    print("=== Step 7: Extract ===")
    tx_hex, err = run_hal(["simplicity", "pset", "extract", "--liquid", final_pset])
    if err:
        print(f"ERROR: {err}")
        return
    tx_hex = tx_hex.strip('"')
    print(f"Transaction hex length: {len(tx_hex)}")

    # Broadcast
    print()
    print("=== Step 8: Broadcast ===")
    broadcast = input("Broadcast transaction? (y/n) ").lower()
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
            print(f"*** {mode.upper()} SUCCESS! ***")
            print("=" * 70)
            print()
            print(f"TXID: {result}")
            print(f"Explorer: https://blockstream.info/liquidtestnet/tx/{result}")

            if needs_covenants:
                print()
                print("Certificate UTXO created at output 1")
                print(f"Certificate Address: {CERT_ADDRESS}")
        else:
            print(f"Broadcast failed: {result}")
    else:
        print("Broadcast skipped.")


if __name__ == "__main__":
    main()
