#!/usr/bin/env python3
"""Generate BIP-340 Schnorr signature for a given message using secp256k1"""

import secp256k1
import hashlib
import os

def schnorr_sign(private_key_hex: str, message_hex: str) -> str:
    """
    Sign a message using BIP-340 Schnorr signature.

    Args:
        private_key_hex: 32-byte private key in hex
        message_hex: 32-byte message hash in hex

    Returns:
        64-byte signature in hex
    """
    private_key_bytes = bytes.fromhex(private_key_hex)
    message_bytes = bytes.fromhex(message_hex)

    # Create private key object
    privkey = secp256k1.PrivateKey(private_key_bytes)

    # Get the public key (x-only for BIP-340)
    pubkey = privkey.pubkey.serialize()
    print(f"Public Key (compressed): {pubkey.hex()}")

    # For BIP-340, we need the x-only public key (32 bytes)
    # The compressed pubkey is 33 bytes: prefix (02 or 03) + x-coordinate
    x_only_pubkey = pubkey[1:]  # Remove the prefix
    print(f"Public Key (x-only): {x_only_pubkey.hex()}")

    # BIP-340 Schnorr signature
    # Note: secp256k1-py might not have direct BIP-340 support
    # We'll use the schnorr_sign function if available

    try:
        # Try using schnorrsig if available (newer versions)
        sig = privkey.schnorr_sign(message_bytes, bip340tag=None)
        return sig.hex()
    except AttributeError:
        # Fallback: manual BIP-340 implementation
        print("schnorr_sign not available, trying ecdsa_sign_recoverable...")

        # For now, let's check what methods are available
        print(f"Available methods: {[m for m in dir(privkey) if not m.startswith('_')]}")
        return None

def main():
    # Admin private key from TESTNET_KEYS.md
    admin_private_key = "c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"

    # The sig_all_hash from our transaction with OP_RETURN
    # This is the message we need to sign
    sig_all_hash = "a6e8b945cf27bd68506c58dd7a3a975a6d10deb101178c6c01d52cd8257b7c15"

    print("=== BIP-340 Schnorr Signature ===")
    print(f"Private Key: {admin_private_key}")
    print(f"Message (sig_all_hash): {sig_all_hash}")
    print()

    signature = schnorr_sign(admin_private_key, sig_all_hash)
    if signature:
        print(f"\nSignature: {signature}")
    else:
        print("\nFailed to generate signature")

        # Try using cryptography library instead
        print("\nTrying alternative approach with hashlib...")

if __name__ == "__main__":
    main()
