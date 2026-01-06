#!/usr/bin/env python3
"""
Complete flow using IDE - improved version to extract sig_all_hash
"""

import asyncio
import re
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

RECIPIENT = "tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"


def sign_schnorr(message_hex: str) -> str:
    """Sign message using Admin private key"""
    private_key_bytes = bytes.fromhex(ADMIN_PRIVATE_KEY)
    message_bytes = bytes.fromhex(message_hex)
    privkey = ec.PrivateKey(private_key_bytes)
    sig = privkey.schnorr_sign(message_bytes)
    return sig.serialize().hex()


async def main():
    print("=" * 60)
    print("SAID Protocol - Complete OP_RETURN Flow via IDE v2")
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

        # Compile
        print("5. Compiling...")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(4)

        # Go to Key Store
        print("6. Going to Key Store...")
        keystore_tab = page.locator('button:has-text("Key Store")')
        await keystore_tab.click()
        await asyncio.sleep(2)

        # Expand all sections by clicking More buttons
        print("7. Expanding sections...")
        for _ in range(5):
            more_btns = await page.locator('button:has-text("More")').all()
            for btn in more_btns:
                try:
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(0.3)
                except:
                    pass

        await asyncio.sleep(1)

        # Screenshot after expanding
        await page.screenshot(path="/tmp/ide_expanded.png", full_page=True)
        print("Screenshot saved to /tmp/ide_expanded.png")

        # Now try to find the sig_all_hash in "Signed Data" section
        # The sig_all_hash should be under "SIGHASH_ALL"
        body_text = await page.locator('body').inner_text()
        print(f"\nBody text contains 'SIGHASH': {'SIGHASH' in body_text}")

        # Look for patterns like "SIGHASH_ALL" followed by hex
        lines = body_text.split('\n')
        sig_all_hash = None
        for i, line in enumerate(lines):
            if 'SIGHASH' in line.upper():
                print(f"Found SIGHASH line: {line}")
                # Check next few lines for hex value
                for j in range(1, 5):
                    if i + j < len(lines):
                        next_line = lines[i + j].strip()
                        if len(next_line) == 64 and all(c in '0123456789abcdefABCDEF' for c in next_line):
                            sig_all_hash = next_line
                            print(f"Found sig_all_hash: {sig_all_hash}")
                            break

        # Also try to find it in the HTML
        if not sig_all_hash:
            html = await page.content()
            # Look for data-* attributes or specific elements
            hex_in_html = re.findall(r'>([0-9a-fA-F]{64})<', html)
            print(f"Hex values in HTML: {hex_in_html}")
            for h in hex_in_html:
                if h.lower() != ADMIN_PUBKEY.lower():
                    sig_all_hash = h
                    break

        # Try clicking "Copy" button in Signatures section (should copy sig_all_hash or signature)
        if not sig_all_hash:
            print("\n8. Trying to copy from Signatures section...")
            # Find the "Alice" button in Signatures section
            signatures_section = page.locator('text=Signatures').first
            if await signatures_section.count() > 0:
                # Find Alice copy button after Signatures
                alice_btns = await page.locator('button:has-text("Alice")').all()
                for btn in alice_btns:
                    try:
                        await btn.click()
                        await asyncio.sleep(0.3)
                        clipboard = await page.evaluate("navigator.clipboard.readText()")
                        print(f"Copied from Alice: {clipboard[:100]}..." if len(clipboard) > 100 else f"Copied: {clipboard}")
                        # Check if it's a signature (128 hex chars) or hash (64 hex chars)
                        if len(clipboard) == 64 and all(c in '0123456789abcdefABCDEF' for c in clipboard):
                            if clipboard.lower() != ADMIN_PUBKEY.lower():
                                sig_all_hash = clipboard
                                print(f"Found sig_all_hash from clipboard: {sig_all_hash}")
                                break
                        elif len(clipboard) == 128 and all(c in '0123456789abcdefABCDEF' for c in clipboard):
                            print(f"This is a signature, not sighash")
                    except Exception as e:
                        print(f"Error: {e}")

        if sig_all_hash:
            print(f"\n*** Found sig_all_hash: {sig_all_hash} ***")

            # Sign with Admin key
            print("\n9. Signing with Admin key...")
            signature = sign_schnorr(sig_all_hash)
            print(f"Admin Signature: {signature}")

            # Update code with our signature
            print("\n10. Updating code with Admin signature...")
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
            print("11. Recompiling with Admin signature...")
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
                print("\n12. Getting signed transaction...")
                copy_tx_btn = page.locator('button:has-text("Copy Transaction")')
                await copy_tx_btn.click()
                await asyncio.sleep(0.5)
                tx_hex = await page.evaluate("navigator.clipboard.readText()")

                if tx_hex and not tx_hex.startswith("Execution"):
                    print(f"\nSigned Transaction (first 200 chars): {tx_hex[:200]}...")
                    with open("/tmp/simplicity_tx.hex", "w") as f:
                        f.write(tx_hex)
                    print("Transaction saved to /tmp/simplicity_tx.hex")
                else:
                    print(f"Transaction copy failed: {tx_hex[:100]}")
            else:
                print(f"\nExecution failed:")
                print(exec_text[:500])
        else:
            print("\n*** Could not find sig_all_hash! ***")
            print("Please check /tmp/ide_expanded.png for the UI state")

        await asyncio.sleep(3)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
