"""
SAS SDK - Simplicity Attestation Protocol SDK

A Python SDK to simplify operations with the SAS system on Liquid Network.

Usage (Recommended - Full Abstraction):
    from sdk import SAS
    
    # Just provide your keys - SDK handles everything
    sap = SAS(
        admin_private_key="abc123...",
        delegate_private_key="def456...",
        network="testnet"
    )
    
    print(f"Fund vault: {sap.vault_address}")
    result = sap.issue_certificate(cid="QmYwAPJzv5...")
    sap.revoke_certificate(result.txid, 1)

Usage (External Signing - multisig/hardware wallets):
    sap = SAS(
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
# Legacy client
from .client import SAPClient
from .config import ContractInfo, NetworkConfig, SASConfig

# Confirmation tracking
from .confirmation import ConfirmationStatus, ConfirmationTracker, TxStatus

# Error types
from .errors import (
    BroadcastError,
    CertificateAlreadyRevokedError,
    CertificateError,
    CertificateNotFoundError,
    ConfigurationError,
    ConfirmationTimeoutError,
    HalSimplicityError,
    InsufficientFundsError,
    NetworkError,
    PayloadTooLargeError,
    SAPError,
    TransactionError,
    VaultEmptyError,
    VaultError,
)

# Event hooks
from .events import Event, EventEmitter, EventType

# Fee estimation
from .fees import FeeEstimate, FeeEstimator, FeePriority

# Logging
from .logging import LogLevel, StructuredLogger, create_file_logger
from .models import UTXO, Certificate, CertificateStatus, TransactionResult, Vault

# External signature support
from .prepared import PreparedTransaction, SignedTransaction, TransactionType

# Key providers
from .providers import (
    EnvKeyProvider,
    FileKeyProvider,
    KeyProvider,
    MemoryKeyProvider,
)

# Roles and permissions
from .roles import PermissionError, Permissions, Role, RoleContext
from .sas import SAS

# Tool management
from .tools import ToolManager, ensure_tools, get_tool_path

# Vault creation and funding
from .vault import VaultBuilder, VaultFunder, VaultSetup

__version__ = "0.6.0"
__all__ = [
    # Core
    "SAS",
    "SAPClient",
    "SASConfig",
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
