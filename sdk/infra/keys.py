"""
SAS SDK - Key Management

Handles cryptographic key operations including Schnorr signatures.
"""

from typing import Optional
from embit import ec


class KeyManager:
    """
    Manages cryptographic keys for SAS operations.
    
    Provides Schnorr signature generation using embit library.
    """
    
    def __init__(self, private_key: str, public_key: Optional[str] = None):
        """
        Initialize key manager.
        
        Args:
            private_key: Hex-encoded 32-byte private key.
            public_key: Optional hex-encoded public key (derived if not provided).
        """
        self._private_key_hex = private_key
        self._private_key = ec.PrivateKey(bytes.fromhex(private_key))
        
        # Derive public key if not provided
        if public_key:
            self._public_key_hex = public_key
        else:
            self._public_key_hex = self._private_key.get_public_key().xonly().hex()
    
    @classmethod
    def from_secret(cls, secret: str) -> "KeyManager":
        """Create KeyManager from private key hex string."""
        return cls(private_key=secret)
    
    @property
    def public_key(self) -> str:
        """Get public key as hex string."""
        return self._public_key_hex
    
    @property
    def private_key(self) -> str:
        """Get private key as hex string."""
        return self._private_key_hex
    
    def schnorr_sign(self, message: str) -> bytes:
        """
        Create Schnorr signature for a message.
        
        Args:
            message: Hex-encoded message to sign (typically sig_all_hash).
        
        Returns:
            64-byte signature.
        """
        message_bytes = bytes.fromhex(message)
        signature = self._private_key.schnorr_sign(message_bytes)
        return signature.serialize()
    
    def sign_hash(self, sig_all_hash: str) -> bytes:
        """
        Sign a sig_all_hash from Simplicity.
        
        This is the main signing method used for Simplicity transactions.
        
        Args:
            sig_all_hash: Hex-encoded sig_all_hash from pset_run.
        
        Returns:
            64-byte Schnorr signature.
        """
        return self.schnorr_sign(sig_all_hash)
    
    def verify(self, message: str, signature: bytes) -> bool:
        """
        Verify a Schnorr signature.
        
        Args:
            message: Hex-encoded message.
            signature: 64-byte signature.
        
        Returns:
            True if valid, False otherwise.
        """
        try:
            message_bytes = bytes.fromhex(message)
            pubkey = self._private_key.get_public_key()
            return pubkey.schnorr_verify(signature, message_bytes)
        except Exception:
            return False
