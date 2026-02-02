"""
Unit tests for WitnessEncoder (bit-level witness encoding).
"""

import pytest
from sdk.core.witness import WitnessEncoder


class TestWitnessEncoderBitPatterns:
    """Tests for witness bit pattern encoding."""

    @pytest.mark.unit
    def test_vault_admin_unconditional_pattern(self):
        """Test that admin unconditional path starts with Left tag (0)."""
        sig = b'\x00' * 64
        witness = WitnessEncoder.vault_admin_unconditional(sig)

        # Convert to bits and check first bit is 0 (Left path)
        first_byte = int(witness[:2], 16)
        assert (first_byte >> 7) == 0  # First bit should be 0

    @pytest.mark.unit
    def test_vault_admin_issue_pattern(self):
        """Test that admin issue path starts with Right-Left tag (10)."""
        sig = b'\x00' * 64
        witness = WitnessEncoder.vault_admin_issue(sig)

        # Convert to bits and check first two bits are 10
        first_byte = int(witness[:2], 16)
        assert (first_byte >> 6) == 2  # Binary 10 = decimal 2

    @pytest.mark.unit
    def test_vault_delegate_issue_pattern(self):
        """Test that delegate issue path starts with Right-Right tag (11)."""
        sig = b'\x00' * 64
        witness = WitnessEncoder.vault_delegate_issue(sig)

        # Convert to bits and check first two bits are 11
        first_byte = int(witness[:2], 16)
        assert (first_byte >> 6) == 3  # Binary 11 = decimal 3

    @pytest.mark.unit
    def test_certificate_admin_pattern(self):
        """Test that certificate admin path starts with Left tag (0)."""
        sig = b'\x00' * 64
        witness = WitnessEncoder.certificate_admin(sig)

        first_byte = int(witness[:2], 16)
        assert (first_byte >> 7) == 0  # First bit should be 0

    @pytest.mark.unit
    def test_certificate_delegate_pattern(self):
        """Test that certificate delegate path starts with Right tag (1)."""
        sig = b'\x00' * 64
        witness = WitnessEncoder.certificate_delegate(sig)

        first_byte = int(witness[:2], 16)
        assert (first_byte >> 7) == 1  # First bit should be 1


class TestWitnessEncoderOutput:
    """Tests for witness output format."""

    @pytest.mark.unit
    def test_witness_length(self):
        """Test that all witnesses are 65 bytes (130 hex chars)."""
        sig = b'\x00' * 64

        witnesses = [
            WitnessEncoder.vault_admin_unconditional(sig),
            WitnessEncoder.vault_admin_issue(sig),
            WitnessEncoder.vault_delegate_issue(sig),
            WitnessEncoder.certificate_admin(sig),
            WitnessEncoder.certificate_delegate(sig),
        ]

        for witness in witnesses:
            assert len(witness) == 130  # 65 bytes * 2 chars/byte

    @pytest.mark.unit
    def test_witness_is_hex(self):
        """Test that witness output is valid hexadecimal."""
        sig = b'\xab' * 64
        witness = WitnessEncoder.vault_admin_unconditional(sig)

        # Should not raise
        bytes.fromhex(witness)


class TestWitnessEncoderValidation:
    """Tests for input validation."""

    @pytest.mark.unit
    def test_invalid_signature_length_short(self):
        """Test that short signature raises ValueError."""
        short_sig = b'\x00' * 63  # 63 bytes, should be 64
        with pytest.raises(ValueError, match="64 bytes"):
            WitnessEncoder.vault_admin_unconditional(short_sig)

    @pytest.mark.unit
    def test_invalid_signature_length_long(self):
        """Test that long signature raises ValueError."""
        long_sig = b'\x00' * 65  # 65 bytes, should be 64
        with pytest.raises(ValueError, match="64 bytes"):
            WitnessEncoder.vault_admin_unconditional(long_sig)

    @pytest.mark.unit
    def test_empty_signature(self):
        """Test that empty signature raises ValueError."""
        with pytest.raises(ValueError):
            WitnessEncoder.vault_admin_unconditional(b'')


