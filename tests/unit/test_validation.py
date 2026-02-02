"""
Unit tests for input validation helpers in sdk/sas.py.
"""

import pytest

# Import validation functions from sas module
from sdk.sas import _validate_hex, _validate_cid, _is_hex


class TestValidateHex:
    """Tests for _validate_hex helper function."""

    @pytest.mark.unit
    def test_valid_hex_lowercase(self):
        """Test valid lowercase hex string."""
        result = _validate_hex("abcd1234" * 8, "txid", 64)
        assert result == "abcd1234" * 8

    @pytest.mark.unit
    def test_valid_hex_uppercase(self):
        """Test valid uppercase hex is normalized to lowercase."""
        result = _validate_hex("ABCD1234" * 8, "txid", 64)
        assert result == "abcd1234" * 8

    @pytest.mark.unit
    def test_valid_hex_mixed_case(self):
        """Test valid mixed case hex is normalized to lowercase."""
        result = _validate_hex("AbCd1234" * 8, "txid", 64)
        assert result == "abcd1234" * 8

    @pytest.mark.unit
    def test_empty_value_raises(self):
        """Test empty value raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_hex("", "txid", 64)

    @pytest.mark.unit
    def test_non_hex_chars_raises(self):
        """Test non-hex characters raise ValueError."""
        with pytest.raises(ValueError, match="must be hexadecimal"):
            _validate_hex("ghijklmn" * 8, "txid", 64)

    @pytest.mark.unit
    def test_wrong_length_raises(self):
        """Test wrong length raises ValueError."""
        with pytest.raises(ValueError, match="must be 64 hex characters"):
            _validate_hex("abcd", "txid", 64)

    @pytest.mark.unit
    def test_special_chars_raises(self):
        """Test special characters raise ValueError."""
        with pytest.raises(ValueError, match="must be hexadecimal"):
            _validate_hex("abcd!@#$" * 8, "txid", 64)

    @pytest.mark.unit
    def test_spaces_raises(self):
        """Test spaces in hex string raise ValueError."""
        with pytest.raises(ValueError, match="must be hexadecimal"):
            _validate_hex("abcd 1234", "value", 9)


class TestValidateCid:
    """Tests for _validate_cid helper function."""

    @pytest.mark.unit
    def test_valid_ipfs_cid(self):
        """Test valid IPFS CID v0."""
        cid = "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG"
        result = _validate_cid(cid)
        assert result == cid

    @pytest.mark.unit
    def test_valid_ipfs_cid_v1(self):
        """Test valid IPFS CID v1."""
        cid = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
        result = _validate_cid(cid)
        assert result == cid

    @pytest.mark.unit
    def test_valid_hex_cid(self):
        """Test valid hex string CID."""
        cid = "abcd1234" * 8  # 64 hex chars = 32 bytes
        result = _validate_cid(cid)
        assert result == cid

    @pytest.mark.unit
    def test_empty_cid_raises(self):
        """Test empty CID raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_cid("")

    @pytest.mark.unit
    def test_cid_exceeds_75_bytes_raises(self):
        """Test CID exceeding 75 bytes raises ValueError."""
        # Use non-hex characters to ensure it's treated as text
        cid = "x" * 76  # 76 bytes (text), not valid hex
        with pytest.raises(ValueError, match="exceeds 75 byte limit"):
            _validate_cid(cid)

    @pytest.mark.unit
    def test_cid_at_75_bytes(self):
        """Test CID at exactly 75 bytes is valid."""
        cid = "a" * 75  # 75 bytes (text)
        result = _validate_cid(cid)
        assert result == cid

    @pytest.mark.unit
    def test_hex_cid_byte_length(self):
        """Test hex CID byte length is checked correctly."""
        # 150 hex chars = 75 bytes, should pass
        cid = "ab" * 75  # 150 hex chars = 75 bytes
        result = _validate_cid(cid)
        assert result == cid

    @pytest.mark.unit
    def test_hex_cid_exceeds_75_bytes(self):
        """Test hex CID exceeding 75 bytes raises ValueError."""
        # 152 hex chars = 76 bytes, should fail
        cid = "ab" * 76  # 152 hex chars = 76 bytes
        with pytest.raises(ValueError, match="exceeds 75 byte limit"):
            _validate_cid(cid)


class TestIsHex:
    """Tests for _is_hex helper function."""

    @pytest.mark.unit
    def test_valid_hex(self):
        """Test valid hex string returns True."""
        assert _is_hex("abcd1234") is True

    @pytest.mark.unit
    def test_valid_hex_uppercase(self):
        """Test valid uppercase hex returns True."""
        assert _is_hex("ABCD1234") is True

    @pytest.mark.unit
    def test_empty_string_is_hex(self):
        """Test empty string is valid hex (edge case)."""
        assert _is_hex("") is True

    @pytest.mark.unit
    def test_odd_length_not_hex(self):
        """Test odd-length string is not valid hex."""
        assert _is_hex("abc") is False

    @pytest.mark.unit
    def test_non_hex_chars(self):
        """Test non-hex characters return False."""
        assert _is_hex("ghijk") is False

    @pytest.mark.unit
    def test_special_chars(self):
        """Test special characters return False."""
        assert _is_hex("!@#$") is False

    @pytest.mark.unit
    def test_spaces_not_hex(self):
        """Test spaces are not valid hex."""
        assert _is_hex("ab cd") is False
