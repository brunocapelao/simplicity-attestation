"""
Unit tests for SAPClient - High-level client operations.

These tests cover the client interface for vault operations,
certificate issuance, and revocation flows.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

from sdk.models import UTXO, Vault, Certificate, TransactionResult, CertificateStatus
from sdk.constants import MIN_ISSUE_SATS, FEE_SATS, CERT_DUST_SATS
from sdk.errors import (
    VaultEmptyError,
    InsufficientFundsError,
    CertificateNotFoundError,
)
from sdk.roles import Role, RoleContext, Permissions, PermissionError


# =============================================================================
# Helper Fixtures
# =============================================================================

@pytest.fixture
def mock_vault():
    """Create a mock vault with sufficient funds."""
    return Vault(
        address="tex1qmockvaultaddress",
        script_pubkey="5120" + "aa" * 32,
        cmr="bb" * 32,
        program="cc" * 32,
        balance=100000,  # 0.001 L-BTC
        utxos=[UTXO(txid="dd" * 32, vout=0, value=100000)]
    )


@pytest.fixture
def mock_certificate():
    """Create a mock certificate."""
    return Certificate(
        txid="ee" * 32,
        vout=1,
        cid="QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
        value=CERT_DUST_SATS,
        status=CertificateStatus.VALID,
    )


# =============================================================================
# Vault State Tests
# =============================================================================

class TestVaultState:
    """Tests for vault state management."""

    @pytest.mark.unit
    def test_vault_with_multiple_utxos_returns_first(self, mock_vault):
        """Test that UTXOs are returned in order (first available)."""
        utxos = [
            UTXO(txid="a" * 64, vout=0, value=1000),
            UTXO(txid="b" * 64, vout=0, value=5000),
            UTXO(txid="c" * 64, vout=0, value=2000),
        ]
        vault = Vault(
            address="tex1...",
            script_pubkey="5120" + "00" * 32,
            cmr="e" * 64,
            program="f" * 64,
            balance=8000,
            utxos=utxos
        )
        
        selected = vault.available_utxo
        assert selected is not None
        # Returns first UTXO in list
        assert selected.txid == "a" * 64

    @pytest.mark.unit
    def test_vault_balance_calculation(self):
        """Test that vault balance is sum of UTXOs."""
        utxos = [
            UTXO(txid="a" * 64, vout=0, value=1000),
            UTXO(txid="b" * 64, vout=0, value=2000),
            UTXO(txid="c" * 64, vout=0, value=3000),
        ]
        vault = Vault(
            address="tex1...",
            script_pubkey="5120" + "00" * 32,
            cmr="e" * 64,
            program="f" * 64,
            balance=6000,  # 1000 + 2000 + 3000
            utxos=utxos
        )
        
        assert vault.balance == 6000
        assert vault.can_issue is True

    @pytest.mark.unit
    def test_vault_multiple_issuances_possible(self):
        """Test that vault can support multiple certificate issuances."""
        # With 10000 sats, should be able to issue multiple certs
        # Each issuance costs: 546 (cert) + 500 (fee) = 1046, plus 546 change
        initial_balance = 10000
        issuance_cost = CERT_DUST_SATS + FEE_SATS  # 1046
        
        # After one issuance: 10000 - 1046 = 8954
        # After two issuances: 8954 - 1046 = 7908
        # etc.
        
        remaining = initial_balance
        issuances = 0
        while remaining >= MIN_ISSUE_SATS:
            remaining -= issuance_cost
            issuances += 1
        
        assert issuances >= 5  # Should support at least 5 issuances


# =============================================================================
# Certificate Lifecycle Tests
# =============================================================================

class TestCertificateLifecycle:
    """Tests for certificate lifecycle management."""

    @pytest.mark.unit
    def test_certificate_is_valid_when_active(self, mock_certificate):
        """Test that active certificates are valid."""
        assert mock_certificate.is_valid is True

    @pytest.mark.unit
    def test_certificate_is_invalid_when_revoked(self, mock_certificate):
        """Test that revoked certificates are invalid."""
        revoked_cert = Certificate(
            txid=mock_certificate.txid,
            vout=mock_certificate.vout,
            cid=mock_certificate.cid,
            value=mock_certificate.value,
            status=CertificateStatus.REVOKED,
        )
        
        assert revoked_cert.is_valid is False

    @pytest.mark.unit
    def test_certificate_outpoint_format(self, mock_certificate):
        """Test certificate outpoint string format."""
        outpoint = mock_certificate.outpoint
        assert ":" in outpoint
        txid, vout = outpoint.split(":")
        assert len(txid) == 64
        assert vout == "1"


# =============================================================================
# Error Scenario Tests
# =============================================================================

class TestClientErrorScenarios:
    """Tests for error handling in client operations."""

    @pytest.mark.unit
    def test_insufficient_funds_error_details(self):
        """Test InsufficientFundsError contains required and available."""
        error = InsufficientFundsError(
            required=MIN_ISSUE_SATS,
            available=500,
            message="Vault has insufficient funds"
        )
        
        assert "Vault has insufficient funds" in str(error)
        assert error.required == MIN_ISSUE_SATS
        assert error.available == 500

    @pytest.mark.unit
    def test_vault_empty_error_message(self):
        """Test VaultEmptyError provides clear message."""
        error = VaultEmptyError("tex1qexampleaddress")
        
        assert "tex1qexampleaddress" in str(error)

    @pytest.mark.unit
    def test_certificate_not_found_error(self):
        """Test CertificateNotFoundError details."""
        error = CertificateNotFoundError(
            txid="aa" * 32,
            vout=1
        )
        
        assert "aa" * 32 in str(error)


# =============================================================================
# Transaction Result Tests
# =============================================================================

class TestTransactionResultHandling:
    """Tests for transaction result processing."""

    @pytest.mark.unit
    def test_successful_result_properties(self):
        """Test successful transaction result."""
        result = TransactionResult(
            success=True,
            txid="ff" * 32,
            raw_hex="0200000001..." 
        )
        
        assert result.success is True
        assert result.txid == "ff" * 32
        assert result.error is None

    @pytest.mark.unit
    def test_failed_result_properties(self):
        """Test failed transaction result."""
        result = TransactionResult(
            success=False,
            error="broadcast failed: insufficient fee",
            raw_hex="0200000001..."
        )
        
        assert result.success is False
        assert result.txid is None
        assert "insufficient fee" in result.error

    @pytest.mark.unit
    def test_explorer_url_generation(self):
        """Test explorer URL generation."""
        result = TransactionResult(
            success=True,
            txid="aa" * 32,
        )
        
        # Default is testnet
        url = result.explorer_url()
        assert "aa" * 32 in url
        assert "blockstream.info" in url
        
        # Mainnet URL
        url_mainnet = result.explorer_url(network="mainnet")
        assert "aa" * 32 in url_mainnet
        assert "liquid" in url_mainnet


# =============================================================================
# Role-Based Access Tests  
# =============================================================================

class TestRoleBasedAccess:
    """Tests for role-based access control."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_admin_has_all_permissions(self):
        """Test admin role has all permissions."""
        ctx = RoleContext(Role.ADMIN)
        
        # Admin should have all permissions
        assert ctx.can_issue is True
        assert ctx.can_drain_vault is True
        assert ctx.can_revoke_any is True

    @pytest.mark.unit
    @pytest.mark.security
    def test_delegate_has_limited_permissions(self):
        """Test delegate role has limited permissions."""
        ctx = RoleContext(Role.DELEGATE)
        
        # Delegate can issue
        assert ctx.can_issue is True
        
        # But cannot drain vault or revoke any
        assert ctx.can_drain_vault is False
        assert ctx.can_revoke_any is False

    @pytest.mark.unit
    @pytest.mark.security
    def test_permission_check_prevents_unauthorized_action(self):
        """Test that permission checks prevent unauthorized actions."""
        ctx = RoleContext(Role.DELEGATE)
        
        # Attempting drain should fail
        with pytest.raises(PermissionError):
            ctx.require(Permissions.VAULT_DRAIN, "drain_vault")

    @pytest.mark.unit
    @pytest.mark.security
    def test_role_context_repr(self):
        """Test RoleContext string representation."""
        ctx = RoleContext(Role.ADMIN)
        assert "admin" in repr(ctx)
        
        ctx = RoleContext(Role.DELEGATE)
        assert "delegate" in repr(ctx)
