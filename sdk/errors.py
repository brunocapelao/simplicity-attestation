"""
SAS SDK - Error Types

Specific exception classes for better error handling and debugging.
"""



class SAPError(Exception):
    """Base exception for all SAS SDK errors."""
    
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigurationError(SAPError):
    """Error in SDK configuration."""


class MissingConfigError(ConfigurationError):
    """Required configuration is missing."""


class InvalidConfigError(ConfigurationError):
    """Configuration value is invalid."""


# =============================================================================
# Key and Signature Errors
# =============================================================================

class KeyError(SAPError):
    """Error related to cryptographic keys."""


class InvalidKeyError(KeyError):
    """Key format is invalid."""


class SignatureError(SAPError):
    """Error during signature creation or verification."""


class SignatureVerificationError(SignatureError):
    """Signature verification failed."""
    
    def __init__(self, message: str = "Signature verification failed", failed_jets: list[str] | None = None):
        super().__init__(message, {"failed_jets": failed_jets or []})
        self.failed_jets = failed_jets or []


# =============================================================================
# Transaction Errors
# =============================================================================

class TransactionError(SAPError):
    """Error during transaction construction or broadcast."""


class InsufficientFundsError(TransactionError):
    """Not enough funds to complete the operation."""
    
    def __init__(self, required: int, available: int, message: str | None = None):
        msg = message or f"Insufficient funds: required {required} sats, available {available} sats"
        super().__init__(msg, {"required": required, "available": available})
        self.required = required
        self.available = available


class BroadcastError(TransactionError):
    """Error broadcasting transaction to the network."""
    
    def __init__(self, message: str, tx_hex: str | None = None):
        super().__init__(message, {"tx_hex_length": len(tx_hex) if tx_hex else 0})
        self.tx_hex = tx_hex


class TransactionNotFoundError(TransactionError):
    """Transaction not found on blockchain."""
    
    def __init__(self, txid: str):
        super().__init__(f"Transaction not found: {txid}", {"txid": txid})
        self.txid = txid


class ConfirmationTimeoutError(TransactionError):
    """Transaction confirmation timed out."""
    
    def __init__(self, txid: str, timeout_seconds: int, current_confirmations: int = 0):
        super().__init__(
            f"Confirmation timeout for {txid}: waited {timeout_seconds}s, got {current_confirmations} confirmations",
            {"txid": txid, "timeout": timeout_seconds, "confirmations": current_confirmations}
        )
        self.txid = txid
        self.timeout_seconds = timeout_seconds
        self.current_confirmations = current_confirmations


# =============================================================================
# UTXO Errors
# =============================================================================

class UTXOError(SAPError):
    """Error related to UTXO operations."""


class UTXONotFoundError(UTXOError):
    """UTXO not found or already spent."""
    
    def __init__(self, txid: str, vout: int):
        super().__init__(f"UTXO not found: {txid}:{vout}", {"txid": txid, "vout": vout})
        self.txid = txid
        self.vout = vout


class UTXOAlreadySpentError(UTXOError):
    """UTXO has already been spent."""
    
    def __init__(self, txid: str, vout: int, spending_txid: str | None = None):
        super().__init__(
            f"UTXO already spent: {txid}:{vout}",
            {"txid": txid, "vout": vout, "spending_txid": spending_txid}
        )
        self.txid = txid
        self.vout = vout
        self.spending_txid = spending_txid


# =============================================================================
# Certificate Errors
# =============================================================================

class CertificateError(SAPError):
    """Error related to certificate operations."""


class CertificateNotFoundError(CertificateError):
    """Certificate not found."""
    
    def __init__(self, txid: str, vout: int):
        super().__init__(f"Certificate not found: {txid}:{vout}", {"txid": txid, "vout": vout})
        self.txid = txid
        self.vout = vout


class CertificateAlreadyRevokedError(CertificateError):
    """Certificate has already been revoked."""
    
    def __init__(self, txid: str, vout: int):
        super().__init__(f"Certificate already revoked: {txid}:{vout}", {"txid": txid, "vout": vout})
        self.txid = txid
        self.vout = vout


# =============================================================================
# Vault Errors
# =============================================================================

class VaultError(SAPError):
    """Error related to vault operations."""


class VaultEmptyError(VaultError):
    """Vault has no UTXOs available."""
    
    def __init__(self, vault_address: str):
        super().__init__(f"Vault is empty: {vault_address}", {"address": vault_address})
        self.vault_address = vault_address


class VaultInsufficientFundsError(VaultError, InsufficientFundsError):
    """Vault doesn't have enough funds for the operation."""


# =============================================================================
# Network Errors
# =============================================================================

class NetworkError(SAPError):
    """Error communicating with the blockchain network."""


class APIError(NetworkError):
    """Error from the blockchain API."""
    
    def __init__(self, message: str, status_code: int | None = None, endpoint: str | None = None):
        super().__init__(message, {"status_code": status_code, "endpoint": endpoint})
        self.status_code = status_code
        self.endpoint = endpoint


class ConnectionError(NetworkError):
    """Cannot connect to the blockchain network."""


class TimeoutError(NetworkError):
    """Request to blockchain network timed out."""


# =============================================================================
# Payload Errors
# =============================================================================

class PayloadError(SAPError):
    """Error related to OP_RETURN payload."""


class PayloadTooLargeError(PayloadError):
    """Payload exceeds OP_RETURN size limit."""
    
    def __init__(self, size: int, max_size: int = 75):
        super().__init__(
            f"Payload is {size} bytes, exceeds maximum of {max_size} bytes",
            {"size": size, "max_size": max_size}
        )
        self.size = size
        self.max_size = max_size


class InvalidPayloadError(PayloadError):
    """Payload format is invalid."""


# =============================================================================
# Tool Errors
# =============================================================================

class HalSimplicityError(SAPError):
    """Error from hal-simplicity CLI tool."""
    
    def __init__(self, message: str, command: str | None = None, stderr: str | None = None):
        super().__init__(message, {"command": command, "stderr": stderr})
        self.command = command
        self.stderr = stderr


class HalNotFoundError(HalSimplicityError):
    """hal-simplicity binary not found."""


class ProgramExecutionError(HalSimplicityError):
    """Error executing Simplicity program."""
