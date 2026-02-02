"""
SAS SDK - Transaction Builder

High-level transaction construction for SAS operations.
Encapsulates the 8-step PSET workflow into simple method calls.
"""

from typing import Literal, Optional

from ..models import UTXO, TransactionResult
from ..config import SASConfig
from ..constants import FEE_SATS, CERT_DUST_SATS
from .witness import WitnessEncoder
from .contracts import ContractRegistry
from ..infra.hal import HalSimplicity
from ..infra.api import BlockstreamAPI
from ..infra.keys import KeyManager
from ..protocols.sas import SAPProtocol


class TransactionBuilder:
    """
    Builds and executes SAS transactions.
    
    Encapsulates the complex 8-step PSET workflow:
    1. Create PSET
    2. Update input
    3. Get sig_all_hash with dummy witness
    4. Sign with appropriate key
    5. Create witness with proper encoding
    6. Verify signature
    7. Finalize PSET
    8. Extract and broadcast
    """
    
    def __init__(
        self,
        hal: HalSimplicity,
        api: BlockstreamAPI,
        contracts: ContractRegistry,
        config: SASConfig
    ):
        """
        Initialize transaction builder.
        
        Args:
            hal: HalSimplicity CLI wrapper.
            api: Blockstream API client.
            contracts: Contract registry.
            config: SAS configuration.
        """
        self.hal = hal
        self.api = api
        self.contracts = contracts
        self.config = config
    
    def _sats_to_btc(self, sats: int) -> float:
        """Convert satoshis to BTC float."""
        return sats / 100_000_000
    
    def _get_signer(self, role: Literal["admin", "delegate"]) -> KeyManager:
        """Get KeyManager for the specified role."""
        key = self.config.get_key(role)
        return KeyManager(key.private_key, key.public_key)
    
    # =========================================================================
    # Certificate Issuance
    # =========================================================================
    
    def issue_certificate(
        self,
        vault_utxo: UTXO,
        cid: str,
        issuer: Literal["admin", "delegate"] = "delegate",
        broadcast: bool = True
    ) -> TransactionResult:
        """
        Issue a new certificate from the vault.
        
        This creates a transaction with:
        - Output 0: Change back to vault
        - Output 1: Certificate UTXO
        - Output 2: OP_RETURN with SAS payload (CID)
        - Output 3: Fee
        
        Args:
            vault_utxo: UTXO from the vault to spend.
            cid: IPFS CID or hash to embed in OP_RETURN.
            issuer: "admin" or "delegate".
            broadcast: Whether to broadcast the transaction.
        
        Returns:
            TransactionResult with txid or error.
        """
        vault = self.contracts.vault
        cert = self.contracts.certificate
        
        # Calculate outputs
        change_sats = vault_utxo.value - FEE_SATS - CERT_DUST_SATS
        if change_sats < CERT_DUST_SATS:
            return TransactionResult(
                success=False,
                error=f"Insufficient funds: {vault_utxo.value} sats"
            )
        
        # Build SAS payload for OP_RETURN
        sap_payload = self._build_sas_attest_payload(cid)
        
        # Create transaction outputs
        inputs = [vault_utxo.to_dict()]
        outputs = [
            {"address": vault.address, "asset": self.contracts.asset_id, 
             "amount": self._sats_to_btc(change_sats)},
            {"address": cert.address, "asset": self.contracts.asset_id,
             "amount": self._sats_to_btc(CERT_DUST_SATS)},
            {"address": f"data:{sap_payload}", "asset": self.contracts.asset_id, "amount": 0},
            {"address": "fee", "asset": self.contracts.asset_id,
             "amount": self._sats_to_btc(FEE_SATS)}
        ]
        
        # Determine spending path
        if issuer == "admin":
            dummy_witness = WitnessEncoder.vault_dummy("admin_issue")
        else:
            dummy_witness = WitnessEncoder.vault_dummy("delegate_issue")
        
        # Execute the 8-step workflow
        return self._execute_transaction(
            inputs=inputs,
            outputs=outputs,
            contract=vault,
            utxo_value=vault_utxo.value,
            signer_role=issuer,
            dummy_witness=dummy_witness,
            witness_encoder=lambda sig: WitnessEncoder.encode_vault_witness(sig, issuer, False),
            broadcast=broadcast
        )
    
    # =========================================================================
    # Certificate Revocation
    # =========================================================================
    
    def revoke_certificate(
        self,
        cert_utxo: UTXO,
        revoker: Literal["admin", "delegate"] = "admin",
        recipient: Optional[str] = None,
        reason_code: Optional[int] = None,
        replacement_txid: Optional[str] = None,
        broadcast: bool = True
    ) -> TransactionResult:
        """
        Revoke a certificate by spending its UTXO.
        
        Args:
            cert_utxo: The certificate UTXO to spend.
            revoker: "admin" or "delegate".
            recipient: Address to send funds to. If None, burns as fee.
            broadcast: Whether to broadcast the transaction.
        
        Returns:
            TransactionResult with txid or error.
        """
        cert = self.contracts.certificate
        
        outputs = []
        sap_payload = None
        if reason_code is not None or replacement_txid is not None:
            sap_payload = self._build_sas_revoke_payload(
                cert_utxo.txid, cert_utxo.vout, reason_code, replacement_txid
            )

        # Calculate outputs
        if recipient and cert_utxo.value > FEE_SATS:
            output_sats = cert_utxo.value - FEE_SATS
            outputs.append(
                {"address": recipient, "asset": self.contracts.asset_id,
                 "amount": self._sats_to_btc(output_sats)}
            )
        else:
            # Burn everything as fee
            outputs.append(
                {"address": "fee", "asset": self.contracts.asset_id,
                 "amount": self._sats_to_btc(cert_utxo.value)}
            )

        if sap_payload:
            outputs.append(
                {"address": f"data:{sap_payload}", "asset": self.contracts.asset_id, "amount": 0}
            )

        if recipient and cert_utxo.value > FEE_SATS:
            outputs.append(
                {"address": "fee", "asset": self.contracts.asset_id,
                 "amount": self._sats_to_btc(FEE_SATS)}
            )
        
        inputs = [cert_utxo.to_dict()]
        
        # Determine spending path
        dummy_witness = WitnessEncoder.certificate_dummy(revoker)
        
        return self._execute_transaction(
            inputs=inputs,
            outputs=outputs,
            contract=cert,
            utxo_value=cert_utxo.value,
            signer_role=revoker,
            dummy_witness=dummy_witness,
            witness_encoder=lambda sig: WitnessEncoder.encode_certificate_witness(sig, revoker),
            broadcast=broadcast
        )
    
    # =========================================================================
    # Vault Drain (Admin Only)
    # =========================================================================
    
    def drain_vault(
        self,
        vault_utxo: UTXO,
        recipient: str,
        broadcast: bool = True
    ) -> TransactionResult:
        """
        Drain the vault (admin-only unconditional spend).
        
        This deactivates the delegate by emptying the vault.
        
        Args:
            vault_utxo: Vault UTXO to drain.
            recipient: Address to send funds to.
            broadcast: Whether to broadcast.
        
        Returns:
            TransactionResult with txid or error.
        """
        vault = self.contracts.vault
        
        output_sats = vault_utxo.value - FEE_SATS
        if output_sats < CERT_DUST_SATS:
            return TransactionResult(
                success=False,
                error=f"Insufficient funds: {vault_utxo.value} sats"
            )
        
        inputs = [vault_utxo.to_dict()]
        outputs = [
            {"address": recipient, "asset": self.contracts.asset_id,
             "amount": self._sats_to_btc(output_sats)},
            {"address": "fee", "asset": self.contracts.asset_id,
             "amount": self._sats_to_btc(FEE_SATS)}
        ]
        
        dummy_witness = WitnessEncoder.vault_dummy("admin_unconditional")
        
        return self._execute_transaction(
            inputs=inputs,
            outputs=outputs,
            contract=vault,
            utxo_value=vault_utxo.value,
            signer_role="admin",
            dummy_witness=dummy_witness,
            witness_encoder=lambda sig: WitnessEncoder.encode_vault_witness(sig, "admin", True),
            broadcast=broadcast
        )
    
    # =========================================================================
    # Internal Workflow
    # =========================================================================
    
    def _execute_transaction(
        self,
        inputs: list,
        outputs: list,
        contract,
        utxo_value: int,
        signer_role: str,
        dummy_witness: str,
        witness_encoder,
        broadcast: bool
    ) -> TransactionResult:
        """
        Execute the full 8-step PSET workflow.
        """
        try:
            # Step 1: Create PSET
            pset = self.hal.pset_create(inputs, outputs)
            
            # Step 2: Update input
            pset = self.hal.pset_update_input(
                pset=pset,
                index=0,
                script_pubkey=contract.script_pubkey,
                asset=self.contracts.asset_id,
                amount=contract.sats_to_btc(utxo_value),
                cmr=contract.cmr,
                internal_key=self.contracts.internal_key
            )
            
            # Step 3: Get sig_all_hash with dummy witness
            run_result = self.hal.pset_run(pset, 0, contract.program, dummy_witness)
            if not run_result.sig_all_hash:
                return TransactionResult(
                    success=False,
                    error="Failed to extract sig_all_hash"
                )
            
            # Step 4: Sign
            signer = self._get_signer(signer_role)
            signature = signer.sign_hash(run_result.sig_all_hash)
            
            # Step 5: Create witness
            witness = witness_encoder(signature)
            
            # Step 6: Verify
            verify_result = self.hal.pset_run(pset, 0, contract.program, witness)
            if not verify_result.success:
                failed_jets = [j.jet for j in verify_result.jets if not j.success]
                return TransactionResult(
                    success=False,
                    error=f"Verification failed. Failed jets: {failed_jets}"
                )
            
            # Step 7: Finalize
            finalized_pset = self.hal.pset_finalize(pset, 0, contract.program, witness)
            
            # Step 8: Extract
            tx_hex = self.hal.pset_extract(finalized_pset)
            
            # Broadcast if requested
            if broadcast:
                return self.api.broadcast(tx_hex)
            else:
                return TransactionResult(
                    success=True,
                    raw_hex=tx_hex
                )
                
        except Exception as e:
            return TransactionResult(
                success=False,
                error=str(e)
            )
    
    def _build_sas_attest_payload(self, cid: str) -> str:
        """Build SAS ATTEST OP_RETURN payload."""
        # SAS protocol: "SAS" + version(0x01) + type(0x01=ATTEST) + CID
        magic = b"SAS"
        version = bytes([0x01])
        op_type = bytes([0x01])  # ATTEST
        
        # CID as UTF-8 bytes (or raw if it's already hex)
        try:
            # Try to treat as hex
            cid_bytes = bytes.fromhex(cid)
        except ValueError:
            # Treat as UTF-8 string
            cid_bytes = cid.encode('utf-8')
        
        payload = magic + version + op_type + cid_bytes
        return payload.hex()

    def _build_sas_revoke_payload(
        self,
        txid: str,
        vout: int,
        reason_code: Optional[int],
        replacement_txid: Optional[str]
    ) -> str:
        """Build SAS REVOKE OP_RETURN payload with optional reason code."""
        return SAPProtocol.encode_revoke(
            txid, vout, reason_code=reason_code, replacement_txid=replacement_txid
        )
    
    # =========================================================================
    # External Signature Support (prepare/finalize pattern)
    # =========================================================================
    
    def prepare_issue_certificate(
        self,
        vault_utxo: UTXO,
        cid: str,
        issuer: Literal["admin", "delegate"] = "delegate"
    ) -> dict:
        """
        Prepare certificate issuance for external signing.
        
        Returns dict with pset, sig_hash, and data needed for finalization.
        """
        vault = self.contracts.vault
        cert = self.contracts.certificate
        
        change_sats = vault_utxo.value - FEE_SATS - CERT_DUST_SATS
        sap_payload = self._build_sas_attest_payload(cid)
        
        inputs = [vault_utxo.to_dict()]
        outputs = [
            {"address": vault.address, "asset": self.contracts.asset_id, 
             "amount": self._sats_to_btc(change_sats)},
            {"address": cert.address, "asset": self.contracts.asset_id,
             "amount": self._sats_to_btc(CERT_DUST_SATS)},
            {"address": f"data:{sap_payload}", "asset": self.contracts.asset_id, "amount": 0},
            {"address": "fee", "asset": self.contracts.asset_id,
             "amount": self._sats_to_btc(FEE_SATS)}
        ]
        
        if issuer == "admin":
            dummy_witness = WitnessEncoder.vault_dummy("admin_issue")
        else:
            dummy_witness = WitnessEncoder.vault_dummy("delegate_issue")
        
        return self._prepare_transaction(
            inputs=inputs,
            outputs=outputs,
            contract=vault,
            utxo_value=vault_utxo.value,
            signer_role=issuer,
            dummy_witness=dummy_witness,
            witness_type="vault_issue"
        )
    
    def prepare_revoke_certificate(
        self,
        cert_utxo: UTXO,
        revoker: Literal["admin", "delegate"] = "admin",
        recipient: Optional[str] = None,
        reason_code: Optional[int] = None,
        replacement_txid: Optional[str] = None
    ) -> dict:
        """Prepare certificate revocation for external signing."""
        cert = self.contracts.certificate

        outputs = []
        sap_payload = None
        if reason_code is not None or replacement_txid is not None:
            sap_payload = self._build_sas_revoke_payload(
                cert_utxo.txid, cert_utxo.vout, reason_code, replacement_txid
            )

        if recipient and cert_utxo.value > FEE_SATS:
            output_sats = cert_utxo.value - FEE_SATS
            outputs.append(
                {"address": recipient, "asset": self.contracts.asset_id,
                 "amount": self._sats_to_btc(output_sats)}
            )
        else:
            outputs.append(
                {"address": "fee", "asset": self.contracts.asset_id,
                 "amount": self._sats_to_btc(cert_utxo.value)}
            )

        if sap_payload:
            outputs.append(
                {"address": f"data:{sap_payload}", "asset": self.contracts.asset_id, "amount": 0}
            )

        if recipient and cert_utxo.value > FEE_SATS:
            outputs.append(
                {"address": "fee", "asset": self.contracts.asset_id,
                 "amount": self._sats_to_btc(FEE_SATS)}
            )
        
        inputs = [cert_utxo.to_dict()]
        dummy_witness = WitnessEncoder.certificate_dummy(revoker)
        
        return self._prepare_transaction(
            inputs=inputs,
            outputs=outputs,
            contract=cert,
            utxo_value=cert_utxo.value,
            signer_role=revoker,
            dummy_witness=dummy_witness,
            witness_type="certificate"
        )
    
    def prepare_drain_vault(
        self,
        vault_utxo: UTXO,
        recipient: str
    ) -> dict:
        """Prepare vault drain for external signing."""
        vault = self.contracts.vault
        
        output_sats = vault_utxo.value - FEE_SATS
        inputs = [vault_utxo.to_dict()]
        outputs = [
            {"address": recipient, "asset": self.contracts.asset_id,
             "amount": self._sats_to_btc(output_sats)},
            {"address": "fee", "asset": self.contracts.asset_id,
             "amount": self._sats_to_btc(FEE_SATS)}
        ]
        
        dummy_witness = WitnessEncoder.vault_dummy("admin_unconditional")
        
        return self._prepare_transaction(
            inputs=inputs,
            outputs=outputs,
            contract=vault,
            utxo_value=vault_utxo.value,
            signer_role="admin",
            dummy_witness=dummy_witness,
            witness_type="vault_drain"
        )
    
    def _prepare_transaction(
        self,
        inputs: list,
        outputs: list,
        contract,
        utxo_value: int,
        signer_role: str,
        dummy_witness: str,
        witness_type: str
    ) -> dict:
        """
        Prepare transaction and return data for external signing.
        
        Returns dict with:
        - pset: Base64 encoded PSET
        - sig_hash: Hash to sign
        - input_index: Input being signed
        - program: Simplicity program
        - witness_template: Witness structure info
        """
        # Step 1: Create PSET
        pset = self.hal.pset_create(inputs, outputs)
        
        # Step 2: Update input
        pset = self.hal.pset_update_input(
            pset=pset,
            index=0,
            script_pubkey=contract.script_pubkey,
            asset=self.contracts.asset_id,
            amount=contract.sats_to_btc(utxo_value),
            cmr=contract.cmr,
            internal_key=self.contracts.internal_key
        )
        
        # Step 3: Get sig_all_hash with dummy witness
        run_result = self.hal.pset_run(pset, 0, contract.program, dummy_witness)
        
        return {
            "pset": pset,
            "sig_hash": run_result.sig_all_hash,
            "input_index": 0,
            "program": contract.program,
            "witness_template": witness_type,
            "signer_role": signer_role,
        }
    
    def finalize_with_signature(
        self,
        pset: str,
        input_index: int,
        program: str,
        witness_template: str,
        signature: bytes,
        issuer: str,
        broadcast: bool = True
    ) -> TransactionResult:
        """
        Finalize a prepared transaction with an external signature.
        
        Args:
            pset: Base64 encoded PSET from prepare_*.
            input_index: Input index being signed.
            program: Simplicity program.
            witness_template: Type of witness to create.
            signature: 64-byte Schnorr signature.
            issuer: Role that signed.
            broadcast: Whether to broadcast.
        
        Returns:
            TransactionResult.
        """
        try:
            # Create witness with signature based on type
            sig_hex = signature.hex()
            
            if witness_template == "vault_issue":
                witness = WitnessEncoder.encode_vault_witness(sig_hex, issuer, False)
            elif witness_template == "vault_drain":
                witness = WitnessEncoder.encode_vault_witness(sig_hex, "admin", True)
            elif witness_template == "certificate":
                witness = WitnessEncoder.encode_certificate_witness(sig_hex, issuer)
            else:
                return TransactionResult(
                    success=False,
                    error=f"Unknown witness_template: {witness_template}"
                )
            
            # Finalize
            finalized_pset = self.hal.pset_finalize(pset, input_index, program, witness)
            
            # Extract
            tx_hex = self.hal.pset_extract(finalized_pset)
            
            # Broadcast if requested
            if broadcast:
                return self.api.broadcast(tx_hex)
            else:
                return TransactionResult(
                    success=True,
                    raw_hex=tx_hex
                )
                
        except Exception as e:
            return TransactionResult(
                success=False,
                error=str(e)
            )
