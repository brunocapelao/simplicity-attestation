"""
SAS SDK - Constants

Centralized configuration constants for the SDK.
"""

# =============================================================================
# Transaction Fees and Amounts
# =============================================================================

# Transaction fee in satoshis
FEE_SATS = 500

# Certificate dust limit (minimum output value)
CERT_DUST_SATS = 546

# Minimum vault balance to issue a certificate
# = certificate dust + fee + change dust (must be non-zero for covenant)
MIN_ISSUE_SATS = CERT_DUST_SATS + FEE_SATS + CERT_DUST_SATS  # 1592

# Recommended deposit for vault funding (~100 certificates)
RECOMMENDED_DEPOSIT_SATS = 100000


# =============================================================================
# SAS Protocol Constants
# =============================================================================

# Magic bytes for SAS OP_RETURN
SAS_MAGIC = b"SAS"

# Protocol version
SAS_VERSION = 0x01

# Operation types
SAS_TYPE_ATTEST = 0x01
SAS_TYPE_REVOKE = 0x02
SAS_TYPE_UPDATE = 0x03
SAS_TYPE_DELEGATE = 0x10
SAS_TYPE_UNDELEGATE = 0x11

# OP_RETURN limits
MAX_OP_RETURN_SIZE = 80  # Maximum OP_RETURN data size
SAS_HEADER_SIZE = 5  # 3 (magic) + 1 (version) + 1 (type)
MAX_PAYLOAD_SIZE = MAX_OP_RETURN_SIZE - SAS_HEADER_SIZE  # 75 bytes


# =============================================================================
# Network URLs
# =============================================================================

TESTNET_API_URL = "https://blockstream.info/liquidtestnet/api"
MAINNET_API_URL = "https://blockstream.info/liquid/api"

TESTNET_EXPLORER_URL = "https://blockstream.info/liquidtestnet"
MAINNET_EXPLORER_URL = "https://blockstream.info/liquid"


# =============================================================================
# Asset IDs
# =============================================================================

# Liquid testnet L-BTC asset ID
TESTNET_ASSET_ID = "144c654344aa716d6f3abcc1ca90e5641e4e2a7f633bc09fe3baf64585819a49"

# Liquid mainnet L-BTC asset ID
MAINNET_ASSET_ID = "6f0279e9ed041c3d710a9f57d0c02928416460c4b722ae3457a11eec381c526d"


# =============================================================================
# Default Taproot Internal Key
# =============================================================================

# NUMS point - Nothing Up My Sleeve key for Taproot
# (x-coordinate of a point with unknown discrete log)
DEFAULT_INTERNAL_KEY = "50929b74c1a04954b78b4b6035e97a5e078a5a0f28ec96d547bfee9ace803ac0"
