#!/usr/bin/env python3
"""
SAP System - Edge Case Security Tests

This script tests various attack vectors and edge cases to verify
that the covenant enforcement is working correctly.

Tests:
1. Vault spend with WRONG key (random key) - should FAIL
2. Vault spend with wrong number of outputs (3 instead of 4) - should FAIL
3. Vault spend with wrong certificate destination - should FAIL
4. Vault spend without OP_RETURN - should FAIL
5. Vault spend with correct params - should SUCCEED
6. Certificate revocation with Admin key - should SUCCEED
7. Certificate revocation with random key - should FAIL
"""

import subprocess
import json
import requests
import os
from embit import ec

# Configuration
HAL = "/tmp/hal-simplicity-new/target/release/hal-simplicity"

# Vault v2 info
VAULT_PROGRAM = "6Bx0ChBibTeYJ9/CQ2a45OGIOcx7Vu0RgGTYsYvrw6NeYvgqB5WooIExQYfQKEkCThzOKohIroTMAEVcLBi8KWE9gYVC6wl+uKkZCyw4BW3fgCGAYkChJB95uAig/ARQLJsYc113LwehOp6MgcZy/xtyV5RlPnsqZbVWnstdoxRHioxDhgGITafiQEA4CBwwJwwDEHEYHFAnFAnFPwxOYF3vtQo+60Po4ukCQ0VtLxJhSxmV3EYSgDejbdP5dgAwwDEJxikhBlkAAAACAxCoWTNuJzPwVWs2QTLHYGP5UtFmHGH7DUSVZobR0Jn/z1azRDnuMGAYhbGDmCIv9QHGkTTAYXN78l9PRKwkaP7L+QgG2hgCZadW734oMAxC4FwP4cEObxOhhI4BnviN4uejwVYdGCizvg8pDe+f7r9U2pQklHLAwDEgUJIsgAAAAAFCr4ajm7yVnAtI8+S8yl59PzZ/zkJz3syU4qvsOOiPsQAebHRMMAxIFCDEChJAkUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHNoIdBYp6q5KhBFsqP1kw1Q0/1NmyUvYAJjylwJh4AskwYBiSQblCccblIKBZM26Dm2lWdqdI4MIvl0AcbRhlhcvv8aEsogMPZlhHFbihtOV8MAxC2G+hBP3N4n8lKDXNWc5D51IOoGdxv4z3M+5PnkVShbIQcPGYFB4EBwsm0gGBEOwa89FBy8IqJ5Pf43GnEY4HkbdyQ42PU9xuP/gUCBOILIAAAABBwgLhBpfUrjPo6am4SMqOQVAyrOdwjFyUX8dPWnCyLNYfpe9LDxaBSBQbitAoSQJGBl1ZEAS/2+THhcVojCPmayqj9hAYmv02lB1nFEjYADgPFQFJIPxKcbmLFAsTBi6VBevQW78EBaALmPstZ4ECX6kj2m31kWfStxdo3UWHicChaTSoNzoMc1Ae/7Z55CGHj0gOG/ZVBjb5kbDqY2kAJh07WHkwBQd4HBibIAAAACBAnC0gck0ChJBuWZxuWooFi+Gs5jBbZzwv8YiOVW/VsGSBnM4usfNJuBkKmLBi5jygFqsUDAMSBQgxAoSQJGyP1bXZ8fbYfc8F6bPlNwmZrTEAzLzw8LZOFjNOL3Sl0PJoCkGIFCSBIxsXX6Q/gR6bfNv+QIkq2TSNzaS+85toDfqr3uY18KY5B5SAUkMA0kigDmqDwEDhBJFkAAAABgoVfDYcxaVg5c7bCv5v4Efeky6pdqN8+a2UbNm+82P8XJkfgUkBgGITiRBiBQkgSNuPwXvzv9stXb3QFgqI0+EkTeqbTD8hwv1sedPf8PVoQeYECkkIMFTP9zPh4dh4ko0WrJyJQTlK2SXXo9RW3uqZeUTSraHl1AHmpAoOkDgBNphXf04FOFCi6wyGzkyBIV/exoHCjgFkj0QB4MR6QnZBMECcFNz2H58zjjjjjjjjhawHO0kUAc74OAhcGAc8QOLAuOAHPKDksBylA5VBcrwHPUDmKA5kwuZgBz3A5uQOcYLnPAc+QOeQDoFQee4DoGQ="
VAULT_CMR = "0b816a7c013697d7d773fd79e7d85ab9b8d1d31ecc4d2298266edcad58b52e45"
VAULT_ADDRESS = "tex1pgrwxqqg00u3pgyt4gyfccav5x2vyz7h0u6y0ujqk3khf3mwcg8ashz9ymw"
VAULT_SCRIPT_PUBKEY = "512040dc60010f7f2214117541138c75943298417aefe688fe48168dae98edd841fb"

