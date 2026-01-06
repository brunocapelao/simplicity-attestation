"""
SAP SDK - Configuration Management

Handles loading and managing SDK configuration from secrets.json.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class KeyPair:
    """Public/private key pair."""
    name: str
    private_key: str
    public_key: str


@dataclass
class ContractInfo:
    """Compiled contract information."""
    address: str
    cmr: str
    script_pubkey: str
    program: str


@dataclass
class SAPConfig:
    """SAP system configuration."""
    network: str
    asset_id: str
    admin: KeyPair
    delegate: KeyPair
    vault: ContractInfo
    certificate: ContractInfo
    internal_key: str
    hal_binary: str = "/tmp/hal-simplicity-new/target/release/hal-simplicity"
    api_base_url: str = "https://blockstream.info/liquidtestnet/api"
    
    @classmethod
    def from_file(cls, path: str) -> "SAPConfig":
        """Load configuration from secrets.json file."""
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
    
    @classmethod
    def from_dict(cls, data: dict) -> "SAPConfig":
        """Create configuration from dictionary."""
        return cls(
            network=data.get("network", "liquidtestnet"),
            asset_id=data["asset_id"],
            admin=KeyPair(**data["admin"]),
            delegate=KeyPair(**data["delegate"]),
            vault=ContractInfo(**data["vault"]),
            certificate=ContractInfo(**data["certificate"]),
            internal_key=data["taproot"]["internal_key"],
            hal_binary=data.get("hal_binary", cls.hal_binary),
            api_base_url=data.get("api_base_url", cls.api_base_url)
        )
    
    def get_key(self, role: str) -> KeyPair:
        """Get key pair by role name."""
        if role.lower() in ("admin", "alice"):
            return self.admin
        elif role.lower() in ("delegate", "bob"):
            return self.delegate
        else:
            raise ValueError(f"Unknown role: {role}")
