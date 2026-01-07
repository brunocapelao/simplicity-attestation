"""
SAP SDK - Simplicity Attestation Protocol SDK

A Python SDK to simplify operations with the SAP system on Liquid Network.

Usage (Recommended - Full Abstraction):
    from sdk import SAP
    
    # Just provide your keys - SDK handles everything
    sap = SAP(
        admin_private_key="abc123...",
        delegate_private_key="def456...",
        network="testnet"
    )
    
    print(f"Fund vault: {sap.vault_address}")
    result = sap.issue_certificate(cid="QmYwAPJzv5...")
    sap.revoke_certificate(result.txid, 1)

Usage (External Signing - multisig/hardware wallets):
    sap = SAP(
        admin_pubkey="abc123...",
        delegate_pubkey="def456...",
        signer=my_hardware_wallet,
        network="testnet"
    )
    
    prepared = sap.prepare_issue_certificate(cid="Qm...")
    signature = my_hardware_wallet.sign(prepared.sig_hash)
    result = sap.finalize_transaction(prepared, signature)

Legacy usage (with secrets.json):
    from sdk import SAPClient
    client = SAPClient.from_config("secrets.json")
"""

# New unified API
from .sap import SAP

# Legacy client
from .client import SAPClient
from .config import SAPConfig, NetworkConfig, ContractInfo
from .models import Certificate, Vault, TransactionResult, UTXO, CertificateStatus

# External signature support
from .prepared import PreparedTransaction, TransactionType, SignedTransaction

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

# Tool management
from .tools import ToolManager, ensure_tools, get_tool_path

__version__ = "0.6.0"
__all__ = [
    # Core
    "SAP",
    "SAPClient",
    "SAPConfig",
    "NetworkConfig",
    "ContractInfo",
    "Certificate",
    "Vault",
    "TransactionResult",
    "UTXO",
    "CertificateStatus",
    
    # External Signature
    "PreparedTransaction",
    "TransactionType",
    "SignedTransaction",
    
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

    # Tools
    "ToolManager",
    "ensure_tools",
    "get_tool_path",
]
