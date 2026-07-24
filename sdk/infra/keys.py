"""
SAS SDK - Key Management

Handles cryptographic key operations including Schnorr signatures.

SECURITY NOTE: This class intentionally does NOT expose private key material
through properties or serialization. The private key is only used internally
for signing operations.
"""

import logging

from embit import ec  # type: ignore[import-untyped]
from embit.ec import SchnorrSig  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class KeyManager:
    """
    Manages cryptographic keys for SAS operations.

    Provides Schnorr signature generation using embit library.

    SECURITY: Private key material is never exposed through properties,
    serialization, or string representation. Use only the provided
    signing methods.
    """

    __slots__ = ('_private_key', '_public_key_hex')  # Prevent __dict__ access

    def __init__(self, private_key: str, public_key: str | None = None):
        """
        Initialize key manager.

        Args:
            private_key: Hex-encoded 32-byte private key.
            public_key: Optional hex-encoded public key (derived if not provided).
        """
        try:
            self._private_key = ec.PrivateKey(bytes.fromhex(private_key))
        except ValueError as e:
            logger.debug("KeyManager: invalid hex string (length=%d)", len(private_key))
            raise e

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

    def __repr__(self) -> str:
        """Safe representation that doesn't leak private key."""
        return f"KeyManager(public_key={self._public_key_hex[:16]}...)"

    def __str__(self) -> str:
        """Safe string representation."""
        return self.__repr__()

    def __getstate__(self):
        """Prevent pickling to avoid accidental key serialization."""
        raise TypeError("KeyManager cannot be pickled (contains secret material)")

    def __reduce__(self):
        """Prevent pickling via reduce protocol."""
        raise TypeError("KeyManager cannot be pickled (contains secret material)")
    
    def schnorr_sign(self, message: str) -> bytes:
        """
        Create Schnorr signature for a message.
        
        Args:
            message: Hex-encoded message to sign (typically sig_all_hash).
        
        Returns:
            64-byte signature.
        """
        try:
            message_bytes = bytes.fromhex(message)
        except ValueError as e:
            logger.debug("KeyManager: schnorr_sign received invalid hex message")
            raise e
        signature = self._private_key.schnorr_sign(message_bytes)
        return bytes(signature.serialize())
    
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
            sig_obj = SchnorrSig(signature)
            return bool(pubkey.schnorr_verify(sig_obj, message_bytes))
        except Exception as e:
            if isinstance(e, ValueError) and "non-hexadecimal" in str(e):
                logger.debug("KeyManager: verify received invalid hex message")
            return False
