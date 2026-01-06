#!/usr/bin/env python3
"""Get signature from IDE for a specific UTXO"""

import asyncio
import re
from playwright.async_api import async_playwright

# Available UTXOs at P2PK address
UTXOS = [
    {"txid": "a6e83d005bb5bbbd738e92cea13306cf45b5aeb0ac7d86e692c8e20cd73f20b4", "vout": 0, "value": 100000},
    {"txid": "45b0c033e74bacb8f9e7ae74122af2a719890f9b531b5eff5f751bcc9b78e367", "vout": 0, "value": 100000},
]

# Use the first UTXO
UTXO = UTXOS[0]
FEE = 1000
RECIPIENT = "tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = await context.new_page()

        print("=== Opening Simplicity Web IDE ===")
        await page.goto("https://ide.simplicity-lang.org/")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Load P2PK example
        print("\n=== Loading P2PK Example ===")
        dropdown = page.locator('button.dropdown-button:has-text("Examples")')
        await dropdown.click()
        await asyncio.sleep(1)

        p2pk = page.locator('button.action-button').filter(has_text="P2PK").first
        await p2pk.click()
        await asyncio.sleep(2)

        # Configure UTXO FIRST
        print(f"\n=== Configuring UTXO: {UTXO['txid'][:16]}... ===")
        tx_tab = page.locator('button:has-text("Transaction")').last
        await tx_tab.click()
        await asyncio.sleep(1)

        visible_inputs = page.locator("input:visible")

        # Fill txid
        await visible_inputs.nth(0).click()
        await visible_inputs.nth(0).fill("")
        await visible_inputs.nth(0).fill(UTXO["txid"])

        # Fill vout
        await visible_inputs.nth(1).click()
        await visible_inputs.nth(1).fill("")
        await visible_inputs.nth(1).fill(str(UTXO["vout"]))

        # Fill value
        await visible_inputs.nth(2).click()
        await visible_inputs.nth(2).fill("")
        await visible_inputs.nth(2).fill(str(UTXO["value"]))

        # Fill recipient
        await visible_inputs.nth(3).click()
        await visible_inputs.nth(3).fill("")
        await visible_inputs.nth(3).fill(RECIPIENT)

        # Fill fee
        await visible_inputs.nth(4).click()
        await visible_inputs.nth(4).fill("")
        await visible_inputs.nth(4).fill(str(FEE))

        print("  UTXO configured")

        # Compile
        print("\n=== Compiling ===")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(3)

        # Get signature from Key Store
        print("\n=== Getting Signature from Key Store ===")
        keystore_tab = page.locator('button:has-text("Key Store")')
        await keystore_tab.click()
        await asyncio.sleep(1)

        # Find the CopyAlice button under Signatures
        copy_alice_buttons = page.locator('button:has-text("CopyAlice")')
        btn_count = await copy_alice_buttons.count()

        if btn_count >= 2:
            await copy_alice_buttons.nth(1).click()
            await asyncio.sleep(0.5)

            signature = await page.evaluate("navigator.clipboard.readText()")
            print(f"  Signature: {signature}")

            # Save signature
            with open("/tmp/alice_signature.txt", "w") as f:
                f.write(signature)
            print("  Saved to /tmp/alice_signature.txt")

            # Also get the raw transaction
            print("\n=== Getting Transaction ===")

            # First update code with signature
            textarea = page.locator("textarea.program-input-field")
            current_code = await textarea.input_value()

            new_code = re.sub(
                r'const ALICE_SIGNATURE: \[u8; 64\] = 0x[a-fA-F0-9]+;',
                f'const ALICE_SIGNATURE: [u8; 64] = {signature};',
                current_code
            )

            await textarea.click()
            await textarea.fill("")
            await textarea.fill(new_code)

            # Recompile
            await run_btn.click()
            await asyncio.sleep(3)

            # Get transaction
            tx_button = page.get_by_role("button", name="Transaction").first
            await tx_button.click()
            await asyncio.sleep(1)

            tx_hex = await page.evaluate("navigator.clipboard.readText()")
            if tx_hex and len(tx_hex) > 100 and not "fail" in tx_hex.lower():
                print(f"  Transaction: {tx_hex[:80]}...")
                with open("/tmp/signed_tx_utxo1.hex", "w") as f:
                    f.write(tx_hex)
                print("  Saved to /tmp/signed_tx_utxo1.hex")
            else:
                print(f"  Failed: {tx_hex[:100] if tx_hex else 'empty'}")

        # Keep browser open
        print("\n=== Done ===")
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
