#!/usr/bin/env python3
"""Complete flow: Create Simplicity transaction with OP_RETURN using Admin P2PK"""

import asyncio
import re
import subprocess
import json
from embit import ec
from playwright.async_api import async_playwright

# Configuration
ADMIN_PRIVATE_KEY = "c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"
ADMIN_PUBKEY = "bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45"
ADMIN_P2PK_ADDR = "tex1pzlskxj29qaxfzrvxv97mzz9q04wydwwr4w2yvxxhule4yau2j2tsx7he84"

# UTXO details
UTXO_TXID = "207b72109d49d3e588ae2bc4c1dcf4f40dabbbb7acda425e36a732b12473aa04"
UTXO_VOUT = 0
UTXO_VALUE = 100000

# Asset ID (L-BTC testnet)
ASSET = "144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"

# SAID Protocol payload
# "SAID" (4 bytes) + VERSION (1 byte) + TYPE (1 byte) + CID (32 bytes test)
SAID_PAYLOAD = "534149440101deadbeefcafebabedeadbeefcafebabedeadbeefcafebabedeadbeefcafebabe"

# Fee and change
FEE = 1000
CHANGE = UTXO_VALUE - FEE  # 99000 sats

# Recipient (return to a testnet address)
RECIPIENT = "tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"

# hal-simplicity path
HAL = "/tmp/hal-simplicity-new/target/release/hal-simplicity"

# BIP-0341 unspendable key
INTERNAL_KEY = "50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"


