#!/usr/bin/env python3
"""
VAULT V2 - Delegate Certificate Emission Test

This script tests the Delegate (Bob) certificate emission from vault_v2.
Delegate path requires:
  1. Valid signature
  2. Exactly 4 outputs
  3. Output 0 (troco) goes to vault_v2 (self-reference enforced by covenant)
  4. Output 1 (certificate) goes to certificate_v2 address
  5. Output 2 contains OP_RETURN with data
  6. Output 3 is fee output

Usage:
    python test_vault_v2_emit.py

Before running:
    1. Fund vault_v2 address via https://liquidtestnet.com/faucet
    2. Update UTXO_TXID and UTXO_VOUT with the funding transaction
"""

import subprocess
import json
import requests
from embit import ec

# Configuration
HAL = "/tmp/hal-simplicity-new/target/release/hal-simplicity"

# === UPDATE THESE VALUES BEFORE RUNNING ===
UTXO_TXID = ""  # Update with actual UTXO txid
UTXO_VOUT = 0
UTXO_VALUE_SATS = 100000  # Update with actual value in satoshis
# ==========================================

# Vault v2 compiled program (from secrets.json)
VAULT_PROGRAM = "6Bx0ChBibTeYJ9/CQ2a45OGIOcx7Vu0RgGTYsYvrw6NeYvgqB5WooIExQYfQKEkCThzOKohIroTMAEVcLBi8KWE9gYVC6wl+uKkZCyw4BW3fgCGAYkChJB95uAig/ARQLJsYc113LwehOp6MgcZy/xtyV5RlPnsqZbVWnstdoxRHioxDhgGITafiQEA4CBwwJwwDEHEYHFAnFAnFPwxOYF3vtQo+60Po4ukCQ0VtLxJhSxmV3EYSgDejbdP5dgAwwDEJxikhBlkAAAACAxCoWTNuJzPwVWs2QTLHYGP5UtFmHGH7DUSVZobR0Jn/z1azRDnuMGAYhbGDmCIv9QHGkTTAYXN78l9PRKwkaP7L+QgG2hgCZadW734oMAxC4FwP4cEObxOhhI4BnviN4uejwVYdGCizvg8pDe+f7r9U2pQklHLAwDEgUJIsgAAAAAFCr4ajm7yVnAtI8+S8yl59PzZ/zkJz3syU4qvsOOiPsQAebHRMMAxIFCDEChJAkUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHNoIdBYp6q5KhBFsqP1kw1Q0/1NmyUvYAJjylwJh4AskwYBiSQblCccblIKBZM26Dm2lWdqdI4MIvl0AcbRhlhcvv8aEsogMPZlhHFbihtOV8MAxC2G+hBP3N4n8lKDXNWc5D51IOoGdxv4z3M+5PnkVShbIQcPGYFB4EBwsm0gGBEOwa89FBy8IqJ5Pf43GnEY4HkbdyQ42PU9xuP/gUCBOILIAAAABBwgLhBpfUrjPo6am4SMqOQVAyrOdwjFyUX8dPWnCyLNYfpe9LDxaBSBQbitAoSQJGBl1ZEAS/2+THhcVojCPmayqj9hAYmv02lB1nFEjYADgPFQFJIPxKcbmLFAsTBi6VBevQW78EBaALmPstZ4ECX6kj2m31kWfStxdo3UWHicChaTSoNzoMc1Ae/7Z55CGHj0gOG/ZVBjb5kbDqY2kAJh07WHkwBQd4HBibIAAAACBAnC0gck0ChJBuWZxuWooFi+Gs5jBbZzwv8YiOVW/VsGSBnM4usfNJuBkKmLBi5jygFqsUDAMSBQgxAoSQJGyP1bXZ8fbYfc8F6bPlNwmZrTEAzLzw8LZOFjNOL3Sl0PJoCkGIFCSBIxsXX6Q/gR6bfNv+QIkq2TSNzaS+85toDfqr3uY18KY5B5SAUkMA0kigDmqDwEDhBJFkAAAABgoVfDYcxaVg5c7bCv5v4Efeky6pdqN8+a2UbNm+82P8XJkfgUkBgGITiRBiBQkgSNuPwXvzv9stXb3QFgqI0+EkTeqbTD8hwv1sedPf8PVoQeYECkkIMFTP9zPh4dh4ko0WrJyJQTlK2SXXo9RW3uqZeUTSraHl1AHmpAoOkDgBNphXf04FOFCi6wyGzkyBIV/exoHCjgFkj0QB4MR6QnZBMECcFNz2H58zjjjjjjjjhawHO0kUAc74OAhcGAc8QOLAuOAHPKDksBylA5VBcrwHPUDmKA5kwuZgBz3A5uQOcYLnPAc+QOeQDoFQee4DoGQ="

