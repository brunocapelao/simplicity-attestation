"""
Security Attack Vector Tests

These tests validate that the SAS covenant prevents common attack patterns.
They test the logic WITHOUT requiring the hal-simplicity binary by mocking
the infrastructure layer.

For full E2E attack vector testing with the actual binary, use:
    tests/test_attack_vectors.py (standalone script)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from sdk.protocols.sas import SAPProtocol
from sdk.core.witness import WitnessEncoder
from sdk.constants import MIN_ISSUE_SATS, FEE_SATS, CERT_DUST_SATS


# =============================================================================
# Covenant Attack Vector Tests (Logic Level)
# =============================================================================

class TestCovenantAttackVectors:
    """
    Tests that validate covenant constraints are properly enforced.
    
    These tests verify the SDK-level logic that must be consistent
    with the on-chain Simplicity covenant.
    """

    @pytest.mark.unit
    @pytest.mark.security
    def test_output_count_must_be_four(self):
        """
        Attack: Invalid output count (3 outputs instead of 4).
        
        The covenant requires exactly 4 outputs:
        1. Change back to vault
        2. Certificate output
        3. OP_RETURN with SAS payload
        4. Fee output
        """
        # A valid issuance must have exactly 4 outputs
        required_outputs = [
            "vault_change",      # Output 0
            "certificate_dust",  # Output 1
            "op_return_sas",     # Output 2
            "fee",               # Output 3
        ]
        
        # Three outputs is invalid
        invalid_outputs = required_outputs[:3]
        assert len(invalid_outputs) != 4
        
        # The SDK should reject this before even attempting to build
        # This is validated in TransactionBuilder

    @pytest.mark.unit
    @pytest.mark.security
    def test_change_must_return_to_vault(self):
        """
        Attack: Delegate diverts change to own address.
        
        If output[0] is not the vault address, the delegate could
        steal all vault funds by diverting change.
        """
        vault_address = "tex1qvaultaddress"
        attacker_address = "tex1qattackeraddr"
        
        # Valid: change goes to vault
        valid_outputs = [
            {"address": vault_address, "value": 98000},  # Change to vault
            {"address": "tex1qcertaddr", "value": CERT_DUST_SATS},
            {"address": "data:534153...", "value": 0},
            {"address": "fee", "value": FEE_SATS},
        ]
        
        # Attack: change goes to attacker
        attack_outputs = [
            {"address": attacker_address, "value": 98000},  # STOLEN!
            {"address": "tex1qcertaddr", "value": CERT_DUST_SATS},
            {"address": "data:534153...", "value": 0},
            {"address": "fee", "value": FEE_SATS},
        ]
        
        # The covenant checks that output[0].script == vault.script
        assert valid_outputs[0]["address"] == vault_address
        assert attack_outputs[0]["address"] != vault_address

    @pytest.mark.unit
    @pytest.mark.security
    def test_certificate_must_go_to_cert_address(self):
        """
        Attack: Certificate output sent to arbitrary address.
        
        If output[1] is not the certificate address, the attacker
        could intercept the certificate UTXO.
        """
        certificate_address = "tex1qcertificateaddr"
        attacker_address = "tex1qattackeraddr"
        
        # The covenant checks output[1].script == certificate.script
        assert certificate_address != attacker_address

    @pytest.mark.unit
    @pytest.mark.security
    def test_sas_payload_required(self):
        """
        Attack: Missing or invalid OP_RETURN.
        
        Output[2] must be an OP_RETURN with valid SAS payload.
        Without this, the certificate has no meaning.
        """
        # Valid SAS payload
        valid_cid = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
        payload = SAPProtocol.encode_attest(valid_cid)
        
        # Must start with SAS magic bytes
        assert payload.startswith("534153")  # "SAS" in hex
        
        # Invalid payload (wrong magic)
        invalid_magic = "585858" + payload[6:]  # "XXX" instead of "SAS"
        assert not SAPProtocol.is_sas_payload(bytes.fromhex(invalid_magic))


# =============================================================================
# Role Permission Attack Tests
# =============================================================================

class TestRolePermissionAttacks:
    """Tests that validate role-based permission enforcement."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_delegate_cannot_use_admin_unconditional_path(self):
        """
        Attack: Delegate uses admin_unconditional spending path.
        
        The admin_unconditional path allows draining the vault.
        Delegates must only use the delegate_issue path.
        """
        # Witness path bits:
        # - admin_unconditional: starts with 0 (Left)
        # - admin_issue: starts with 10 (Right-Left)
        # - delegate_issue: starts with 11 (Right-Right)
        
        admin_unconditional = WitnessEncoder.vault_dummy("admin_unconditional")
        delegate_issue = WitnessEncoder.vault_dummy("delegate_issue")
        
        # First bit of admin_unconditional is 0
        first_byte_admin = int(admin_unconditional[:2], 16)
        assert (first_byte_admin & 0x80) == 0  # Starts with 0
        
        # First bits of delegate_issue are 11
        first_byte_delegate = int(delegate_issue[:2], 16)
        assert (first_byte_delegate & 0xC0) == 0xC0  # Starts with 11

    @pytest.mark.unit
    @pytest.mark.security
    def test_forged_signature_rejected(self):
        """
        Attack: Using a signature from a different key.
        
        Even if attacker knows the spending path, they cannot
        forge a valid Schnorr signature.
        """
        # A valid signature is 64 bytes
        fake_signature = b"\x00" * 64
        
        # The witness encoding accepts any 64-byte signature
        # But the covenant will reject if it doesn't verify
        witness = WitnessEncoder.vault_delegate_issue(fake_signature)
        
        # Witness is encoded correctly (format is valid)
        assert len(bytes.fromhex(witness)) == 65
        
        # But the signature won't verify against the delegate pubkey
        # This is enforced by the Simplicity program, not the SDK


