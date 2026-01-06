#!/usr/bin/env python3
"""Complete P2PK spend flow via Simplicity Web IDE"""

import asyncio
import re
from playwright.async_api import async_playwright

# Our funded UTXO
UTXO_TXID = "bbe5f47bd98bf600f41d8d9d674812c67eb2b06743bff2941ddcf4aaa86dd825"
UTXO_VOUT = "0"
UTXO_VALUE = "100000"
FEE = "1000"

# Recipient - Liquid testnet faucet return address
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

        # Step 1: Configure UTXO BEFORE compiling
        print("\n=== Configuring UTXO ===")
        tx_tab = page.locator('button:has-text("Transaction")').last
        await tx_tab.click()
        await asyncio.sleep(1)

        visible_inputs = page.locator("input:visible")

        # Fill txid
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

        # Step 2: Compile to compute sig_all_hash
        print("\n=== Compiling (to compute sig_all_hash) ===")
        run_btn = page.get_by_role("button", name="Run")
        await run_btn.click()
        await asyncio.sleep(3)

        # Step 3: Get the signature from Key Store
        print("\n=== Getting Signature from Key Store ===")
        keystore_tab = page.locator('button:has-text("Key Store")')
        await keystore_tab.click()
        await asyncio.sleep(1)

        await page.screenshot(path="/tmp/ide_keystore_with_utxo.png")

        # Find the CopyAlice button under Signatures (it's the second CopyAlice)
        # First CopyAlice is for Public Keys, second is for Signatures
        copy_alice_buttons = page.locator('button:has-text("CopyAlice")')
        btn_count = await copy_alice_buttons.count()
        print(f"  Found {btn_count} CopyAlice buttons")

        # Click the second one (Signatures)
        if btn_count >= 2:
            await copy_alice_buttons.nth(1).click()
            await asyncio.sleep(0.5)

            # Read signature from clipboard
            signature = await page.evaluate("navigator.clipboard.readText()")
            print(f"  Signature: {signature[:80]}..." if signature else "  Signature: empty")

            if signature and signature.startswith("0x"):
                # Step 4: Update the code with the correct signature
                print("\n=== Updating Code with Correct Signature ===")

                # Get the textarea
                textarea = page.locator("textarea.program-input-field")
                current_code = await textarea.input_value()

                # Replace the signature in the code
                # Find the pattern: const ALICE_SIGNATURE: [u8; 64] = 0x...;
                new_code = re.sub(
                    r'const ALICE_SIGNATURE: \[u8; 64\] = 0x[a-fA-F0-9]+;',
                    f'const ALICE_SIGNATURE: [u8; 64] = {signature};',
                    current_code
                )

                # Clear and fill the textarea
                await textarea.click()
                await textarea.fill("")
                await textarea.fill(new_code)
                print("  Code updated with new signature")

                # Step 5: Recompile with correct signature
                print("\n=== Recompiling with Correct Signature ===")
                await run_btn.click()
                await asyncio.sleep(3)

                await page.screenshot(path="/tmp/ide_after_recompile.png")

                # Check execution result
                print("\n=== Checking Execution Result ===")
                exec_tab = page.locator('button:has-text("Execution")').last
                await exec_tab.click()
                await asyncio.sleep(1)

                exec_content = await page.locator(".tab-content").last.text_content()
                print(f"  Execution: {exec_content[:200] if exec_content else 'empty'}...")

                if "succeeded" in exec_content.lower() or "success" in exec_content.lower():
                    print("\n  ✓ EXECUTION SUCCEEDED!")
                elif "fail" in exec_content.lower():
                    print("\n  ✗ Execution failed")
                    await page.screenshot(path="/tmp/ide_execution_failed.png")

                # Step 6: Get the signed transaction
                print("\n=== Getting Signed Transaction ===")
                tx_button = page.get_by_role("button", name="Transaction").first
                await tx_button.click()
                await asyncio.sleep(1)

                tx_hex = await page.evaluate("navigator.clipboard.readText()")
                print(f"  Transaction: {tx_hex[:100] if tx_hex else 'empty'}...")

                if tx_hex and len(tx_hex) > 100 and not "fail" in tx_hex.lower():
                    # Save transaction
                    with open("/tmp/signed_tx_ide.hex", "w") as f:
                        f.write(tx_hex)
                    print(f"  Transaction saved to /tmp/signed_tx_ide.hex")
                    print(f"  Transaction length: {len(tx_hex)} chars")

                    # Try to broadcast
                    print("\n=== Ready to Broadcast ===")
                    print(f"  Use: curl -X POST -d '{tx_hex[:50]}...' https://blockstream.info/liquidtestnet/api/tx")
                else:
                    print("  No valid transaction generated")
        else:
            print("  Could not find signature buttons")

        await page.screenshot(path="/tmp/ide_final.png")

        # Keep browser open
        print("\n=== Keeping browser open for 15 seconds ===")
        await asyncio.sleep(15)

        await browser.close()
        print("\n=== Done ===")

if __name__ == "__main__":
    asyncio.run(main())
