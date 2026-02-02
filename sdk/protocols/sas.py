"""
SAS SDK - SAS Protocol Implementation

Encoder and decoder for the SAS OP_RETURN protocol.
"""

from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class SAPAttest:
    """SAS Attestation payload."""
    cid: str
    version: int = 1


@dataclass
class SAPRevoke:
    """SAS Revocation payload."""
    txid: str
    vout: int
    reason_code: Optional[int] = None
    replacement_txid: Optional[str] = None
    version: int = 1


@dataclass
class SAPUpdate:
    """SAS Update payload."""
    cid: str
    version: int = 1


class SAPProtocol:
    """
    SAS OP_RETURN Protocol Implementation.
    
    Format:
    ┌───────┬─────────┬──────────┬─────────────────────────────────────┐
    │  TAG  │ VERSION │   TYPE   │             PAYLOAD                 │
    │ "SAS" │  0x01   │  0x01    │   IPFS CID (variable)               │
    ├───────┼─────────┼──────────┼─────────────────────────────────────┤
    │3 bytes│ 1 byte  │  1 byte  │           variable                  │
    └───────┴─────────┴──────────┴─────────────────────────────────────┘
    """
    
    MAGIC = b"SAS"
    VERSION = 0x01
    
    # Operation types
    TYPE_ATTEST = 0x01
    TYPE_REVOKE = 0x02
    TYPE_UPDATE = 0x03
    TYPE_DELEGATE = 0x10
    TYPE_UNDELEGATE = 0x11

    # Revocation reason codes (optional 1-byte extension)
    REVOKE_REASON_CODES = {
        1: "DATA_ERROR",
        2: "DUPLICATE",
        3: "FRAUD_SUSPECTED",
        4: "FRAUD_CONFIRMED",
        5: "HOLDER_REQUEST",
        6: "REISSUE_REPLACEMENT",
        7: "ADMINISTRATIVE",
        8: "LEGAL_ORDER",
        9: "KEY_COMPROMISE",
        10: "SUSPENDED",
        11: "CRYPTO_DEPRECATED",
        12: "PROCESS_ERROR",
        13: "RESERVED",
        14: "RESERVED",
        15: "RESERVED",
    }
    
    # OP_RETURN size limits
    MAX_OP_RETURN_SIZE = 80  # Maximum OP_RETURN data size
    HEADER_SIZE = 5          # 3 (magic) + 1 (version) + 1 (type)
    MAX_PAYLOAD_SIZE = MAX_OP_RETURN_SIZE - HEADER_SIZE  # 75 bytes for payload
    
    class PayloadTooLargeError(Exception):
        """Raised when payload exceeds OP_RETURN size limit."""
        pass
    
    @classmethod
    def validate_payload_size(cls, payload: bytes, payload_type: str = "payload") -> None:
        """
        Validate that payload doesn't exceed OP_RETURN limits.
        
        Args:
            payload: The payload bytes to validate.
            payload_type: Description for error message.
        
        Raises:
            PayloadTooLargeError: If payload exceeds 75 bytes.
        """
        if len(payload) > cls.MAX_PAYLOAD_SIZE:
            raise cls.PayloadTooLargeError(
                f"{payload_type} is {len(payload)} bytes, exceeds maximum of "
                f"{cls.MAX_PAYLOAD_SIZE} bytes for OP_RETURN"
            )
    
    @classmethod
    def encode_attest(cls, cid: str, validate: bool = True) -> str:
        """
        Encode an attestation OP_RETURN payload.
        
        Args:
            cid: IPFS CID or content hash.
            validate: If True, validates payload size (default: True).
        
        Returns:
            Hex-encoded SAS payload.
        
        Raises:
            PayloadTooLargeError: If CID exceeds 75 bytes.
        """
        header = cls.MAGIC + bytes([cls.VERSION, cls.TYPE_ATTEST])
        
        # Encode CID - try as hex first, then as UTF-8
        try:
            cid_bytes = bytes.fromhex(cid)
        except ValueError:
            cid_bytes = cid.encode('utf-8')
        
        # Validate size
        if validate:
            cls.validate_payload_size(cid_bytes, "CID")
        
        return (header + cid_bytes).hex()
    
    @classmethod
    def encode_revoke(
        cls,
        txid: str,
        vout: int,
        reason_code: Optional[int] = None,
        replacement_txid: Optional[str] = None
    ) -> str:
        """
        Encode a revocation OP_RETURN payload.
        
        Args:
            txid: Transaction ID of the certificate to revoke.
            vout: Output index of the certificate.
            reason_code: Optional small integer reason code (0-255).
            replacement_txid: Optional txid for replacement certificate.
        
        Returns:
            Hex-encoded SAS payload.
        """
        header = cls.MAGIC + bytes([cls.VERSION, cls.TYPE_REVOKE])
        txid_bytes = bytes.fromhex(txid)
        vout_bytes = vout.to_bytes(2, 'big')
        payload = txid_bytes + vout_bytes

        if reason_code is not None:
            if not (0 <= reason_code <= 255):
                raise ValueError("reason_code must be between 0 and 255")
            payload += bytes([reason_code])

        if replacement_txid is not None:
            if reason_code is None:
                raise ValueError("replacement_txid requires reason_code")
            if len(replacement_txid) != 64:
                raise ValueError("replacement_txid must be 64 hex characters")
            payload += bytes.fromhex(replacement_txid)

        cls.validate_payload_size(payload, "REVOKE payload")
        return (header + payload).hex()
    
    @classmethod
    def encode_update(cls, cid: str, validate: bool = True) -> str:
        """
        Encode an update OP_RETURN payload.
        
        Args:
            cid: New IPFS CID.
            validate: If True, validates payload size (default: True).
        
        Returns:
            Hex-encoded SAS payload.
        
        Raises:
            PayloadTooLargeError: If CID exceeds 75 bytes.
        """
        header = cls.MAGIC + bytes([cls.VERSION, cls.TYPE_UPDATE])
        
        try:
            cid_bytes = bytes.fromhex(cid)
        except ValueError:
            cid_bytes = cid.encode('utf-8')
        
        # Validate size
        if validate:
            cls.validate_payload_size(cid_bytes, "CID")
        
        return (header + cid_bytes).hex()
    
    @classmethod
    def decode(cls, data: bytes) -> Optional[Union[SAPAttest, SAPRevoke, SAPUpdate]]:
        """
        Decode a SAS OP_RETURN payload.
        
        Args:
            data: Raw OP_RETURN data bytes.
        
        Returns:
            Decoded SAS object or None if invalid.
        """
        if len(data) < 5:
            return None
        
        # Check magic bytes
        if data[:3] != cls.MAGIC:
            return None
        
        version = data[3]
        op_type = data[4]
        payload = data[5:]
        
        # Only support version 1
        if version != cls.VERSION:
            return None
        
        if op_type == cls.TYPE_ATTEST:
            try:
                cid = payload.decode('utf-8')
            except UnicodeDecodeError:
                cid = payload.hex()
            return SAPAttest(cid=cid, version=version)
        
        elif op_type == cls.TYPE_REVOKE:
            # Minimum payload: 32 (txid) + 2 (vout) = 34 bytes
            if len(payload) < 34:
                return None

            txid = payload[:32].hex()
            vout = int.from_bytes(payload[32:34], 'big')

            reason_code = None
            replacement_txid = None

            # Valid payload lengths:
            # - 34 bytes: txid + vout only
            # - 35 bytes: txid + vout + reason_code
            # - 67 bytes: txid + vout + reason_code + replacement_txid (32 bytes)
            # Anything else (36-66 bytes) is partial/corrupted - reject
            if len(payload) == 34:
                pass  # No reason_code or replacement
            elif len(payload) == 35:
                reason_code = payload[34]
            elif len(payload) == 67:
                reason_code = payload[34]
                replacement_txid = payload[35:67].hex()
            else:
                # Invalid length - partial data or corrupted
                return None

            return SAPRevoke(
                txid=txid,
                vout=vout,
                reason_code=reason_code,
                replacement_txid=replacement_txid,
                version=version
            )
        
        elif op_type == cls.TYPE_UPDATE:
            try:
                cid = payload.decode('utf-8')
            except UnicodeDecodeError:
                cid = payload.hex()
            return SAPUpdate(cid=cid, version=version)
        
        return None
    
    @classmethod
    def decode_hex(cls, hex_data: str) -> Optional[Union[SAPAttest, SAPRevoke, SAPUpdate]]:
        """
        Decode a hex-encoded SAS OP_RETURN payload.
        
        Args:
            hex_data: Hex-encoded OP_RETURN data.
        
        Returns:
            Decoded SAS object or None if invalid.
        """
        try:
            data = bytes.fromhex(hex_data)
            return cls.decode(data)
        except ValueError:
            return None
    
    @classmethod
    def is_sas_payload(cls, data: bytes) -> bool:
        """Check if data is a valid SAS payload."""
        return len(data) >= 5 and data[:3] == cls.MAGIC
