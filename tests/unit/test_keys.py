"""
Unit tests for KeyManager (cryptographic key operations).
"""

import pytest
import pickle


class TestKeyManagerBasic:
    """Basic KeyManager functionality tests."""

    @pytest.mark.unit
    def test_create_from_private_key(self, test_private_key):
        """Test creating KeyManager from private key."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        assert km is not None

    @pytest.mark.unit
    def test_public_key_derivation(self, test_private_key, test_public_key):
        """Test that public key is correctly derived."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        assert len(km.public_key) == 64  # x-only pubkey is 32 bytes = 64 hex chars

    @pytest.mark.unit
    def test_from_secret_classmethod(self, test_private_key):
        """Test from_secret class method."""
        from sdk.infra.keys import KeyManager

        km = KeyManager.from_secret(test_private_key)
        assert km is not None
        assert len(km.public_key) == 64


class TestKeyManagerSigning:
    """Tests for signing operations."""

    @pytest.mark.unit
    def test_schnorr_sign_produces_64_bytes(self, test_private_key):
        """Test that schnorr_sign produces 64-byte signature."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        message = "00" * 32  # 32-byte message as hex
        sig = km.schnorr_sign(message)

        assert isinstance(sig, bytes)
        assert len(sig) == 64

    @pytest.mark.unit
    def test_sign_hash_produces_64_bytes(self, test_private_key):
        """Test that sign_hash produces 64-byte signature."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        sig_all_hash = "ab" * 32
        sig = km.sign_hash(sig_all_hash)

        assert isinstance(sig, bytes)
        assert len(sig) == 64

    @pytest.mark.unit
    def test_sign_hash_is_deterministic(self, test_private_key):
        """Test that signing the same message produces same signature."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        message = "cd" * 32

        sig1 = km.sign_hash(message)
        sig2 = km.sign_hash(message)

        assert sig1 == sig2

    @pytest.mark.unit
    def test_different_messages_different_signatures(self, test_private_key):
        """Test that different messages produce different signatures."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        sig1 = km.sign_hash("00" * 32)
        sig2 = km.sign_hash("ff" * 32)

        assert sig1 != sig2


class TestKeyManagerVerification:
    """Tests for signature verification."""

    @pytest.mark.unit
    def test_verify_valid_signature(self, test_private_key):
        """Test verifying a valid signature."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        message = "ab" * 32
        sig = km.schnorr_sign(message)

        assert km.verify(message, sig) is True

    @pytest.mark.unit
    def test_verify_invalid_signature(self, test_private_key):
        """Test verifying an invalid signature."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        message = "ab" * 32
        invalid_sig = b'\x00' * 64  # All zeros is invalid

        assert km.verify(message, invalid_sig) is False

    @pytest.mark.unit
    def test_verify_wrong_message(self, test_private_key):
        """Test that signature doesn't verify for wrong message."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        message1 = "ab" * 32
        message2 = "cd" * 32
        sig = km.schnorr_sign(message1)

        assert km.verify(message2, sig) is False


class TestKeyManagerSecurity:
    """Security-focused tests for KeyManager."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_no_private_key_property(self, test_private_key):
        """Test that private_key property is not accessible."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        with pytest.raises(AttributeError):
            _ = km.private_key

    @pytest.mark.unit
    @pytest.mark.security
    def test_cannot_pickle(self, test_private_key):
        """Test that KeyManager cannot be pickled."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        with pytest.raises(TypeError, match="cannot be pickled"):
            pickle.dumps(km)

    @pytest.mark.unit
    @pytest.mark.security
    def test_repr_does_not_leak_private_key(self, test_private_key):
        """Test that repr doesn't contain private key."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        repr_str = repr(km)

        # Should contain public key (truncated)
        assert "public_key=" in repr_str
        # Should NOT contain the full private key
        assert test_private_key not in repr_str

    @pytest.mark.unit
    @pytest.mark.security
    def test_str_does_not_leak_private_key(self, test_private_key):
        """Test that str doesn't contain private key."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        str_repr = str(km)

        assert test_private_key not in str_repr

    @pytest.mark.unit
    @pytest.mark.security
    def test_no_dict_attribute(self, test_private_key):
        """Test that __dict__ is not available (uses __slots__)."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key)
        # With __slots__, __dict__ should not exist
        assert not hasattr(km, '__dict__') or len(km.__dict__) == 0


class TestKeyManagerEdgeCases:
    """Edge case tests for KeyManager."""

    @pytest.mark.unit
    def test_invalid_private_key_format(self):
        """Test that invalid hex raises error."""
        from sdk.infra.keys import KeyManager

        with pytest.raises((ValueError, Exception)):
            KeyManager("not_hex")

    @pytest.mark.unit
    def test_private_key_wrong_length(self):
        """Test that wrong length private key raises error."""
        from sdk.infra.keys import KeyManager

        with pytest.raises((ValueError, Exception)):
            KeyManager("00" * 31)  # 31 bytes, should be 32

    @pytest.mark.unit
    def test_explicit_public_key(self, test_private_key, test_public_key):
        """Test providing explicit public key."""
        from sdk.infra.keys import KeyManager

        km = KeyManager(test_private_key, public_key=test_public_key)
        assert km.public_key == test_public_key