# Certificate v2 info
CERT_PROGRAM = "46TabzBPv4SGzXHJwxBzmPat2iMAybFjF9eHRrzF8FQPK1FBCBQm0wrv6cCnChRdYZDZyZAkK/vY0DhRwCyR6IA8GI9ITsgmCECh0ChBhxyDBUkgScOZxVEJFdCZgAirhYMXhSwnsDCoXWEv1xUjIWWHAK278AQwDEgUJINwM43BRQfgZwqFobGHNddy8HoTqejIHGcv8bcleUZT57KmW1Vp7LXaMUR4qMQ4YBiE3n4rBAOBgcOG4lOE4iAxDiBxWBxeBxqA"
CERT_CMR = "5ab59e0758d47c302f04546d1c56b454b1bbbbc852d20d9e471497bfc8713955"
CERT_ADDRESS = "tex1pfeaa7eex2cxa923tehj5vd0emf779fp8v968mcx9uymm6q3gze6s8cvkka"
CERT_SCRIPT_PUBKEY = "51204e7bdf6726560dd2aa2bcde54635f9da7de2a42761747de0c5e137bd02281675"

# Fixed values
ASSET = "144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"
INTERNAL_KEY = "50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"

# Keys
ADMIN_SECRET = "c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"
DELEGATE_SECRET = "0f88f360602b68e02983c2e62a1cbd0e0d71a50f778f886abd1ccc3bc8b3ac9b"
# Random attacker key
RANDOM_SECRET = "1111111111111111111111111111111111111111111111111111111111111111"

# Wrong destination (random P2TR address)
WRONG_CERT_ADDRESS = "tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"

SAP_PAYLOAD = "5341500103a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"


def run_hal(args):
    """Run hal-simplicity command and return output."""
    cmd = [HAL] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.stderr
    return result.stdout.strip(), None


def create_witness(signature_bytes, is_right=True):
    """Create witness for Left (Admin) or Right (Delegate) path."""
    sig_bits = ''.join(format(b, '08b') for b in signature_bytes)
    tag = '1' if is_right else '0'
    witness_bits = tag + sig_bits + '0000000'
    witness_bytes = bytes(int(witness_bits[i:i+8], 2) for i in range(0, len(witness_bits), 8))
    return witness_bytes.hex()


def sats_to_btc(sats):
    return f"{sats / 100_000_000:.8f}"


def get_vault_utxo():
    """Get first available vault UTXO."""
    resp = requests.get(f"https://blockstream.info/liquidtestnet/api/address/{VAULT_ADDRESS}/utxo")
    utxos = resp.json()
    if not utxos:
        return None
    return utxos[0]


def get_cert_utxo():
    """Get first available certificate UTXO."""
    resp = requests.get(f"https://blockstream.info/liquidtestnet/api/address/{CERT_ADDRESS}/utxo")
    utxos = resp.json()
    if not utxos:
        return None
    return utxos[0]


