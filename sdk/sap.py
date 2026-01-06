"""
SAP SDK - Simplicity Attestation Protocol

A fully abstracted SDK that handles all complexity internally.

ARCHITECTURE:
    - Vault Creation: Only requires PUBLIC keys (admin + delegate)
    - Operation: Each party uses their OWN private key

Example (Create Vault - Admin setup):
    from sdk import SAP
    
    # Admin creates vault with both pubkeys
    vault_config = SAP.create_vault(
        admin_pubkey="abc123...",
        delegate_pubkey="def456...",
        network="testnet"
    )
    
    # Share vault_config with delegate
    vault_config.save("vault_config.json")
    print(f"Fund: {vault_config.vault_address}")

Example (Admin Operations):
    sap = SAP.as_admin(
        config="vault_config.json",
        private_key="admin_secret..."
    )
    sap.issue_certificate(cid)
    sap.drain_vault(recipient)

Example (Delegate Operations - Different Company):
    sap = SAP.as_delegate(
        config="vault_config.json",
        private_key="delegate_secret..."
    )
    sap.issue_certificate(cid)
"""

import subprocess
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Literal, List, Union
import time

from embit import ec

from .models import Certificate, Vault, TransactionResult, UTXO, CertificateStatus
from .infra.hal import HalSimplicity
from .infra.api import BlockstreamAPI
from .infra.keys import KeyManager
from .core.witness import WitnessEncoder
from .errors import SAPError, VaultEmptyError, InsufficientFundsError


class CompilationError(SAPError):
    """Error compiling Simplicity contracts."""
    pass


class ConfigurationError(SAPError):
    """Error in SDK configuration."""
    pass


class PermissionError(SAPError):
    """Operation not permitted for current role."""
    pass


