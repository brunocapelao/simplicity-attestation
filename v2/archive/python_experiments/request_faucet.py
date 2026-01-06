#!/usr/bin/env python3
"""Request funds from Liquid Testnet faucet"""

import asyncio
from playwright.async_api import async_playwright

ADMIN_P2PK_ADDR = "tex1pzlskxj29qaxfzrvxv97mzz9q04wydwwr4w2yvxxhule4yau2j2tsx7he84"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Requesting funds for: {ADMIN_P2PK_ADDR}")
        print("Loading faucet...")

        await page.goto("https://liquidtestnet.com/faucet")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        # Find the address input field
        print("Entering address...")
        address_input = page.locator('input[type="text"], input[name="address"], input[placeholder*="address"]').first
        await address_input.fill(ADMIN_P2PK_ADDR)
        await asyncio.sleep(1)

        # Find and click the submit button
        print("Submitting request...")
        submit_btn = page.locator('button[type="submit"], button:has-text("Get"), button:has-text("Send"), button:has-text("Request")').first
        await submit_btn.click()
        await asyncio.sleep(5)

        # Check for response/TXID
        body_text = await page.locator('body').inner_text()
        print(f"\nFaucet response:\n{body_text[:500]}...")

        # Take screenshot
        await page.screenshot(path="/tmp/faucet_result.png")
        print("\nScreenshot saved to /tmp/faucet_result.png")

        await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
