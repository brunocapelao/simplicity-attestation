#!/usr/bin/env python3
"""Get Admin P2PK program from IDE by copying the compiled program"""

import asyncio
import re
from playwright.async_api import async_playwright

ADMIN_PUBKEY = "bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45"
ADMIN_PRIVATE_KEY = "c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"

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

        # Compile - this will fail because we don't have a valid signature
        # But we should be able to get the sig_all_hash
        print("Compiling (will fail on sig verify, but we get sig_all_hash)...")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(4)

        # Go to Key Store to find sig_all_hash
        print("\nGoing to Key Store...")
        keystore_tab = page.locator('button:has-text("Key Store")')
        await keystore_tab.click()
        await asyncio.sleep(2)

        # Look for the sighash - it should be displayed somewhere
        # Try to find it in "SIGHASH_ALL" section
        body = await page.content()

        # Search for hex patterns in the HTML
        hex_patterns = re.findall(r'[0-9a-fA-F]{64}', body)
        print(f"Found {len(hex_patterns)} 64-char hex values")
        for h in hex_patterns[:10]:
            print(f"  {h}")

        # Try clicking on More buttons to expand
        more_btns = await page.locator('button:has-text("More")').all()
        for btn in more_btns:
            try:
                await btn.click()
                await asyncio.sleep(0.5)
            except:
                pass

        await asyncio.sleep(1)

        # Get text content again
        body_text = await page.locator('body').inner_text()

        # Find all hex values
        all_hex = re.findall(r'[0-9a-fA-F]{64}', body_text)
        print(f"\nHex values in body text: {all_hex}")

        # The sig_all_hash is usually labeled or near SIGHASH
        lines = body_text.split('\n')
        for i, line in enumerate(lines):
            if 'SIGHASH' in line.upper() or 'SIG_ALL' in line.upper():
                print(f"\nLine {i}: {line}")
                # Check next few lines
                for j in range(1, 4):
                    if i+j < len(lines):
                        print(f"Line {i+j}: {lines[i+j]}")

        # Also get the program by looking at Copy Share
        print("\n=== Getting shareable program data ===")
        copy_share = page.locator('button:has-text("Copy Share")')
        await copy_share.click()
        await asyncio.sleep(0.5)
        share_url = await page.evaluate("navigator.clipboard.readText()")
        print(f"Share URL: {share_url}")

        # Parse the share URL to get program
        if "code=" in share_url:
            import urllib.parse
            parsed = urllib.parse.urlparse(share_url)
            params = urllib.parse.parse_qs(parsed.query)
            if 'code' in params:
                print(f"Code param: {params['code'][0][:100]}...")

        await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