# Vault v2 info
VAULT_CMR = "0b816a7c013697d7d773fd79e7d85ab9b8d1d31ecc4d2298266edcad58b52e45"
VAULT_ADDRESS = "tex1pgrwxqqg00u3pgyt4gyfccav5x2vyz7h0u6y0ujqk3khf3mwcg8ashz9ymw"
VAULT_SCRIPT_PUBKEY = "512040dc60010f7f2214117541138c75943298417aefe688fe48168dae98edd841fb"

# Certificate v2 info
CERT_ADDRESS = "tex1pfeaa7eex2cxa923tehj5vd0emf779fp8v968mcx9uymm6q3gze6s8cvkka"

# Fixed values
ASSET = "144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"
INTERNAL_KEY = "50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"

# Delegate keys (Bob)
DELEGATE_SECRET = "0f88f360602b68e02983c2e62a1cbd0e0d71a50f778f886abd1ccc3bc8b3ac9b"
DELEGATE_PUBKEY = "8577f4e053850a2eb0c86ce4c81215fdec681c28e01648f4401e0c47a4276413"

# SAID Protocol OP_RETURN payload (type=0x03 for certificate)
# Format: SAID + version(01) + type(03) + certificate_hash(32 bytes)
SAID_PAYLOAD = "534149440103" + "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"


def run_hal(args):
    """Run hal-simplicity command and return output."""
    cmd = [HAL] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"hal command failed: {result.stderr}\nstdout: {result.stdout}")
    return result.stdout.strip()


