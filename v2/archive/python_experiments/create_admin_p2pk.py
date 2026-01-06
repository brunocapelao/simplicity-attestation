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

        # Get the code and modify the pubkey
        print("Modifying pubkey to Admin key...")
        textarea = page.locator("textarea.program-input-field")
        code = await textarea.input_value()
        print(f"Original code contains ALICE_PUBKEY")

        # Replace Alice pubkey with Admin pubkey
        new_code = re.sub(
            r'const ALICE_PUBKEY: Pubkey = 0x[a-fA-F0-9]+;',
            f'const ALICE_PUBKEY: Pubkey = 0x{ADMIN_PUBKEY};',
            code
        )

        # Also replace in case it's named differently
        new_code = re.sub(
            r'let pk: Pubkey = 0x[a-fA-F0-9]+;',
            f'let pk: Pubkey = 0x{ADMIN_PUBKEY};',
            new_code
        )

        await textarea.fill(new_code)
        await asyncio.sleep(1)

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

        # Get program CMR from the transaction tab or debug output
        tx_tab = page.locator('button:has-text("Transaction")').last
        await tx_tab.click()
        await asyncio.sleep(1)

        # Get the program info
        # The program hex/base64 might be shown somewhere
        body_text = await page.locator('body').inner_text()

        # Look for CMR in the output
        cmr_match = re.search(r'CMR[:\s]+([a-fA-F0-9]{64})', body_text)
        if cmr_match:
            print(f"CMR: {cmr_match.group(1)}")

        # Get the program
        print("\nGetting program...")
        # The program is embedded in the witness, let's get it from execution output
        exec_tab = page.locator('button:has-text("Execution")')
        await exec_tab.click()
        await asyncio.sleep(1)

        exec_text = await page.locator('.execution-output, [class*="execution"]').first.inner_text() if await page.locator('.execution-output, [class*="execution"]').count() > 0 else ""
        print(f"Execution output: {exec_text[:500]}...")

        print("\n=== RESULTS ===")
        print(f"Admin PubKey: {ADMIN_PUBKEY}")
        print(f"Address: {address}")

        await browser.close()
        return address

if __name__ == "__main__":
    address = asyncio.run(main())
