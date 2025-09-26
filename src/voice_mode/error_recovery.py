"""
Error recovery mechanisms for voice conversations.

This module provides comprehensive error handling, retry logic,
and fallback mechanisms to ensure robust voice interactions.
"""

import asyncio
import time
import logging
from typing import Optional, Callable, Any, List, Dict, TypeVar, Generic
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
import traceback
import random

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = auto()      # Can be ignored
    MEDIUM = auto()   # Should be handled
    HIGH = auto()     # Must be handled
    CRITICAL = auto() # System failure


class ErrorCategory(Enum):
    """Error categories for classification."""
    NETWORK = auto()
    AUDIO = auto()
    SERVICE = auto()
    TIMEOUT = auto()
    RATE_LIMIT = auto()
    AUTHENTICATION = auto()
    CONFIGURATION = auto()
    UNKNOWN = auto()


@dataclass
class ErrorContext:
    """Context information for errors."""
    error_type: type
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)
    traceback: Optional[str] = None
    
    def should_retry(self) -> bool:
        """Check if error should be retried."""
        # Don't retry critical errors or auth failures
        if self.severity == ErrorSeverity.CRITICAL:
            return False
        if self.category == ErrorCategory.AUTHENTICATION:
            return False
        return self.retry_count < self.max_retries
    
    def increment_retry(self):
        """Increment retry counter."""
        self.retry_count += 1


