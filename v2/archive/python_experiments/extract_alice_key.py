#!/usr/bin/env python3
"""Extract Alice private key from Web IDE Key Store"""

import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
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
        await asyncio.sleep(1)

        # Try to find the private key display or controls
        # Look for any element containing the key info
        content = await page.content()

        # Find elements in the key store
        key_elements = await page.locator('.keystore-entry, [class*="key"], [class*="secret"]').all()
        print(f"Found {len(key_elements)} key elements")

        # Get all text content from the keystore panel
        keystore_panel = page.locator('.keystore, [class*="keystore"], .panel').first
        if await keystore_panel.count() > 0:
            text = await keystore_panel.text_content()
            print(f"Key Store content: {text[:500] if text else 'empty'}...")

        # Try to find the private key in the page source
        # Sometimes it's stored in JavaScript variables
        alice_secret = await page.evaluate("""
            () => {
                // Try to find Alice's secret key in the global scope or Vue/React state
                if (window.keyStore) return JSON.stringify(window.keyStore);
                if (window.__KEYSTORE__) return JSON.stringify(window.__KEYSTORE__);

                // Look for any element with 'secret' or 'private' in its data
                const elements = document.querySelectorAll('[data-secret], [data-private-key]');
                return Array.from(elements).map(e => e.dataset).join(', ');
            }
        """)
        print(f"JS Keystore: {alice_secret}")

        # Take a screenshot for manual inspection
        await page.screenshot(path="/tmp/ide_keystore.png")
        print("Screenshot saved to /tmp/ide_keystore.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
