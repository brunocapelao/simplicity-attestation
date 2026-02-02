"""
Unit tests for SAS Protocol (OP_RETURN encoding/decoding).
"""

import pytest
from sdk.protocols.sas import SAPProtocol, SAPAttest, SAPRevoke, SAPUpdate


class TestSAPProtocolEncode:
    """Tests for SAS protocol encoding."""

    @pytest.mark.unit
    def test_encode_attest_valid_cid(self):
        """Test encoding attestation with valid CID."""
        result = SAPProtocol.encode_attest("QmTest123")
        # Should start with "SAS" magic (534153) + version (01) + type (01)
        assert result.startswith("534153")
        assert len(result) > 10  # Header + CID

    @pytest.mark.unit
    def test_encode_attest_hex_cid(self):
        """Test encoding attestation with hex CID."""
        hex_cid = "abcd1234" * 8  # 32-byte hex
        result = SAPProtocol.encode_attest(hex_cid)
        assert "534153" in result

    @pytest.mark.unit
    def test_encode_attest_too_large(self):
        """Test that oversized CID raises error."""
        large_cid = "x" * 76  # Exceeds 75 byte limit
        with pytest.raises(SAPProtocol.PayloadTooLargeError):
            SAPProtocol.encode_attest(large_cid)

    @pytest.mark.unit
    def test_encode_attest_max_size(self):
        """Test encoding attestation at exactly max size."""
        max_cid = "x" * 75  # Exactly 75 bytes
        result = SAPProtocol.encode_attest(max_cid)
        assert result is not None

    @pytest.mark.unit
    def test_encode_revoke_minimal(self):
        """Test encoding revocation with minimal payload (txid + vout)."""
        txid = "a" * 64
        vout = 1
        result = SAPProtocol.encode_revoke(txid, vout)
        # Header (10 chars) + txid (64 chars) + vout (4 chars) = 78 chars
        assert len(result) == 78

    @pytest.mark.unit
    def test_encode_revoke_with_reason(self):
        """Test encoding revocation with reason code."""
        txid = "a" * 64
        result = SAPProtocol.encode_revoke(txid, 1, reason_code=6)
        # Should have 2 more chars for reason_code byte
        assert len(result) == 80

    @pytest.mark.unit
    def test_encode_revoke_with_replacement(self):
        """Test encoding revocation with replacement txid."""
        txid = "a" * 64
        replacement = "b" * 64
        result = SAPProtocol.encode_revoke(txid, 1, reason_code=6, replacement_txid=replacement)
        # Header + txid + vout + reason + replacement = 144 chars
        assert len(result) == 144

    @pytest.mark.unit
    def test_encode_revoke_replacement_requires_reason(self):
        """Test that replacement_txid requires reason_code."""
        txid = "a" * 64
        replacement = "b" * 64
        with pytest.raises(ValueError, match="replacement_txid requires reason_code"):
            SAPProtocol.encode_revoke(txid, 1, replacement_txid=replacement)

    @pytest.mark.unit
    def test_encode_revoke_invalid_reason_code(self):
        """Test that invalid reason_code raises error."""
        txid = "a" * 64
        with pytest.raises(ValueError, match="reason_code must be between"):
            SAPProtocol.encode_revoke(txid, 1, reason_code=256)

    @pytest.mark.unit
    def test_encode_update_valid(self):
        """Test encoding update payload."""
        result = SAPProtocol.encode_update("QmNewCID")
        assert result.startswith("534153")


