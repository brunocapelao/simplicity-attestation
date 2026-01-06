#!/usr/bin/env python3
"""Get Alice secret key from Web IDE by intercepting JS calls"""

import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = await context.new_page()

        # Intercept console logs
        page.on("console", lambda msg: print(f"CONSOLE: {msg.text}") if "key" in msg.text.lower() or "secret" in msg.text.lower() else None)

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

        # Go to Key Store tab
        print("Accessing Key Store...")
        keystore_tab = page.locator('button:has-text("Key Store")')
        await keystore_tab.click()
        await asyncio.sleep(2)

        # Look for "Copy Secret" button
        print("Looking for Copy Secret button...")
        buttons = await page.locator('button').all()
        for btn in buttons:
            text = await btn.text_content()
            if text:
                print(f"Button: {text}")
                if "secret" in text.lower():
                    print(f"Found secret button: {text}")
                    await btn.click()
                    await asyncio.sleep(0.5)
                    secret = await page.evaluate("navigator.clipboard.readText()")
                    print(f"\n*** ALICE SECRET KEY: {secret} ***\n")

        # Try to copy Alice secret
        copy_buttons = await page.locator('button:has-text("Copy")').all()
        print(f"\nFound {len(copy_buttons)} Copy buttons")
        for i, btn in enumerate(copy_buttons):
            text = await btn.text_content()
            print(f"Copy button {i}: {text}")

        # Try to get Alice's row and click copy secret
        alice_row = page.locator('tr:has-text("Alice"), div:has-text("Alice")')
        if await alice_row.count() > 0:
            print("Found Alice row")
            # Look for any copy button in Alice's row
            inner_buttons = await alice_row.locator('button').all()
            for btn in inner_buttons:
                text = await btn.text_content()
                print(f"  Alice button: {text}")

        await asyncio.sleep(2)

        # Take screenshot
        await page.screenshot(path="/tmp/ide_keystore2.png")
        print("Screenshot saved to /tmp/ide_keystore2.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
