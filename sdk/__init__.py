"""
SAP SDK - Simplicity Attestation Protocol SDK

A Python SDK to simplify operations with the SAP system on Liquid Network.

Usage (legacy - with secrets.json):
    from sdk import SAPClient
    
    client = SAPClient.from_config("secrets.json")
    cert = client.issue_certificate(cid="Qm...")

Usage (recommended - with KeyProvider):
    from sdk import SAPClient, NetworkConfig, EnvKeyProvider, Role
    
    config = NetworkConfig.from_file("network_config.json")
    provider = EnvKeyProvider("SAP_PRIVATE_KEY")
    
    client = SAPClient.create(config, provider, Role.DELEGATE)
    cert = client.issue_certificate(cid="Qm...")
"""

from .client import SAPClient
from .config import SAPConfig, NetworkConfig, ContractInfo
from .models import Certificate, Vault, TransactionResult, UTXO, CertificateStatus

# Key providers
from .providers import (
    KeyProvider,
    EnvKeyProvider,
    MemoryKeyProvider,
    FileKeyProvider,
)

# Roles and permissions
from .roles import Role, RoleContext, Permissions, PermissionError

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

# Vault creation and funding
from .vault import VaultBuilder, VaultFunder, VaultSetup

__version__ = "0.4.0"
__all__ = [
    # Core
    "SAPClient",
    "SAPConfig",
    "NetworkConfig",
    "ContractInfo",
    "Certificate",
    "Vault",
    "TransactionResult",
    "UTXO",
    "CertificateStatus",
    
    # Vault Creation
    "VaultBuilder",
    "VaultFunder",
    "VaultSetup",
    
    # Key Providers
    "KeyProvider",
    "EnvKeyProvider",
    "MemoryKeyProvider",
    "FileKeyProvider",
    
    # Roles
    "Role",
    "RoleContext",
    "Permissions",
    "PermissionError",
    
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
