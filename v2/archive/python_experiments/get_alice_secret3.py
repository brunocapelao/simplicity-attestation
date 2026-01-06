#!/usr/bin/env python3
"""Get Alice secret key from browser localStorage"""

import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("Loading IDE...")
        await page.goto("https://ide.simplicity-lang.org/")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)

        # Load P2PK example to initialize keys
        print("Loading P2PK example...")
        dropdown = page.locator('button.dropdown-button:has-text("Examples")')
        await dropdown.click()
        await asyncio.sleep(1)
        p2pk = page.locator('button.action-button').filter(has_text="P2PK").first
        await p2pk.click()
        await asyncio.sleep(2)

        # Get localStorage
        print("\nExtracting localStorage...")
        local_storage = await page.evaluate("""
            () => {
                const items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
            }
        """)

        print("\nLocalStorage contents:")
        for key, value in local_storage.items():
            print(f"  {key}: {value[:100]}..." if len(str(value)) > 100 else f"  {key}: {value}")
            if "secret" in key.lower() or "key" in key.lower() or "master" in key.lower():
                print(f"\n*** FOUND SECRET KEY: {key} = {value} ***\n")

        # Also try sessionStorage
        print("\nExtracting sessionStorage...")
        session_storage = await page.evaluate("""
            () => {
                const items = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    const key = sessionStorage.key(i);
                    items[key] = sessionStorage.getItem(key);
                }
                return items;
            }
        """)

        for key, value in session_storage.items():
            print(f"  {key}: {value[:100]}..." if len(str(value)) > 100 else f"  {key}: {value}")

        # Try to access window variables
        print("\nSearching for key in window scope...")
        window_keys = await page.evaluate("""
            () => {
                const result = {};
                // Look for common variable names that might hold keys
                const varNames = ['secretKey', 'masterKey', 'privateKey', 'secret', 'key', 'alice', 'ALICE', 'keys'];
                for (const name of varNames) {
                    if (window[name]) result[name] = String(window[name]).substring(0, 100);
                }
                // Look in common framework stores
                if (window.__NUXT__) result['__NUXT__'] = 'present';
                if (window.__VUE__) result['__VUE__'] = 'present';
                if (window.app) result['app'] = typeof window.app;
                return result;
            }
        """)
        print(f"Window vars: {window_keys}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