class TestSAPProtocolDecode:
    """Tests for SAS protocol decoding."""

    @pytest.mark.unit
    def test_decode_attest_roundtrip(self):
        """Test encode-decode roundtrip for attestation."""
        original_cid = "QmTestCID123"
        encoded = SAPProtocol.encode_attest(original_cid)
        decoded = SAPProtocol.decode_hex(encoded)

        assert isinstance(decoded, SAPAttest)
        assert decoded.cid == original_cid
        assert decoded.version == 1

    @pytest.mark.unit
    def test_decode_revoke_minimal_roundtrip(self):
        """Test encode-decode roundtrip for minimal revocation."""
        txid = "a" * 64
        vout = 1
        encoded = SAPProtocol.encode_revoke(txid, vout)
        decoded = SAPProtocol.decode_hex(encoded)

        assert isinstance(decoded, SAPRevoke)
        assert decoded.txid == txid
        assert decoded.vout == vout
        assert decoded.reason_code is None
        assert decoded.replacement_txid is None

    @pytest.mark.unit
    def test_decode_revoke_with_reason_roundtrip(self):
        """Test encode-decode roundtrip for revocation with reason."""
        txid = "a" * 64
        encoded = SAPProtocol.encode_revoke(txid, 1, reason_code=6)
        decoded = SAPProtocol.decode_hex(encoded)

        assert isinstance(decoded, SAPRevoke)
        assert decoded.reason_code == 6
        assert decoded.replacement_txid is None

    @pytest.mark.unit
    def test_decode_revoke_with_replacement_roundtrip(self):
        """Test encode-decode roundtrip for revocation with replacement."""
        txid = "a" * 64
        replacement = "b" * 64
        encoded = SAPProtocol.encode_revoke(txid, 1, reason_code=6, replacement_txid=replacement)
        decoded = SAPProtocol.decode_hex(encoded)

        assert isinstance(decoded, SAPRevoke)
        assert decoded.reason_code == 6
        assert decoded.replacement_txid == replacement

    @pytest.mark.unit
    def test_decode_update_roundtrip(self):
        """Test encode-decode roundtrip for update."""
        original_cid = "QmNewCID456"
        encoded = SAPProtocol.encode_update(original_cid)
        decoded = SAPProtocol.decode_hex(encoded)

        assert isinstance(decoded, SAPUpdate)
        assert decoded.cid == original_cid

    @pytest.mark.unit
    def test_decode_invalid_magic(self):
        """Test that invalid magic bytes returns None."""
        invalid = "414243" + "01" + "01" + "00" * 10  # "ABC" instead of "SAS"
        decoded = SAPProtocol.decode_hex(invalid)
        assert decoded is None

    @pytest.mark.unit
    def test_decode_unsupported_version(self):
        """Test that unsupported version returns None."""
        # "SAS" + version 2 + type 1
        invalid = "534153" + "02" + "01" + "00" * 10
        decoded = SAPProtocol.decode_hex(invalid)
        assert decoded is None

    @pytest.mark.unit
    def test_decode_too_short(self):
        """Test that too short data returns None."""
        decoded = SAPProtocol.decode_hex("534153")  # Only magic, missing version+type
        assert decoded is None

    @pytest.mark.unit
    def test_decode_revoke_partial_replacement_rejected(self):
        """Test that partial replacement_txid (36-66 bytes payload) is rejected."""
        # Create a payload with 40 bytes (txid:32 + vout:2 + reason:1 + partial:5)
        # This should be rejected as invalid
        header = "534153" + "01" + "02"  # SAS + version + REVOKE type
        txid = "a" * 64
        vout = "0001"  # 1 as big-endian 2 bytes
        reason = "06"
        partial_replacement = "b" * 10  # Only 5 bytes instead of 32

        invalid = header + txid + vout + reason + partial_replacement
        decoded = SAPProtocol.decode_hex(invalid)
        assert decoded is None


class TestSAPProtocolValidation:
    """Tests for SAS protocol validation."""

    @pytest.mark.unit
    def test_is_sas_payload_valid(self):
        """Test is_sas_payload with valid payload."""
        encoded = SAPProtocol.encode_attest("test")
        data = bytes.fromhex(encoded)
        assert SAPProtocol.is_sas_payload(data) is True

    @pytest.mark.unit
    def test_is_sas_payload_invalid(self):
        """Test is_sas_payload with invalid payload."""
        data = b"invalid"
        assert SAPProtocol.is_sas_payload(data) is False

    @pytest.mark.unit
    def test_is_sas_payload_too_short(self):
        """Test is_sas_payload with too short data."""
        data = b"SAS"  # Only magic, missing version+type
        assert SAPProtocol.is_sas_payload(data) is False

    @pytest.mark.unit
    def test_validate_payload_size_valid(self):
        """Test validate_payload_size with valid size."""
        payload = b"x" * 75
        # Should not raise
        SAPProtocol.validate_payload_size(payload)

    @pytest.mark.unit
    def test_validate_payload_size_invalid(self):
        """Test validate_payload_size with oversized payload."""
        payload = b"x" * 76
        with pytest.raises(SAPProtocol.PayloadTooLargeError):
            SAPProtocol.validate_payload_size(payload)
