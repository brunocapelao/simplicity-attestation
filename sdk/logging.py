"""
SAP SDK - Structured Logging

Provides structured logging for audit and debugging.
"""

import logging
import json
import time
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: float
    level: str
    message: str
    component: str
    operation: Optional[str] = None
    txid: Optional[str] = None
    duration_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class StructuredLogger:
    """
    Structured logger for SAP SDK operations.
    
    Provides JSON-formatted logs suitable for log aggregation
    systems like ELK, Datadog, or CloudWatch.
    
    Example:
        logger = StructuredLogger(component="sap-sdk")
        
        with logger.operation("issue_certificate") as op:
            # do work
            op.set_txid("abc123...")
        # Automatically logs duration
        
        # Or manually:
        logger.info("Certificate issued", txid="abc123")
    """
    
    def __init__(
        self,
        component: str = "sap-sdk",
        logger: Optional[logging.Logger] = None,
        json_output: bool = True,
        include_timestamps: bool = True
    ):
        """
        Initialize structured logger.
        
        Args:
            component: Component name for log entries.
            logger: Underlying Python logger (creates one if None).
            json_output: If True, output JSON format.
            include_timestamps: If True, include timestamps.
        """
        self.component = component
        self.json_output = json_output
        self.include_timestamps = include_timestamps
        
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(component)
            if not self._logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter('%(message)s'))
                self._logger.addHandler(handler)
                self._logger.setLevel(logging.INFO)
    
    def _log(
        self,
        level: LogLevel,
        message: str,
        operation: str = None,
        txid: str = None,
        duration_ms: float = None,
        error: str = None,
        **kwargs
    ) -> LogEntry:
        """Create and emit a log entry."""
        entry = LogEntry(
            timestamp=time.time() if self.include_timestamps else 0,
            level=level.value,
            message=message,
            component=self.component,
            operation=operation,
            txid=txid,
            duration_ms=duration_ms,
            details=kwargs if kwargs else None,
            error=error
        )
        
        if self.json_output:
            log_message = entry.to_json()
        else:
            log_message = f"[{entry.level}] {entry.message}"
            if entry.txid:
                log_message += f" txid={entry.txid}"
            if entry.duration_ms:
                log_message += f" duration={entry.duration_ms:.2f}ms"
        
        log_method = getattr(self._logger, level.value.lower())
        log_method(log_message)
        
        return entry
    
    def debug(self, message: str, **kwargs) -> LogEntry:
        """Log debug message."""
        return self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> LogEntry:
        """Log info message."""
        return self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> LogEntry:
        """Log warning message."""
        return self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, error: Exception = None, **kwargs) -> LogEntry:
        """Log error message."""
        error_str = str(error) if error else None
        return self._log(LogLevel.ERROR, message, error=error_str, **kwargs)
    
    def critical(self, message: str, error: Exception = None, **kwargs) -> LogEntry:
        """Log critical message."""
        error_str = str(error) if error else None
        return self._log(LogLevel.CRITICAL, message, error=error_str, **kwargs)
    
    def operation(self, name: str) -> "OperationContext":
        """
        Create an operation context for timing.
        
        Args:
            name: Operation name.
        
        Returns:
            Context manager that logs duration.
        
        Example:
            with logger.operation("issue_certificate") as op:
                result = do_work()
                op.set_txid(result.txid)
        """
        return OperationContext(self, name)
    
    def set_level(self, level: LogLevel) -> None:
        """Set minimum log level."""
        self._logger.setLevel(getattr(logging, level.value))


class OperationContext:
    """Context manager for timing operations."""
    
    def __init__(self, logger: StructuredLogger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time: float = 0
        self.txid: Optional[str] = None
        self.details: Dict[str, Any] = {}
        self.error: Optional[Exception] = None
    
    def __enter__(self) -> "OperationContext":
        self.start_time = time.time()
        self.logger.debug(f"Starting {self.operation}", operation=self.operation)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        duration_ms = (time.time() - self.start_time) * 1000
        
        if exc_val:
            self.logger.error(
                f"Failed {self.operation}",
                operation=self.operation,
                duration_ms=duration_ms,
                error=exc_val,
                txid=self.txid,
                **self.details
            )
        else:
            self.logger.info(
                f"Completed {self.operation}",
                operation=self.operation,
                duration_ms=duration_ms,
                txid=self.txid,
                **self.details
            )
    
    def set_txid(self, txid: str) -> None:
        """Set transaction ID for the operation."""
        self.txid = txid
    
    def add_detail(self, key: str, value: Any) -> None:
        """Add a detail to the operation log."""
        self.details[key] = value


# Factory functions

def create_file_logger(
    filepath: str,
    component: str = "sap-sdk",
    level: LogLevel = LogLevel.INFO
) -> StructuredLogger:
    """
    Create a logger that writes to a file.
    
    Args:
        filepath: Path to log file.
        component: Component name.
        level: Minimum log level.
    
    Returns:
        Configured StructuredLogger.
    """
    logger = logging.getLogger(f"{component}-file")
    handler = logging.FileHandler(filepath)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.value))
    
    return StructuredLogger(component=component, logger=logger)


def create_audit_logger(
    audit_callback: Callable[[dict], None],
    component: str = "sap-audit"
) -> StructuredLogger:
    """
    Create a logger that sends entries to an audit system.
    
    Args:
        audit_callback: Function to receive log entries.
        component: Component name.
    
    Returns:
        Configured StructuredLogger with audit handler.
    """
    class AuditHandler(logging.Handler):
        def emit(self, record):
            try:
                entry = json.loads(record.getMessage())
                audit_callback(entry)
            except json.JSONDecodeError:
                audit_callback({"message": record.getMessage()})
    
    logger = logging.getLogger(f"{component}-audit")
    logger.addHandler(AuditHandler())
    logger.setLevel(logging.INFO)
    
    return StructuredLogger(component=component, logger=logger)
