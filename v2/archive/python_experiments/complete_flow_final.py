#!/usr/bin/env python3
"""
Complete flow using IDE for signing and hal-simplicity for OP_RETURN transaction.
This script automates the entire process.
"""

import asyncio
import re
import subprocess
import json
from embit import ec
from playwright.async_api import async_playwright

# Configuration from secrets.json
ADMIN_PRIVATE_KEY = "c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"
ADMIN_PUBKEY = "bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45"

# UTXO from faucet
UTXO_TXID = "38ff3f17073233ba3ad0254fe79745c675e9ac9c667811aee0f366abc26281ec"
UTXO_VOUT = 0
UTXO_VALUE = 100000  # sats

ASSET = "144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"
RECIPIENT = "tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"
FEE = 1000

# SAID Protocol payload
SAID_PAYLOAD = "534149440101deadbeefcafebabedeadbeefcafebabedeadbeefcafebabedeadbeefcafebabe"

HAL = "/tmp/hal-simplicity-new/target/release/hal-simplicity"


def sign_schnorr(message_hex: str) -> str:
    """Sign message using Admin private key"""
    private_key_bytes = bytes.fromhex(ADMIN_PRIVATE_KEY)
    message_bytes = bytes.fromhex(message_hex)
    privkey = ec.PrivateKey(private_key_bytes)
    sig = privkey.schnorr_sign(message_bytes)
    return sig.serialize().hex()


async def main():
    print("=" * 60)
    print("SAID Protocol - Complete Flow via IDE")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = await context.new_page()

        print("\n1. Loading IDE...")
        await page.goto("https://ide.simplicity-lang.org/")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Load P2PK example
        print("2. Loading P2PK example...")
        dropdown = page.locator('button.dropdown-button:has-text("Examples")')
        await dropdown.click()
        await asyncio.sleep(1)
        p2pk = page.locator('button.action-button').filter(has_text="P2PK").first
        await p2pk.click()
        await asyncio.sleep(2)

        # Modify pubkey to Admin
        print("3. Modifying to Admin pubkey...")
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

        # Configure transaction (standard tx first, without OP_RETURN)
        print("4. Configuring transaction...")
        tx_tab = page.locator('button:has-text("Transaction")').last
        await tx_tab.click()
        await asyncio.sleep(1)

        inputs = page.locator("input:visible")
        await inputs.nth(0).fill(UTXO_TXID)
        await inputs.nth(1).fill(str(UTXO_VOUT))
        await inputs.nth(2).fill(str(UTXO_VALUE))
        await inputs.nth(3).fill(RECIPIENT)
        await inputs.nth(4).fill(str(FEE))
        await asyncio.sleep(1)

        # First compile
        print("5. Compiling to get sig_all_hash...")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(4)

        # Go to Key Store to find sig_all_hash
        print("6. Getting sig_all_hash from Key Store...")
        keystore_tab = page.locator('button:has-text("Key Store")')
        await keystore_tab.click()
        await asyncio.sleep(2)

        # Expand sections
        for _ in range(3):
            more_btns = await page.locator('button:has-text("More")').all()
            for btn in more_btns:
                try:
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(0.3)
                except:
                    pass
        await asyncio.sleep(1)

        # Screenshot for debugging
        await page.screenshot(path="/tmp/ide_keystore.png", full_page=True)

        # Try to find sig_all_hash
        body_text = await page.locator('body').inner_text()

        # Look for SIGHASH section
        sig_all_hash = None
        lines = body_text.split('\n')
        for i, line in enumerate(lines):
            if 'SIGHASH_ALL' in line.upper() or 'SIGHASH' in line.upper():
                # Check next lines for hex value
                for j in range(1, 5):
                    if i + j < len(lines):
                        candidate = lines[i + j].strip()
                        if len(candidate) == 64 and all(c in '0123456789abcdefABCDEF' for c in candidate):
                            sig_all_hash = candidate.lower()
                            print(f"Found sig_all_hash near SIGHASH: {sig_all_hash}")
                            break
                if sig_all_hash:
                    break

        # Also look for any 64-char hex values that aren't known pubkeys
        if not sig_all_hash:
            hex_values = re.findall(r'\b([0-9a-fA-F]{64})\b', body_text)
            for h in hex_values:
                h_lower = h.lower()
                if h_lower != ADMIN_PUBKEY.lower():
                    # This might be the sig_all_hash
                    sig_all_hash = h_lower
                    print(f"Found potential sig_all_hash: {sig_all_hash}")
                    break

        if sig_all_hash:
            print(f"\n*** sig_all_hash: {sig_all_hash} ***")

            # Sign with Admin key
            print("\n7. Signing with Admin key...")
            signature = sign_schnorr(sig_all_hash)
            print(f"Signature: {signature}")

            # Update code with signature
            print("\n8. Updating code with signature...")
            code = await textarea.input_value()
            new_code = re.sub(
                r'const ALICE_SIGNATURE: \[u8; 64\] = 0x[a-fA-F0-9]+;',
                f'const ALICE_SIGNATURE: [u8; 64] = 0x{signature};',
                code
            )
            await textarea.clear()
            await textarea.fill(new_code)
            await asyncio.sleep(1)

            # Recompile
            print("9. Recompiling with signature...")
            await run_btn.click()
            await asyncio.sleep(4)

            # Check execution result
            exec_tab = page.locator('button:has-text("Execution")')
            await exec_tab.click()
            await asyncio.sleep(1)

            exec_text = await page.locator('body').inner_text()
            if "succeeded" in exec_text.lower():
                print("\n*** EXECUTION SUCCEEDED in IDE! ***")

                # Get the signed transaction
                print("\n10. Getting signed transaction...")

                # Click Copy Transaction button
                copy_tx_btn = page.locator('button:has-text("Copy Transaction")')
                if await copy_tx_btn.count() > 0:
                    await copy_tx_btn.click()
                    await asyncio.sleep(0.5)
                    tx_hex = await page.evaluate("navigator.clipboard.readText()")

                    if tx_hex and len(tx_hex) > 100 and tx_hex.startswith("02"):
                        print(f"\nSigned Transaction (first 200 chars): {tx_hex[:200]}...")

                        # Save the transaction
                        with open("/tmp/simplicity_tx.hex", "w") as f:
                            f.write(tx_hex)
                        print("Transaction saved to /tmp/simplicity_tx.hex")

                        # Broadcast
                        print("\n11. Broadcasting to Liquid Testnet...")
                        import urllib.request
                        import urllib.error

                        try:
                            req = urllib.request.Request(
                                "https://blockstream.info/liquidtestnet/api/tx",
                                data=tx_hex.encode(),
                                headers={"Content-Type": "text/plain"}
                            )
                            with urllib.request.urlopen(req) as response:
                                result = response.read().decode()
                                print(f"\n*** TRANSACTION BROADCAST SUCCESS! ***")
                                print(f"TXID: {result}")
                                print(f"Explorer: https://blockstream.info/liquidtestnet/tx/{result}")
                        except urllib.error.HTTPError as e:
                            error_body = e.read().decode()
                            print(f"Broadcast error: {error_body}")
                    else:
                        print(f"Unexpected clipboard content: {tx_hex[:100] if tx_hex else 'empty'}...")
                else:
                    print("Copy Transaction button not found")
            else:
                print(f"Execution failed: {exec_text[:300]}")
        else:
            print("\n*** Could not find sig_all_hash! ***")
            print("Check /tmp/ide_keystore.png")

        await asyncio.sleep(3)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
