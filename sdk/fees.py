"""
SAP SDK - Fee Estimation

Dynamic fee estimation for Liquid Network transactions.
"""

from typing import Optional, Literal
from dataclasses import dataclass
from enum import Enum

from .infra.api import BlockstreamAPI


class FeePriority(Enum):
    """Fee priority levels."""
    LOW = "low"           # ~30 min confirmation
    MEDIUM = "medium"     # ~10 min confirmation
    HIGH = "high"         # Next block
    URGENT = "urgent"     # Immediate


@dataclass
class FeeEstimate:
    """Fee estimation result."""
    sat_per_vbyte: float
    total_sats: int
    priority: FeePriority
    estimated_blocks: int
    
    @property
    def total_btc(self) -> float:
        return self.total_sats / 100_000_000


class FeeEstimator:
    """
    Estimates transaction fees for Liquid Network.
    
    Liquid has lower fees than Bitcoin mainnet, typically
    around 0.1 sat/vbyte. This estimator provides dynamic
    estimation based on network conditions.
    """
    
    # Liquid default fee rates (sat/vbyte)
    DEFAULT_RATES = {
        FeePriority.LOW: 0.1,
        FeePriority.MEDIUM: 0.11,
        FeePriority.HIGH: 0.15,
        FeePriority.URGENT: 0.2,
    }
    
    # Estimated confirmation times (blocks)
    ESTIMATED_BLOCKS = {
        FeePriority.LOW: 6,
        FeePriority.MEDIUM: 2,
        FeePriority.HIGH: 1,
        FeePriority.URGENT: 1,
    }
    
    # Typical transaction sizes (vbytes)
    TX_SIZES = {
        "issue_certificate": 350,    # 4 outputs
        "revoke_certificate": 200,   # 1-2 outputs
        "drain_vault": 200,          # 2 outputs
        "batch_issue": 500,          # Variable, estimate
    }
    
    # Minimum fee for Liquid
    MIN_FEE_SATS = 100
    
    def __init__(self, api: Optional[BlockstreamAPI] = None):
        """
        Initialize fee estimator.
        
        Args:
            api: Optional BlockstreamAPI for dynamic estimation.
        """
        self.api = api
        self._cached_rates = None
        self._cache_time = 0
    
    def estimate(
        self,
        operation: Literal["issue_certificate", "revoke_certificate", "drain_vault", "batch_issue"] = "issue_certificate",
        priority: FeePriority = FeePriority.MEDIUM,
        num_outputs: int = 4
    ) -> FeeEstimate:
        """
        Estimate fee for an operation.
        
        Args:
            operation: Type of operation.
            priority: Fee priority level.
            num_outputs: Number of outputs (for batch).
        
        Returns:
            FeeEstimate with recommended fee.
        """
        # Get sat/vbyte rate
        rate = self._get_rate(priority)
        
        # Get transaction size estimate
        if operation == "batch_issue":
            # Base size + per-output overhead
            size = 200 + (num_outputs * 75)
        else:
            size = self.TX_SIZES.get(operation, 350)
        
        # Calculate total fee
        total = max(int(size * rate), self.MIN_FEE_SATS)
        
        return FeeEstimate(
            sat_per_vbyte=rate,
            total_sats=total,
            priority=priority,
            estimated_blocks=self.ESTIMATED_BLOCKS[priority]
        )
    
    def estimate_for_size(
        self,
        vbytes: int,
        priority: FeePriority = FeePriority.MEDIUM
    ) -> FeeEstimate:
        """
        Estimate fee for a specific transaction size.
        
        Args:
            vbytes: Transaction size in virtual bytes.
            priority: Fee priority level.
        
        Returns:
            FeeEstimate with recommended fee.
        """
        rate = self._get_rate(priority)
        total = max(int(vbytes * rate), self.MIN_FEE_SATS)
        
        return FeeEstimate(
            sat_per_vbyte=rate,
            total_sats=total,
            priority=priority,
            estimated_blocks=self.ESTIMATED_BLOCKS[priority]
        )
    
    def _get_rate(self, priority: FeePriority) -> float:
        """Get fee rate for priority level."""
        # TODO: Implement dynamic fee fetching from API
        # For now, use static defaults (Liquid fees are very stable)
        return self.DEFAULT_RATES[priority]
    
    def get_minimum_fee(self) -> int:
        """Get minimum recommended fee in satoshis."""
        return self.MIN_FEE_SATS
    
    def get_recommended_fee(
        self,
        operation: str = "issue_certificate"
    ) -> int:
        """
        Get recommended fee for an operation.
        
        Convenience method using MEDIUM priority.
        
        Args:
            operation: Type of operation.
        
        Returns:
            Recommended fee in satoshis.
        """
        estimate = self.estimate(operation=operation, priority=FeePriority.MEDIUM)
        return estimate.total_sats
