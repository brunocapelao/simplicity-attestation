#!/usr/bin/env python3
"""Create P2PK program with Admin key via Web IDE - debug version"""

import asyncio
import re
from playwright.async_api import async_playwright

ADMIN_PUBKEY = "bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45"

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

        # Get the code
        print("Getting original code...")
        textarea = page.locator("textarea.program-input-field")
        code = await textarea.input_value()
        print(f"Original code:\n{code[:500]}...")

        # Find the pubkey pattern
        pubkey_patterns = [
            r'const ALICE_PUBKEY: Pubkey = (0x[a-fA-F0-9]+);',
            r'const ALICE_PUBKEY:\s*\[u8;\s*32\]\s*=\s*(0x[a-fA-F0-9]+);',
            r'Pubkey\s*=\s*(0x[a-fA-F0-9]+)',
        ]

        for pattern in pubkey_patterns:
            match = re.search(pattern, code)
            if match:
                print(f"Found pubkey: {match.group(1)}")

        # Replace the pubkey - be more specific with the pattern
        new_code = re.sub(
            r'(const ALICE_PUBKEY:\s*(?:Pubkey|\[u8;\s*32\])\s*=\s*)0x[a-fA-F0-9]+',
            f'\\g<1>0x{ADMIN_PUBKEY}',
            code
        )

        print(f"\nModified code:\n{new_code[:500]}...")

        # Clear and refill
        await textarea.clear()
        await asyncio.sleep(0.5)
        await textarea.fill(new_code)
        await asyncio.sleep(1)

        # Verify the change
        verify_code = await textarea.input_value()
        if ADMIN_PUBKEY in verify_code:
            print(f"\n✓ Admin pubkey successfully inserted!")
        else:
            print(f"\n✗ Admin pubkey NOT found in code!")
            # Show what's actually in the textarea
            print(f"Current code in textarea:\n{verify_code[:500]}...")

        # Compile
        print("\nCompiling...")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(3)

        # Get the address
        print("Getting address...")
        copy_addr_btn = page.locator('button:has-text("Copy Address")')
        await copy_addr_btn.click()
        await asyncio.sleep(0.5)
        address = await page.evaluate("navigator.clipboard.readText()")
        print(f"\n*** ADDRESS: {address} ***")

        await asyncio.sleep(2)
        await browser.close()
        return address

if __name__ == "__main__":
    address = asyncio.run(main())
