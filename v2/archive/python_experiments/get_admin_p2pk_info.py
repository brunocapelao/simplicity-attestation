#!/usr/bin/env python3
"""Get Admin P2PK program info from IDE"""

import asyncio
import re
from playwright.async_api import async_playwright

ADMIN_PUBKEY = "bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45"

# UTXO details
UTXO_TXID = "207b72109d49d3e588ae2bc4c1dcf4f40dabbbb7acda425e36a732b12473aa04"
UTXO_VOUT = 0
UTXO_VALUE = 100000
FEE = 1000
RECIPIENT = "tex1qyh6tyhspd9w8jhqee8a2uzvyk9lnwp2n8ssur0"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = await context.new_page()

        print("Loading IDE...")
        await page.goto("https://ide.simplicity-lang.org/")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Load P2PK example
        print("Loading P2PK example...")
        dropdown = page.locator('button.dropdown-button:has-text("Examples")')
        await dropdown.click()
        await asyncio.sleep(1)
        p2pk = page.locator('button.action-button').filter(has_text="P2PK").first
        await p2pk.click()
        await asyncio.sleep(2)

        # Modify pubkey to Admin
        print("Modifying to Admin pubkey...")
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
        print("Configuring transaction...")
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
        print("Compiling...")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(4)

        # Get address
        print("\nGetting address...")
        copy_addr_btn = page.locator('button:has-text("Copy Address")')
        await copy_addr_btn.click()
        await asyncio.sleep(0.5)
        address = await page.evaluate("navigator.clipboard.readText()")
        print(f"Address: {address}")

        # Go to Key Store to get sig_all_hash
        print("\nGetting sig_all_hash from Key Store...")
        keystore_tab = page.locator('button:has-text("Key Store")')
        await keystore_tab.click()
        await asyncio.sleep(1)

        # Find SIGHASH_ALL section and copy
        body_text = await page.locator('body').inner_text()

        # Find sig_all_hash
        sighash_match = re.search(r'SIGHASH_ALL[^0-9a-fA-F]*([0-9a-fA-F]{64})', body_text)
        if sighash_match:
            print(f"sig_all_hash: {sighash_match.group(1)}")

        # Try to find in hash store
        hash_tab = page.locator('button:has-text("Hash Store")')
        await hash_tab.click()
        await asyncio.sleep(1)

        hash_text = await page.locator('body').inner_text()
        print(f"\nHash Store content (first 1000 chars):\n{hash_text[:1000]}")

        # Get all hex values from the page
        hex_values = re.findall(r'\b[0-9a-fA-F]{64}\b', hash_text)
        print(f"\nHex values found: {hex_values}")

        # Go to Execution tab for more info
        exec_tab = page.locator('button:has-text("Execution")')
        await exec_tab.click()
        await asyncio.sleep(1)

        exec_text = await page.locator('body').inner_text()

        # Find program base64
        prog_match = re.search(r'Program[:\s]+([A-Za-z0-9+/=]{20,})', exec_text)
        if prog_match:
            print(f"\nProgram: {prog_match.group(1)}")

        # Find CMR
        cmr_match = re.search(r'CMR[:\s]+([0-9a-fA-F]{64})', exec_text)
        if cmr_match:
            print(f"CMR: {cmr_match.group(1)}")

        # Take screenshot
        await page.screenshot(path="/tmp/admin_p2pk_info.png", full_page=True)
        print("\nScreenshot saved to /tmp/admin_p2pk_info.png")

        await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
