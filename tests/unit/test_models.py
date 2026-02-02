"""
Unit tests for SDK data models.
"""

import pytest
from sdk.models import (
    UTXO, Certificate, Vault, TransactionResult,
    CertificateStatus, IssuerType, SpendingPath,
    JetResult, RunResult
)
from sdk.constants import MIN_ISSUE_SATS


class TestUTXO:
    """Tests for UTXO model."""

    @pytest.mark.unit
    def test_utxo_outpoint(self, sample_utxo):
        """Test UTXO outpoint property."""
        assert sample_utxo.outpoint == f"{sample_utxo.txid}:{sample_utxo.vout}"

    @pytest.mark.unit
    def test_utxo_to_dict(self, sample_utxo):
        """Test UTXO to_dict method."""
        d = sample_utxo.to_dict()
        assert d["txid"] == sample_utxo.txid
        assert d["vout"] == sample_utxo.vout


class TestCertificate:
    """Tests for Certificate model."""

    @pytest.mark.unit
    def test_certificate_outpoint(self, sample_certificate):
        """Test Certificate outpoint property."""
        expected = f"{sample_certificate.txid}:{sample_certificate.vout}"
        assert sample_certificate.outpoint == expected

    @pytest.mark.unit
    def test_certificate_is_valid_true(self, sample_certificate):
        """Test is_valid returns True for valid certificate."""
        assert sample_certificate.is_valid is True

    @pytest.mark.unit
    def test_certificate_is_valid_false(self):
        """Test is_valid returns False for revoked certificate."""
        cert = Certificate(
            txid="a" * 64,
            vout=1,
            cid="QmTest",
            status=CertificateStatus.REVOKED
        )
        assert cert.is_valid is False


class TestVault:
    """Tests for Vault model."""

    @pytest.mark.unit
    def test_vault_can_issue_sufficient_funds(self, sample_vault):
        """Test can_issue with sufficient funds."""
        # sample_vault has 100000 sats, MIN_ISSUE_SATS is 1592
        assert sample_vault.can_issue is True

    @pytest.mark.unit
    def test_vault_can_issue_minimum(self):
        """Test can_issue at exactly minimum balance."""
        vault = Vault(
            address="tex1...",
            script_pubkey="5120" + "00" * 32,
            cmr="e" * 64,
            program="f" * 64,
            balance=MIN_ISSUE_SATS  # Exactly minimum
        )
        assert vault.can_issue is True

    @pytest.mark.unit
    def test_vault_can_issue_below_minimum(self):
        """Test can_issue below minimum balance."""
        vault = Vault(
            address="tex1...",
            script_pubkey="5120" + "00" * 32,
            cmr="e" * 64,
            program="f" * 64,
            balance=MIN_ISSUE_SATS - 1  # One below minimum
        )
        assert vault.can_issue is False

    @pytest.mark.unit
    def test_vault_can_issue_zero_balance(self):
        """Test can_issue with zero balance."""
        vault = Vault(
            address="tex1...",
            script_pubkey="5120" + "00" * 32,
            cmr="e" * 64,
            program="f" * 64,
            balance=0
        )
        assert vault.can_issue is False

    @pytest.mark.unit
    def test_vault_available_utxo(self, sample_vault):
        """Test available_utxo returns first UTXO."""
        assert sample_vault.available_utxo is not None
        assert sample_vault.available_utxo.txid == "a" * 64

    @pytest.mark.unit
    def test_vault_available_utxo_empty(self):
        """Test available_utxo returns None when empty."""
        vault = Vault(
            address="tex1...",
            script_pubkey="5120" + "00" * 32,
            cmr="e" * 64,
            program="f" * 64,
            utxos=[]
        )
        assert vault.available_utxo is None

    @pytest.mark.unit
    def test_vault_min_issue_sats_value(self):
        """Test MIN_ISSUE_SATS is correct value."""
        # 546 (cert) + 500 (fee) + 546 (change) = 1592
        assert MIN_ISSUE_SATS == 1592


class TestTransactionResult:
    """Tests for TransactionResult model."""

    @pytest.mark.unit
    def test_transaction_result_success(self):
        """Test successful TransactionResult."""
        result = TransactionResult(success=True, txid="a" * 64)
        assert result.success is True
        assert result.txid == "a" * 64

    @pytest.mark.unit
    def test_transaction_result_failure(self):
        """Test failed TransactionResult."""
        result = TransactionResult(success=False, error="Test error")
        assert result.success is False
        assert result.error == "Test error"

    @pytest.mark.unit
    def test_explorer_url_testnet(self):
        """Test explorer_url for testnet."""
        result = TransactionResult(success=True, txid="abc123")
        url = result.explorer_url("testnet")
        assert "liquidtestnet" in url
        assert "abc123" in url

    @pytest.mark.unit
    def test_explorer_url_mainnet(self):
        """Test explorer_url for mainnet."""
        result = TransactionResult(success=True, txid="abc123")
        url = result.explorer_url("mainnet")
        assert "liquid" in url
        assert "liquidtestnet" not in url
        assert "abc123" in url

    @pytest.mark.unit
    def test_explorer_url_no_txid(self):
        """Test explorer_url returns None when no txid."""
        result = TransactionResult(success=False, error="failed")
        assert result.explorer_url() is None


class TestRunResult:
    """Tests for RunResult model."""

    @pytest.mark.unit
    def test_run_result_from_dict_success(self):
        """Test creating RunResult from hal-simplicity output."""
        data = {
            "success": True,
            "jets": [
                {"jet": "sig_all_hash", "success": True, "output_value": "0xabcd1234"}
            ]
        }
        result = RunResult.from_dict(data)

        assert result.success is True
        assert result.sig_all_hash == "abcd1234"  # 0x prefix removed
        assert len(result.jets) == 1

    @pytest.mark.unit
    def test_run_result_from_dict_failure(self):
        """Test creating RunResult from failed execution."""
        data = {
            "success": False,
            "jets": [
                {"jet": "bip_0340_verify", "success": False}
            ]
        }
        result = RunResult.from_dict(data)

        assert result.success is False
        assert result.sig_all_hash is None

    @pytest.mark.unit
    def test_run_result_from_dict_empty_jets(self):
        """Test creating RunResult with empty jets."""
        data = {"success": True, "jets": []}
        result = RunResult.from_dict(data)

        assert result.success is True
        assert result.jets == []
        assert result.sig_all_hash is None


class TestEnums:
    """Tests for SDK enums."""

    @pytest.mark.unit
    def test_certificate_status_values(self):
        """Test CertificateStatus enum values."""
        assert CertificateStatus.VALID.value == "valid"
        assert CertificateStatus.REVOKED.value == "revoked"
        assert CertificateStatus.UNKNOWN.value == "unknown"

    @pytest.mark.unit
    def test_issuer_type_values(self):
        """Test IssuerType enum values."""
        assert IssuerType.ADMIN.value == "admin"
        assert IssuerType.DELEGATE.value == "delegate"

    @pytest.mark.unit
    def test_spending_path_values(self):
        """Test SpendingPath enum values."""
        assert SpendingPath.ADMIN_UNCONDITIONAL.value == "left"
        assert SpendingPath.ADMIN_ISSUE.value == "right_left"
        assert SpendingPath.DELEGATE_ISSUE.value == "right_right"
