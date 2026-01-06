#!/bin/bash
cd /Users/brunocapelao/Projects/satshack-3-main/v2

# Compile and save
/Users/brunocapelao/.cargo/bin/simc delegation_vault.simf 2>&1 | tail -1 > delegation_vault.b64

# Check
echo "File size:"
wc -c delegation_vault.b64

echo ""
echo "First 100 chars:"
head -c 100 delegation_vault.b64

echo ""
echo ""
echo "Running info:"
/tmp/hal-simplicity-new/target/release/hal-simplicity simplicity info delegation_vault.b64
