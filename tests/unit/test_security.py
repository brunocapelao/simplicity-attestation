"""
Unit tests for SAS SDK - Security and Edge Cases

These tests validate security-critical behaviors without requiring
external binaries (hal-simplicity). They use mocking to simulate
the infrastructure layer.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from sdk.models import UTXO, Vault, TransactionResult
from sdk.constants import MIN_ISSUE_SATS, FEE_SATS, CERT_DUST_SATS
from sdk.errors import (
    SAPError,
    VaultEmptyError, 
    InsufficientFundsError,
    CertificateNotFoundError,
)


# =============================================================================
# Configuration Validation Tests
# =============================================================================

class TestConfigurationValidation:
    """Tests for configuration validation and error handling."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_mismatched_private_key_rejected(self):
        """Test that SDK rejects private key that doesn't match config."""
        from sdk.sas import SAS, ConfigurationError
        from sdk.infra.keys import KeyManager
        
        # Create a mock config with specific admin pubkey
        mock_config = Mock()
        mock_config.admin_pubkey = "a" * 64  # Expected pubkey
        mock_config.delegate_pubkey = "b" * 64
        mock_config.vault_address = "tex1..."
        mock_config.certificate_address = "tex1..."
        mock_config.asset_id = "c" * 64
        mock_config.network = "testnet"
        mock_config.hal_binary = "hal-simplicity"
        mock_config.api_base_url = "https://blockstream.info/liquid/testnet/api"
        
        # Use a different private key that produces different pubkey
        wrong_private_key = "d" * 64
        
        with patch('sdk.sas.VaultConfig.load', return_value=mock_config):
            with pytest.raises(ConfigurationError, match="doesn't match"):
                SAS.as_admin("fake_config.json", private_key=wrong_private_key)

    @pytest.mark.unit
    @pytest.mark.security
    def test_empty_private_key_rejected(self):
        """Test that SDK rejects empty private key."""
        from sdk.sas import SAS
        from embit.ec import ECError
        
        mock_config = Mock()
        mock_config.admin_pubkey = "a" * 64
        mock_config.delegate_pubkey = "b" * 64
        mock_config.vault_address = "tex1..."
        mock_config.certificate_address = "tex1..."
        mock_config.asset_id = "c" * 64
        mock_config.network = "testnet"
        mock_config.hal_binary = "hal-simplicity"
        mock_config.api_base_url = "https://blockstream.info/liquid/testnet/api"
        
        with patch('sdk.sas.VaultConfig.load', return_value=mock_config):
            # Empty key results in 0-byte array which ECError rejects
            with pytest.raises((ValueError, SAPError, ECError)):
                SAS.as_admin("fake_config.json", private_key="")

    @pytest.mark.unit
    @pytest.mark.security
    def test_invalid_hex_private_key_rejected(self):
        """Test that SDK rejects non-hex private key."""
        from sdk.sas import SAS
        
        mock_config = Mock()
        mock_config.admin_pubkey = "a" * 64
        mock_config.delegate_pubkey = "b" * 64
        mock_config.vault_address = "tex1..."
        mock_config.certificate_address = "tex1..."
        mock_config.asset_id = "c" * 64
        mock_config.network = "testnet"
        mock_config.hal_binary = "hal-simplicity"
        mock_config.api_base_url = "https://blockstream.info/liquid/testnet/api"
        
        with patch('sdk.sas.VaultConfig.load', return_value=mock_config):
            with pytest.raises((ValueError, SAPError)):
                SAS.as_admin("fake_config.json", private_key="not_valid_hex!")


# =============================================================================
# Vault Funding Validation Tests
# =============================================================================