async def get_program_and_cmr():
    """Get the compiled program and CMR from the IDE"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = await context.new_page()

        print("Loading IDE...")
        await page.goto("https://ide.simplicity-lang.org/")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Load P2PK example
        dropdown = page.locator('button.dropdown-button:has-text("Examples")')
        await dropdown.click()
        await asyncio.sleep(1)
        p2pk = page.locator('button.action-button').filter(has_text="P2PK").first
        await p2pk.click()
        await asyncio.sleep(2)

        # Modify pubkey to Admin
        textarea = page.locator("textarea.program-input-field")
        code = await textarea.input_value()
        new_code = re.sub(
            r'const ALICE_PUBLIC_KEY: u256 = 0x[a-fA-F0-9]+;',
            f'const ALICE_PUBLIC_KEY: u256 = 0x{ADMIN_PUBKEY};',
            code
        )
        await textarea.clear()
        await textarea.fill(new_code)
        await asyncio.sleep(1)

        # Get address to extract scriptPubKey
        copy_addr_btn = page.locator('button:has-text("Copy Address")')
        await copy_addr_btn.click()
        await asyncio.sleep(0.5)
        address = await page.evaluate("navigator.clipboard.readText()")
        print(f"Address: {address}")

        # We need to get the program from the IDE
        # Configure transaction to compile
        tx_tab = page.locator('button:has-text("Transaction")').last
        await tx_tab.click()
        await asyncio.sleep(1)

        inputs = page.locator("input:visible")
        await inputs.nth(0).fill(UTXO_TXID)
        await inputs.nth(1).fill(str(UTXO_VOUT))
        await inputs.nth(2).fill(str(UTXO_VALUE))
        await inputs.nth(3).fill(RECIPIENT)
        await inputs.nth(4).fill(str(FEE))

        # Compile
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(3)

        # Get the signature hash
        keystore_tab = page.locator('button:has-text("Key Store")')
        await keystore_tab.click()
        await asyncio.sleep(1)

        # Look for sig_all_hash in the page content
        body_text = await page.locator('body').inner_text()

        # Find hex values that could be the sighash
        hex_matches = re.findall(r'\b[a-fA-F0-9]{64}\b', body_text)
        print(f"Found hex values: {hex_matches[:5]}")

        # The program is shown in execution output
        exec_tab = page.locator('button:has-text("Execution")')
        await exec_tab.click()
        await asyncio.sleep(1)

        await browser.close()

        return address, None, None  # We'll get program differently


def run_hal_command(args):
    """Run hal-simplicity command and return output"""
    cmd = [HAL] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    return result.stdout


def create_pset_with_op_return():
    """Create PSET with OP_RETURN output"""
    print("\n=== Creating PSET with OP_RETURN ===")

    inputs_json = json.dumps([{"txid": UTXO_TXID, "vout": UTXO_VOUT}])
    outputs_json = json.dumps([
        {"address": RECIPIENT, "asset": ASSET, "amount": CHANGE - 1000},  # Leave room for OP_RETURN
        {"address": f"data:{SAID_PAYLOAD}", "asset": ASSET, "amount": 0},
        {"address": "fee", "asset": ASSET, "amount": FEE}
    ])

    result = run_hal_command([
        "simplicity", "pset", "create", "--liquid",
        inputs_json, outputs_json
    ])

    pset_data = json.loads(result)
    print(f"PSET created: {pset_data['pset'][:50]}...")
    return pset_data['pset']


def update_pset_input(pset, script_pubkey, cmr):
    """Update PSET input with UTXO info"""
    print("\n=== Updating PSET input ===")

    result = run_hal_command([
        "simplicity", "pset", "update-input", "--liquid", pset, "0",
        "--input-utxo", f"{script_pubkey}:{ASSET}:{UTXO_VALUE}",
        "--cmr", cmr,
        "--internal-key", INTERNAL_KEY
    ])

    pset_data = json.loads(result)
    print(f"PSET updated")
    return pset_data['pset']


def get_sig_all_hash(pset, program, witness):
    """Run program to get sig_all_hash"""
    print("\n=== Getting sig_all_hash ===")

    result = run_hal_command([
        "simplicity", "pset", "run", "--liquid", pset, "0", program, witness
    ])

    data = json.loads(result)
    for jet in data.get('jets', []):
        if jet['jet'] == 'bip_0340_verify':
            # Extract sig_all_hash from input_value
            input_val = jet['input_value']
            # Format: pubkey (32 bytes) + hash (32 bytes) + sig (64 bytes)
            # Skip "0x" prefix if present
            if input_val.startswith('0x'):
                input_val = input_val[2:]
            # First 64 chars = pubkey, next 64 chars = sig_all_hash
            sig_all_hash = input_val[64:128]
            print(f"sig_all_hash: {sig_all_hash}")
            return sig_all_hash

    return None


def sign_schnorr(message_hex):
    """Sign message using Admin private key"""
    print(f"\n=== Signing message ===")
    print(f"Message: {message_hex}")

    private_key_bytes = bytes.fromhex(ADMIN_PRIVATE_KEY)
    message_bytes = bytes.fromhex(message_hex)

    privkey = ec.PrivateKey(private_key_bytes)
    sig = privkey.schnorr_sign(message_bytes)
    signature = sig.serialize().hex()

    print(f"Signature: {signature}")
    return signature


def finalize_pset(pset, program, witness):
    """Finalize PSET with program and witness"""
    print("\n=== Finalizing PSET ===")

    result = run_hal_command([
        "simplicity", "pset", "finalize", "--liquid", pset, "0", program, witness
    ])

    print(f"Result: {result}")
    return result


async def main():
    print("=" * 60)
    print("SAID Protocol - Complete OP_RETURN Flow")
    print("=" * 60)

    # For now, we'll need to get the program info from the IDE
    # This is a simplified version - in practice, we'd extract all info

    # Get the scriptPubKey from the address
    # tex1pzlskxj29qaxfzrvxv97mzz9q04wydwwr4w2yvxxhule4yau2j2tsx7he84
    # This is a Taproot address, scriptPubKey = OP_1 <32-byte-key>

    # We need the program and CMR from compiling with Admin key
    # For now, let's use the IDE to get this info

    address, program, cmr = await get_program_and_cmr()

    print(f"\nAdmin P2PK Address: {address}")
    print(f"Expected: {ADMIN_P2PK_ADDR}")

    # The scriptPubKey for the address
    # We need to extract this from the address or use hal to decode
    print("\n=== Extracting scriptPubKey ===")
    result = run_hal_command(["address", "inspect", address])
    print(f"Address info: {result}")


if __name__ == "__main__":
    asyncio.run(main())
