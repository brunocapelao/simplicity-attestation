#!/usr/bin/env python3
"""Create P2PK program with Admin key via Web IDE"""

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
        textarea = page.locator("textarea.program-input-field")
        code = await textarea.input_value()

        # Replace ALICE_PUBLIC_KEY: u256 = 0x...
        new_code = re.sub(
            r'const ALICE_PUBLIC_KEY: u256 = 0x[a-fA-F0-9]+;',
            f'const ALICE_PUBLIC_KEY: u256 = 0x{ADMIN_PUBKEY};',
            code
        )

        print(f"✓ Replacing Alice pubkey with Admin pubkey")

        # Clear and refill
        await textarea.clear()
        await asyncio.sleep(0.5)
        await textarea.fill(new_code)
        await asyncio.sleep(1)

        # Verify
        verify_code = await textarea.input_value()
        if ADMIN_PUBKEY in verify_code:
            print(f"✓ Admin pubkey successfully inserted!")
        else:
            print(f"✗ FAILED!")
            return

        # Compile
        print("Compiling...")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(3)

        # Get the address
        print("Getting address...")
        copy_addr_btn = page.locator('button:has-text("Copy Address")')
        await copy_addr_btn.click()
        await asyncio.sleep(0.5)
        address = await page.evaluate("navigator.clipboard.readText()")
        print(f"\n*** ADMIN P2PK ADDRESS: {address} ***")

        # Also get the program
        print("\nGetting program and signature hash...")

        # Copy transaction to see what we have
        copy_tx_btn = page.locator('button:has-text("Copy Transaction")')
        await copy_tx_btn.click()
        await asyncio.sleep(0.5)
        tx = await page.evaluate("navigator.clipboard.readText()")
        print(f"Transaction hex (first 100 chars): {tx[:100]}...")

        await asyncio.sleep(1)
        await browser.close()
        return address

if __name__ == "__main__":
    address = asyncio.run(main())
