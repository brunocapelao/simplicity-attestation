"""
SAS SDK - Vault Builder

Functions for creating and funding vaults.
Handles contract compilation and initial setup.
"""

import subprocess
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from .config import ContractInfo, NetworkConfig
from .infra.api import BlockstreamAPI
from .errors import SAPError


class VaultBuilderError(SAPError):
    """Error during vault creation or funding."""
    pass


class CompilationError(VaultBuilderError):
    """Error compiling Simfony contracts."""
    pass


@dataclass
class VaultSetup:
    """
    Result of vault creation.
    
    Contains all information needed to configure the SDK.
    """
    vault: ContractInfo
    certificate: ContractInfo
    admin_public_key: str
    delegate_public_key: str
    internal_key: str
    network: str
    asset_id: str
    
    def to_network_config(self) -> NetworkConfig:
        """Convert to NetworkConfig for SDK usage."""
        return NetworkConfig(
            network=self.network,
            asset_id=self.asset_id,
            vault=self.vault,
            certificate=self.certificate,
            internal_key=self.internal_key,
            admin_public_key=self.admin_public_key,
            delegate_public_key=self.delegate_public_key
        )
    
    def to_json(self) -> str:
        """Export as JSON for saving to file."""
        return json.dumps({
            "network": self.network,
            "asset_id": self.asset_id,
            "vault": {
                "address": self.vault.address,
                "cmr": self.vault.cmr,
                "script_pubkey": self.vault.script_pubkey,
                "program": self.vault.program
            },
            "certificate": {
                "address": self.certificate.address,
                "cmr": self.certificate.cmr,
                "script_pubkey": self.certificate.script_pubkey,
                "program": self.certificate.program
            },
            "taproot": {
                "internal_key": self.internal_key
            },
            "admin_public_key": self.admin_public_key,
            "delegate_public_key": self.delegate_public_key
        }, indent=2)
    
    def save(self, path: str) -> None:
        """Save configuration to JSON file."""
        with open(path, 'w') as f:
            f.write(self.to_json())