class TestWitnessEncoderDummy:
    """Tests for dummy witness generation."""

    @pytest.mark.unit
    def test_vault_dummy_admin_unconditional(self):
        """Test dummy witness for admin unconditional path."""
        dummy = WitnessEncoder.vault_dummy("admin_unconditional")
        assert len(dummy) == 130
        # Should have zero signature but correct path bits
        first_byte = int(dummy[:2], 16)
        assert (first_byte >> 7) == 0  # Left path

    @pytest.mark.unit
    def test_vault_dummy_admin_issue(self):
        """Test dummy witness for admin issue path."""
        dummy = WitnessEncoder.vault_dummy("admin_issue")
        assert len(dummy) == 130
        first_byte = int(dummy[:2], 16)
        assert (first_byte >> 6) == 2  # Right-Left

    @pytest.mark.unit
    def test_vault_dummy_delegate_issue(self):
        """Test dummy witness for delegate issue path."""
        dummy = WitnessEncoder.vault_dummy("delegate_issue")
        assert len(dummy) == 130
        first_byte = int(dummy[:2], 16)
        assert (first_byte >> 6) == 3  # Right-Right

    @pytest.mark.unit
    def test_certificate_dummy_admin(self):
        """Test dummy witness for admin revoke path."""
        dummy = WitnessEncoder.certificate_dummy("admin")
        assert len(dummy) == 130

    @pytest.mark.unit
    def test_certificate_dummy_delegate(self):
        """Test dummy witness for delegate revoke path."""
        dummy = WitnessEncoder.certificate_dummy("delegate")
        assert len(dummy) == 130


class TestWitnessEncoderHighLevel:
    """Tests for high-level encoding methods."""

    @pytest.mark.unit
    def test_encode_vault_witness_admin_issue(self):
        """Test encode_vault_witness for admin issue."""
        sig = b'\xab' * 64
        witness = WitnessEncoder.encode_vault_witness(sig, "admin", unconditional=False)
        # Should use admin issue path
        first_byte = int(witness[:2], 16)
        assert (first_byte >> 6) == 2  # Right-Left

    @pytest.mark.unit
    def test_encode_vault_witness_admin_unconditional(self):
        """Test encode_vault_witness for admin unconditional."""
        sig = b'\xab' * 64
        witness = WitnessEncoder.encode_vault_witness(sig, "admin", unconditional=True)
        # Should use admin unconditional path
        first_byte = int(witness[:2], 16)
        assert (first_byte >> 7) == 0  # Left

    @pytest.mark.unit
    def test_encode_vault_witness_delegate(self):
        """Test encode_vault_witness for delegate."""
        sig = b'\xab' * 64
        witness = WitnessEncoder.encode_vault_witness(sig, "delegate")
        # Should use delegate issue path
        first_byte = int(witness[:2], 16)
        assert (first_byte >> 6) == 3  # Right-Right

    @pytest.mark.unit
    def test_encode_certificate_witness_admin(self):
        """Test encode_certificate_witness for admin."""
        sig = b'\xab' * 64
        witness = WitnessEncoder.encode_certificate_witness(sig, "admin")
        first_byte = int(witness[:2], 16)
        assert (first_byte >> 7) == 0  # Left

    @pytest.mark.unit
    def test_encode_certificate_witness_delegate(self):
        """Test encode_certificate_witness for delegate."""
        sig = b'\xab' * 64
        witness = WitnessEncoder.encode_certificate_witness(sig, "delegate")
        first_byte = int(witness[:2], 16)
        assert (first_byte >> 7) == 1  # Right


class TestWitnessEncoderHexString:
    """Tests for hex string signature input."""

    @pytest.mark.unit
    def test_encode_vault_witness_accepts_hex_string(self):
        """Test that encode_vault_witness accepts hex string."""
        sig_hex = "ab" * 64  # 128 char hex = 64 bytes
        witness = WitnessEncoder.encode_vault_witness(sig_hex, "admin")
        assert len(witness) == 130

    @pytest.mark.unit
    def test_encode_certificate_witness_accepts_hex_string(self):
        """Test that encode_certificate_witness accepts hex string."""
        sig_hex = "cd" * 64
        witness = WitnessEncoder.encode_certificate_witness(sig_hex, "delegate")
        assert len(witness) == 130

    @pytest.mark.unit
    def test_hex_and_bytes_produce_same_result(self):
        """Test that hex string and bytes produce identical output."""
        sig_bytes = b'\xab' * 64
        sig_hex = "ab" * 64

        witness_bytes = WitnessEncoder.encode_vault_witness(sig_bytes, "admin")
        witness_hex = WitnessEncoder.encode_vault_witness(sig_hex, "admin")

        assert witness_bytes == witness_hex
