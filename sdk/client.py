"""
SAP SDK - Main Client

High-level interface for SAP operations.
This is the primary entry point for SDK users.
"""

from pathlib import Path
from typing import Optional, List, Literal

from .config import SAPConfig
from .models import Certificate, Vault, TransactionResult, UTXO, CertificateStatus
from .core.witness import WitnessEncoder
from .core.transaction import TransactionBuilder
from .core.contracts import ContractRegistry
from .infra.hal import HalSimplicity
from .infra.api import BlockstreamAPI
from .protocols.sap import SAPProtocol


class SAPClient:
    """
    High-level client for SAP operations.
    
    Provides simple one-line methods for:
    - Issuing certificates
    - Verifying certificates
    - Revoking certificates
    - Managing the vault
    
    Example:
        # Initialize from config file
        client = SAPClient.from_config("secrets.json")
        
        # Issue a certificate
        cert = client.issue_certificate(cid="QmYwAPJzv5...")
        
        # Verify a certificate
        is_valid = client.verify_certificate(cert.txid, cert.vout)
        
        # Revoke a certificate
        client.revoke_certificate(cert.txid, cert.vout)
    """
    
    def __init__(
        self,
        config: SAPConfig,
        hal: Optional[HalSimplicity] = None,
        api: Optional[BlockstreamAPI] = None
    ):
        """
        Initialize SAP client.
        
        Args:
            config: SAP configuration.
            hal: Optional HalSimplicity instance.
            api: Optional BlockstreamAPI instance.
        """
        self.config = config
        
        # Initialize infrastructure
        self.hal = hal or HalSimplicity(
            binary_path=config.hal_binary,
            network="liquid"
        )
        self.api = api or BlockstreamAPI(
            base_url=config.api_base_url,
            network="testnet" if "testnet" in config.network else "mainnet"
        )
        
        # Initialize core components
        self.contracts = ContractRegistry(config)
        self.transaction_builder = TransactionBuilder(
            hal=self.hal,
            api=self.api,
            contracts=self.contracts,
            config=config
        )
        
        # Protocol handlers
        self.sap_protocol = SAPProtocol
    
    @classmethod
    def from_config(cls, config_path: str) -> "SAPClient":
        """
        Create client from secrets.json config file.
        
        Args:
            config_path: Path to secrets.json file.
        
        Returns:
            Configured SAPClient.
        """
        # Handle relative paths
        path = Path(config_path)
        if not path.is_absolute():
            # Try to find in parent directories
            for parent in [Path.cwd()] + list(Path.cwd().parents)[:3]:
                candidate = parent / config_path
                if candidate.exists():
                    path = candidate
                    break
        
        config = SAPConfig.from_file(str(path))
        return cls(config)
    
    # =========================================================================
    # Vault Operations
    # =========================================================================
    
    def get_vault(self) -> Vault:
        """
        Get current vault state.
        
        Returns:
            Vault object with balance and UTXOs.
        """
        vault = self.contracts.vault
        utxos = self.api.get_utxos(vault.address)
        balance = sum(u.value for u in utxos)
        
        return Vault(
            address=vault.address,
            script_pubkey=vault.script_pubkey,
            cmr=vault.cmr,
            program=vault.program,
            balance=balance,
            utxos=utxos
        )
    
    def get_vault_balance(self) -> int:
        """Get vault balance in satoshis."""
        return self.api.get_balance(self.contracts.vault.address)
    
    def drain_vault(
        self,
        recipient: str,
        broadcast: bool = True
    ) -> TransactionResult:
        """
        Drain the vault (admin only).
        
        This deactivates the delegate by emptying the vault.
        
        Args:
            recipient: Address to send funds to.
            broadcast: Whether to broadcast immediately.
        
        Returns:
            TransactionResult.
        """
        vault = self.get_vault()
        if not vault.available_utxo:
            return TransactionResult(
                success=False,
                error="No UTXOs available in vault"
            )
        
        return self.transaction_builder.drain_vault(
            vault_utxo=vault.available_utxo,
            recipient=recipient,
            broadcast=broadcast
        )
    
    # =========================================================================
    # Certificate Operations
    # =========================================================================
    
    def issue_certificate(
        self,
        cid: str,
        issuer: Literal["admin", "delegate"] = "delegate",
        broadcast: bool = True
    ) -> TransactionResult:
        """
        Issue a new certificate.
        
        Args:
            cid: IPFS CID or content hash to embed.
            issuer: "admin" or "delegate".
            broadcast: Whether to broadcast immediately.
        
        Returns:
            TransactionResult with new certificate info.
        """
        vault = self.get_vault()
        if not vault.can_issue:
            return TransactionResult(
                success=False,
                error=f"Insufficient vault funds: {vault.balance} sats"
            )
        
        if not vault.available_utxo:
            return TransactionResult(
                success=False,
                error="No UTXOs available in vault"
            )
        
        return self.transaction_builder.issue_certificate(
            vault_utxo=vault.available_utxo,
            cid=cid,
            issuer=issuer,
            broadcast=broadcast
        )
    
    def revoke_certificate(
        self,
        txid: str,
        vout: int = 1,
        revoker: Literal["admin", "delegate"] = "admin",
        recipient: Optional[str] = None,
        broadcast: bool = True
    ) -> TransactionResult:
        """
        Revoke a certificate by spending its UTXO.
        
        Args:
            txid: Transaction ID of the certificate.
            vout: Output index (default 1 for standard issuance).
            revoker: "admin" or "delegate".
            recipient: Where to send funds (burns as fee if None).
            broadcast: Whether to broadcast immediately.
        
        Returns:
            TransactionResult.
        """
        # Get certificate UTXO
        cert_utxos = self.api.get_utxos(self.contracts.certificate.address)
        
        # Find matching UTXO
        cert_utxo = None
        for utxo in cert_utxos:
            if utxo.txid == txid and utxo.vout == vout:
                cert_utxo = utxo
                break
        
        if not cert_utxo:
            return TransactionResult(
                success=False,
                error=f"Certificate UTXO not found: {txid}:{vout}"
            )
        
        return self.transaction_builder.revoke_certificate(
            cert_utxo=cert_utxo,
            revoker=revoker,
            recipient=recipient,
            broadcast=broadcast
        )
    
    def verify_certificate(self, txid: str, vout: int = 1) -> CertificateStatus:
        """
        Verify if a certificate is valid (UTXO not spent).
        
        Args:
            txid: Transaction ID of the certificate.
            vout: Output index.
        
        Returns:
            CertificateStatus (VALID, REVOKED, or UNKNOWN).
        """
        is_spent = self.api.is_utxo_spent(txid, vout)
        
        if is_spent:
            return CertificateStatus.REVOKED
        else:
            return CertificateStatus.VALID
    
    def get_certificate(self, txid: str, vout: int = 1) -> Optional[Certificate]:
        """
        Get certificate details.
        
        Args:
            txid: Transaction ID.
            vout: Output index.
        
        Returns:
            Certificate object or None if not found.
        """
        # Get transaction details
        tx = self.api.get_transaction(txid)
        if not tx:
            return None
        
        # Get status
        status = self.verify_certificate(txid, vout)
        
        # Try to extract CID from OP_RETURN (output 2)
        cid = ""
        if len(tx.get("vout", [])) > 2:
            op_return = tx["vout"][2]
            if op_return.get("scriptpubkey_type") == "op_return":
                # Try to decode SAP payload
                hex_data = op_return.get("scriptpubkey", "")[4:]  # Skip OP_RETURN opcode
                sap = self.sap_protocol.decode_hex(hex_data)
                if hasattr(sap, 'cid'):
                    cid = sap.cid
        
        # Get confirmation info
        tx_status = self.api.get_tx_status(txid)
        issued_at = tx_status.get("block_height") if tx_status else None
        
        # Get revocation info if revoked
        revoked_at = None
        if status == CertificateStatus.REVOKED:
            outspend = self.api.get_outspend(txid, vout)
            if outspend and outspend.get("spent"):
                revoked_at = outspend.get("status", {}).get("block_height")
        
        return Certificate(
            txid=txid,
            vout=vout,
            cid=cid,
            status=status,
            issued_at=issued_at,
            revoked_at=revoked_at
        )
    
    def list_certificates(self) -> List[Certificate]:
        """
        List all certificate UTXOs at the certificate address.
        
        Note: This only shows currently valid (unspent) certificates.
        
        Returns:
            List of Certificate objects.
        """
        utxos = self.api.get_utxos(self.contracts.certificate.address)
        
        certificates = []
        for utxo in utxos:
            cert = self.get_certificate(utxo.txid, utxo.vout)
            if cert:
                certificates.append(cert)
        
        return certificates
