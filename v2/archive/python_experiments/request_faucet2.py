#!/usr/bin/env python3
"""Request funds from Liquid Testnet faucet for simc-compiled address"""

import asyncio
from playwright.async_api import async_playwright

# Address from simc-compiled Admin P2PK
SIMC_ADDR = "tex1pz28yevfp9f3nhgsqzxermr5w5zdrdxaxdltmpuptx5p36n7hutqqctuxjl"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"Requesting funds for simc address: {SIMC_ADDR}")
        print("Loading faucet...")

        await page.goto("https://liquidtestnet.com/faucet")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)

        # Find the address input field
        print("Entering address...")
        address_input = page.locator('input[type="text"], input[name="address"], input[placeholder*="address"]').first
        await address_input.fill(SIMC_ADDR)
        await asyncio.sleep(1)

        # Find and click the submit button
        print("Submitting request...")
        submit_btn = page.locator('button[type="submit"], button:has-text("Get"), button:has-text("Send"), button:has-text("Request")').first
        await submit_btn.click()
        await asyncio.sleep(5)

        # Check for response/TXID
        body_text = await page.locator('body').inner_text()
        print(f"\nFaucet response:\n{body_text[:500]}...")

        await asyncio.sleep(2)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