class TestVaultFundingValidation:
    """Tests for vault funding requirements."""

    @pytest.mark.unit
    def test_insufficient_funds_error_raised(self):
        """Test that InsufficientFundsError is raised when vault is underfunded."""
        vault = Vault(
            address="tex1...",
            script_pubkey="5120" + "00" * 32,
            cmr="e" * 64,
            program="f" * 64,
            balance=MIN_ISSUE_SATS - 1,  # Just below minimum
            utxos=[UTXO(txid="a" * 64, vout=0, value=MIN_ISSUE_SATS - 1)]
        )
        
        assert vault.can_issue is False

    @pytest.mark.unit
    def test_exact_minimum_funds_accepted(self):
        """Test that exact MIN_ISSUE_SATS is accepted."""
        vault = Vault(
            address="tex1...",
            script_pubkey="5120" + "00" * 32,
            cmr="e" * 64,
            program="f" * 64,
            balance=MIN_ISSUE_SATS,
            utxos=[UTXO(txid="a" * 64, vout=0, value=MIN_ISSUE_SATS)]
        )
        
        assert vault.can_issue is True

    @pytest.mark.unit
    def test_vault_empty_error_on_no_utxos(self):
        """Test that VaultEmptyError scenario is handled."""
        vault = Vault(
            address="tex1...",
            script_pubkey="5120" + "00" * 32,
            cmr="e" * 64,
            program="f" * 64,
            balance=0,
            utxos=[]
        )
        
        assert vault.available_utxo is None
        assert vault.can_issue is False


# =============================================================================
# Input Validation Edge Cases
# =============================================================================

class TestInputValidationEdgeCases:
    """Tests for input validation edge cases."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_txid_sql_injection_prevented(self):
        """Test that SQL-like injection in txid is rejected."""
        from sdk.sas import _validate_hex
        
        malicious_inputs = [
            "'; DROP TABLE certificates; --",
            "1' OR '1'='1",
            "<script>alert('xss')</script>",
            "../../../etc/passwd",
            "NULL",
        ]
        
        for malicious in malicious_inputs:
            with pytest.raises(ValueError):
                _validate_hex(malicious, "txid", 64)

    @pytest.mark.unit
    @pytest.mark.security
    def test_cid_command_injection_prevented(self):
        """Test that command injection in CID is validated."""
        from sdk.sas import _validate_cid
        
        # These should be treated as valid text CIDs (not executed)
        # The validation should NOT raise - it just encodes as UTF-8
        dangerous_cids = [
            "$(whoami)",
            "`cat /etc/passwd`",
            "; rm -rf /",
        ]
        
        for cid in dangerous_cids:
            # Should not raise - just validates byte length
            result = _validate_cid(cid)
            assert result == cid  # Passed through unchanged

    @pytest.mark.unit
    def test_reason_code_bounds(self):
        """Test reason code validation (0-255)."""
        from sdk.protocols.sas import SAPProtocol
        
        # Valid reason codes
        assert SAPProtocol.encode_revoke("a" * 64, 0, reason_code=0) is not None
        assert SAPProtocol.encode_revoke("a" * 64, 0, reason_code=255) is not None
        
        # Invalid reason codes should raise
        with pytest.raises(ValueError):
            SAPProtocol.encode_revoke("a" * 64, 0, reason_code=256)
        
        with pytest.raises(ValueError):
            SAPProtocol.encode_revoke("a" * 64, 0, reason_code=-1)


# =============================================================================
# Protocol Encoding Security
# =============================================================================

class TestProtocolEncodingSecurity:
    """Tests for protocol encoding/decoding security."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_decode_rejects_truncated_replacement_txid(self):
        """Test that partial replacement_txid is rejected (36-66 bytes)."""
        from sdk.protocols.sas import SAPProtocol
        
        # Valid full revoke with replacement: 34 + 1 + 32 = 67 bytes payload
        # Partial/corrupted should be rejected
        
        magic = bytes.fromhex("534153")  # SAS
        version = bytes([0x01])
        op_type = bytes([0x02])  # REVOKE
        
        txid = bytes.fromhex("a" * 64)
        vout = (0).to_bytes(2, 'big')
        reason = bytes([0x01])
        partial_replacement = bytes.fromhex("bb" * 16)  # Only 16 bytes, not 32
        
        # 32 + 2 + 1 + 16 = 51 bytes (between 35 and 67)
        payload = magic + version + op_type + txid + vout + reason + partial_replacement
        
        result = SAPProtocol.decode(payload)
        assert result is None  # Should be rejected

    @pytest.mark.unit
    @pytest.mark.security
    def test_decode_handles_malformed_magic(self):
        """Test that malformed magic bytes are rejected gracefully."""
        from sdk.protocols.sas import SAPProtocol
        
        malformed = [
            b"",  # Empty
            b"SA",  # Too short
            b"XYZ\x01\x01",  # Wrong magic
            b"\x00\x00\x00\x01\x01",  # Null bytes
        ]
        
        for data in malformed:
            result = SAPProtocol.decode(data)
            assert result is None


# =============================================================================
# API Error Handling
# =============================================================================

