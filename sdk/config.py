"""
SAS SDK - Configuration Management

Handles loading and managing SDK configuration.
Separates public configuration from private keys for security.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ContractInfo:
    """
    Compiled contract information (PUBLIC).
    
    All fields are safe to commit to version control.
    """
    address: str
    cmr: str
    script_pubkey: str
    program: str


@dataclass
class NetworkConfig:
    """
    Network and contract configuration (PUBLIC).
    
    This configuration contains no private keys and is safe
    to commit to version control or share publicly.
    """
    network: str
    asset_id: str
    vault: ContractInfo
    certificate: ContractInfo
    internal_key: str
    hal_binary: str = "hal-simplicity"
    api_base_url: str = "https://blockstream.info/liquidtestnet/api"
    admin_public_key: Optional[str] = None
    delegate_public_key: Optional[str] = None
    
    @classmethod
    def from_file(cls, path: str) -> "NetworkConfig":
        """
        Load network configuration from JSON file.
        
        The file should NOT contain private keys.
        
        Example network_config.json:
        {
            "network": "liquidtestnet",
            "asset_id": "144c...",
            "vault": {"address": "tex1...", "cmr": "...", ...},
            "certificate": {"address": "tex1...", ...},
            "taproot": {"internal_key": "..."},
            "admin_public_key": "abc123...",
            "delegate_public_key": "def456..."
        }
        """
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(config_path) as f:
            data = json.load(f)
        
        return cls(
            network=data.get("network", "liquidtestnet"),
            asset_id=data["asset_id"],
            vault=ContractInfo(
                address=data["vault"]["address"],
                cmr=data["vault"]["cmr"],
                script_pubkey=data["vault"]["script_pubkey"],
                program=data["vault"]["program"]
            ),
            certificate=ContractInfo(
                address=data["certificate"]["address"],
                cmr=data["certificate"]["cmr"],
                script_pubkey=data["certificate"]["script_pubkey"],
                program=data["certificate"]["program"]
            ),
            internal_key=data["taproot"]["internal_key"],
            hal_binary=data.get("hal_binary", cls.hal_binary),
            api_base_url=data.get("api_base_url", cls.api_base_url),
            admin_public_key=data.get("admin_public_key") or data.get("admin", {}).get("public_key"),
            delegate_public_key=data.get("delegate_public_key") or data.get("delegate", {}).get("public_key")
        )


# =============================================================================
# Legacy support - to be deprecated
# =============================================================================

@dataclass
class KeyPair:
    """
    Public/private key pair.
    
    DEPRECATED: Use KeyProvider instead for private key management.
    This class is kept for backward compatibility with secrets.json.
    """
    name: str
    private_key: str
    public_key: str


@dataclass
class SASConfig:
    """
    Full SAS configuration including keys.
    
    DEPRECATED for new code: Use NetworkConfig + KeyProvider instead.
    
    This class is maintained for backward compatibility with existing
    code that uses secrets.json with embedded keys.
    """
    network: str
    asset_id: str
    admin: KeyPair
    delegate: KeyPair
    vault: ContractInfo
    certificate: ContractInfo
    internal_key: str
    hal_binary: str = "hal-simplicity"
    api_base_url: str = "https://blockstream.info/liquidtestnet/api"
    
    @classmethod
    def from_file(cls, path: str) -> "SASConfig":
        """Load configuration from secrets.json file (legacy format)."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(config_path) as f:
            data = json.load(f)
        
        return cls(
            network=data.get("network", "liquidtestnet"),
            asset_id=data["asset_id"],
            admin=KeyPair(
                name=data["admin"]["name"],
                private_key=data["admin"]["private_key"],
                public_key=data["admin"]["public_key"]
            ),
            delegate=KeyPair(
                name=data["delegate"]["name"],
                private_key=data["delegate"]["private_key"],
                public_key=data["delegate"]["public_key"]
            ),
            vault=ContractInfo(
                address=data["vault"]["address"],
                cmr=data["vault"]["cmr"],
                script_pubkey=data["vault"]["script_pubkey"],
                program=data["vault"]["program"]
            ),
            certificate=ContractInfo(
                address=data["certificate"]["address"],
                cmr=data["certificate"]["cmr"],
                script_pubkey=data["certificate"]["script_pubkey"],
                program=data["certificate"]["program"]
            ),
            internal_key=data["taproot"]["internal_key"]
        )
    
    def to_network_config(self) -> NetworkConfig:
        """Convert to NetworkConfig (strips private keys)."""
        return NetworkConfig(
            network=self.network,
            asset_id=self.asset_id,
            vault=self.vault,
            certificate=self.certificate,
            internal_key=self.internal_key,
            hal_binary=self.hal_binary,
            api_base_url=self.api_base_url,
            admin_public_key=self.admin.public_key,
            delegate_public_key=self.delegate.public_key
        )
    
    def get_key(self, role: str) -> KeyPair:
        """Get key pair by role name."""
        if role.lower() in ("admin", "alice"):
            return self.admin
        elif role.lower() in ("delegate", "bob"):
            return self.delegate
        else:
            raise ValueError(f"Unknown role: {role}")