def get_vault_utxos():
    """Get all UTXOs for vault_v2 address."""
    resp = requests.get(f"https://blockstream.info/liquidtestnet/api/address/{VAULT_ADDRESS}/utxo")
    if resp.status_code != 200:
        return []
    return resp.json()


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
    print("=" * 70)
    print("VAULT V2 - Delegate Certificate Emission Test")
    print("=" * 70)
    print()

    # Check for available UTXOs
    print("=== Checking for available UTXOs ===")
    utxos = get_vault_utxos()

    if not utxos:
        print(f"No UTXOs found at vault address: {VAULT_ADDRESS}")
        print()
        print("Please fund the vault address via:")
        print("  https://liquidtestnet.com/faucet")
        print()
        print("Then run this script again.")
        return

    print(f"Found {len(utxos)} UTXO(s):")
    for i, utxo in enumerate(utxos):
        print(f"  [{i}] {utxo['txid']}:{utxo['vout']} = {utxo['value']} sats")

    # Select UTXO
    if len(utxos) == 1:
        selected = utxos[0]
    else:
        idx = int(input("\nSelect UTXO index: "))
        selected = utxos[idx]

    utxo_txid = selected["txid"]
    utxo_vout = selected["vout"]
    utxo_value_sats = selected["value"]

    print()
    print(f"Using UTXO: {utxo_txid}:{utxo_vout}")
    print(f"Value: {utxo_value_sats} sats")
    print()

    # Calculate outputs
    # Fee: 500 sats (minimal for testnet)
    # Certificate: 546 sats (dust limit)
    # OP_RETURN: 0 sats
    # Troco: rest
    FEE_SATS = 500
    CERT_SATS = 546  # minimum for non-dust output

    troco_sats = utxo_value_sats - FEE_SATS - CERT_SATS

    if troco_sats < 546:
        print(f"ERROR: UTXO value too small. Need at least {FEE_SATS + CERT_SATS + 546} sats")
        return

    print("=== Output Plan ===")
    print(f"  Output 0 (Troco to Vault):    {troco_sats} sats")
    print(f"  Output 1 (Certificate):       {CERT_SATS} sats")
    print(f"  Output 2 (OP_RETURN):         0 sats")
    print(f"  Output 3 (Fee):               {FEE_SATS} sats")
    print(f"  Total:                        {troco_sats + CERT_SATS + FEE_SATS} sats")
    print()

    # Step 1: Create PSET with 4 outputs
    print("=== Step 1: Create PSET with 4 outputs ===")

    inputs_json = json.dumps([{"txid": utxo_txid, "vout": utxo_vout}])
    outputs_json = json.dumps([
        {"address": VAULT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(troco_sats))},
        {"address": CERT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(CERT_SATS))},
        {"address": f"data:{SAID_PAYLOAD}", "asset": ASSET, "amount": 0},
        {"address": "fee", "asset": ASSET, "amount": float(sats_to_btc(FEE_SATS))}
    ])

    print(f"Inputs: {inputs_json}")
    print(f"Outputs: {outputs_json[:100]}...")

    pset_output = run_hal(["simplicity", "pset", "create", "--liquid", inputs_json, outputs_json])
    pset_json = json.loads(pset_output)
    pset = pset_json["pset"]
    print(f"PSET created: {pset[:60]}...")

    # Step 2: Update input with UTXO info
    print()
    print("=== Step 2: Update input with UTXO info ===")

    input_utxo = f"{VAULT_SCRIPT_PUBKEY}:{ASSET}:{sats_to_btc(utxo_value_sats)}"
    pset2_output = run_hal([
        "simplicity", "pset", "update-input", "--liquid", pset, "0",
        "--input-utxo", input_utxo,
        "--cmr", VAULT_CMR,
        "--internal-key", INTERNAL_KEY
    ])
    pset2_json = json.loads(pset2_output)
    pset2 = pset2_json["pset"]
    print("PSET updated with input info")

    # Step 3: Get sig_all_hash with dummy witness
    print()
    print("=== Step 3: Get sig_all_hash ===")

    # Dummy witness for Right path: 1 bit + 512 zero bits + 7 padding = 65 bytes
    dummy_witness = "80" + "00" * 64  # 0x80 = 10000000 in binary (Right tag)

    run_output = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", VAULT_PROGRAM, dummy_witness])
    run_json = json.loads(run_output)

    sig_all_hash = None
    for jet in run_json.get("jets", []):
        if jet["jet"] == "sig_all_hash":
            sig_all_hash = jet["output_value"].replace("0x", "")
            break

    if not sig_all_hash:
        print("ERROR: Could not extract sig_all_hash")
        print("Full jet output:")
        for jet in run_json.get("jets", []):
            print(f"  {jet}")
        return

    print(f"sig_all_hash: {sig_all_hash}")

    # Step 4: Sign with Delegate key
    print()
    print("=== Step 4: Sign with Delegate key ===")

    privkey = ec.PrivateKey(bytes.fromhex(DELEGATE_SECRET))
    signature = privkey.schnorr_sign(bytes.fromhex(sig_all_hash))
    sig_bytes = signature.serialize()
    print(f"Signature: {sig_bytes.hex()}")

    # Create delegate witness (Right path)
    delegate_witness = create_delegate_witness(sig_bytes)
    print(f"Delegate witness: {delegate_witness[:40]}...")

    # Step 5: Verify with real signature
    print()
    print("=== Step 5: Verify signature and covenants ===")

    run_output = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", VAULT_PROGRAM, delegate_witness])
    run_json = json.loads(run_output)
    success = run_json.get("success", False)

    print(f"Overall success: {success}")
    print("Jet results:")
    for jet in run_json.get("jets", []):
        jet_success = jet.get("success", "N/A")
        jet_name = jet.get("jet", "unknown")
        print(f"  {jet_name}: success={jet_success}")

    if not success:
        print()
        print("=" * 70)
        print("VERIFICATION FAILED!")
        print("=" * 70)
        print()
        print("Possible causes:")
        print("  - Covenant violation (outputs don't match expected)")
        print("  - Signature invalid")
        print("  - Wrong number of outputs")
        print()
        print("Check the jet results above for details.")
        return

    # Step 6: Finalize PSET
    print()
    print("=== Step 6: Finalize PSET ===")

    final_output = run_hal(["simplicity", "pset", "finalize", "--liquid", pset2, "0", VAULT_PROGRAM, delegate_witness])
    final_json = json.loads(final_output)
    final_pset = final_json["pset"]
    print("PSET finalized")

    # Step 7: Extract transaction
    print()
    print("=== Step 7: Extract transaction ===")

    tx_hex = run_hal(["simplicity", "pset", "extract", "--liquid", final_pset])
    tx_hex = tx_hex.strip('"')
    print(f"Transaction hex length: {len(tx_hex)} chars")

    # Step 8: Broadcast
    print()
    print("=== Step 8: Ready to broadcast ===")
    print()
    print("Transaction details:")
    print(f"  Input: {utxo_txid}:{utxo_vout} ({utxo_value_sats} sats)")
    print(f"  Output 0: {VAULT_ADDRESS} ({troco_sats} sats) [TROCO]")
    print(f"  Output 1: {CERT_ADDRESS} ({CERT_SATS} sats) [CERTIFICATE]")
    print(f"  Output 2: OP_RETURN with SAID payload")
    print(f"  Output 3: Fee ({FEE_SATS} sats)")
    print()

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
            print("*** CERTIFICATE EMISSION SUCCESS! ***")
            print("=" * 70)
            print()
            print(f"TXID: {result}")
            print(f"Explorer: https://blockstream.info/liquidtestnet/tx/{result}")
            print()
            print("Certificate UTXO created at output 1")
            print(f"Certificate Address: {CERT_ADDRESS}")
            print()
            print("The certificate is now VALID.")
            print("To REVOKE: spend the certificate UTXO (output 1 of this tx)")
        else:
            print(f"Broadcast failed: {result}")
    else:
        print("Broadcast skipped.")
        print()
        print("Transaction hex (for manual broadcast):")
        print(tx_hex)


if __name__ == "__main__":
    main()
