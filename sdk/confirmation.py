"""
SAP SDK - Transaction Confirmation Tracking

Provides async transaction confirmation waiting and status tracking.
"""

import time
import threading
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from .infra.api import BlockstreamAPI
from .errors import ConfirmationTimeoutError, TransactionNotFoundError


class TxStatus(Enum):
    """Transaction confirmation status."""
    PENDING = "pending"          # Broadcast but not confirmed
    CONFIRMED = "confirmed"      # Has at least 1 confirmation
    DEEP_CONFIRMED = "deep"      # Has 6+ confirmations
    NOT_FOUND = "not_found"      # Transaction not found
    REPLACED = "replaced"        # Replaced by another tx (RBF)


@dataclass
class ConfirmationStatus:
    """Status of a transaction confirmation."""
    txid: str
    status: TxStatus
    confirmations: int = 0
    block_height: Optional[int] = None
    block_hash: Optional[str] = None
    timestamp: Optional[int] = None
    
    @property
    def is_confirmed(self) -> bool:
        return self.confirmations >= 1
    
    @property
    def is_deep_confirmed(self) -> bool:
        return self.confirmations >= 6


@dataclass
class ConfirmationCallback:
    """Callback configuration for confirmation events."""
    txid: str
    target_confirmations: int
    callback: Callable[[ConfirmationStatus], None]
    triggered: bool = False


class ConfirmationTracker:
    """
    Tracks transaction confirmations.
    
    Provides both blocking wait and async callback patterns.
    """
    
    DEFAULT_POLL_INTERVAL = 10  # seconds
    DEFAULT_TIMEOUT = 600       # 10 minutes
    
    def __init__(self, api: BlockstreamAPI, poll_interval: int = None):
        """
        Initialize confirmation tracker.
        
        Args:
            api: BlockstreamAPI instance for querying.
            poll_interval: Seconds between confirmation checks.
        """
        self.api = api
        self.poll_interval = poll_interval or self.DEFAULT_POLL_INTERVAL
        self._callbacks: List[ConfirmationCallback] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def get_status(self, txid: str) -> ConfirmationStatus:
        """
        Get current confirmation status of a transaction.
        
        Args:
            txid: Transaction ID.
        
        Returns:
            ConfirmationStatus with current state.
        """
        tx_status = self.api.get_tx_status(txid)
        
        if not tx_status:
            return ConfirmationStatus(
                txid=txid,
                status=TxStatus.NOT_FOUND,
                confirmations=0
            )
        
        confirmed = tx_status.get("confirmed", False)
        block_height = tx_status.get("block_height")
        block_hash = tx_status.get("block_hash")
        
        if not confirmed:
            return ConfirmationStatus(
                txid=txid,
                status=TxStatus.PENDING,
                confirmations=0
            )
        
        # Calculate confirmations (approximate from block height)
        # In production, would need current chain height
        confirmations = 1  # At least 1 if confirmed
        
        if block_height:
            # Try to get current height for accurate confirmation count
            # For now, assume confirmed = 1+ confirmations
            confirmations = max(1, confirmations)
        
        status = TxStatus.CONFIRMED
        if confirmations >= 6:
            status = TxStatus.DEEP_CONFIRMED
        
        return ConfirmationStatus(
            txid=txid,
            status=status,
            confirmations=confirmations,
            block_height=block_height,
            block_hash=block_hash
        )
    
    def wait_for_confirmation(
        self,
        txid: str,
        target_confirmations: int = 1,
        timeout: int = None,
        poll_interval: int = None
    ) -> ConfirmationStatus:
        """
        Wait synchronously for transaction confirmation.
        
        Args:
            txid: Transaction ID to wait for.
            target_confirmations: Number of confirmations to wait for.
            timeout: Maximum seconds to wait (default: 600).
            poll_interval: Seconds between checks (default: 10).
        
        Returns:
            ConfirmationStatus when target reached.
        
        Raises:
            ConfirmationTimeoutError: If timeout exceeded.
            TransactionNotFoundError: If transaction never appears.
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        poll_interval = poll_interval or self.poll_interval
        
        start_time = time.time()
        not_found_count = 0
        max_not_found = 3  # Allow a few not-found before failing
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed >= timeout:
                status = self.get_status(txid)
                raise ConfirmationTimeoutError(
                    txid=txid,
                    timeout_seconds=int(elapsed),
                    current_confirmations=status.confirmations
                )
            
            status = self.get_status(txid)
            
            if status.status == TxStatus.NOT_FOUND:
                not_found_count += 1
                if not_found_count >= max_not_found:
                    raise TransactionNotFoundError(txid)
            else:
                not_found_count = 0
            
            if status.confirmations >= target_confirmations:
                return status
            
            time.sleep(poll_interval)
    
    def on_confirmation(
        self,
        txid: str,
        callback: Callable[[ConfirmationStatus], None],
        target_confirmations: int = 1
    ) -> None:
        """
        Register callback for when transaction reaches confirmations.
        
        Args:
            txid: Transaction ID to track.
            callback: Function to call when confirmed.
            target_confirmations: Confirmations needed to trigger.
        """
        self._callbacks.append(ConfirmationCallback(
            txid=txid,
            target_confirmations=target_confirmations,
            callback=callback
        ))
        
        # Start background thread if not running
        if not self._running:
            self._start_background_tracker()
    
    def _start_background_tracker(self) -> None:
        """Start background confirmation tracking thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._background_loop, daemon=True)
        self._thread.start()
    
    def _background_loop(self) -> None:
        """Background loop checking confirmations."""
        while self._running and self._callbacks:
            # Check each pending callback
            for cb in self._callbacks[:]:  # Copy list to allow removal
                if cb.triggered:
                    continue
                
                try:
                    status = self.get_status(cb.txid)
                    
                    if status.confirmations >= cb.target_confirmations:
                        cb.triggered = True
                        try:
                            cb.callback(status)
                        except Exception:
                            pass  # Don't crash on callback errors
                        self._callbacks.remove(cb)
                        
                except Exception:
                    pass  # Continue on API errors
            
            if self._callbacks:
                time.sleep(self.poll_interval)
            else:
                self._running = False
    
    def stop(self) -> None:
        """Stop background tracking."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
