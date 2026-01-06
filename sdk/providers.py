"""
SAP SDK - Key Providers

Abstract interface for key management with multiple backend implementations.
Separates key storage/signing from SDK logic for security best practices.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional
from embit import ec


class KeyProvider(ABC):
    """
    Abstract base class for key providers.
    
    Implementations handle secure key storage and signing operations
    without exposing private keys to the SDK core.
    
    Example implementations:
    - EnvKeyProvider: Keys from environment variables
    - FileKeyProvider: Keys from encrypted file (dev only)
    - AWSKMSProvider: AWS Key Management Service
    - HashiCorpVaultProvider: HashiCorp Vault
    - HardwareWalletProvider: Ledger/Trezor
    """
    
    @property
    @abstractmethod
    def public_key(self) -> str:
        """
        Get the public key as hex string.
        
        Returns:
            64-character hex string (32 bytes x-only pubkey).
        """
        pass
    
    @abstractmethod
    def sign(self, message: bytes) -> bytes:
        """
        Sign a message using Schnorr signature.
        
        Args:
            message: 32-byte message to sign (typically sig_all_hash).
        
        Returns:
            64-byte Schnorr signature.
        """
        pass
    
    def sign_hex(self, message_hex: str) -> bytes:
        """
        Sign a hex-encoded message.
        
        Args:
            message_hex: Hex-encoded message.
        
        Returns:
            64-byte Schnorr signature.
        """
        return self.sign(bytes.fromhex(message_hex))


class EnvKeyProvider(KeyProvider):
    """
    Key provider that reads private key from environment variable.
    
    This is the recommended approach for production deployments
    where keys are injected via secrets management.
    
    Example:
        export SAP_PRIVATE_KEY="abc123..."
        
        provider = EnvKeyProvider("SAP_PRIVATE_KEY")
        signature = provider.sign(message)
    """
    
    def __init__(self, env_var: str = "SAP_PRIVATE_KEY"):
        """
        Initialize from environment variable.
        
        Args:
            env_var: Name of environment variable containing private key.
        
        Raises:
            ValueError: If environment variable is not set.
        """
        private_key_hex = os.environ.get(env_var)
        if not private_key_hex:
            raise ValueError(
                f"Environment variable {env_var} not set. "
                f"Set it with: export {env_var}=<your-private-key-hex>"
            )
        
        self._private_key = ec.PrivateKey(bytes.fromhex(private_key_hex))
        self._public_key = self._private_key.get_public_key().xonly().hex()
    
    @property
    def public_key(self) -> str:
        return self._public_key
    
    def sign(self, message: bytes) -> bytes:
        signature = self._private_key.schnorr_sign(message)
        return signature.serialize()


class MemoryKeyProvider(KeyProvider):
    """
    Key provider with key in memory.
    
    WARNING: Only use for testing or when key is already in memory.
    For production, prefer EnvKeyProvider or KMS-based providers.
    
    Example:
        provider = MemoryKeyProvider("abc123...")
        signature = provider.sign(message)
    """
    
    def __init__(self, private_key_hex: str):
        """
        Initialize with private key.
        
        Args:
            private_key_hex: 64-character hex private key.
        """
        if len(private_key_hex) != 64:
            raise ValueError("Private key must be 64 hex characters (32 bytes)")
        
        self._private_key = ec.PrivateKey(bytes.fromhex(private_key_hex))
        self._public_key = self._private_key.get_public_key().xonly().hex()
    
    @property
    def public_key(self) -> str:
        return self._public_key
    
    def sign(self, message: bytes) -> bytes:
        signature = self._private_key.schnorr_sign(message)
        return signature.serialize()


class FileKeyProvider(KeyProvider):
    """
    Key provider that reads from a file.
    
    WARNING: Only for development. Never store unencrypted keys in files
    in production environments.
    
    The file should contain only the hex-encoded private key.
    """
    
    def __init__(self, key_file_path: str):
        """
        Initialize from key file.
        
        Args:
            key_file_path: Path to file containing private key hex.
        """
        with open(key_file_path, 'r') as f:
            private_key_hex = f.read().strip()
        
        self._private_key = ec.PrivateKey(bytes.fromhex(private_key_hex))
        self._public_key = self._private_key.get_public_key().xonly().hex()
    
    @property
    def public_key(self) -> str:
        return self._public_key
    
    def sign(self, message: bytes) -> bytes:
        signature = self._private_key.schnorr_sign(message)
        return signature.serialize()


# =============================================================================
# Placeholder for future KMS integrations
# =============================================================================

class AWSKMSProvider(KeyProvider):
    """
    AWS Key Management Service provider.
    
    NOTE: This is a placeholder. Full implementation requires:
    - boto3 dependency
    - AWS credentials configuration
    - KMS key with SIGN_VERIFY usage
    
    Example:
        provider = AWSKMSProvider(key_id="alias/sap-delegate")
    """
    
    def __init__(self, key_id: str, region: str = "us-east-1"):
        raise NotImplementedError(
            "AWS KMS provider not yet implemented. "
            "Use EnvKeyProvider or MemoryKeyProvider for now."
        )
    
    @property
    def public_key(self) -> str:
        raise NotImplementedError()
    
    def sign(self, message: bytes) -> bytes:
        raise NotImplementedError()


class HashiCorpVaultProvider(KeyProvider):
    """
    HashiCorp Vault provider.
    
    NOTE: This is a placeholder. Full implementation requires:
    - hvac dependency
    - Vault server configuration
    - Transit secrets engine
    """
    
    def __init__(self, vault_addr: str, key_name: str, token: Optional[str] = None):
        raise NotImplementedError(
            "HashiCorp Vault provider not yet implemented. "
            "Use EnvKeyProvider or MemoryKeyProvider for now."
        )
    
    @property
    def public_key(self) -> str:
        raise NotImplementedError()
    
    def sign(self, message: bytes) -> bytes:
        raise NotImplementedError()
