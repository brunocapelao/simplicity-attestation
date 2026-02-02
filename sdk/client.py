"""
SAS SDK - Main Client

High-level interface for SAS operations.
This is the primary entry point for SDK users.
"""

from pathlib import Path
from typing import Optional, List, Literal, Callable
import logging

from .config import SASConfig
from .models import Certificate, Vault, TransactionResult, CertificateStatus
from .constants import MIN_ISSUE_SATS
from .core.transaction import TransactionBuilder
from .core.contracts import ContractRegistry
from .infra.hal import HalSimplicity
from .infra.api import BlockstreamAPI
from .protocols.sas import SAPProtocol

# New production features
from .confirmation import ConfirmationTracker, ConfirmationStatus
from .fees import FeeEstimator, FeePriority, FeeEstimate
from .events import EventEmitter, EventType
from .logging import StructuredLogger
from .errors import (
    VaultEmptyError,
    InsufficientFundsError,
    CertificateNotFoundError,
)

# External signature support
from .prepared import PreparedTransaction, TransactionType


class SAPClient:
    """
    High-level client for SAS operations.
    
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
        config: SASConfig,
        hal: Optional[HalSimplicity] = None,
        api: Optional[BlockstreamAPI] = None,
        logger: Optional[logging.Logger] = None,
        enable_events: bool = True
    ):
        """
        Initialize SAS client.
        
        Args:
            config: SAS configuration.
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
        
        config = SASConfig.from_file(str(path))
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
        reason_code: Optional[int] = None,
        replacement_txid: Optional[str] = None,
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
            reason_code=reason_code,
            replacement_txid=replacement_txid,
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
                # Try to decode SAS payload
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
    # External Signature Operations (prepare/finalize pattern)
    # =========================================================================
    
    def prepare_issue_certificate(
        self,
        cid: str,
        issuer: Literal["admin", "delegate"] = "delegate"
    ) -> PreparedTransaction:
        """
        Prepare a certificate issuance for external signing.
        
        Use this when signatures come from external sources like:
        - Multisig ceremonies
        - Hardware wallets
        - Approval workflows
        
        Args:
            cid: IPFS CID or content hash to embed.
            issuer: "admin" or "delegate".
        
        Returns:
            PreparedTransaction with sig_hash to sign externally.
        
        Example:
            prepared = client.prepare_issue_certificate(cid="Qm...")
            signature = external_signer.sign(prepared.sig_hash_bytes)
            result = client.finalize_transaction(prepared, signature)
        """
        vault = self.get_vault()
        if not vault.can_issue:
            raise InsufficientFundsError(
                required=MIN_ISSUE_SATS,
                available=vault.balance,
                message="Vault has insufficient funds for issuance"
            )
        
        if not vault.available_utxo:
            raise VaultEmptyError(vault.address)
        
        # Get required pubkey for verification
        key_info = self.config.get_key(issuer)
        
        # Build transaction and get sig_hash
        prepared_data = self.transaction_builder.prepare_issue_certificate(
            vault_utxo=vault.available_utxo,
            cid=cid,
            issuer=issuer
        )
        
        return PreparedTransaction(
            tx_type=TransactionType.ISSUE_CERTIFICATE,
            sig_hash=prepared_data["sig_hash"],
            signer_role=issuer,
            required_pubkey=key_info.public_key,
            pset=prepared_data["pset"],
            input_index=prepared_data["input_index"],
            program=prepared_data["program"],
            witness_template=prepared_data["witness_template"],
            details={
                "cid": cid,
                "vault_utxo": f"{vault.available_utxo.txid}:{vault.available_utxo.vout}",
                "vault_balance": vault.balance,
            }
        )
    
    def prepare_revoke_certificate(
        self,
        txid: str,
        vout: int = 1,
        revoker: Literal["admin", "delegate"] = "admin",
        recipient: Optional[str] = None,
        reason_code: Optional[int] = None,
        replacement_txid: Optional[str] = None
    ) -> PreparedTransaction:
        """
        Prepare a certificate revocation for external signing.
        
        Args:
            txid: Transaction ID of the certificate.
            vout: Output index.
            revoker: "admin" or "delegate".
            recipient: Where to send funds.
        
        Returns:
            PreparedTransaction with sig_hash to sign externally.
        """
        # Find certificate UTXO
        cert_utxos = self.api.get_utxos(self.contracts.certificate.address)
        cert_utxo = None
        for utxo in cert_utxos:
            if utxo.txid == txid and utxo.vout == vout:
                cert_utxo = utxo
                break
        
        if not cert_utxo:
            raise CertificateNotFoundError(txid, vout)
        
        key_info = self.config.get_key(revoker)
        
        prepared_data = self.transaction_builder.prepare_revoke_certificate(
            cert_utxo=cert_utxo,
            revoker=revoker,
            recipient=recipient,
            reason_code=reason_code,
            replacement_txid=replacement_txid
        )
        
        return PreparedTransaction(
            tx_type=TransactionType.REVOKE_CERTIFICATE,
            sig_hash=prepared_data["sig_hash"],
            signer_role=revoker,
            required_pubkey=key_info.public_key,
            pset=prepared_data["pset"],
            input_index=prepared_data["input_index"],
            program=prepared_data["program"],
            witness_template=prepared_data["witness_template"],
            details={
                "certificate": f"{txid}:{vout}",
                "recipient": recipient or "(burn as fee)",
                "reason_code": reason_code,
                "replacement_txid": replacement_txid,
            }
        )
    
    def prepare_drain_vault(
        self,
        recipient: str
    ) -> PreparedTransaction:
        """
        Prepare a vault drain for external signing (admin only).
        
        Args:
            recipient: Address to send funds to.
        
        Returns:
            PreparedTransaction with sig_hash to sign externally.
        """
        vault = self.get_vault()
        if not vault.available_utxo:
            raise VaultEmptyError(vault.address)
        
        key_info = self.config.get_key("admin")
        
        prepared_data = self.transaction_builder.prepare_drain_vault(
            vault_utxo=vault.available_utxo,
            recipient=recipient
        )
        
        return PreparedTransaction(
            tx_type=TransactionType.DRAIN_VAULT,
            sig_hash=prepared_data["sig_hash"],
            signer_role="admin",
            required_pubkey=key_info.public_key,
            pset=prepared_data["pset"],
            input_index=prepared_data["input_index"],
            program=prepared_data["program"],
            witness_template=prepared_data["witness_template"],
            details={
                "vault_balance": vault.balance,
                "recipient": recipient,
            }
        )
    
    def finalize_transaction(
        self,
        prepared: PreparedTransaction,
        signature: bytes,
        broadcast: bool = True
    ) -> TransactionResult:
        """
        Finalize a prepared transaction with an external signature.
        
        Args:
            prepared: PreparedTransaction from prepare_* methods.
            signature: 64-byte Schnorr signature.
            broadcast: Whether to broadcast immediately.
        
        Returns:
            TransactionResult with txid or error.
        
        Example:
            prepared = client.prepare_issue_certificate(cid)
            signature = hardware_wallet.sign(prepared.sig_hash_bytes)
            result = client.finalize_transaction(prepared, signature)
        """
        # Validate signature format
        if len(signature) != 64:
            return TransactionResult(
                success=False,
                error=f"Invalid signature length: expected 64 bytes, got {len(signature)}"
            )
        
        # Check expiration
        if prepared.is_expired:
            return TransactionResult(
                success=False,
                error="Prepared transaction has expired"
            )
        
        # Emit event
        if self.events:
            self.events.emit(EventType.BEFORE_SIGN, {
                "tx_type": prepared.tx_type.value,
                "sig_hash": prepared.sig_hash,
            })
        
        # Finalize transaction
        result = self.transaction_builder.finalize_with_signature(
            pset=prepared.pset,
            input_index=prepared.input_index,
            program=prepared.program,
            witness_template=prepared.witness_template,
            signature=signature,
            issuer=prepared.signer_role,
            broadcast=broadcast
        )
        
        # Emit after event
        if self.events and result.success:
            event_type = {
                TransactionType.ISSUE_CERTIFICATE: EventType.AFTER_ISSUE,
                TransactionType.REVOKE_CERTIFICATE: EventType.AFTER_REVOKE,
                TransactionType.DRAIN_VAULT: EventType.AFTER_DRAIN,
            }.get(prepared.tx_type, EventType.AFTER_BROADCAST)
            
            self.events.emit(event_type, {
                "txid": result.txid,
                "tx_type": prepared.tx_type.value,
            })
        
        return result
    
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