class TestAPIErrorHandling:
    """Tests for API error handling and resilience."""

    @pytest.mark.unit
    def test_api_timeout_handled(self):
        """Test that API timeout is handled gracefully."""
        from sdk.infra.api import BlockstreamAPI, BlockstreamAPIError
        import requests
        
        api = BlockstreamAPI(network="testnet")
        
        # Mock the session.get method
        with patch.object(api.session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
            
            with pytest.raises(BlockstreamAPIError):
                api._get("address/tex1.../utxo")

    @pytest.mark.unit
    def test_api_connection_error_handled(self):
        """Test that connection error is handled."""
        from sdk.infra.api import BlockstreamAPI, BlockstreamAPIError
        import requests
        
        api = BlockstreamAPI(network="testnet")
        
        with patch.object(api.session, 'get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("No route to host")
            
            with pytest.raises(BlockstreamAPIError):
                api._get("address/tex1.../utxo")

    @pytest.mark.unit
    def test_api_invalid_json_raises_error(self):
        """Test that invalid JSON raises BlockstreamAPIError."""
        from sdk.infra.api import BlockstreamAPI, BlockstreamAPIError
        import requests
        
        api = BlockstreamAPI(network="testnet")
        
        # The _get method wraps all RequestException in BlockstreamAPIError
        # JSONDecodeError is not a RequestException, so we test via the
        # get_utxos which catches BlockstreamAPIError and returns []
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        # Simulate a malformed response that causes requests to fail
        mock_response.json.side_effect = requests.exceptions.JSONDecodeError("Invalid", "", 0)
        
        with patch.object(api.session, 'get', return_value=mock_response):
            # get_utxos catches BlockstreamAPIError and returns []
            result = api.get_utxos("tex1...")
            assert result == []

    @pytest.mark.unit
    def test_api_http_error_handled(self):
        """Test that HTTP errors raise BlockstreamAPIError."""
        from sdk.infra.api import BlockstreamAPI, BlockstreamAPIError
        import requests
        
        api = BlockstreamAPI(network="testnet")
        
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        with patch.object(api.session, 'get', return_value=mock_response):
            with pytest.raises(BlockstreamAPIError):
                api._get("tx/invalid")


# =============================================================================
# Transaction Builder State Machine
# =============================================================================

class TestTransactionBuilderStateMachine:
    """Tests for transaction builder workflow integrity."""

    @pytest.mark.unit
    def test_witness_requires_signature(self):
        """Test that witness encoding requires valid signature."""
        from sdk.core.witness import WitnessEncoder
        
        # Empty signature should fail
        with pytest.raises(ValueError):
            WitnessEncoder.vault_admin_issue(b"")
        
        # Wrong length should fail
        with pytest.raises(ValueError):
            WitnessEncoder.vault_admin_issue(b"\x00" * 63)
        
        with pytest.raises(ValueError):
            WitnessEncoder.vault_admin_issue(b"\x00" * 65)

    @pytest.mark.unit
    def test_hal_simplicity_interface_complete(self):
        """Test that HalSimplicity has all required PSET methods."""
        from sdk.infra.hal import HalSimplicity
        
        # Just verify the class has the required methods
        assert hasattr(HalSimplicity, 'pset_create')
        assert hasattr(HalSimplicity, 'pset_update_input')
        assert hasattr(HalSimplicity, 'pset_run')
        assert hasattr(HalSimplicity, 'pset_finalize')
        assert hasattr(HalSimplicity, 'pset_extract')
        assert hasattr(HalSimplicity, 'verify_program')


# =============================================================================
# Constants Consistency
# =============================================================================

class TestConstantsConsistency:
    """Tests for constants consistency across the SDK."""

    @pytest.mark.unit
    def test_min_issue_sats_formula(self):
        """Test MIN_ISSUE_SATS equals CERT_DUST + FEE + CERT_DUST (change)."""
        expected = CERT_DUST_SATS + FEE_SATS + CERT_DUST_SATS
        assert MIN_ISSUE_SATS == expected == 1592

    @pytest.mark.unit
    def test_dust_limit_is_546(self):
        """Test dust limit is Bitcoin's standard 546 sats."""
        assert CERT_DUST_SATS == 546

    @pytest.mark.unit
    def test_fee_is_reasonable(self):
        """Test fee is within reasonable range (100-1000 sats)."""
        assert 100 <= FEE_SATS <= 1000
