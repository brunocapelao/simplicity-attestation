#!/usr/bin/env python3
"""Compile delegation_vault via Web IDE and get the program"""

import asyncio
from playwright.async_api import async_playwright

# Read the delegation_vault source
with open("/Users/brunocapelao/Projects/satshack-3-main/v2/delegation_vault.simf", "r") as f:
    VAULT_CODE = f.read()

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

        # Clear existing code and paste our vault code
        print("\n=== Pasting delegation_vault code ===")
        textarea = page.locator("textarea.program-input-field")
        await textarea.click()
        await textarea.fill("")
        await textarea.fill(VAULT_CODE)
        print(f"  Pasted {len(VAULT_CODE)} chars")

        await asyncio.sleep(1)

        # Click Run to compile
        print("\n=== Compiling ===")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(5)

        await page.screenshot(path="/tmp/ide_vault_compile.png")

        # Check for errors
        body_text = await page.locator("body").text_content()
        if "error" in body_text.lower() or "fail" in body_text.lower():
            print("  Compilation might have errors - check screenshot")
            # Check execution tab
            exec_tab = page.locator('button:has-text("Execution")').last
            await exec_tab.click()
            await asyncio.sleep(1)
            exec_content = await page.locator(".tab-content").last.text_content()
            print(f"  Execution: {exec_content[:300] if exec_content else 'empty'}...")
        else:
            print("  Compilation successful!")

        # Try to get the address
        print("\n=== Getting Address ===")
        try:
            addr_btn = page.get_by_role("button", name="Address")
            await addr_btn.click()
            await asyncio.sleep(1)
            address = await page.evaluate("navigator.clipboard.readText()")
            print(f"  Vault Address: {address}")

            # Save address
            with open("/tmp/vault_address.txt", "w") as f:
                f.write(address)
        except Exception as e:
            print(f"  Could not get address: {e}")

        # Keep browser open
        print("\n=== Keeping browser open for 20 seconds ===")
        await asyncio.sleep(20)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
