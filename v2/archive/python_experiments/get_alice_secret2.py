#!/usr/bin/env python3
"""Get Alice secret key by expanding the Key Store More section"""

import asyncio
from playwright.async_api import async_playwright

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

        # Go to Key Store tab
        print("Accessing Key Store...")
        keystore_tab = page.locator('button:has-text("Key Store")')
        await keystore_tab.click()
        await asyncio.sleep(2)

        # Click all "More" buttons to expand
        print("Clicking More buttons to expand...")
        more_buttons = await page.locator('button:has-text("More")').all()
        for i, btn in enumerate(more_buttons):
            print(f"Clicking More button {i}...")
            await btn.click()
            await asyncio.sleep(0.5)

        await asyncio.sleep(1)

        # Now look for Secret key or Copy Secret buttons
        print("\nLooking for Secret info...")
        all_text = await page.locator('.keystore, [class*="key"]').all_text_contents()
        for text in all_text:
            if text.strip():
                print(f"Key content: {text[:200]}...")

        # Try to find and copy secret
        copy_secret_buttons = await page.locator('button:has-text("Secret"), button:has-text("secret"), button:has-text("Copy Secret")').all()
        print(f"\nFound {len(copy_secret_buttons)} secret buttons")

        # Look for any element containing "secret" or "private"
        secret_elements = await page.locator('*:has-text("secret"), *:has-text("Secret"), *:has-text("private")').all()
        print(f"Found {len(secret_elements)} elements with 'secret' or 'private'")

        # Take screenshot after expanding
        await page.screenshot(path="/tmp/ide_keystore_expanded.png", full_page=True)
        print("\nScreenshot saved to /tmp/ide_keystore_expanded.png")

        # Get all visible text on the page
        body_text = await page.locator('body').inner_text()
        if "secret" in body_text.lower():
            # Find the line with secret
            lines = body_text.split('\n')
            for line in lines:
                if "secret" in line.lower() or (len(line) == 64 and all(c in '0123456789abcdef' for c in line)):
                    print(f"POTENTIAL SECRET: {line}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
