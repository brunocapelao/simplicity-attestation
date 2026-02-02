"""
SAS SDK Test Configuration

Shared fixtures and test utilities.
"""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
import sys

# Ensure sdk is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sdk.models import UTXO, Vault, TransactionResult, Certificate, CertificateStatus


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_api():
    """Mock BlockstreamAPI for isolated testing."""
    api = Mock()
    api.get_utxos.return_value = [
        UTXO(txid="a" * 64, vout=0, value=100000)
    ]
    api.get_balance.return_value = 100000
    api.broadcast.return_value = TransactionResult(
        success=True,
        txid="b" * 64
    )
    return api


@pytest.fixture
def mock_hal():
    """Mock HalSimplicity for isolated testing."""
    from sdk.models import RunResult, JetResult

    hal = Mock()
    hal.pset_create.return_value = "base64pset=="
    hal.pset_update_input.return_value = "updated_pset=="
    hal.pset_run.return_value = RunResult(
        success=True,
        sig_all_hash="c" * 64,
        jets=[JetResult(jet="sig_all_hash", success=True, output_value="0x" + "c" * 64)]
    )
    hal.pset_finalize.return_value = "finalized_pset=="
    hal.pset_extract.return_value = "d" * 128  # tx hex
    return hal


@pytest.fixture
def sample_vault():
    """Sample Vault for testing."""
    return Vault(
        address="tex1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqd3h7hu",
        script_pubkey="5120" + "00" * 32,
        cmr="e" * 64,
        program="f" * 64,
        balance=100000,
        utxos=[UTXO(txid="a" * 64, vout=0, value=100000)]
    )


@pytest.fixture
def sample_certificate():
    """Sample Certificate for testing."""
    return Certificate(
        txid="a" * 64,
        vout=1,
        cid="QmTestCID123",
        status=CertificateStatus.VALID,
        value=546
    )


@pytest.fixture
def sample_utxo():
    """Sample UTXO for testing."""
    return UTXO(
        txid="a" * 64,
        vout=0,
        value=100000
    )


# =============================================================================
# Test Keys (DO NOT USE IN PRODUCTION)
# =============================================================================

@pytest.fixture
def test_private_key():
    """Test private key - DO NOT USE IN PRODUCTION."""
    return "0000000000000000000000000000000000000000000000000000000000000001"


@pytest.fixture
def test_public_key():
    """Expected public key for test_private_key."""
    # This is the x-only pubkey for private key = 1
    return "79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798"


# =============================================================================
# Marker Helpers
# =============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (mocked services)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (real network)")
    config.addinivalue_line("markers", "security: Security-focused tests")
