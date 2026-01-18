"""
SAS SDK - Prepared Transactions

Data structures for transactions pending external signatures.
Enables multisig, hardware wallets, and approval workflows.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal, Dict, Any
from enum import Enum
import time
import json


class TransactionType(Enum):
    """Type of SAS transaction."""
    ISSUE_CERTIFICATE = "issue_certificate"
    REVOKE_CERTIFICATE = "revoke_certificate"
    DRAIN_VAULT = "drain_vault"


@dataclass
class PreparedTransaction:
    """
    A transaction prepared for external signing.
    
    Contains all data needed to:
    1. Display to user for approval
    2. Send to external signer
    3. Complete the transaction after signing
    
    Example:
        # Prepare transaction
        prepared = client.prepare_issue_certificate(cid="Qm...")
        
        # Show to user / send to multisig
        print(f"Sign this hash: {prepared.sig_hash}")
        print(f"Operation: {prepared.tx_type.value}")
        print(f"Details: {prepared.details}")
        
        # Get signature from external source
        signature = hardware_wallet.sign(prepared.sig_hash_bytes)
        
        # Complete
        result = client.finalize_transaction(prepared, signature)
    """
    # Transaction identification
    tx_type: TransactionType
    created_at: float = field(default_factory=time.time)
    
    # The hash that needs to be signed (Schnorr)
    sig_hash: str = ""  # Hex string
    
    # Role that will sign
    signer_role: Literal["admin", "delegate"] = "delegate"
    
    # Required public key for verification
    required_pubkey: str = ""
    
    # Internal state for finalization
    pset: str = ""  # Base64 encoded PSET
    input_index: int = 0
    program: str = ""  # Base64 encoded Simplicity program
    witness_template: str = ""  # Witness without signature
    
    # Human-readable details for approval
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Expiration (prevent stale transactions)
    expires_at: Optional[float] = None
    
    @property
    def sig_hash_bytes(self) -> bytes:
        """Get sig_hash as bytes for signing."""
        return bytes.fromhex(self.sig_hash)
    
    @property
    def is_expired(self) -> bool:
        """Check if transaction has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    @property
    def age_seconds(self) -> float:
        """Time since creation in seconds."""
        return time.time() - self.created_at
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "tx_type": self.tx_type.value,
            "created_at": self.created_at,
            "sig_hash": self.sig_hash,
            "signer_role": self.signer_role,
            "required_pubkey": self.required_pubkey,
            "details": self.details,
            "expires_at": self.expires_at,
            # Note: pset, program, witness_template not included for security
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def summary(self) -> str:
        """Human-readable summary for approval."""
        lines = [
            f"=== {self.tx_type.value.upper()} ===",
            f"Signer: {self.signer_role}",
            f"Hash to sign: {self.sig_hash[:16]}...{self.sig_hash[-8:]}",
        ]
        
        for key, value in self.details.items():
            lines.append(f"{key}: {value}")
        
        if self.expires_at:
            remaining = self.expires_at - time.time()
            lines.append(f"Expires in: {int(remaining)}s")
        
        return "\n".join(lines)


@dataclass
class SignedTransaction:
    """
    A transaction with signature attached, ready for finalization.
    """
    prepared: PreparedTransaction
    signature: bytes  # 64-byte Schnorr signature
    signed_at: float = field(default_factory=time.time)
    
    @property
    def signature_hex(self) -> str:
        return self.signature.hex()
    
    def verify_signature_format(self) -> bool:
        """Verify signature has correct format (64 bytes for Schnorr)."""
        return len(self.signature) == 64


class ExternalSignerProtocol:
    """
    Protocol for external signers to implement.
    
    This is a reference for what external signers should provide.
    Not required to inherit - duck typing is sufficient.
    """
    
    def sign(self, message_hash: bytes) -> bytes:
        """
        Sign a 32-byte message hash.
        
        Args:
            message_hash: 32-byte hash to sign.
        
        Returns:
            64-byte Schnorr signature.
        """
        raise NotImplementedError()
    
    def get_public_key(self) -> str:
        """
        Get the signer's public key.
        
        Returns:
            64-character hex x-only public key.
        """
        raise NotImplementedError()


# Helper functions for signature validation

def validate_signature(signature: bytes) -> bool:
    """Validate Schnorr signature format."""
    return isinstance(signature, bytes) and len(signature) == 64


def signature_from_hex(hex_sig: str) -> bytes:
    """Convert hex signature to bytes."""
    sig_bytes = bytes.fromhex(hex_sig)
    if len(sig_bytes) != 64:
        raise ValueError(f"Signature must be 64 bytes, got {len(sig_bytes)}")
    return sig_bytes
