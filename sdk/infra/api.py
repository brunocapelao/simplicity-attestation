"""
SAP SDK - Blockstream API Client

Handles all blockchain interactions via the Blockstream Esplora API.
"""

import requests
from typing import Optional, List

from ..models import UTXO, TransactionResult


class BlockstreamAPIError(Exception):
    """Error from Blockstream API."""
    pass


class BlockstreamAPI:
    """
    Client for Blockstream's Esplora API.
    
    Handles UTXO queries and transaction broadcasting for Liquid Network.
    """
    
    TESTNET_URL = "https://blockstream.info/liquidtestnet/api"
    MAINNET_URL = "https://blockstream.info/liquid/api"
    
    def __init__(self, base_url: Optional[str] = None, network: str = "testnet"):
        """
        Initialize API client.
        
        Args:
            base_url: Custom API base URL. Auto-selected if None.
            network: "testnet" or "mainnet".
        """
        if base_url:
            self.base_url = base_url
        elif network == "mainnet":
            self.base_url = self.MAINNET_URL
        else:
            self.base_url = self.TESTNET_URL
        
        self.session = requests.Session()
        self.timeout = 30
    
    def _get(self, endpoint: str) -> dict:
        """Make GET request to API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise BlockstreamAPIError(f"API request failed: {e}")
    
    def _post(self, endpoint: str, data: str) -> str:
        """Make POST request to API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.post(
                url,
                headers={"Content-Type": "text/plain"},
                data=data,
                timeout=self.timeout
            )
            return response.text
        except requests.RequestException as e:
            raise BlockstreamAPIError(f"API request failed: {e}")
    
    # =========================================================================
    # Address Operations
    # =========================================================================
    
    def get_utxos(self, address: str) -> List[UTXO]:
        """
        Get all UTXOs for an address.
        
        Args:
            address: Liquid address (tex1... or ex1...).
        
        Returns:
            List of UTXO objects.
        """
        try:
            data = self._get(f"address/{address}/utxo")
        except BlockstreamAPIError:
            return []
        
        utxos = []
        for item in data:
            utxo = UTXO(
                txid=item["txid"],
                vout=item["vout"],
                value=item["value"],
                asset=item.get("asset")
            )
            utxos.append(utxo)
        
        return utxos
    
    def get_balance(self, address: str) -> int:
        """
        Get total balance for an address in satoshis.
        
        Args:
            address: Liquid address.
        
        Returns:
            Total balance in satoshis.
        """
        utxos = self.get_utxos(address)
        return sum(utxo.value for utxo in utxos)
    
    # =========================================================================
    # Transaction Operations
    # =========================================================================
    
    def broadcast(self, tx_hex: str) -> TransactionResult:
        """
        Broadcast a raw transaction.
        
        Args:
            tx_hex: Raw transaction hex.
        
        Returns:
            TransactionResult with txid or error.
        """
        result = self._post("tx", tx_hex)
        
        # Check if result is a valid txid (64 hex chars)
        if len(result) == 64 and all(c in '0123456789abcdef' for c in result):
            return TransactionResult(
                success=True,
                txid=result,
                raw_hex=tx_hex
            )
        else:
            return TransactionResult(
                success=False,
                error=result,
                raw_hex=tx_hex
            )
    
    def get_transaction(self, txid: str) -> Optional[dict]:
        """
        Get transaction details.
        
        Args:
            txid: Transaction ID.
        
        Returns:
            Transaction details or None if not found.
        """
        try:
            return self._get(f"tx/{txid}")
        except BlockstreamAPIError:
            return None
    
    def get_tx_status(self, txid: str) -> Optional[dict]:
        """
        Get transaction confirmation status.
        
        Args:
            txid: Transaction ID.
        
        Returns:
            Status dict with confirmed, block_height, etc.
        """
        try:
            return self._get(f"tx/{txid}/status")
        except BlockstreamAPIError:
            return None
    
    def is_utxo_spent(self, txid: str, vout: int) -> bool:
        """
        Check if a specific UTXO has been spent.
        
        Args:
            txid: Transaction ID.
            vout: Output index.
        
        Returns:
            True if spent, False if unspent.
        """
        try:
            spending = self._get(f"tx/{txid}/outspend/{vout}")
            return spending.get("spent", False)
        except BlockstreamAPIError:
            return False
    
    def get_outspend(self, txid: str, vout: int) -> Optional[dict]:
        """
        Get spending information for a UTXO.
        
        Args:
            txid: Transaction ID.
            vout: Output index.
        
        Returns:
            Spending info dict or None.
        """
        try:
            return self._get(f"tx/{txid}/outspend/{vout}")
        except BlockstreamAPIError:
            return None
