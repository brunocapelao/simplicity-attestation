#!/usr/bin/env python3
"""Explore the Key Store tab in Simplicity Web IDE"""

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

        # Load P2PK example
        print("\n=== Loading P2PK Example ===")
        dropdown = page.locator('button.dropdown-button:has-text("Examples")')
        await dropdown.click()
        await asyncio.sleep(1)

        p2pk = page.locator('button.action-button').filter(has_text="P2PK").first
        await p2pk.click()
        await asyncio.sleep(2)

        # Click Run to compile first
        print("\n=== Compiling ===")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(3)

        # Click on Key Store tab
        print("\n=== Opening Key Store Tab ===")
        keystore_tab = page.locator('button:has-text("Key Store")')
        await keystore_tab.click()
        await asyncio.sleep(1)

        await page.screenshot(path="/tmp/ide_keystore.png")
        print("  Screenshot saved to /tmp/ide_keystore.png")

        # Look at the content
        print("\n=== Key Store Content ===")

        # Get all visible text
        keystore_content = await page.locator(".tab-content").last.text_content()
        print(f"  Content: {keystore_content[:500] if keystore_content else 'empty'}...")

        # Find all buttons in key store
        buttons = page.locator(".tab-content button")
        btn_count = await buttons.count()
        print(f"\n  Found {btn_count} buttons")

        for i in range(btn_count):
            btn = buttons.nth(i)
            text = await btn.text_content()
            print(f"    Button {i}: '{text}'")

        # Find all labels/inputs
        print("\n=== Looking for key entries ===")
        labels = page.locator(".tab-content label, .tab-content .display-row-label")
        label_count = await labels.count()

        for i in range(label_count):
            label = labels.nth(i)
            text = await label.text_content()
            print(f"    Label {i}: '{text}'")

        # Get all input values
        print("\n=== Input Fields ===")
        inputs = page.locator(".tab-content input")
        inp_count = await inputs.count()

        for i in range(inp_count):
            inp = inputs.nth(i)
            value = await inp.input_value()
            placeholder = await inp.get_attribute("placeholder") or ""
            readonly = await inp.get_attribute("readonly")
            print(f"    Input {i}: value='{value[:40]}...' placeholder='{placeholder}' readonly={readonly}")

        # Look for Alice's keys
        print("\n=== Looking for Alice Keys ===")
        alice_elements = page.locator("text=/alice/i")
        alice_count = await alice_elements.count()
        print(f"  Found {alice_count} Alice-related elements")

        for i in range(alice_count):
            el = alice_elements.nth(i)
            text = await el.text_content()
            print(f"    Element {i}: '{text}'")

        # Check for signature generation
        print("\n=== Looking for Sign functionality ===")
        sign_elements = page.locator("text=/sign|signature/i")
        sign_count = await sign_elements.count()
        print(f"  Found {sign_count} sign-related elements")

        for i in range(min(sign_count, 10)):
            el = sign_elements.nth(i)
            text = await el.text_content()
            print(f"    Element {i}: '{text[:50]}'")

        # Keep browser open
        await asyncio.sleep(15)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
