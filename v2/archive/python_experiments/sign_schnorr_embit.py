#!/usr/bin/env python3
"""Generate BIP-340 Schnorr signature using embit library"""

from embit import ec
from embit.util import secp256k1

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
    privkey = ec.PrivateKey(private_key_bytes)

    # Get public key (x-only for BIP-340)
    pubkey = privkey.get_public_key()
    print(f"Public Key (x-only): {pubkey.xonly().hex()}")

    # Sign using BIP-340 Schnorr
    sig = privkey.schnorr_sign(message_bytes)
    return sig.serialize().hex()

def main():
    # Admin private key from TESTNET_KEYS.md
    admin_private_key = "c92b2771c01e3b89e446ab7c773cb7621a59e4d665902e26f1e847acc2d56379"

    # Expected public key
    admin_pubkey_expected = "bcc13efe121b35c7270c41ce63dab7688c0326c58c5f5e1d1af317c1503cad45"

    # The sig_all_hash from our transaction with OP_RETURN
    sig_all_hash = "a6e8b945cf27bd68506c58dd7a3a975a6d10deb101178c6c01d52cd8257b7c15"

    print("=== BIP-340 Schnorr Signature ===")
    print(f"Private Key: {admin_private_key}")
    print(f"Expected PubKey: {admin_pubkey_expected}")
    print(f"Message (sig_all_hash): {sig_all_hash}")
    print()

    signature = schnorr_sign(admin_private_key, sig_all_hash)
    print(f"\n*** SIGNATURE: {signature} ***")

    # Verify signature
    print("\n=== Verification ===")
    privkey = ec.PrivateKey(bytes.fromhex(admin_private_key))
    pubkey = privkey.get_public_key()
    sig_obj = ec.SchnorrSignature(bytes.fromhex(signature))
    is_valid = pubkey.schnorr_verify(sig_obj, bytes.fromhex(sig_all_hash))
    print(f"Signature valid: {is_valid}")

if __name__ == "__main__":
    main()
