#!/usr/bin/env python3
"""Debug the Jet failed error in Simplicity Web IDE"""

import asyncio
from playwright.async_api import async_playwright

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

        # Take screenshot
        await page.screenshot(path="/tmp/ide_initial.png")
        print("  Initial screenshot saved to /tmp/ide_initial.png")

        # Load P2PK example via URL hack - check if IDE supports URL params
        # Or directly navigate to P2PK
        print("\n=== Loading P2PK Example ===")

        # Click the Examples dropdown
        dropdown = page.locator('button.dropdown-button:has-text("Examples")')
        await dropdown.click()
        await asyncio.sleep(1)

        await page.screenshot(path="/tmp/ide_examples_dropdown.png")
        print("  Dropdown screenshot saved")

        # Get all buttons in the dropdown
        buttons = page.locator('button.action-button')
        count = await buttons.count()
        print(f"  Found {count} action buttons")

        for i in range(count):
            btn = buttons.nth(i)
            text = await btn.text_content()
            print(f"    Button {i}: '{text}'")

        # Click P2PK specifically
        p2pk = page.locator('button.action-button').filter(has_text="P2PK").first
        await p2pk.click()
        await asyncio.sleep(2)

        await page.screenshot(path="/tmp/ide_p2pk_loaded.png")
        print("  P2PK loaded screenshot saved")

        # Click Run to compile
        print("\n=== Compiling ===")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(3)

        await page.screenshot(path="/tmp/ide_compiled.png")
        print("  Compiled screenshot saved")

        # Get Address
        print("\n=== Getting Address ===")
        addr_btn = page.get_by_role("button", name="Address")
        await addr_btn.click()
        await asyncio.sleep(1)

        # Read clipboard
        address = await page.evaluate("navigator.clipboard.readText()")
        print(f"  P2PK Address: {address}")

        # Click on Transaction tab at the bottom
        print("\n=== Opening Transaction Tab ===")
        tx_tab = page.locator('button:has-text("Transaction")').last
        await tx_tab.click()
        await asyncio.sleep(1)

        await page.screenshot(path="/tmp/ide_tx_tab.png")
        print("  Transaction tab screenshot saved")

        # Look for input fields
        print("\n=== Looking for Input Fields ===")
        all_inputs = page.locator("input")
        input_count = await all_inputs.count()
        print(f"  Found {input_count} input fields")

        for i in range(input_count):
            inp = all_inputs.nth(i)
            try:
                placeholder = await inp.get_attribute("placeholder") or ""
                value = await inp.input_value() or ""
                is_visible = await inp.is_visible()
                print(f"    Input {i}: placeholder='{placeholder}' value='{value[:30]}' visible={is_visible}")
            except:
                pass

        # Look for UTXO-related elements
        print("\n=== Looking for UTXO fields ===")

        # Get all text content
        body_text = await page.locator("body").text_content()

        # Search for common field names
        fields = ["txid", "vout", "value", "recipient", "fee", "nLockTime", "nSequence"]
        for field in fields:
            if field.lower() in body_text.lower():
                print(f"  Found '{field}' in page")

        # Try to fill UTXO values if fields are found
        print("\n=== Trying to fill UTXO ===")

        # UTXO we want to spend
        utxo_txid = "bbe5f47bd98bf600f41d8d9d674812c67eb2b06743bff2941ddcf4aaa86dd825"
        utxo_vout = "0"
        utxo_value = "100000"

        # Look for visible inputs in Transaction tab area
        visible_inputs = page.locator("input:visible")
        vis_count = await visible_inputs.count()
        print(f"  Found {vis_count} visible inputs")

        # Get the full HTML of the page for debugging
        html = await page.content()
        with open("/tmp/ide_page.html", "w") as f:
            f.write(html)
        print("  Full HTML saved to /tmp/ide_page.html")

        # Keep browser open briefly
        await asyncio.sleep(5)
        await browser.close()

        print("\n=== Done ===")
        print("Check screenshots in /tmp/")

if __name__ == "__main__":
    asyncio.run(main())
