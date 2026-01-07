"""
SAP SDK - Witness Encoder

Handles bit-level encoding of witnesses for Simplicity spending paths.
"""

from typing import Literal


class WitnessEncoder:
    """
    Encodes witnesses for Simplicity spending paths.
    
    Simplicity uses a tree structure for spending paths encoded in bits:
    - Left = 0
    - Right = 1
    
    Vault paths:
    - Left: Admin unconditional (0 + sig + 7 padding)
    - Right-Left: Admin issue certificate (10 + sig + 6 padding)  
    - Right-Right: Delegate issue certificate (11 + sig + 6 padding)
    
    Certificate paths:
    - Left: Admin revoke (0 + sig + 7 padding)
    - Right: Delegate revoke (1 + sig + 7 padding)
    """
    
    @staticmethod
    def _signature_to_bits(signature: bytes) -> str:
        """Convert 64-byte signature to 512-bit string."""
        if len(signature) != 64:
            raise ValueError(f"Signature must be 64 bytes, got {len(signature)}")
        return ''.join(format(b, '08b') for b in signature)
    
    @staticmethod
    def _bits_to_hex(bits: str) -> str:
        """Convert bit string to hex string."""
        # Ensure bit string length is multiple of 8
        if len(bits) % 8 != 0:
            raise ValueError(f"Bit string length must be multiple of 8, got {len(bits)}")
        
        result = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))
        return result.hex()
    
    # =========================================================================
    # Vault Witnesses (3 spending paths)
    # =========================================================================
    
    @classmethod
    def vault_admin_unconditional(cls, signature: bytes) -> str:
        """
        Encode witness for Admin Unconditional path (Left).
        
        Used to drain the vault and deactivate the delegate.
        
        Witness structure: Either<Sig, Either<Sig, Sig>>
        Left(sig) = 0 + sig(512 bits) + 7 padding = 520 bits = 65 bytes
        """
        sig_bits = cls._signature_to_bits(signature)
        witness_bits = '0' + sig_bits + '0000000'  # Left tag + sig + 7 padding
        return cls._bits_to_hex(witness_bits)
    
    @classmethod
    def vault_admin_issue(cls, signature: bytes) -> str:
        """
        Encode witness for Admin Issue Certificate path (Right-Left).
        
        Admin issues certificate with covenant enforcement.
        
        Witness structure: Either<Sig, Either<Sig, Sig>>
        Right(Left(sig)) = 10 + sig(512 bits) + 6 padding = 520 bits = 65 bytes
        """
        sig_bits = cls._signature_to_bits(signature)
        witness_bits = '10' + sig_bits + '000000'  # Right-Left tags + sig + 6 padding
        return cls._bits_to_hex(witness_bits)
    
    @classmethod
    def vault_delegate_issue(cls, signature: bytes) -> str:
        """
        Encode witness for Delegate Issue Certificate path (Right-Right).
        
        Delegate issues certificate with covenant enforcement.
        
        Witness structure: Either<Sig, Either<Sig, Sig>>
        Right(Right(sig)) = 11 + sig(512 bits) + 6 padding = 520 bits = 65 bytes
        """
        sig_bits = cls._signature_to_bits(signature)
        witness_bits = '11' + sig_bits + '000000'  # Right-Right tags + sig + 6 padding
        return cls._bits_to_hex(witness_bits)
    
    # =========================================================================
    # Certificate Witnesses (2 spending paths)
    # =========================================================================
    
    @classmethod
    def certificate_admin(cls, signature: bytes) -> str:
        """
        Encode witness for Admin revocation path (Left).
        
        Witness structure: Either<Sig, Sig>
        Left(sig) = 0 + sig(512 bits) + 7 padding = 520 bits = 65 bytes
        """
        sig_bits = cls._signature_to_bits(signature)
        witness_bits = '0' + sig_bits + '0000000'  # Left tag + sig + 7 padding
        return cls._bits_to_hex(witness_bits)
    
    @classmethod
    def certificate_delegate(cls, signature: bytes) -> str:
        """
        Encode witness for Delegate revocation path (Right).
        
        Witness structure: Either<Sig, Sig>
        Right(sig) = 1 + sig(512 bits) + 7 padding = 520 bits = 65 bytes
        """
        sig_bits = cls._signature_to_bits(signature)
        witness_bits = '1' + sig_bits + '0000000'  # Right tag + sig + 7 padding
        return cls._bits_to_hex(witness_bits)
    
    # =========================================================================
    # Dummy Witnesses (for sig_all_hash extraction)
    # =========================================================================
    
    @classmethod
    def vault_dummy(cls, path: Literal["admin_unconditional", "admin_issue", "delegate_issue"]) -> str:
        """
        Create dummy witness for extracting sig_all_hash.
        
        The dummy witness has the correct path tags but zero signature.
        """
        dummy_sig = b'\x00' * 64
        
        if path == "admin_unconditional":
            return cls.vault_admin_unconditional(dummy_sig)
        elif path == "admin_issue":
            return cls.vault_admin_issue(dummy_sig)
        else:
            return cls.vault_delegate_issue(dummy_sig)
    
    @classmethod
    def certificate_dummy(cls, path: Literal["admin", "delegate"]) -> str:
        """
        Create dummy witness for extracting sig_all_hash.
        """
        dummy_sig = b'\x00' * 64
        
        if path == "admin":
            return cls.certificate_admin(dummy_sig)
        else:
            return cls.certificate_delegate(dummy_sig)
    
    # =========================================================================
    # High-Level Methods
    # =========================================================================
    
    @classmethod
    def encode_vault_witness(
        cls,
        signature: bytes,
        issuer: Literal["admin", "delegate"],
        unconditional: bool = False
    ) -> str:
        """
        Encode vault witness for any spending path.
        
        Args:
            signature: 64-byte Schnorr signature.
            issuer: "admin" or "delegate".
            unconditional: If True and issuer is admin, use unconditional path.
        
        Returns:
            Hex-encoded witness.
        """
        if issuer == "admin":
            if unconditional:
                return cls.vault_admin_unconditional(signature)
            else:
                return cls.vault_admin_issue(signature)
        else:
            return cls.vault_delegate_issue(signature)
    
    @classmethod
    def encode_certificate_witness(
        cls,
        signature: bytes,
        revoker: Literal["admin", "delegate"]
    ) -> str:
        """
        Encode certificate witness for revocation.
        
        Args:
            signature: 64-byte Schnorr signature.
            revoker: "admin" or "delegate".
        
        Returns:
            Hex-encoded witness.
        """
        if revoker == "admin":
            return cls.certificate_admin(signature)
        else:
            return cls.certificate_delegate(signature)
