"""
SAP SDK - Data Models

Core data structures used throughout the SDK.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Literal
from enum import Enum


class CertificateStatus(Enum):
    """Certificate validity status."""
    VALID = "valid"
    REVOKED = "revoked"
    UNKNOWN = "unknown"


class IssuerType(Enum):
    """Who can issue/revoke certificates."""
    ADMIN = "admin"
    DELEGATE = "delegate"


class SpendingPath(Enum):
    """Vault spending paths."""
    ADMIN_UNCONDITIONAL = "left"           # Admin drains vault
    ADMIN_ISSUE = "right_left"             # Admin issues certificate
    DELEGATE_ISSUE = "right_right"         # Delegate issues certificate


@dataclass
class UTXO:
    """Unspent Transaction Output."""
    txid: str
    vout: int
    value: int  # satoshis
    asset: Optional[str] = None
    script_pubkey: Optional[str] = None
    
    @property
    def outpoint(self) -> str:
        """Return txid:vout format."""
        return f"{self.txid}:{self.vout}"
    
    def to_dict(self) -> dict:
        return {"txid": self.txid, "vout": self.vout}


@dataclass
class Certificate:
    """Represents a SAP certificate."""
    txid: str
    vout: int
    cid: str
    status: CertificateStatus = CertificateStatus.UNKNOWN
    issued_at: Optional[int] = None  # block height
    revoked_at: Optional[int] = None
    issuer: Optional[IssuerType] = None
    value: int = 546  # satoshis (dust limit)
    
    @property
    def outpoint(self) -> str:
        """Return txid:vout format."""
        return f"{self.txid}:{self.vout}"
    
    @property
    def is_valid(self) -> bool:
        """Check if certificate is valid (not revoked)."""
        return self.status == CertificateStatus.VALID


@dataclass
class Vault:
    """Represents a SAP delegation vault."""
    address: str
    script_pubkey: str
    cmr: str
    program: str
    balance: int = 0  # total satoshis
    utxos: List[UTXO] = field(default_factory=list)
    
    @property
    def can_issue(self) -> bool:
        """Check if vault has enough funds to issue a certificate."""
        MIN_REQUIRED = 546 + 500  # cert dust + fee
        return self.balance >= MIN_REQUIRED
    
    @property
    def available_utxo(self) -> Optional[UTXO]:
        """Get the first available UTXO for spending."""
        return self.utxos[0] if self.utxos else None


@dataclass
class TransactionResult:
    """Result of a transaction operation."""
    success: bool
    txid: Optional[str] = None
    raw_hex: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def explorer_url(self) -> Optional[str]:
        """Get Blockstream explorer URL for this transaction."""
        if self.txid:
            return f"https://blockstream.info/liquidtestnet/tx/{self.txid}"
        return None


@dataclass
class JetResult:
    """Result from a Simplicity jet execution."""
    jet: str
    success: bool
    output_value: Optional[str] = None


@dataclass
class RunResult:
    """Result from running a Simplicity program."""
    success: bool
    jets: List[JetResult] = field(default_factory=list)
    sig_all_hash: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "RunResult":
        """Create from hal-simplicity JSON output."""
        jets = []
        sig_all_hash = None
        
        for jet_data in data.get("jets", []):
            jet = JetResult(
                jet=jet_data.get("jet", ""),
                success=jet_data.get("success", True),
                output_value=jet_data.get("output_value")
            )
            jets.append(jet)
            
            if jet.jet == "sig_all_hash" and jet.output_value:
                sig_all_hash = jet.output_value.replace("0x", "")
        
        return cls(
            success=data.get("success", False),
            jets=jets,
            sig_all_hash=sig_all_hash
        )
