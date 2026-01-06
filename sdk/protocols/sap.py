"""
SAP SDK - SAP Protocol Implementation

Encoder and decoder for the SAP OP_RETURN protocol.
"""

from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class SAPAttest:
    """SAP Attestation payload."""
    cid: str
    version: int = 1


@dataclass
class SAPRevoke:
    """SAP Revocation payload."""
    txid: str
    vout: int
    version: int = 1


@dataclass
class SAPUpdate:
    """SAP Update payload."""
    cid: str
    version: int = 1


class SAPProtocol:
    """
    SAP OP_RETURN Protocol Implementation.
    
    Format:
    ┌───────┬─────────┬──────────┬─────────────────────────────────────┐
    │  TAG  │ VERSION │   TYPE   │             PAYLOAD                 │
    │ "SAP" │  0x01   │  0x01    │   IPFS CID (variable)               │
    ├───────┼─────────┼──────────┼─────────────────────────────────────┤
    │3 bytes│ 1 byte  │  1 byte  │           variable                  │
    └───────┴─────────┴──────────┴─────────────────────────────────────┘
    """
    
    MAGIC = b"SAP"
    VERSION = 0x01
    
    # Operation types
    TYPE_ATTEST = 0x01
    TYPE_REVOKE = 0x02
    TYPE_UPDATE = 0x03
    TYPE_DELEGATE = 0x10
    TYPE_UNDELEGATE = 0x11
    
    @classmethod
    def encode_attest(cls, cid: str) -> str:
        """
        Encode an attestation OP_RETURN payload.
        
        Args:
            cid: IPFS CID or content hash.
        
        Returns:
            Hex-encoded SAP payload.
        """
        header = cls.MAGIC + bytes([cls.VERSION, cls.TYPE_ATTEST])
        
        # Encode CID - try as hex first, then as UTF-8
        try:
            cid_bytes = bytes.fromhex(cid)
        except ValueError:
            cid_bytes = cid.encode('utf-8')
        
        return (header + cid_bytes).hex()
    
    @classmethod
    def encode_revoke(cls, txid: str, vout: int) -> str:
        """
        Encode a revocation OP_RETURN payload.
        
        Args:
            txid: Transaction ID of the certificate to revoke.
            vout: Output index of the certificate.
        
        Returns:
            Hex-encoded SAP payload.
        """
        header = cls.MAGIC + bytes([cls.VERSION, cls.TYPE_REVOKE])
        txid_bytes = bytes.fromhex(txid)
        vout_bytes = vout.to_bytes(2, 'big')
        
        return (header + txid_bytes + vout_bytes).hex()
    
    @classmethod
    def encode_update(cls, cid: str) -> str:
        """
        Encode an update OP_RETURN payload.
        
        Args:
            cid: New IPFS CID.
        
        Returns:
            Hex-encoded SAP payload.
        """
        header = cls.MAGIC + bytes([cls.VERSION, cls.TYPE_UPDATE])
        
        try:
            cid_bytes = bytes.fromhex(cid)
        except ValueError:
            cid_bytes = cid.encode('utf-8')
        
        return (header + cid_bytes).hex()
    
    @classmethod
    def decode(cls, data: bytes) -> Optional[Union[SAPAttest, SAPRevoke, SAPUpdate]]:
        """
        Decode a SAP OP_RETURN payload.
        
        Args:
            data: Raw OP_RETURN data bytes.
        
        Returns:
            Decoded SAP object or None if invalid.
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
            if len(payload) < 34:
                return None
            txid = payload[:32].hex()
            vout = int.from_bytes(payload[32:34], 'big')
            return SAPRevoke(txid=txid, vout=vout, version=version)
        
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
        Decode a hex-encoded SAP OP_RETURN payload.
        
        Args:
            hex_data: Hex-encoded OP_RETURN data.
        
        Returns:
            Decoded SAP object or None if invalid.
        """
        try:
            data = bytes.fromhex(hex_data)
            return cls.decode(data)
        except ValueError:
            return None
    
    @classmethod
    def is_sap_payload(cls, data: bytes) -> bool:
        """Check if data is a valid SAP payload."""
        return len(data) >= 5 and data[:3] == cls.MAGIC