def test_vault_verification(test_name, inputs_json, outputs_json, utxo_value, secret_key, expect_success):
    """Test vault spend verification (not broadcast)."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"Expected: {'SUCCESS' if expect_success else 'FAILURE'}")
    print('='*60)

    # Create PSET
    pset_out, err = run_hal(["simplicity", "pset", "create", "--liquid", inputs_json, outputs_json])
    if err:
        if not expect_success:
            print(f"RESULT: FAILED (as expected) - PSET creation failed")
            print(f"  Error: {err[:100]}...")
            return True
        print(f"RESULT: UNEXPECTED FAILURE - PSET creation failed: {err}")
        return False

    pset = json.loads(pset_out)["pset"]

    # Update input
    input_utxo = f"{VAULT_SCRIPT_PUBKEY}:{ASSET}:{sats_to_btc(utxo_value)}"
    pset2_out, err = run_hal([
        "simplicity", "pset", "update-input", "--liquid", pset, "0",
        "--input-utxo", input_utxo,
        "--cmr", VAULT_CMR,
        "--internal-key", INTERNAL_KEY
    ])
    if err:
        if not expect_success:
            print(f"RESULT: FAILED (as expected) - Update input failed")
            return True
        print(f"RESULT: UNEXPECTED FAILURE - Update input failed: {err}")
        return False

    pset2 = json.loads(pset2_out)["pset"]

    # Get sig_all_hash with dummy witness
    dummy_witness = "80" + "00" * 64
    run_out, err = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", VAULT_PROGRAM, dummy_witness])
    if err:
        if not expect_success:
            print(f"RESULT: FAILED (as expected) - Run failed")
            return True
        print(f"RESULT: UNEXPECTED FAILURE - Run failed: {err}")
        return False

    run_json = json.loads(run_out)
    sig_all_hash = None
    for jet in run_json.get("jets", []):
        if jet["jet"] == "sig_all_hash":
            sig_all_hash = jet["output_value"].replace("0x", "")
            break

    if not sig_all_hash:
        if not expect_success:
            print(f"RESULT: FAILED (as expected) - No sig_all_hash")
            return True
        print(f"RESULT: UNEXPECTED FAILURE - No sig_all_hash")
        return False

    # Sign
    privkey = ec.PrivateKey(bytes.fromhex(secret_key))
    signature = privkey.schnorr_sign(bytes.fromhex(sig_all_hash))
    witness = create_witness(signature.serialize(), is_right=True)

    # Verify
    run_out, err = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", VAULT_PROGRAM, witness])
    if err:
        if not expect_success:
            print(f"RESULT: FAILED (as expected) - Verification error")
            return True
        print(f"RESULT: UNEXPECTED FAILURE - Verification error: {err}")
        return False

    run_json = json.loads(run_out)
    success = run_json.get("success", False)

    # Check individual jets for debugging
    failed_jets = [j["jet"] for j in run_json.get("jets", []) if not j.get("success", True)]

    if success == expect_success:
        status = "SUCCESS" if success else "FAILED (as expected)"
        print(f"RESULT: {status}")
        if failed_jets:
            print(f"  Failed jets: {', '.join(failed_jets)}")
        return True
    else:
        status = "UNEXPECTED SUCCESS" if success else "UNEXPECTED FAILURE"
        print(f"RESULT: {status}")
        if failed_jets:
            print(f"  Failed jets: {', '.join(failed_jets)}")
        return False


def test_certificate_revocation(test_name, cert_utxo, secret_key, is_admin, expect_success):
    """Test certificate revocation."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"Expected: {'SUCCESS' if expect_success else 'FAILURE'}")
    print('='*60)

    utxo_txid = cert_utxo["txid"]
    utxo_vout = cert_utxo["vout"]
    utxo_value = cert_utxo["value"]

    FEE_SATS = utxo_value  # Burn all as fee for simplicity

    inputs_json = json.dumps([{"txid": utxo_txid, "vout": utxo_vout}])
    outputs_json = json.dumps([
        {"address": "fee", "asset": ASSET, "amount": float(sats_to_btc(FEE_SATS))}
    ])

    # Create PSET
    pset_out, err = run_hal(["simplicity", "pset", "create", "--liquid", inputs_json, outputs_json])
    if err:
        print(f"RESULT: FAILED - PSET creation failed: {err}")
        return False

    pset = json.loads(pset_out)["pset"]

    # Update input
    input_utxo = f"{CERT_SCRIPT_PUBKEY}:{ASSET}:{sats_to_btc(utxo_value)}"
    pset2_out, err = run_hal([
        "simplicity", "pset", "update-input", "--liquid", pset, "0",
        "--input-utxo", input_utxo,
        "--cmr", CERT_CMR,
        "--internal-key", INTERNAL_KEY
    ])
    if err:
        print(f"RESULT: FAILED - Update input failed: {err}")
        return False

    pset2 = json.loads(pset2_out)["pset"]

    # Get sig_all_hash
    dummy_witness = "00" + "00" * 64 if is_admin else "80" + "00" * 64
    run_out, err = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", CERT_PROGRAM, dummy_witness])
    if err:
        print(f"RESULT: FAILED - Run failed: {err}")
        return False

    run_json = json.loads(run_out)
    sig_all_hash = None
    for jet in run_json.get("jets", []):
        if jet["jet"] == "sig_all_hash":
            sig_all_hash = jet["output_value"].replace("0x", "")
            break

    if not sig_all_hash:
        print(f"RESULT: FAILED - No sig_all_hash")
        return False

    # Sign
    privkey = ec.PrivateKey(bytes.fromhex(secret_key))
    signature = privkey.schnorr_sign(bytes.fromhex(sig_all_hash))
    witness = create_witness(signature.serialize(), is_right=not is_admin)

    # Verify
    run_out, err = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", CERT_PROGRAM, witness])
    if err:
        if not expect_success:
            print(f"RESULT: FAILED (as expected)")
            return True
        print(f"RESULT: UNEXPECTED FAILURE: {err}")
        return False

    run_json = json.loads(run_out)
    success = run_json.get("success", False)

    if success == expect_success:
        status = "SUCCESS" if success else "FAILED (as expected)"
        print(f"RESULT: {status}")
        return True
    else:
        status = "UNEXPECTED SUCCESS" if success else "UNEXPECTED FAILURE"
        print(f"RESULT: {status}")
        failed_jets = [j["jet"] for j in run_json.get("jets", []) if not j.get("success", True)]
        if failed_jets:
            print(f"  Failed jets: {', '.join(failed_jets)}")
        return False