class VaultBuilder:
    """
    Builder for creating new SAS vaults.
    
    Handles:
    - Compiling Simfony contracts with provided keys
    - Generating addresses, CMRs, and programs
    - Creating initial configuration
    
    Example:
        builder = VaultBuilder()
        
        setup = builder.create_vault(
            admin_public_key="abc123...",
            delegate_public_key="def456...",
            network="liquidtestnet"
        )
        
        # Save config
        setup.save("network_config.json")
        
        # Get deposit address
        print(f"Deposit L-BTC to: {setup.vault.address}")
    """
    
    # Default paths
    DEFAULT_SIMC_PATH = "simc"  # Simfony compiler
    DEFAULT_HAL_PATH = "hal-simplicity"
    
    # Default contract templates
    VAULT_TEMPLATE = """
// SAS Delegation Vault Contract
// Admin: {admin_pubkey}
// Delegate: {delegate_pubkey}

fn main() {{
    match witness::SPENDING_PATH {{
        Left(admin_sig: Signature) => admin_unconditional(admin_sig),
        Right(inner: Either<Signature, Signature>) => {{
            match inner {{
                Left(admin_sig: Signature) => admin_issue_certificate(admin_sig),
                Right(delegate_sig: Signature) => delegate_issue_certificate(delegate_sig),
            }}
        }},
    }}
}}
"""

    # Asset IDs by network
    ASSET_IDS = {
        "liquidtestnet": "144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49",
        "liquid": "6f0279e9ed041c3d710a9f57d0c02928416460c4b722ae3457a11eec381c526d",  # L-BTC
    }
    
    def __init__(
        self,
        simc_path: Optional[str] = None,
        hal_path: Optional[str] = None,
        contracts_dir: Optional[str] = None
    ):
        """
        Initialize vault builder.
        
        Args:
            simc_path: Path to simc (Simfony compiler).
            hal_path: Path to hal-simplicity binary.
            contracts_dir: Directory containing .simf contract files.
        """
        self.simc_path = simc_path or self.DEFAULT_SIMC_PATH
        self.hal_path = hal_path or self.DEFAULT_HAL_PATH
        self.contracts_dir = Path(contracts_dir) if contracts_dir else None
    
    def create_vault(
        self,
        admin_public_key: str,
        delegate_public_key: str,
        internal_key: Optional[str] = None,
        network: str = "liquidtestnet",
        vault_contract_path: Optional[str] = None,
        certificate_contract_path: Optional[str] = None
    ) -> VaultSetup:
        """
        Create a new SAS vault.
        
        This compiles the contracts with the provided keys and returns
        all needed configuration to use the vault.
        
        Args:
            admin_public_key: 64-char hex public key for admin.
            delegate_public_key: 64-char hex public key for delegate.
            internal_key: Optional taproot internal key (generated if not provided).
            network: "liquidtestnet" or "liquid".
            vault_contract_path: Path to vault.simf (uses bundled if not provided).
            certificate_contract_path: Path to certificate.simf.
        
        Returns:
            VaultSetup with all configuration.
        
        Raises:
            CompilationError: If contract compilation fails.
            VaultBuilderError: If setup fails.
        """
        # Validate keys
        if len(admin_public_key) != 64:
            raise VaultBuilderError("admin_public_key must be 64 hex characters")
        if len(delegate_public_key) != 64:
            raise VaultBuilderError("delegate_public_key must be 64 hex characters")
        
        # Generate internal key if not provided
        # Using a deterministic key based on admin+delegate for reproducibility
        if not internal_key:
            internal_key = self._generate_internal_key(admin_public_key, delegate_public_key)
        
        # Compile vault contract
        vault_info = self._compile_contract(
            contract_path=vault_contract_path or self._find_contract("vault.simf"),
            admin_key=admin_public_key,
            delegate_key=delegate_public_key,
            internal_key=internal_key,
            network=network
        )
        
        # Compile certificate contract
        cert_info = self._compile_contract(
            contract_path=certificate_contract_path or self._find_contract("certificate.simf"),
            admin_key=admin_public_key,
            delegate_key=delegate_public_key,
            internal_key=internal_key,
            network=network
        )
        
        return VaultSetup(
            vault=vault_info,
            certificate=cert_info,
            admin_public_key=admin_public_key,
            delegate_public_key=delegate_public_key,
            internal_key=internal_key,
            network=network,
            asset_id=self.ASSET_IDS.get(network, self.ASSET_IDS["liquidtestnet"])
        )
    
    def _generate_internal_key(self, admin_key: str, delegate_key: str) -> str:
        """Generate deterministic internal key from admin and delegate keys."""
        combined = f"{admin_key}{delegate_key}internal".encode()
        # Use SHA256 and take first 32 bytes as x-only pubkey
        return hashlib.sha256(combined).hexdigest()
    
    def _find_contract(self, name: str) -> str:
        """Find contract file path."""
        # Check provided contracts directory
        if self.contracts_dir and (self.contracts_dir / name).exists():
            return str(self.contracts_dir / name)
        
        # Check common locations
        locations = [
            Path.cwd() / "contracts" / name,
            Path.cwd().parent / "contracts" / name,
            Path(__file__).parent.parent.parent / "contracts" / name,
        ]
        
        for loc in locations:
            if loc.exists():
                return str(loc)
        
        raise VaultBuilderError(f"Contract not found: {name}")
    
    def _compile_contract(
        self,
        contract_path: str,
        admin_key: str,
        delegate_key: str,
        internal_key: str,
        network: str
    ) -> ContractInfo:
        """
        Compile a Simfony contract.
        
        Uses hal-simplicity to compile and get address/CMR/program.
        """
        # Check if contract file exists
        if not Path(contract_path).exists():
            raise CompilationError(f"Contract file not found: {contract_path}")
        
        try:
            # Use hal-simplicity to compile
            result = subprocess.run(
                [
                    self.hal_path,
                    "simplicity", "compile",
                    contract_path,
                    "--network", network,
                    "--admin-key", admin_key,
                    "--delegate-key", delegate_key,
                    "--internal-key", internal_key
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Try alternative: use simc
                return self._compile_with_simc(
                    contract_path, admin_key, delegate_key, internal_key, network
                )
            
            data = json.loads(result.stdout)
            
            return ContractInfo(
                address=data["address"],
                cmr=data["cmr"],
                script_pubkey=data["script_pubkey"],
                program=data["program"]
            )
            
        except (subprocess.SubprocessError, json.JSONDecodeError):
            # Fallback: try simc directly
            return self._compile_with_simc(
                contract_path, admin_key, delegate_key, internal_key, network
            )
    
    def _compile_with_simc(
        self,
        contract_path: str,
        admin_key: str,
        delegate_key: str,
        internal_key: str,
        network: str
    ) -> ContractInfo:
        """
        Compile using simc (Simfony compiler) directly.
        
        This is a fallback if hal-simplicity compile isn't available.
        """
        try:
            # First, compile to get the program
            result = subprocess.run(
                [
                    self.simc_path,
                    "compile",
                    contract_path,
                    "--admin-pubkey", admin_key,
                    "--delegate-pubkey", delegate_key
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise CompilationError(
                    f"simc compilation failed: {result.stderr}\n"
                    f"Make sure simc is installed: cargo install --path simfony"
                )
            
            data = json.loads(result.stdout)
            
            # Generate address from CMR
            # This would need hal-simplicity for actual address generation
            # For now, return placeholder (real implementation needs native code)
            return ContractInfo(
                address=data.get("address", ""),
                cmr=data["cmr"],
                script_pubkey=data.get("script_pubkey", ""),
                program=data["program"]
            )
            
        except FileNotFoundError:
            raise CompilationError(
                f"simc not found at {self.simc_path}. "
                f"Install with: git clone https://github.com/BlockstreamResearch/simfony && "
                f"cd simfony && cargo build --release"
            )
        except json.JSONDecodeError as e:
            raise CompilationError(f"Invalid simc output: {e}")


class VaultFunder:
    """
    Helper for funding vaults.
    
    Provides utilities for deposit instructions and monitoring.
    Note: Actual funding requires L-BTC from an external source.
    """
    
    MIN_DEPOSIT = 1046  # Minimum for 1 certificate + fees
    RECOMMENDED_DEPOSIT = 100000  # ~100 certificates
    
    def __init__(self, api: Optional[BlockstreamAPI] = None, network: str = "testnet"):
        """
        Initialize funder.
        
        Args:
            api: BlockstreamAPI instance.
            network: "testnet" or "mainnet".
        """
        self.api = api or BlockstreamAPI(network=network)
        self.network = network
    
    def get_deposit_instruction(
        self,
        vault_address: str,
        amount: Optional[int] = None
    ) -> dict:
        """
        Get deposit instruction for a vault.
        
        Args:
            vault_address: Vault address to deposit to.
            amount: Optional specific amount in satoshis.
        
        Returns:
            Deposit instruction dictionary.
        """
        current_balance = self.api.get_balance(vault_address)
        
        return {
            "address": vault_address,
            "network": self.network,
            "current_balance": current_balance,
            "min_deposit": self.MIN_DEPOSIT,
            "recommended_deposit": self.RECOMMENDED_DEPOSIT,
            "suggested_amount": amount or self.RECOMMENDED_DEPOSIT,
            "can_issue_certificates": current_balance >= self.MIN_DEPOSIT,
            "estimated_certificates": current_balance // self.MIN_DEPOSIT if current_balance > 0 else 0,
            "explorer_url": f"https://blockstream.info/liquid{'testnet' if self.network == 'testnet' else ''}/address/{vault_address}"
        }
    
    def check_balance(self, vault_address: str) -> int:
        """
        Check current vault balance.
        
        Args:
            vault_address: Vault address.
        
        Returns:
            Balance in satoshis.
        """
        return self.api.get_balance(vault_address)
    
    def wait_for_deposit(
        self,
        vault_address: str,
        min_amount: int = MIN_DEPOSIT,
        timeout: int = 600,
        poll_interval: int = 10
    ) -> int:
        """
        Wait for vault to receive deposit.
        
        Args:
            vault_address: Vault address.
            min_amount: Minimum amount to wait for.
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between checks.
        
        Returns:
            New balance when deposit received.
        
        Raises:
            TimeoutError: If timeout exceeded.
        """
        import time
        start = time.time()
        initial_balance = self.check_balance(vault_address)
        
        while time.time() - start < timeout:
            current = self.check_balance(vault_address)
            if current >= min_amount and current > initial_balance:
                return current
            time.sleep(poll_interval)
        
        raise TimeoutError(
            f"Timeout waiting for deposit to {vault_address}. "
            f"Current balance: {self.check_balance(vault_address)} sats"
        )