@dataclass
class VaultConfig:
    """
    Vault configuration - can be shared publicly.
    Contains only PUBLIC information, no private keys.
    """
    network: str
    asset_id: str
    admin_pubkey: str
    delegate_pubkey: str
    vault_address: str
    vault_cmr: str
    vault_program: str
    certificate_address: str
    certificate_cmr: str
    certificate_program: str
    internal_key: str
    
    def save(self, path: str):
        """Save config to JSON file."""
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> "VaultConfig":
        """Load config from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)


class SAP:
    """
    Simplicity Attestation Protocol SDK.
    
    Separates vault creation from operation:
    - create_vault(): Only needs PUBLIC keys
    - as_admin(): Operate as admin with admin's private key
    - as_delegate(): Operate as delegate with delegate's private key
    """
    
    # Network configurations
    NETWORKS = {
        "testnet": {
            "asset_id": "144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49",
            "api_url": "https://blockstream.info/liquidtestnet/api",
            "hal_network": "liquid",
        },
        "mainnet": {
            "asset_id": "6f0279e9ed041c3d710a9f57d0c02928416460c4b722ae3457a11eec381c526d",
            "api_url": "https://blockstream.info/liquid/api",
            "hal_network": "liquid",
        }
    }
    
    INTERNAL_KEY = "50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"
    DEFAULT_HAL_PATH = "/tmp/hal-simplicity-new/target/release/hal-simplicity"
    DEFAULT_SIMC_PATH = "simc"
    
    # =========================================================================
    # Factory Methods
    # =========================================================================
    
    @classmethod
    def create_vault(
        cls,
        admin_pubkey: str,
        delegate_pubkey: str,
        network: str = "testnet",
        hal_path: Optional[str] = None,
        simc_path: Optional[str] = None,
        contracts_dir: Optional[str] = None,
    ) -> VaultConfig:
        """
        Create a new vault configuration.
        
        ONLY requires PUBLIC KEYS - no private keys needed.
        Returns a VaultConfig that can be shared with all parties.
        
        Args:
            admin_pubkey: Admin x-only public key (64 hex chars).
            delegate_pubkey: Delegate x-only public key (64 hex chars).
            network: "testnet" or "mainnet".
        
        Returns:
            VaultConfig with all public information.
        """
        hal_path = hal_path or cls.DEFAULT_HAL_PATH
        simc_path = simc_path or cls.DEFAULT_SIMC_PATH
        contracts_dir = Path(contracts_dir) if contracts_dir else cls._find_contracts_dir()
        network_config = cls.NETWORKS.get(network, cls.NETWORKS["testnet"])
        
        # Update contracts with pubkeys and compile
        vault_data = cls._compile_contract_with_keys(
            contracts_dir / "vault.simf",
            admin_pubkey, delegate_pubkey,
            simc_path, hal_path, network
        )
        
        cert_data = cls._compile_contract_with_keys(
            contracts_dir / "certificate.simf",
            admin_pubkey, delegate_pubkey,
            simc_path, hal_path, network
        )
        
        return VaultConfig(
            network=network,
            asset_id=network_config["asset_id"],
            admin_pubkey=admin_pubkey,
            delegate_pubkey=delegate_pubkey,
            vault_address=vault_data["address"],
            vault_cmr=vault_data["cmr"],
            vault_program=vault_data["program"],
            certificate_address=cert_data["address"],
            certificate_cmr=cert_data["cmr"],
            certificate_program=cert_data["program"],
            internal_key=cls.INTERNAL_KEY,
        )
    
    @classmethod
    def as_admin(
        cls,
        config: Union[str, VaultConfig],
        private_key: str,
        hal_path: Optional[str] = None,
    ) -> "SAP":
        """
        Create SDK instance as ADMIN.
        
        Admin can:
        - Issue certificates
        - Revoke ANY certificate
        - Drain vault unconditionally
        
        Args:
            config: VaultConfig or path to config JSON.
            private_key: Admin private key (64 hex chars).
        
        Returns:
            SAP instance configured as admin.
        """
        if isinstance(config, str):
            config = VaultConfig.load(config)
        
        return cls(
            config=config,
            role="admin",
            private_key=private_key,
            hal_path=hal_path,
        )
    
    @classmethod
    def as_delegate(
        cls,
        config: Union[str, VaultConfig],
        private_key: str,
        hal_path: Optional[str] = None,
    ) -> "SAP":
        """
        Create SDK instance as DELEGATE.
        
        Delegate can:
        - Issue certificates
        - Revoke own certificates
        
        Cannot:
        - Drain vault
        - Revoke admin's certificates
        
        Args:
            config: VaultConfig or path to config JSON.
            private_key: Delegate private key (64 hex chars).
        
        Returns:
            SAP instance configured as delegate.
        """
        if isinstance(config, str):
            config = VaultConfig.load(config)
        
        return cls(
            config=config,
            role="delegate",
            private_key=private_key,
            hal_path=hal_path,
        )
    
    # =========================================================================
    # Constructor (Private - use factory methods)
    # =========================================================================
    
    def __init__(
        self,
        config: VaultConfig,
        role: Literal["admin", "delegate"],
        private_key: str,
        hal_path: Optional[str] = None,
    ):
        """Initialize SAP instance. Use as_admin() or as_delegate() instead."""
        self.config = config
        self.role = role
        self._key = KeyManager(private_key)
        
        # Verify key matches expected pubkey
        expected_pub = config.admin_pubkey if role == "admin" else config.delegate_pubkey
        if self._key.public_key != expected_pub:
            raise ConfigurationError(
                f"Private key doesn't match {role} pubkey. "
                f"Expected: {expected_pub[:16]}..., Got: {self._key.public_key[:16]}..."
            )
        
        # Initialize infrastructure
        network_config = self.NETWORKS[config.network]
        self.hal = HalSimplicity(
            hal_path or self.DEFAULT_HAL_PATH,
            network_config["hal_network"]
        )
        self.api = BlockstreamAPI(
            network_config["api_url"],
            "testnet" if config.network == "testnet" else "mainnet"
        )
    
    # =========================================================================
    # Properties
    # =========================================================================
    
    @property
    def vault_address(self) -> str:
        """Vault address for funding."""
        return self.config.vault_address
    
    @property
    def certificate_address(self) -> str:
        """Certificate contract address."""
        return self.config.certificate_address
    
    @property
    def asset_id(self) -> str:
        """L-BTC asset ID."""
        return self.config.asset_id
    
    # =========================================================================
    # Vault Operations
    # =========================================================================
    
    def get_vault(self) -> Vault:
        """Get current vault status."""
        utxos = self.api.get_utxos(self.vault_address)
        balance = sum(u.value for u in utxos)
        
        return Vault(
            address=self.vault_address,
            script_pubkey=f"5120{self.config.vault_cmr}",
            cmr=self.config.vault_cmr,
            program=self.config.vault_program,
            balance=balance,
            utxos=utxos
        )
    
    def drain_vault(self, recipient: str) -> TransactionResult:
        """
        Drain all vault funds to recipient.
        
        ADMIN ONLY - unconditional spend.
        
        Args:
            recipient: Address to send funds.
        
        Returns:
            TransactionResult.
        """
        if self.role != "admin":
            raise PermissionError("Only admin can drain vault")
        
        vault = self.get_vault()
        if not vault.available_utxo:
            raise VaultEmptyError(self.vault_address)
        
        return self._build_and_sign_drain(vault.available_utxo, recipient)
    
    # =========================================================================
    # Certificate Operations
    # =========================================================================
    
    def issue_certificate(self, cid: str) -> TransactionResult:
        """
        Issue a new certificate.
        
        Both admin and delegate can issue.
        
        Args:
            cid: Content ID (IPFS CID or hash) to embed.
        
        Returns:
            TransactionResult with txid.
        """
        vault = self.get_vault()
        if not vault.can_issue:
            raise InsufficientFundsError(1046, vault.balance)
        
        if not vault.available_utxo:
            raise VaultEmptyError(self.vault_address)
        
        return self._build_and_sign_issue(vault.available_utxo, cid)
    
    def revoke_certificate(
        self,
        txid: str,
        vout: int = 1,
        recipient: Optional[str] = None
    ) -> TransactionResult:
        """
        Revoke a certificate.
        
        Admin can revoke any. Delegate can only revoke own.
        
        Args:
            txid: Certificate transaction ID.
            vout: Output index (default 1).
            recipient: Where to send funds (optional).
        
        Returns:
            TransactionResult.
        """
        cert_utxos = self.api.get_utxos(self.certificate_address)
        cert_utxo = next(
            (u for u in cert_utxos if u.txid == txid and u.vout == vout),
            None
        )
        
        if not cert_utxo:
            return TransactionResult(
                success=False,
                error=f"Certificate UTXO not found: {txid}:{vout}"
            )
        
        return self._build_and_sign_revoke(cert_utxo, recipient)
    
    def verify_certificate(self, txid: str, vout: int = 1) -> CertificateStatus:
        """Verify a certificate's status."""
        cert_utxos = self.api.get_utxos(self.certificate_address)
        
        for utxo in cert_utxos:
            if utxo.txid == txid and utxo.vout == vout:
                return CertificateStatus.VALID
        
        return CertificateStatus.REVOKED
    
    def list_certificates(self) -> List[Certificate]:
        """List all active certificates."""
        utxos = self.api.get_utxos(self.certificate_address)
        return [
            Certificate(
                txid=u.txid,
                vout=u.vout,
                cid=None,
                status=CertificateStatus.VALID
            )
            for u in utxos
        ]
    
    # =========================================================================
    # Transaction Building (Internal)
    # =========================================================================
    
    def _build_and_sign_issue(self, vault_utxo: UTXO, cid: str) -> TransactionResult:
        """Build and sign certificate issuance."""
        FEE_SATS = 500
        CERT_SATS = 546
        
        change_sats = vault_utxo.value - FEE_SATS - CERT_SATS
        sap_payload = self._build_sap_payload(cid)
        
        inputs = [{"txid": vault_utxo.txid, "vout": vault_utxo.vout}]
        outputs = [
            {"address": self.vault_address, "asset": self.asset_id, 
             "amount": change_sats / 100_000_000},
            {"address": self.certificate_address, "asset": self.asset_id,
             "amount": CERT_SATS / 100_000_000},
            {"address": f"data:{sap_payload}", "asset": self.asset_id, "amount": 0},
            {"address": "fee", "asset": self.asset_id, "amount": FEE_SATS / 100_000_000}
        ]
        
        try:
            pset = self.hal.pset_create(inputs, outputs)
            
            pset = self.hal.pset_update_input(
                pset=pset,
                index=0,
                script_pubkey=f"5120{self.config.vault_cmr}",
                asset=self.asset_id,
                amount=f"{vault_utxo.value / 100_000_000:.8f}",
                cmr=self.config.vault_cmr,
                internal_key=self.config.internal_key
            )
            
            dummy_witness = WitnessEncoder.vault_dummy(
                "admin_issue" if self.role == "admin" else "delegate_issue"
            )
            run_result = self.hal.pset_run(pset, 0, self.config.vault_program, dummy_witness)
            
            signature = self._key.sign_hash(run_result.sig_all_hash)
            witness = WitnessEncoder.encode_vault_witness(signature, self.role, False)
            
            finalized = self.hal.pset_finalize(pset, 0, self.config.vault_program, witness)
            tx_hex = self.hal.pset_extract(finalized)
            
            return self.api.broadcast(tx_hex)
            
        except Exception as e:
            return TransactionResult(success=False, error=str(e))
    
    def _build_and_sign_revoke(self, cert_utxo: UTXO, recipient: Optional[str]) -> TransactionResult:
        """Build and sign certificate revocation."""
        FEE_SATS = 500
        
        inputs = [{"txid": cert_utxo.txid, "vout": cert_utxo.vout}]
        
        if recipient and cert_utxo.value > FEE_SATS:
            output_sats = cert_utxo.value - FEE_SATS
            outputs = [
                {"address": recipient, "asset": self.asset_id,
                 "amount": output_sats / 100_000_000},
                {"address": "fee", "asset": self.asset_id,
                 "amount": FEE_SATS / 100_000_000}
            ]
        else:
            outputs = [
                {"address": "fee", "asset": self.asset_id,
                 "amount": cert_utxo.value / 100_000_000}
            ]
        
        try:
            pset = self.hal.pset_create(inputs, outputs)
            
            pset = self.hal.pset_update_input(
                pset=pset,
                index=0,
                script_pubkey=f"5120{self.config.certificate_cmr}",
                asset=self.asset_id,
                amount=f"{cert_utxo.value / 100_000_000:.8f}",
                cmr=self.config.certificate_cmr,
                internal_key=self.config.internal_key
            )
            
            dummy_witness = WitnessEncoder.certificate_dummy(self.role)
            run_result = self.hal.pset_run(pset, 0, self.config.certificate_program, dummy_witness)
            
            signature = self._key.sign_hash(run_result.sig_all_hash)
            witness = WitnessEncoder.encode_certificate_witness(signature, self.role)
            
            finalized = self.hal.pset_finalize(pset, 0, self.config.certificate_program, witness)
            tx_hex = self.hal.pset_extract(finalized)
            
            return self.api.broadcast(tx_hex)
            
        except Exception as e:
            return TransactionResult(success=False, error=str(e))
    
    def _build_and_sign_drain(self, vault_utxo: UTXO, recipient: str) -> TransactionResult:
        """Build and sign vault drain (admin unconditional)."""
        FEE_SATS = 500
        output_sats = vault_utxo.value - FEE_SATS
        
        inputs = [{"txid": vault_utxo.txid, "vout": vault_utxo.vout}]
        outputs = [
            {"address": recipient, "asset": self.asset_id,
             "amount": output_sats / 100_000_000},
            {"address": "fee", "asset": self.asset_id,
             "amount": FEE_SATS / 100_000_000}
        ]
        
        try:
            pset = self.hal.pset_create(inputs, outputs)
            
            pset = self.hal.pset_update_input(
                pset=pset,
                index=0,
                script_pubkey=f"5120{self.config.vault_cmr}",
                asset=self.asset_id,
                amount=f"{vault_utxo.value / 100_000_000:.8f}",
                cmr=self.config.vault_cmr,
                internal_key=self.config.internal_key
            )
            
            dummy_witness = WitnessEncoder.vault_dummy("admin_unconditional")
            run_result = self.hal.pset_run(pset, 0, self.config.vault_program, dummy_witness)
            
            signature = self._key.sign_hash(run_result.sig_all_hash)
            witness = WitnessEncoder.encode_vault_witness(signature, "admin", True)
            
            finalized = self.hal.pset_finalize(pset, 0, self.config.vault_program, witness)
            tx_hex = self.hal.pset_extract(finalized)
            
            return self.api.broadcast(tx_hex)
            
        except Exception as e:
            return TransactionResult(success=False, error=str(e))
    
    def _build_sap_payload(self, cid: str) -> str:
        """Build SAP OP_RETURN payload."""
        magic = b"SAP"
        version = bytes([0x01])
        op_type = bytes([0x01])
        
        try:
            cid_bytes = bytes.fromhex(cid)
        except ValueError:
            cid_bytes = cid.encode('utf-8')
        
        payload = magic + version + op_type + cid_bytes
        return payload.hex()
    
    # =========================================================================
    # Static Helpers
    # =========================================================================
    
    @staticmethod
    def _find_contracts_dir() -> Path:
        """Find contracts directory."""
        locations = [
            Path.cwd() / "contracts",
            Path(__file__).parent.parent / "contracts",
            Path.home() / ".sap-sdk" / "contracts",
        ]
        for loc in locations:
            if loc.exists() and (loc / "vault.simf").exists():
                return loc
        raise ConfigurationError("Contracts directory not found")
    
    @classmethod
    def _compile_contract_with_keys(
        cls,
        template_path: Path,
        admin_pubkey: str,
        delegate_pubkey: str,
        simc_path: str,
        hal_path: str,
        network: str
    ) -> dict:
        """Compile contract with given pubkeys."""
        if not template_path.exists():
            raise CompilationError(f"Contract not found: {template_path}")
        
        # Read and update pubkeys in contract
        content = template_path.read_text()
        
        # Replace pubkey placeholders (find 64-char hex after 0x)
        import re
        pubkeys_in_file = re.findall(r'0x([a-f0-9]{64})', content)
        
        # First unique pubkey -> admin, second -> delegate
        if len(pubkeys_in_file) >= 2:
            old_admin = pubkeys_in_file[0]
            # Find second unique
            old_delegate = next((p for p in pubkeys_in_file[1:] if p != old_admin), pubkeys_in_file[1])
            
            content = content.replace(old_admin, admin_pubkey)
            content = content.replace(old_delegate, delegate_pubkey)
        
        # Write to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.simf', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Compile with simc
            result = subprocess.run(
                [simc_path, temp_path],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                raise CompilationError(f"simc failed: {result.stderr}")
            
            program = result.stdout.replace("Program:\n", "").strip()
            
            # Get address info
            result = subprocess.run([
                hal_path, "simplicity", "info", "--liquid",
                "-s", cls.INTERNAL_KEY,
                program
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise CompilationError(f"hal info failed: {result.stderr}")
            
            data = json.loads(result.stdout)
            address_key = "liquid_testnet_address_unconf" if network == "testnet" else "liquid_address_unconf"
            
            return {
                "address": data[address_key],
                "cmr": data["cmr"],
                "program": program
            }
        finally:
            Path(temp_path).unlink()
    
    # =========================================================================
    # Info
    # =========================================================================
    
    def info(self) -> dict:
        """Get SDK info."""
        vault = self.get_vault()
        certs = self.list_certificates()
        
        return {
            "role": self.role,
            "network": self.config.network,
            "vault_address": self.vault_address,
            "vault_balance": vault.balance,
            "can_issue": vault.can_issue,
            "active_certificates": len(certs),
            "permissions": {
                "issue": True,
                "revoke_any": self.role == "admin",
                "drain_vault": self.role == "admin",
            }
        }