def emit_certificate_for_test(vault_utxo):
    """Emit a new certificate for testing revocation."""
    print(f"\n{'='*60}")
    print("SETUP: Emitting new certificate for revocation tests")
    print('='*60)

    utxo_txid = vault_utxo["txid"]
    utxo_vout = vault_utxo["vout"]
    utxo_value = vault_utxo["value"]

    FEE_SATS = 500
    CERT_SATS = 546
    troco_sats = utxo_value - FEE_SATS - CERT_SATS

    inputs_json = json.dumps([{"txid": utxo_txid, "vout": utxo_vout}])
    outputs_json = json.dumps([
        {"address": VAULT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(troco_sats))},
        {"address": CERT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(CERT_SATS))},
        {"address": f"data:{SAP_PAYLOAD}", "asset": ASSET, "amount": 0},
        {"address": "fee", "asset": ASSET, "amount": float(sats_to_btc(FEE_SATS))}
    ])

    pset_out, _ = run_hal(["simplicity", "pset", "create", "--liquid", inputs_json, outputs_json])
    pset = json.loads(pset_out)["pset"]

    input_utxo = f"{VAULT_SCRIPT_PUBKEY}:{ASSET}:{sats_to_btc(utxo_value)}"
    pset2_out, _ = run_hal([
        "simplicity", "pset", "update-input", "--liquid", pset, "0",
        "--input-utxo", input_utxo,
        "--cmr", VAULT_CMR,
        "--internal-key", INTERNAL_KEY
    ])
    pset2 = json.loads(pset2_out)["pset"]

    dummy_witness = "80" + "00" * 64
    run_out, _ = run_hal(["simplicity", "pset", "run", "--liquid", pset2, "0", VAULT_PROGRAM, dummy_witness])
    run_json = json.loads(run_out)
    sig_all_hash = None
    for jet in run_json.get("jets", []):
        if jet["jet"] == "sig_all_hash":
            sig_all_hash = jet["output_value"].replace("0x", "")
            break

    privkey = ec.PrivateKey(bytes.fromhex(DELEGATE_SECRET))
    signature = privkey.schnorr_sign(bytes.fromhex(sig_all_hash))
    witness = create_witness(signature.serialize(), is_right=True)

    final_out, _ = run_hal(["simplicity", "pset", "finalize", "--liquid", pset2, "0", VAULT_PROGRAM, witness])
    final_pset = json.loads(final_out)["pset"]

    tx_hex, _ = run_hal(["simplicity", "pset", "extract", "--liquid", final_pset])
    tx_hex = tx_hex.strip('"')

    resp = requests.post(
        "https://blockstream.info/liquidtestnet/api/tx",
        headers={"Content-Type": "text/plain"},
        data=tx_hex
    )
    txid = resp.text

    if len(txid) == 64:
        print(f"Certificate emitted: {txid}")
        print(f"Certificate UTXO: {txid}:1")
        return {"txid": txid, "vout": 1, "value": CERT_SATS}
    else:
        print(f"Failed to emit certificate: {txid}")
        return None


