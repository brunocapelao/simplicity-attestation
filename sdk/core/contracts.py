"""
SAP SDK - Contract Registry

Manages contract information and provides contract-specific utilities.
"""

from dataclasses import dataclass
from typing import Optional

from ..config import SAPConfig


@dataclass
class Contract:
    """A Simplicity contract with all its metadata."""
    name: str
    address: str
    script_pubkey: str
    cmr: str
    program: str
    
    def sats_to_btc(self, sats: int) -> str:
        """Convert satoshis to BTC string format."""
        return f"{sats / 100_000_000:.8f}"


class ContractRegistry:
    """
    Registry of SAP contracts.
    
    Provides access to vault and certificate contract information.
    """
    
    def __init__(self, config: SAPConfig):
        """
        Initialize registry from config.
        
        Args:
            config: SAP configuration.
        """
        self.config = config
        
        self._vault = Contract(
            name="vault",
            address=config.vault.address,
            script_pubkey=config.vault.script_pubkey,
            cmr=config.vault.cmr,
            program=config.vault.program
        )
        
        self._certificate = Contract(
            name="certificate",
            address=config.certificate.address,
            script_pubkey=config.certificate.script_pubkey,
            cmr=config.certificate.cmr,
            program=config.certificate.program
        )
    
    @property
    def vault(self) -> Contract:
        """Get vault contract."""
        return self._vault
    
    @property
    def certificate(self) -> Contract:
        """Get certificate contract."""
        return self._certificate
    
    @property
    def asset_id(self) -> str:
        """Get the asset ID (L-BTC on testnet)."""
        return self.config.asset_id
    
    @property
    def internal_key(self) -> str:
        """Get the Taproot internal key."""
        return self.config.internal_key
    
    def get_contract(self, name: str) -> Optional[Contract]:
        """
        Get contract by name.
        
        Args:
            name: "vault" or "certificate".
        
        Returns:
            Contract or None if not found.
        """
        if name == "vault":
            return self._vault
        elif name == "certificate":
            return self._certificate
        return None
