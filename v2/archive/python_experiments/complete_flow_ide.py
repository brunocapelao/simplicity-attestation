#!/usr/bin/env python3
"""
Complete flow using IDE for signature and hal-simplicity for OP_RETURN transaction.

Strategy:
1. Use IDE to get sig_all_hash for a simple transaction (same input, different output)
2. Sign the sig_all_hash with Admin key
3. Use IDE to get the program with the signature embedded
4. Use hal-simplicity to create final transaction with OP_RETURN
"""

import asyncio
import re
import subprocess
import json
from embit import ec
from playwright.async_api import async_playwright

# Configuration
ADMIN_PRIVATE_KEY = "c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"
ADMIN_PUBKEY = "bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45"

# UTXO from faucet
UTXO_TXID = "38ff3f17073233ba3ad0254fe79745c675e9ac9c667811aee0f366abc26281ec"
UTXO_VOUT = 0
UTXO_VALUE = 100000
FEE = 1000

ASSET = "144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"
RECIPIENT = "tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"

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
    print("SAID Protocol - Complete OP_RETURN Flow via IDE")
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

        # Configure transaction
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

        # First compile to get sig_all_hash (will fail because we don't have signature yet)
        print("5. First compile to get sig_all_hash...")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(4)

        # Go to Key Store to find sig_all_hash
        print("6. Getting sig_all_hash from Key Store...")
        keystore_tab = page.locator('button:has-text("Key Store")')
        await keystore_tab.click()
        await asyncio.sleep(2)

        # Expand the sections
        more_btns = await page.locator('button:has-text("More")').all()
        for btn in more_btns:
            try:
                await btn.click()
                await asyncio.sleep(0.3)
            except:
                pass

        # Take screenshot to see the sig_all_hash
        await page.screenshot(path="/tmp/ide_sighash.png")

        # Try to find sighash - look for "SIGHASH" label and hex value near it
        body_html = await page.content()

        # The sig_all_hash should be in the Key Store under Signatures section
        # Let's look for hex values
        all_text = await page.locator('body').inner_text()
        hex_values = re.findall(r'[0-9a-fA-F]{64}', all_text)

        print(f"Found hex values: {hex_values}")

        # The sig_all_hash is typically shown in the Signatures section
        # Let's try to find it by copying

        # Look for copy buttons near SIGHASH
        sig_copy_buttons = await page.locator('button:has-text("Copy")').all()

        sig_all_hash = None
        for btn in sig_copy_buttons:
            try:
                await btn.click()
                await asyncio.sleep(0.3)
                clipboard = await page.evaluate("navigator.clipboard.readText()")
                if len(clipboard) == 64 and all(c in '0123456789abcdefABCDEF' for c in clipboard):
                    print(f"Copied value: {clipboard}")
                    # Check if this looks like a hash (not a pubkey we know)
                    if clipboard.lower() != ADMIN_PUBKEY.lower():
                        sig_all_hash = clipboard
                        break
            except:
                pass

        if not sig_all_hash and hex_values:
            # Try the first hex value that's not the pubkey
            for h in hex_values:
                if h.lower() != ADMIN_PUBKEY.lower():
                    sig_all_hash = h
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
                print("\n*** EXECUTION SUCCEEDED! ***")

                # Get the transaction
                print("\n10. Getting signed transaction...")
                tx_btn = page.get_by_role("button", name="Transaction").first
                await tx_btn.click()
                await asyncio.sleep(0.5)
                tx_hex = await page.evaluate("navigator.clipboard.readText()")

                print(f"\nSigned Transaction (first 200 chars): {tx_hex[:200]}...")

                # Save the transaction
                with open("/tmp/simplicity_tx.hex", "w") as f:
                    f.write(tx_hex)
                print("Transaction saved to /tmp/simplicity_tx.hex")

            else:
                print(f"Execution result: {exec_text[:500]}")
        else:
            print("Could not find sig_all_hash!")

        await asyncio.sleep(2)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