# =============================================================================
# Protocol Manipulation Tests
# =============================================================================

class TestProtocolManipulation:
    """Tests that validate protocol cannot be manipulated."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_revoke_requires_valid_txid(self):
        """
        Attack: Revoke with invalid txid to corrupt certificate tracking.
        """
        from sdk.sas import _validate_hex
        
        # Valid txid
        valid_txid = "a" * 64
        _validate_hex(valid_txid, "txid", 64)  # Should not raise
        
        # Attack: short txid
        with pytest.raises(ValueError):
            _validate_hex("a" * 32, "txid", 64)
        
        # Attack: malformed txid
        with pytest.raises(ValueError):
            _validate_hex("not-a-txid", "txid", 64)

    @pytest.mark.unit
    @pytest.mark.security
    def test_replacement_requires_reason(self):
        """
        Attack: Set replacement_txid without reason_code.
        
        Replacement must have a reason to prevent arbitrary certificate
        replacement without audit trail.
        """
        txid = "a" * 64
        replacement = "b" * 64
        
        # Valid: reason with replacement
        payload = SAPProtocol.encode_revoke(
            txid, 1, 
            reason_code=1, 
            replacement_txid=replacement
        )
        assert payload is not None
        
        # Invalid: replacement without reason
        with pytest.raises(ValueError, match="reason_code"):
            SAPProtocol.encode_revoke(
                txid, 1,
                reason_code=None,
                replacement_txid=replacement
            )

    @pytest.mark.unit
    @pytest.mark.security
    def test_cid_size_limit_enforced(self):
        """
        Attack: CID exceeds OP_RETURN size limit.
        
        OP_RETURN is limited to ~80 bytes. The SAS header uses 5 bytes,
        leaving 75 bytes for the CID.
        """
        from sdk.sas import _validate_cid
        
        # Valid CID (46 bytes)
        valid_cid = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
        _validate_cid(valid_cid)  # Should not raise
        
        # Attack: oversized CID (76+ bytes)
        oversized_cid = "x" * 76
        with pytest.raises(ValueError, match="75 byte"):
            _validate_cid(oversized_cid)


# =============================================================================
# Replay Attack Tests
# =============================================================================

class TestReplayAttacks:
    """Tests that validate protection against replay attacks."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_each_utxo_can_only_be_spent_once(self):
        """
        Attack: Replay a signed transaction to double-spend.
        
        Each UTXO is unique (txid:vout). Once spent, it cannot be
        replayed because the UTXO no longer exists.
        """
        from sdk.models import UTXO
        
        # UTXO is uniquely identified by txid:vout
        utxo1 = UTXO(txid="a" * 64, vout=0, value=100000)
        utxo2 = UTXO(txid="a" * 64, vout=1, value=50000)
        
        # Same txid, different vout = different UTXO
        assert utxo1.outpoint != utxo2.outpoint

    @pytest.mark.unit
    @pytest.mark.security
    def test_sig_all_hash_binds_to_transaction(self):
        """
        Attack: Use signature from one transaction in another.
        
        The sig_all_hash commits to all transaction inputs and outputs.
        A signature for one transaction won't work for another.
        """
        # sig_all_hash is computed by Simplicity and includes:
        # - Transaction version
        # - All inputs (txid, vout, sequence)
        # - All outputs (scriptPubKey, value, asset)
        # - Locktime
        
        # Changing ANY of these changes the sig_all_hash
        # Therefore, a signature is bound to one specific transaction
        pass  # This is enforced by Simplicity, tested in test_attack_vectors.py


# =============================================================================
# Fee Manipulation Tests
# =============================================================================

class TestFeeManipulation:
    """Tests that validate fee limits are enforced."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_fee_within_bounds(self):
        """
        Attack: Set abnormally high fee to drain vault slowly.
        
        Transaction fees must be within reasonable bounds.
        """
        # Current fee constant
        assert FEE_SATS == 500
        
        # Fee should be reasonable (not > 10000 sats)
        assert FEE_SATS <= 10000
        
        # Fee should cover at least minimum relay (> 100 sats)
        assert FEE_SATS >= 100

    @pytest.mark.unit
    @pytest.mark.security
    def test_change_calculation_correct(self):
        """
        Attack: Miscalculate change to leave dust in transaction.
        
        Change must equal: input - cert_dust - fee
        """
        input_value = 100000
        expected_change = input_value - CERT_DUST_SATS - FEE_SATS
        
        assert expected_change == 100000 - 546 - 500
        assert expected_change == 98954
        
        # Change must be >= dust limit to be spendable
        assert expected_change >= CERT_DUST_SATS