def main():
    print("=" * 70)
    print("SAP SYSTEM - EDGE CASE SECURITY TESTS")
    print("=" * 70)

    # Get vault UTXO
    vault_utxo = get_vault_utxo()
    if not vault_utxo:
        print("ERROR: No vault UTXO available for testing")
        return

    print(f"\nVault UTXO: {vault_utxo['txid']}:{vault_utxo['vout']}")
    print(f"Value: {vault_utxo['value']} sats")

    utxo_txid = vault_utxo["txid"]
    utxo_vout = vault_utxo["vout"]
    utxo_value = vault_utxo["value"]

    FEE_SATS = 500
    CERT_SATS = 546
    troco_sats = utxo_value - FEE_SATS - CERT_SATS

    results = []

    # =========================================================================
    # TEST 1: Vault spend with RANDOM KEY (should FAIL)
    # =========================================================================
    inputs_json = json.dumps([{"txid": utxo_txid, "vout": utxo_vout}])
    outputs_json = json.dumps([
        {"address": VAULT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(troco_sats))},
        {"address": CERT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(CERT_SATS))},
        {"address": f"data:{SAP_PAYLOAD}", "asset": ASSET, "amount": 0},
        {"address": "fee", "asset": ASSET, "amount": float(sats_to_btc(FEE_SATS))}
    ])

    result = test_vault_verification(
        "Vault spend with RANDOM KEY (attacker)",
        inputs_json, outputs_json, utxo_value,
        RANDOM_SECRET,
        expect_success=False
    )
    results.append(("Random key attack", result))

    # =========================================================================
    # TEST 2: Vault spend with WRONG NUMBER OF OUTPUTS (3 instead of 4)
    # =========================================================================
    outputs_json_3 = json.dumps([
        {"address": VAULT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(troco_sats + CERT_SATS))},
        {"address": f"data:{SAP_PAYLOAD}", "asset": ASSET, "amount": 0},
        {"address": "fee", "asset": ASSET, "amount": float(sats_to_btc(FEE_SATS))}
    ])

    result = test_vault_verification(
        "Vault spend with WRONG NUMBER OF OUTPUTS (3 instead of 4)",
        inputs_json, outputs_json_3, utxo_value,
        DELEGATE_SECRET,
        expect_success=False
    )
    results.append(("Wrong output count", result))

    # =========================================================================
    # TEST 3: Vault spend with WRONG CERTIFICATE DESTINATION
    # =========================================================================
    outputs_json_wrong_dest = json.dumps([
        {"address": VAULT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(troco_sats))},
        {"address": WRONG_CERT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(CERT_SATS))},
        {"address": f"data:{SAP_PAYLOAD}", "asset": ASSET, "amount": 0},
        {"address": "fee", "asset": ASSET, "amount": float(sats_to_btc(FEE_SATS))}
    ])

    result = test_vault_verification(
        "Vault spend with WRONG CERTIFICATE DESTINATION",
        inputs_json, outputs_json_wrong_dest, utxo_value,
        DELEGATE_SECRET,
        expect_success=False
    )
    results.append(("Wrong cert destination", result))

    # =========================================================================
    # TEST 4: Vault spend WITHOUT OP_RETURN
    # =========================================================================
    outputs_json_no_opreturn = json.dumps([
        {"address": VAULT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(troco_sats))},
        {"address": CERT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(CERT_SATS))},
        {"address": CERT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(100))},  # Extra output instead of OP_RETURN
        {"address": "fee", "asset": ASSET, "amount": float(sats_to_btc(FEE_SATS - 100))}
    ])

    result = test_vault_verification(
        "Vault spend WITHOUT OP_RETURN",
        inputs_json, outputs_json_no_opreturn, utxo_value,
        DELEGATE_SECRET,
        expect_success=False
    )
    results.append(("Missing OP_RETURN", result))

    # =========================================================================
    # TEST 5: Vault spend with WRONG TROCO DESTINATION (not self-reference)
    # =========================================================================
    outputs_json_wrong_troco = json.dumps([
        {"address": WRONG_CERT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(troco_sats))},  # Wrong troco!
        {"address": CERT_ADDRESS, "asset": ASSET, "amount": float(sats_to_btc(CERT_SATS))},
        {"address": f"data:{SAP_PAYLOAD}", "asset": ASSET, "amount": 0},
        {"address": "fee", "asset": ASSET, "amount": float(sats_to_btc(FEE_SATS))}
    ])

    result = test_vault_verification(
        "Vault spend with WRONG TROCO DESTINATION (breaks self-reference)",
        inputs_json, outputs_json_wrong_troco, utxo_value,
        DELEGATE_SECRET,
        expect_success=False
    )
    results.append(("Wrong troco destination", result))

    # =========================================================================
    # TEST 6: Correct vault spend (should SUCCEED) + Emit certificate
    # =========================================================================
    result = test_vault_verification(
        "Vault spend with CORRECT PARAMS (sanity check)",
        inputs_json, outputs_json, utxo_value,
        DELEGATE_SECRET,
        expect_success=True
    )
    results.append(("Correct params (sanity)", result))

    # Emit certificate for revocation tests
    cert_utxo = emit_certificate_for_test(vault_utxo)
    if not cert_utxo:
        print("\nCould not emit certificate, skipping revocation tests")
    else:
        # Wait a moment for confirmation
        import time
        print("\nWaiting 5 seconds for certificate confirmation...")
        time.sleep(5)

        # =========================================================================
        # TEST 7: Certificate revocation with ADMIN key (should SUCCEED)
        # =========================================================================
        result = test_certificate_revocation(
            "Certificate revocation with ADMIN key",
            cert_utxo,
            ADMIN_SECRET,
            is_admin=True,
            expect_success=True
        )
        results.append(("Admin revocation", result))

        # Note: We can't actually broadcast admin revocation and then test random key
        # because the UTXO would be spent. So we just verify the signature.

        # =========================================================================
        # TEST 8: Certificate revocation with RANDOM key (should FAIL)
        # =========================================================================
        result = test_certificate_revocation(
            "Certificate revocation with RANDOM key (attacker)",
            cert_utxo,
            RANDOM_SECRET,
            is_admin=True,  # Using admin path but wrong key
            expect_success=False
        )
        results.append(("Random key revocation", result))

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("ALL TESTS PASSED - Security verified!")
    else:
        print("SOME TESTS FAILED - Review security!")
    print("=" * 70)


if __name__ == "__main__":
    main()
