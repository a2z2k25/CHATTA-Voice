#!/usr/bin/env python3
"""Test error recovery implementation."""

import asyncio
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.error_recovery import (
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    ExponentialBackoff,
    LinearBackoff,
    ErrorRecoveryManager,
    CircuitBreaker,
    with_retry,
    classify_error
)


def test_error_classification():
    """Test error classification."""
    print("\n=== Testing Error Classification ===")
    
    # Test various error types
    errors = [
        (ConnectionError("Connection refused"), ErrorCategory.NETWORK),
        (TimeoutError("Operation timed out"), ErrorCategory.TIMEOUT),
        (Exception("Rate limit exceeded"), ErrorCategory.RATE_LIMIT),
        (Exception("Authentication failed"), ErrorCategory.AUTHENTICATION),
        (Exception("Microphone not found"), ErrorCategory.AUDIO),
        (Exception("API endpoint unavailable"), ErrorCategory.SERVICE),
        (Exception("Invalid configuration"), ErrorCategory.CONFIGURATION),
        (Exception("Random error"), ErrorCategory.UNKNOWN),
    ]
    
    for error, expected in errors:
        category = classify_error(error)
        status = "✓" if category == expected else "✗"
        print(f"{status} {error}: {category.name}")


def test_retry_strategies():
    """Test retry strategies."""
    print("\n=== Testing Retry Strategies ===")
    
    # Test exponential backoff
    exp_strategy = ExponentialBackoff(base_delay=1.0, jitter=False)
    print("Exponential backoff delays:")
    for i in range(5):
        delay = exp_strategy.get_delay(i)
        print(f"  Attempt {i}: {delay:.1f}s")
    
    # Test linear backoff
    lin_strategy = LinearBackoff(base_delay=1.0, increment=2.0)
    print("\nLinear backoff delays:")
    for i in range(5):
        delay = lin_strategy.get_delay(i)
        print(f"  Attempt {i}: {delay:.1f}s")


async def test_retry_decorator():
    """Test retry decorator."""
    print("\n=== Testing Retry Decorator ===")
    
    attempt_count = 0
    
    @with_retry(
        strategy=LinearBackoff(base_delay=0.1),
        max_attempts=3
    )
    async def flaky_function():
        nonlocal attempt_count
        attempt_count += 1
        print(f"  Attempt {attempt_count}")
        
        if attempt_count < 3:
            raise ConnectionError("Simulated network error")
        return "Success!"
    
    try:
        result = await flaky_function()
        print(f"Result: {result}")
        assert attempt_count == 3
        print("✓ Retry decorator working")
    except Exception as e:
        print(f"✗ Failed after retries: {e}")


def test_circuit_breaker():
    """Test circuit breaker."""
    print("\n=== Testing Circuit Breaker ===")
    
    breaker = CircuitBreaker(
        name="test",
        failure_threshold=3,
        timeout=1.0
    )
    
    # Test normal operation
    def good_function():
        return "OK"
    
    result = breaker.call(good_function)
    assert result == "OK"
    print(f"✓ Normal call: {result}")
    
    # Test failures
    failure_count = 0
    def bad_function():
        nonlocal failure_count
        failure_count += 1
        raise Exception(f"Failure {failure_count}")
    
    # Trigger failures
    for i in range(3):
        try:
            breaker.call(bad_function)
        except Exception:
            pass
    
    print(f"Failures: {failure_count}, State: {breaker.state}")
    
    # Circuit should be open
    try:
        breaker.call(good_function)
        print("✗ Circuit should be open")
    except Exception as e:
        print(f"✓ Circuit open: {e}")
    
    # Wait for timeout
    print("Waiting for timeout...")
    time.sleep(1.1)
    
    # Should be half-open, then closed
    try:
        result = breaker.call(good_function)
        print(f"✓ Circuit recovered: {result}")
    except Exception as e:
        print(f"✗ Circuit still open: {e}")


async def test_error_recovery_manager():
    """Test error recovery manager."""
    print("\n=== Testing Error Recovery Manager ===")
    
    manager = ErrorRecoveryManager()
    
    # Register fallback
    fallback_called = False
    def fallback_handler(context: ErrorContext):
        nonlocal fallback_called
        fallback_called = True
        print(f"  Fallback for {context.category.name}: {context.message}")
        return "Fallback result"
    
    manager.register_fallback(ErrorCategory.NETWORK, fallback_handler)
    
    # Test error handling
    error = ConnectionError("Network down")
    result = await manager.handle_error(
        error,
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.HIGH
    )
    
    assert fallback_called
    assert result == "Fallback result"
    print(f"✓ Fallback executed: {result}")
    
    # Check statistics
    stats = manager.get_error_stats()
    print(f"Error stats: Total={stats['total_errors']}, "
          f"Categories={stats['by_category']}")


def test_error_context():
    """Test error context."""
    print("\n=== Testing Error Context ===")
    
    context = ErrorContext(
        error_type=ConnectionError,
        message="Test error",
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.MEDIUM,
        max_retries=3
    )
    
    # Test retry logic
    assert context.should_retry()
    print("✓ Should retry: True")
    
    # Increment retries
    for i in range(3):
        context.increment_retry()
        should_retry = context.should_retry()
        print(f"  After retry {i+1}: should_retry={should_retry}")
    
    assert not context.should_retry()
    print("✓ Max retries reached")
    
    # Test critical errors
    critical_context = ErrorContext(
        error_type=Exception,
        message="Critical failure",
        category=ErrorCategory.UNKNOWN,
        severity=ErrorSeverity.CRITICAL
    )
    
    assert not critical_context.should_retry()
    print("✓ Critical errors not retried")


async def test_recovery_callbacks():
    """Test recovery callbacks."""
    print("\n=== Testing Recovery Callbacks ===")
    
    manager = ErrorRecoveryManager()
    
    callback_data = []
    def recovery_callback(context: ErrorContext):
        callback_data.append(context.message)
        print(f"  Recovery callback: {context.message}")
    
    manager.register_recovery_callback(recovery_callback)
    
    # Fallback that succeeds
    manager.register_fallback(
        ErrorCategory.SERVICE,
        lambda ctx: "Recovered"
    )
    
    # Trigger error with recovery
    await manager.handle_error(
        Exception("Service error"),
        category=ErrorCategory.SERVICE
    )
    
    assert len(callback_data) == 1
    print(f"✓ Recovery callback triggered: {callback_data}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("ERROR RECOVERY TESTS")
    print("=" * 60)
    
    # Run synchronous tests
    test_error_classification()
    test_retry_strategies()
    test_circuit_breaker()
    test_error_context()
    
    # Run async tests
    asyncio.run(test_retry_decorator())
    asyncio.run(test_error_recovery_manager())
    asyncio.run(test_recovery_callbacks())
    
    print("\n" + "=" * 60)
    print("✓ All error recovery tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()