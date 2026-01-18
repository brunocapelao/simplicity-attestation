"""
SAS SDK - Event Hooks

Event system for before/after operation callbacks.
"""

from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging


class EventType(Enum):
    """Available event types."""
    # Transaction lifecycle
    BEFORE_CREATE_TX = "before_create_tx"
    AFTER_CREATE_TX = "after_create_tx"
    BEFORE_SIGN = "before_sign"
    AFTER_SIGN = "after_sign"
    BEFORE_BROADCAST = "before_broadcast"
    AFTER_BROADCAST = "after_broadcast"
    
    # Certificate events
    BEFORE_ISSUE = "before_issue"
    AFTER_ISSUE = "after_issue"
    BEFORE_REVOKE = "before_revoke"
    AFTER_REVOKE = "after_revoke"
    
    # Vault events
    BEFORE_DRAIN = "before_drain"
    AFTER_DRAIN = "after_drain"
    
    # Confirmation events
    TX_CONFIRMED = "tx_confirmed"
    TX_DEEP_CONFIRMED = "tx_deep_confirmed"
    
    # Error events
    ON_ERROR = "on_error"
    ON_RETRY = "on_retry"


@dataclass
class Event:
    """Event payload passed to handlers."""
    type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            import time
            self.timestamp = time.time()


# Type alias for event handlers
EventHandler = Callable[[Event], Optional[Any]]


class EventEmitter:
    """
    Event emitter for SDK operations.
    
    Allows registering callbacks for various lifecycle events.
    
    Example:
        emitter = EventEmitter()
        
        @emitter.on(EventType.BEFORE_BROADCAST)
        def log_tx(event):
            print(f"Broadcasting: {event.data['tx_hex'][:50]}...")
        
        emitter.emit(EventType.BEFORE_BROADCAST, {"tx_hex": "..."})
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize event emitter.
        
        Args:
            logger: Optional logger for event debugging.
        """
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._global_handlers: List[EventHandler] = []
        self.logger = logger
    
    def on(self, event_type: EventType) -> Callable:
        """
        Decorator to register an event handler.
        
        Args:
            event_type: Type of event to handle.
        
        Returns:
            Decorator function.
        
        Example:
            @emitter.on(EventType.AFTER_ISSUE)
            def handle_issue(event):
                print(f"Certificate issued: {event.data['txid']}")
        """
        def decorator(handler: EventHandler) -> EventHandler:
            self.add_handler(event_type, handler)
            return handler
        return decorator
    
    def add_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """
        Register an event handler.
        
        Args:
            event_type: Type of event to handle.
            handler: Callback function.
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        
        if self.logger:
            self.logger.debug(f"Registered handler for {event_type.value}")
    
    def remove_handler(self, event_type: EventType, handler: EventHandler) -> bool:
        """
        Remove an event handler.
        
        Returns:
            True if handler was removed, False if not found.
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                return True
            except ValueError:
                pass
        return False
    
    def add_global_handler(self, handler: EventHandler) -> None:
        """
        Register a handler that receives ALL events.
        
        Useful for logging and auditing.
        """
        self._global_handlers.append(handler)
    
    def emit(self, event_type: EventType, data: Dict[str, Any] = None) -> List[Any]:
        """
        Emit an event to all registered handlers.
        
        Args:
            event_type: Type of event.
            data: Event payload data.
        
        Returns:
            List of handler return values (excluding None).
        """
        event = Event(type=event_type, data=data or {})
        results = []
        
        if self.logger:
            self.logger.debug(f"Emitting event: {event_type.value}")
        
        # Call global handlers first
        for handler in self._global_handlers:
            try:
                result = handler(event)
                if result is not None:
                    results.append(result)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Global handler error: {e}")
                # Emit error event (but don't recurse)
                if event_type != EventType.ON_ERROR:
                    self._emit_error(e, event)
        
        # Call specific handlers
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                result = handler(event)
                if result is not None:
                    results.append(result)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Handler error for {event_type.value}: {e}")
                if event_type != EventType.ON_ERROR:
                    self._emit_error(e, event)
        
        return results
    
    def _emit_error(self, error: Exception, source_event: Event) -> None:
        """Emit an error event."""
        error_event = Event(
            type=EventType.ON_ERROR,
            data={
                "error": error,
                "error_type": type(error).__name__,
                "message": str(error),
                "source_event": source_event.type.value
            }
        )
        
        for handler in self._handlers.get(EventType.ON_ERROR, []):
            try:
                handler(error_event)
            except Exception:
                pass  # Avoid infinite recursion
    
    def clear(self, event_type: EventType = None) -> None:
        """
        Clear handlers.
        
        Args:
            event_type: Specific event type to clear, or all if None.
        """
        if event_type:
            self._handlers[event_type] = []
        else:
            self._handlers.clear()
            self._global_handlers.clear()
    
    def handler_count(self, event_type: EventType = None) -> int:
        """Get number of registered handlers."""
        if event_type:
            return len(self._handlers.get(event_type, []))
        return sum(len(h) for h in self._handlers.values()) + len(self._global_handlers)


# Convenience functions for creating common hooks

def create_logging_hook(logger: logging.Logger) -> EventHandler:
    """
    Create a hook that logs all events.
    
    Args:
        logger: Logger instance.
    
    Returns:
        Event handler function.
    """
    def handler(event: Event) -> None:
        logger.info(f"[SAS] {event.type.value}: {event.data}")
    return handler


def create_audit_hook(audit_callback: Callable[[dict], None]) -> EventHandler:
    """
    Create a hook that sends events to audit system.
    
    Args:
        audit_callback: Function to call with audit data.
    
    Returns:
        Event handler function.
    """
    def handler(event: Event) -> None:
        audit_data = {
            "event_type": event.type.value,
            "timestamp": event.timestamp,
            "data": event.data
        }
        audit_callback(audit_data)
    return handler
