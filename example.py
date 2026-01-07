#!/usr/bin/env python3
"""
SAP SDK - Usage Example

Demonstrates how to use the SDK for common operations.
"""

from sdk import SAPClient

def main():
    # Initialize client from config
    print("=" * 60)
    print("SAP SDK Example")
    print("=" * 60)
    
    try:
        client = SAPClient.from_config("secrets.json")
        print("✓ Client initialized")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return
    
    # Check vault status
    print("\n=== Vault Status ===")
    vault = client.get_vault()
    print(f"Address: {vault.address}")
    print(f"Balance: {vault.balance} sats")
    print(f"UTXOs: {len(vault.utxos)}")
    print(f"Can issue: {vault.can_issue}")
    
    if not vault.can_issue:
        print("\n⚠ Vault needs funding to issue certificates")
        print(f"Send funds to: {vault.address}")
        return
    
    # List existing certificates
    print("\n=== Valid Certificates ===")
    certs = client.list_certificates()
    if certs:
        for cert in certs:
            print(f"  - {cert.txid}:{cert.vout} (CID: {cert.cid[:20]}...)")
    else:
        print("  No valid certificates found")
    
    # Example: Issue a certificate
    print("\n=== Issue Certificate (Demo) ===")
    print("To issue a certificate, use:")
    print('  result = client.issue_certificate(cid="QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG")')
    print('  print(f"TXID: {result.txid}")')
    
    # Example: Verify a certificate
    print("\n=== Verify Certificate (Demo) ===")
    print("To verify a certificate, use:")
    print('  status = client.verify_certificate(txid, vout)')
    print('  print(f"Status: {status}")')
    
    # Example: Revoke a certificate
    print("\n=== Revoke Certificate (Demo) ===")
    print("To revoke a certificate, use:")
    print('  result = client.revoke_certificate(txid, vout)')
    print('  print(f"Revoked: {result.success}")')
    
    print("\n" + "=" * 60)
    print("SDK ready for use!")
    print("=" * 60)


if __name__ == "__main__":
    main()