class RetryStrategy:
    """Base class for retry strategies."""
    
    def get_delay(self, attempt: int) -> float:
        """Get delay for retry attempt.
        
        Args:
            attempt: Attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        raise NotImplementedError


class ExponentialBackoff(RetryStrategy):
    """Exponential backoff retry strategy."""
    
    def __init__(
        self,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True
    ):
        """Initialize exponential backoff.
        
        Args:
            base_delay: Initial delay
            max_delay: Maximum delay
            multiplier: Delay multiplier
            jitter: Add random jitter
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        delay = min(
            self.base_delay * (self.multiplier ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            # Add ±25% jitter
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)


class LinearBackoff(RetryStrategy):
    """Linear backoff retry strategy."""
    
    def __init__(
        self,
        base_delay: float = 1.0,
        increment: float = 1.0,
        max_delay: float = 30.0
    ):
        """Initialize linear backoff.
        
        Args:
            base_delay: Initial delay
            increment: Delay increment per attempt
            max_delay: Maximum delay
        """
        self.base_delay = base_delay
        self.increment = increment
        self.max_delay = max_delay
    
    def get_delay(self, attempt: int) -> float:
        """Calculate linear backoff delay."""
        return min(
            self.base_delay + (self.increment * attempt),
            self.max_delay
        )


class ErrorRecoveryManager:
    """Manages error recovery for voice operations."""
    
    def __init__(self):
        """Initialize error recovery manager."""
        self.error_history: List[ErrorContext] = []
        self.max_history = 100
        self.fallback_handlers: Dict[ErrorCategory, List[Callable]] = {}
        self.recovery_callbacks: List[Callable[[ErrorContext], None]] = []
        self.circuit_breakers: Dict[str, 'CircuitBreaker'] = {}
    
    def register_fallback(
        self,
        category: ErrorCategory,
        handler: Callable[[ErrorContext], Any]
    ):
        """Register fallback handler for error category.
        
        Args:
            category: Error category
            handler: Fallback handler function
        """
        if category not in self.fallback_handlers:
            self.fallback_handlers[category] = []
        self.fallback_handlers[category].append(handler)
    
    def register_recovery_callback(
        self,
        callback: Callable[[ErrorContext], None]
    ):
        """Register recovery callback.
        
        Args:
            callback: Function to call after recovery
        """
        self.recovery_callbacks.append(callback)
    
    async def handle_error(
        self,
        error: Exception,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Handle error with recovery logic.
        
        Args:
            error: Exception that occurred
            category: Error category
            severity: Error severity
            metadata: Additional metadata
            
        Returns:
            Recovery result or None
        """
        # Create error context
        context = ErrorContext(
            error_type=type(error),
            message=str(error),
            category=category,
            severity=severity,
            metadata=metadata or {},
            traceback=traceback.format_exc()
        )
        
        # Add to history
        self.error_history.append(context)
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
        
        logger.error(
            f"Error in {category.name}: {error} "
            f"(Severity: {severity.name})"
        )
        
        # Try fallback handlers
        if category in self.fallback_handlers:
            for handler in self.fallback_handlers[category]:
                try:
                    result = await self._call_handler(handler, context)
                    if result is not None:
                        # Notify recovery callbacks
                        for callback in self.recovery_callbacks:
                            try:
                                callback(context)
                            except Exception as e:
                                logger.error(f"Recovery callback error: {e}")
                        return result
                except Exception as e:
                    logger.error(f"Fallback handler error: {e}")
        
        # No recovery possible
        return None
    
    async def _call_handler(
        self,
        handler: Callable,
        context: ErrorContext
    ) -> Any:
        """Call handler function (async or sync).
        
        Args:
            handler: Handler function
            context: Error context
            
        Returns:
            Handler result
        """
        if asyncio.iscoroutinefunction(handler):
            return await handler(context)
        else:
            return handler(context)
    
    def get_circuit_breaker(self, name: str) -> 'CircuitBreaker':
        """Get or create circuit breaker.
        
        Args:
            name: Circuit breaker name
            
        Returns:
            Circuit breaker instance
        """
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name)
        return self.circuit_breakers[name]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics.
        
        Returns:
            Statistics dictionary
        """
        if not self.error_history:
            return {
                'total_errors': 0,
                'by_category': {},
                'by_severity': {}
            }
        
        by_category = {}
        by_severity = {}
        
        for error in self.error_history:
            # Count by category
            cat_name = error.category.name
            by_category[cat_name] = by_category.get(cat_name, 0) + 1
            
            # Count by severity
            sev_name = error.severity.name
            by_severity[sev_name] = by_severity.get(sev_name, 0) + 1
        
        return {
            'total_errors': len(self.error_history),
            'by_category': by_category,
            'by_severity': by_severity,
            'recent_errors': [
                {
                    'message': e.message,
                    'category': e.category.name,
                    'severity': e.severity.name,
                    'timestamp': e.timestamp
                }
                for e in self.error_history[-5:]
            ]
        }


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures."""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        half_open_requests: int = 1
    ):
        """Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name
            failure_threshold: Failures before opening
            timeout: Time before attempting reset
            half_open_requests: Requests in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_requests = half_open_requests
        
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
        self.half_open_count = 0
    
    def call(self, func: Callable[[], T]) -> T:
        """Call function with circuit breaker.
        
        Args:
            func: Function to call
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open
        """
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                self.half_open_count = 0
                logger.info(f"Circuit breaker {self.name}: half-open")
            else:
                raise Exception(f"Circuit breaker {self.name} is open")
        
        try:
            result = func()
            
            # Success - reset on half-open
            if self.state == "half-open":
                self.half_open_count += 1
                if self.half_open_count >= self.half_open_requests:
                    self.state = "closed"
                    self.failure_count = 0
                    logger.info(f"Circuit breaker {self.name}: closed")
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"Circuit breaker {self.name}: opened")
            
            raise e
    
    async def async_call(self, func: Callable[[], T]) -> T:
        """Async version of call."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "half-open"
                self.half_open_count = 0
            else:
                raise Exception(f"Circuit breaker {self.name} is open")
        
        try:
            result = await func()
            
            if self.state == "half-open":
                self.half_open_count += 1
                if self.half_open_count >= self.half_open_requests:
                    self.state = "closed"
                    self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            
            raise e


def with_retry(
    strategy: Optional[RetryStrategy] = None,
    max_attempts: int = 3,
    categories: Optional[List[ErrorCategory]] = None
):
    """Decorator for adding retry logic to functions.
    
    Args:
        strategy: Retry strategy to use
        max_attempts: Maximum retry attempts
        categories: Error categories to retry
        
    Returns:
        Decorated function
    """
    if strategy is None:
        strategy = ExponentialBackoff()
    
    if categories is None:
        categories = [
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.SERVICE
        ]
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                    
                except Exception as e:
                    last_error = e
                    
                    # Check if we should retry
                    error_category = classify_error(e)
                    if error_category not in categories:
                        raise
                    
                    if attempt < max_attempts - 1:
                        delay = strategy.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed")
            
            raise last_error
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    last_error = e
                    
                    error_category = classify_error(e)
                    if error_category not in categories:
                        raise
                    
                    if attempt < max_attempts - 1:
                        delay = strategy.get_delay(attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
            
            raise last_error
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def classify_error(error: Exception) -> ErrorCategory:
    """Classify error into category.
    
    Args:
        error: Exception to classify
        
    Returns:
        Error category
    """
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()
    
    # Network errors
    if any(x in error_str for x in ['connection', 'network', 'socket']):
        return ErrorCategory.NETWORK
    
    # Timeout errors
    if 'timeout' in error_str or 'timeout' in error_type:
        return ErrorCategory.TIMEOUT
    
    # Rate limit errors
    if 'rate' in error_str and 'limit' in error_str:
        return ErrorCategory.RATE_LIMIT
    
    # Auth errors
    if any(x in error_str for x in ['auth', 'token', 'permission', 'forbidden']):
        return ErrorCategory.AUTHENTICATION
    
    # Audio errors
    if any(x in error_str for x in ['audio', 'microphone', 'speaker']):
        return ErrorCategory.AUDIO
    
    # Service errors
    if any(x in error_str for x in ['service', 'api', 'endpoint']):
        return ErrorCategory.SERVICE
    
    # Configuration errors
    if any(x in error_str for x in ['config', 'setting', 'parameter']):
        return ErrorCategory.CONFIGURATION
    
    return ErrorCategory.UNKNOWN


# Global recovery manager instance
_manager: Optional[ErrorRecoveryManager] = None


def get_manager() -> ErrorRecoveryManager:
    """Get global error recovery manager.
    
    Returns:
        Error recovery manager instance
    """
    global _manager
    if _manager is None:
        _manager = ErrorRecoveryManager()
    return _manager


# Example usage
async def example_usage():
    """Example of using error recovery."""
    
    manager = get_manager()
    
    # Register fallback for network errors
    def network_fallback(context: ErrorContext):
        logger.info("Using offline mode due to network error")
        return {"mode": "offline"}
    
    manager.register_fallback(ErrorCategory.NETWORK, network_fallback)
    
    # Function with retry decorator
    @with_retry(
        strategy=ExponentialBackoff(base_delay=1.0),
        max_attempts=3
    )
    async def flaky_operation():
        """Simulated flaky operation."""
        if random.random() < 0.7:  # 70% failure rate
            raise ConnectionError("Network unavailable")
        return "Success!"
    
    # Try operation
    try:
        result = await flaky_operation()
        print(f"Result: {result}")
    except Exception as e:
        # Handle with recovery manager
        fallback = await manager.handle_error(
            e,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH
        )
        print(f"Fallback: {fallback}")
    
    # Check statistics
    stats = manager.get_error_stats()
    print(f"Error stats: {stats}")


if __name__ == "__main__":
    asyncio.run(example_usage())