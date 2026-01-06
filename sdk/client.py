"""
SAP SDK - Main Client

High-level interface for SAP operations.
This is the primary entry point for SDK users.
"""

from pathlib import Path
from typing import Optional, List, Literal, Callable
import logging

from .config import SAPConfig
from .models import Certificate, Vault, TransactionResult, UTXO, CertificateStatus
from .core.witness import WitnessEncoder
from .core.transaction import TransactionBuilder
from .core.contracts import ContractRegistry
from .infra.hal import HalSimplicity
from .infra.api import BlockstreamAPI
from .protocols.sap import SAPProtocol

# New production features
from .confirmation import ConfirmationTracker, ConfirmationStatus, TxStatus
from .fees import FeeEstimator, FeePriority, FeeEstimate
from .events import EventEmitter, EventType, Event
from .logging import StructuredLogger
from .errors import (
    VaultEmptyError,
    InsufficientFundsError,
    CertificateNotFoundError,
    CertificateAlreadyRevokedError,
)


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
        
        # Wait for confirmation
        status = client.wait_for_confirmation(cert.txid)
        
        # Use event hooks
        @client.events.on(EventType.AFTER_ISSUE)
        def on_issue(event):
            print(f"Issued: {event.data['txid']}")
    """
    
    def __init__(
        self,
        config: SAPConfig,
        hal: Optional[HalSimplicity] = None,
        api: Optional[BlockstreamAPI] = None,
        logger: Optional[logging.Logger] = None,
        enable_events: bool = True
    ):
        """
        Initialize SAP client.
        
        Args:
            config: SAP configuration.
            hal: Optional HalSimplicity instance.
            api: Optional BlockstreamAPI instance.
            logger: Optional Python logger for structured logging.
            enable_events: Whether to enable event hooks (default: True).
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
        
        # New production features
        self.confirmations = ConfirmationTracker(self.api)
        self.fees = FeeEstimator(self.api)
        self.events = EventEmitter(logger) if enable_events else None
        self.logger = StructuredLogger(logger=logger) if logger else None
    
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
    
    # =========================================================================
    # Confirmation Operations
    # =========================================================================
    
    def wait_for_confirmation(
        self,
        txid: str,
        target_confirmations: int = 1,
        timeout: int = 600
    ) -> ConfirmationStatus:
        """
        Wait for a transaction to be confirmed.
        
        Args:
            txid: Transaction ID to wait for.
            target_confirmations: Number of confirmations to wait for.
            timeout: Maximum seconds to wait (default: 600).
        
        Returns:
            ConfirmationStatus when target reached.
        
        Raises:
            ConfirmationTimeoutError: If timeout exceeded.
        """
        return self.confirmations.wait_for_confirmation(
            txid=txid,
            target_confirmations=target_confirmations,
            timeout=timeout
        )
    
    def get_confirmation_status(self, txid: str) -> ConfirmationStatus:
        """
        Get current confirmation status of a transaction.
        
        Args:
            txid: Transaction ID.
        
        Returns:
            ConfirmationStatus with current state.
        """
        return self.confirmations.get_status(txid)
    
    def on_confirmation(
        self,
        txid: str,
        callback: Callable[[ConfirmationStatus], None],
        target_confirmations: int = 1
    ) -> None:
        """
        Register callback for when transaction reaches confirmations.
        
        Args:
            txid: Transaction ID to track.
            callback: Function to call when confirmed.
            target_confirmations: Confirmations needed to trigger.
        """
        self.confirmations.on_confirmation(txid, callback, target_confirmations)
    
    # =========================================================================
    # Fee Estimation
    # =========================================================================
    
    def estimate_fee(
        self,
        operation: str = "issue_certificate",
        priority: FeePriority = FeePriority.MEDIUM
    ) -> FeeEstimate:
        """
        Estimate fee for an operation.
        
        Args:
            operation: Type of operation (issue_certificate, revoke_certificate, etc).
            priority: Fee priority level (LOW, MEDIUM, HIGH, URGENT).
        
        Returns:
            FeeEstimate with recommended fee.
        """
        return self.fees.estimate(operation=operation, priority=priority)
    
    # =========================================================================
    # Event Hooks
    # =========================================================================
    
    def on(self, event_type: EventType) -> Callable:
        """
        Decorator to register an event handler.
        
        Args:
            event_type: Type of event to handle.
        
        Returns:
            Decorator function.
        
        Example:
            @client.on(EventType.AFTER_ISSUE)
            def handle_issue(event):
                print(f"Certificate issued: {event.data['txid']}")
        """
        if self.events:
            return self.events.on(event_type)
        return lambda f: f  # No-op if events disabled
    
    def emit(self, event_type: EventType, data: dict = None) -> None:
        """
        Emit an event to all registered handlers.
        
        Args:
            event_type: Type of event.
            data: Event payload data.
        """
        if self.events:
            self.events.emit(event_type, data)
