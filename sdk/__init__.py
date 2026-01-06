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
from .models import Certificate, Vault, TransactionResult, UTXO, CertificateStatus

# Error types
from .errors import (
    SAPError,
    ConfigurationError,
    TransactionError,
    InsufficientFundsError,
    BroadcastError,
    ConfirmationTimeoutError,
    CertificateError,
    CertificateNotFoundError,
    CertificateAlreadyRevokedError,
    VaultError,
    VaultEmptyError,
    NetworkError,
    PayloadTooLargeError,
    HalSimplicityError,
)

# Confirmation tracking
from .confirmation import ConfirmationTracker, ConfirmationStatus, TxStatus

# Fee estimation
from .fees import FeeEstimator, FeeEstimate, FeePriority

# Event hooks
from .events import EventEmitter, EventType, Event

# Logging
from .logging import StructuredLogger, LogLevel, create_file_logger

__version__ = "0.2.0"
__all__ = [
    # Core
    "SAPClient",
    "SAPConfig",
    "Certificate",
    "Vault",
    "TransactionResult",
    "UTXO",
    "CertificateStatus",
    
    # Errors
    "SAPError",
    "ConfigurationError",
    "TransactionError",
    "InsufficientFundsError",
    "BroadcastError",
    "ConfirmationTimeoutError",
    "CertificateError",
    "CertificateNotFoundError",
    "CertificateAlreadyRevokedError",
    "VaultError",
    "VaultEmptyError",
    "NetworkError",
    "PayloadTooLargeError",
    "HalSimplicityError",
    
    # Confirmation
    "ConfirmationTracker",
    "ConfirmationStatus",
    "TxStatus",
    
    # Fees
    "FeeEstimator",
    "FeeEstimate",
    "FeePriority",
    
    # Events
    "EventEmitter",
    "EventType",
    "Event",
    
    # Logging
    "StructuredLogger",
    "LogLevel",
    "create_file_logger",
]
