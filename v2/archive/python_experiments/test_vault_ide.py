#!/usr/bin/env python3
"""Test delegation vault with IDE Alice key"""

import asyncio
from playwright.async_api import async_playwright

# Read the simplified vault source
with open("/Users/brunocapelao/Projects/satshack-3-main/v2/delegation_vault_ide.simf", "r") as f:
    VAULT_CODE = f.read()

# UTXO to use (will be updated after funding)
UTXO_TXID = ""
UTXO_VOUT = "0"
UTXO_VALUE = "100000"
FEE = "1000"

# Faucet return address
RECIPIENT = "tex1qpvs2qnj3ea57wz68uyrmh9sxtk72wd5rcf0eep"

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

        # Paste vault code
        print("\n=== Pasting vault code ===")
        textarea = page.locator("textarea.program-input-field")
        await textarea.click()
        await textarea.fill("")
        await textarea.fill(VAULT_CODE)
        print(f"  Pasted {len(VAULT_CODE)} chars")

        # Compile
        print("\n=== Compiling ===")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(3)

        # Get address
        print("\n=== Getting Vault Address ===")
        addr_btn = page.get_by_role("button", name="Address")
        await addr_btn.click()
        await asyncio.sleep(1)
        vault_address = await page.evaluate("navigator.clipboard.readText()")
        print(f"  Vault Address: {vault_address}")

        # Save address for faucet funding
        with open("/tmp/vault_ide_address.txt", "w") as f:
            f.write(vault_address)

        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("="*60)
        print(f"1. Fund this address from faucet:")
        print(f"   https://liquidtestnet.com/faucet")
        print(f"   Address: {vault_address}")
        print(f"")
        print(f"2. After funding, check UTXOs:")
        print(f"   curl 'https://blockstream.info/liquidtestnet/api/address/{vault_address}/utxo'")
        print("="*60)

        # Keep browser open
        await asyncio.sleep(30)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
