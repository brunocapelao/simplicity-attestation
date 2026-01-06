#!/usr/bin/env python3
"""Test complete P2PK spend flow via Simplicity Web IDE"""

import asyncio
from playwright.async_api import async_playwright

# Our funded UTXO
UTXO_TXID = "bbe5f47bd98bf600f41d8d9d674812c67eb2b06743bff2941ddcf4aaa86dd825"
UTXO_VOUT = "0"
UTXO_VALUE = "100000"
FEE = "1000"

# Recipient - Liquid testnet faucet return address
# From https://liquidtestnet.com/faucet
FAUCET_RETURN_ADDRESS = "tex1qpvs2qnj3ea57wz68uyrmh9sxtk72wd5rcf0eep"

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

        # Click Run to compile
        print("\n=== Compiling ===")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(3)

        # Verify address
        print("\n=== Verifying Address ===")
        addr_btn = page.get_by_role("button", name="Address")
        await addr_btn.click()
        await asyncio.sleep(1)

        address = await page.evaluate("navigator.clipboard.readText()")
        print(f"  P2PK Address: {address}")

        expected_address = "tex1psll4tk527a7p7sedszhua6z3wykxk9g3v8cknv86jfgtju3pk95skx84jl"
        if address != expected_address:
            print(f"  WARNING: Address mismatch!")
            print(f"  Expected: {expected_address}")
            return

        # Click on Transaction tab
        print("\n=== Opening Transaction Tab ===")
        tx_tab = page.locator('button:has-text("Transaction")').last
        await tx_tab.click()
        await asyncio.sleep(1)

        # Find and fill input fields
        print("\n=== Filling UTXO Data ===")

        # Get visible inputs (should be 7 UTXO-related fields)
        visible_inputs = page.locator("input:visible")

        # Based on our debug output:
        # Input 0: txid
        # Input 1: vout
        # Input 2: value
        # Input 3: recipient
        # Input 4: fee
        # Input 5: nLockTime
        # Input 6: nSequence

        # Clear and fill txid
        txid_input = visible_inputs.nth(0)
        await txid_input.click()
        await txid_input.fill("")
        await txid_input.fill(UTXO_TXID)
        print(f"  txid: {UTXO_TXID}")

        # Fill vout
        vout_input = visible_inputs.nth(1)
        await vout_input.click()
        await vout_input.fill("")
        await vout_input.fill(UTXO_VOUT)
        print(f"  vout: {UTXO_VOUT}")

        # Fill value
        value_input = visible_inputs.nth(2)
        await value_input.click()
        await value_input.fill("")
        await value_input.fill(UTXO_VALUE)
        print(f"  value: {UTXO_VALUE}")

        # Fill recipient
        recipient_input = visible_inputs.nth(3)
        await recipient_input.click()
        await recipient_input.fill("")
        await recipient_input.fill(FAUCET_RETURN_ADDRESS)
        print(f"  recipient: {FAUCET_RETURN_ADDRESS}")

        # Fill fee
        fee_input = visible_inputs.nth(4)
        await fee_input.click()
        await fee_input.fill("")
        await fee_input.fill(FEE)
        print(f"  fee: {FEE}")

        await asyncio.sleep(1)
        await page.screenshot(path="/tmp/ide_utxo_filled.png")
        print("  Screenshot saved to /tmp/ide_utxo_filled.png")

        # Now click Run again to execute with the UTXO
        print("\n=== Running with UTXO ===")
        await run_btn.click()
        await asyncio.sleep(3)

        await page.screenshot(path="/tmp/ide_after_run.png")
        print("  Screenshot saved to /tmp/ide_after_run.png")

        # Check for execution results
        print("\n=== Checking Results ===")

        # Look for any error or success messages
        body_text = await page.locator("body").text_content()

        if "Jet failed" in body_text:
            print("  ERROR: Jet failed")
        elif "Execution fails" in body_text:
            print("  ERROR: Execution fails")
        elif "succeeded" in body_text.lower() or "success" in body_text.lower():
            print("  SUCCESS: Execution succeeded!")
        else:
            print("  Status unknown - check screenshots")

        # Try to get the transaction
        print("\n=== Getting Transaction ===")
        tx_btn = page.get_by_role("button", name="Transaction").first
        try:
            await tx_btn.click()
            await asyncio.sleep(1)

            # Read from clipboard
            tx_hex = await page.evaluate("navigator.clipboard.readText()")
            print(f"  Transaction (first 100 chars): {tx_hex[:100] if tx_hex else 'empty'}...")

            if tx_hex and len(tx_hex) > 50:
                # Save full transaction
                with open("/tmp/signed_tx_ide.hex", "w") as f:
                    f.write(tx_hex)
                print("  Full transaction saved to /tmp/signed_tx_ide.hex")
        except Exception as e:
            print(f"  Could not get transaction: {e}")

        # Get Execution tab content
        print("\n=== Checking Execution Tab ===")
        exec_tab = page.locator('button:has-text("Execution")').last
        await exec_tab.click()
        await asyncio.sleep(1)

        await page.screenshot(path="/tmp/ide_execution_tab.png")
        print("  Screenshot saved to /tmp/ide_execution_tab.png")

        # Keep browser open
        print("\n=== Keeping browser open for 10 seconds ===")
        await asyncio.sleep(10)

        await browser.close()
        print("\n=== Done ===")

if __name__ == "__main__":
    asyncio.run(main())
