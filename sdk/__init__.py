"""
SAP SDK - Simplicity Attestation Protocol SDK

A Python SDK to simplify operations with the SAP system on Liquid Network.

Usage:
    from sap_sdk import SAPClient
    
    client = SAPClient.from_config("secrets.json")
    cert = client.issue_certificate(cid="Qm...")
"""

from .client import SAPClient
from .config import SAPConfig
from .models import Certificate, Vault, TransactionResult, UTXO

__version__ = "0.1.0"
__all__ = [
    "SAPClient",
    "SAPConfig", 
    "Certificate",
    "Vault",
    "TransactionResult",
    "UTXO",
]
