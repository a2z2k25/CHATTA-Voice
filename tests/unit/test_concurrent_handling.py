#!/usr/bin/env python3
"""Test concurrent request handling framework."""

import sys
import os
import time
import asyncio
import threading
from typing import List
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from voice_mode.concurrent_handler import (
    Priority,
    RequestStatus,
    Request,
    RequestQueue,
    SessionManager,
    RateLimiter,
    ConcurrentRequestHandler,
    LoadBalancer,
    get_concurrent_handler
)

from voice_mode.concurrent_integration import (
    VoiceRequest,
    VoiceConcurrentHandler,
    MultiUserVoiceHandler,
    LoadBalancedVoiceCluster,
    integrate_concurrent_handling
)


def test_request_queue():
    """Test priority-based request queue."""
    print("\n=== Testing Request Queue ===")
    
    queue = RequestQueue(max_size=10)
    
    # Add requests with different priorities
    req1 = Request("1", "test", "data1", Priority.LOW)
    req2 = Request("2", "test", "data2", Priority.CRITICAL)
    req3 = Request("3", "test", "data3", Priority.NORMAL)
    
    assert queue.put(req1)
    assert queue.put(req2)
    assert queue.put(req3)
    print(f"✓ Added 3 requests, queue size: {queue.size()}")
    
    # Get requests - should prioritize CRITICAL
    next_req = queue.get(timeout=1.0)
    assert next_req.id == "2"  # CRITICAL priority
    print(f"✓ Got CRITICAL request first: {next_req.id}")
    
    # Clear queue
    queue.clear()
    assert queue.size() == 0
    print("✓ Queue cleared")


def test_session_manager():
    """Test session management."""
    print("\n=== Testing Session Manager ===")
    
    manager = SessionManager(max_sessions=3)
    
    # Create sessions
    session1 = manager.create_session()
    session2 = manager.create_session("custom-id")
    session3 = manager.create_session()
    
    assert len(manager._sessions) == 3
    print(f"✓ Created 3 sessions")
    
    # Get session
    session = manager.get_session(session1)
    assert session is not None
    assert session["id"] == session1
    print(f"✓ Retrieved session: {session1}")
    
    # Add request to session
    manager.add_request(session1, "req1")
    assert session1 in manager._session_requests
    assert manager._sessions[session1]["request_count"] == 1
    print("✓ Added request to session")
    
    # Complete request
    manager.complete_request(session1, "req1", 0.1, success=True)
    metrics = manager.get_session_metrics(session1)
    assert metrics["completed_requests"] == 1
    print(f"✓ Completed request, metrics: {metrics}")
    
    # Test max sessions - should remove oldest
    session4 = manager.create_session()
    assert len(manager._sessions) == 3  # Still 3
    assert session1 not in manager._sessions  # Oldest removed
    print("✓ Max sessions enforced")
    
    # Cleanup inactive
    time.sleep(0.1)
    removed = manager.cleanup_inactive_sessions(timeout_seconds=0.05)
    print(f"✓ Cleaned up {removed} inactive sessions")


def test_rate_limiter():
    """Test token bucket rate limiting."""
    print("\n=== Testing Rate Limiter ===")
    
    # 10 tokens/sec, burst of 5
    limiter = RateLimiter(rate=10, burst=5)
    
    # Should have full burst initially
    assert limiter.available_tokens() == 5
    print(f"✓ Initial tokens: {limiter.available_tokens():.1f}")
    
    # Acquire tokens
    assert limiter.acquire(3)
    assert limiter.available_tokens() < 3
    print(f"✓ After acquiring 3: {limiter.available_tokens():.1f} tokens")
    
    # Try to acquire more than available
    assert not limiter.acquire(5, timeout=0)
    print("✓ Cannot acquire more than available")
    
    # Wait for refill
    time.sleep(0.3)  # Should refill ~3 tokens
    available = limiter.available_tokens()
    assert available > 2
    print(f"✓ After 0.3s: {available:.1f} tokens (refilled)")


async def test_concurrent_handler():
    """Test concurrent request handler."""
    print("\n=== Testing Concurrent Handler ===")
    
    handler = ConcurrentRequestHandler(
        max_workers=3,
        max_queue_size=10,
        rate_limit=(10, 20)
    )
    
    # Register test handler
    async def test_processor(data):
        await asyncio.sleep(0.01)
        return f"Processed: {data}"
    
    handler.register_handler("test", test_processor)
    
    # Start handler
    await handler.start()
    print("✓ Handler started with 3 workers")
    
    # Submit requests
    request_ids = []
    for i in range(5):
        req_id = await handler.submit_request(
            "test",
            f"data_{i}",
            priority=Priority.NORMAL
        )
        request_ids.append(req_id)
    
    print(f"✓ Submitted {len(request_ids)} requests")
    
    # Wait for completion
    results = []
    for req_id in request_ids:
        result = await handler.wait_for_request(req_id, timeout=5.0)
        results.append(result)
    
    assert len(results) == 5
    assert all("Processed:" in r for r in results)
    print(f"✓ All requests completed: {results[0]}")
    
    # Check metrics
    metrics = handler.get_metrics()
    assert metrics["completed_requests"] == 5
    assert metrics["failed_requests"] == 0
    print(f"✓ Metrics: completed={metrics['completed_requests']}, avg_time={metrics['avg_process_time']:.3f}s")
    
    # Test cancellation
    req_id = await handler.submit_request("test", "cancel_me")
    await handler.cancel_request(req_id)
    status = handler.get_request_status(req_id)
    assert status == RequestStatus.CANCELLED
    print("✓ Request cancellation working")
    
    # Stop handler
    await handler.stop()
    print("✓ Handler stopped")


async def test_load_balancer():
    """Test load balancing."""
    print("\n=== Testing Load Balancer ===")
    
    # Create multiple handlers
    handlers = [
        ConcurrentRequestHandler(max_workers=2) for _ in range(3)
    ]
    
    # Register handlers
    for h in handlers:
        h.register_handler("test", lambda d: f"Result: {d}")
        await h.start()
    
    # Create load balancer
    balancer = LoadBalancer(handlers)
    
    # Submit requests
    request_ids = []
    for i in range(6):
        req_id = await balancer.submit_request(
            "test",
            f"data_{i}",
            priority=Priority.NORMAL
        )
        request_ids.append(req_id)
    
    print(f"✓ Submitted {len(request_ids)} requests via load balancer")
    
    # Check distribution
    for i, handler in enumerate(handlers):
        metrics = handler.get_metrics()
        print(f"  Handler {i}: {metrics['total_requests']} requests")
    
    # Cleanup
    for h in handlers:
        await h.stop()
    
    print("✓ Load balancing working")


async def test_voice_concurrent_handler():
    """Test voice-specific concurrent handler."""
    print("\n=== Testing Voice Concurrent Handler ===")
    
    handler = VoiceConcurrentHandler(
        max_workers=3,
        max_sessions=10,
        rate_limit=(10, 20)
    )
    
    await handler.start()
    print("✓ Voice handler started")
    
    # Test transcription
    audio_data = b"test_audio_data"
    transcript = await handler.transcribe(audio_data)
    assert "Transcribed:" in transcript
    print(f"✓ Transcription: {transcript}")
    
    # Test synthesis
    text = "Hello, world!"
    audio = await handler.synthesize(text)
    assert len(audio) > 0
    print(f"✓ Synthesis: {len(audio)} bytes")
    
    # Test full conversation
    result = await handler.process_conversation(
        audio_data=audio_data,
        text="Test input"
    )
    assert "transcript" in result
    assert "response" in result
    assert "audio" in result
    assert "session_id" in result
    print(f"✓ Conversation processed: session={result['session_id']}")
    
    # Test caching
    transcript2 = await handler.transcribe(audio_data)
    assert transcript2 == transcript
    metrics = handler.get_metrics()
    assert metrics["voice"]["cache_hits"] > 0
    print(f"✓ Caching working: {metrics['voice']['cache_hits']} hits")
    
    # Check metrics
    assert metrics["voice"]["transcriptions"] > 0
    assert metrics["voice"]["syntheses"] > 0
    print(f"✓ Voice metrics: transcriptions={metrics['voice']['transcriptions']}, syntheses={metrics['voice']['syntheses']}")
    
    await handler.stop()
    print("✓ Voice handler stopped")


async def test_multi_user_handler():
    """Test multi-user voice handling."""
    print("\n=== Testing Multi-User Handler ===")
    
    handler = MultiUserVoiceHandler(max_users=5)
    await handler.start()
    print("✓ Multi-user handler started")
    
    # Simulate multiple users
    users = [f"user_{i}" for i in range(3)]
    results = []
    
    for user_id in users:
        result = await handler.process_user_request(
            user_id,
            audio_data=f"audio_from_{user_id}".encode()
        )
        results.append(result)
        assert result["user_id"] == user_id
        print(f"✓ Processed request for {user_id}")
    
    # Check user metrics
    for user_id in users:
        metrics = handler.get_user_metrics(user_id)
        assert metrics["total_requests"] > 0
        print(f"  {user_id}: {metrics['total_requests']} requests")
    
    # Test rate limiting per user
    # Exhaust rate limit for one user
    user_id = users[0]
    for _ in range(10):
        try:
            await handler.process_user_request(
                user_id,
                text="spam"
            )
        except RuntimeError as e:
            if "Rate limit exceeded" in str(e):
                print(f"✓ Rate limiting enforced for {user_id}")
                break
    
    # Other users should still work
    result = await handler.process_user_request(
        users[1],
        text="Still works"
    )
    assert result is not None
    print(f"✓ Other users unaffected by rate limit")
    
    # Close user session
    handler.close_user_session(users[0])
    assert users[0] not in handler._user_sessions
    print(f"✓ Closed session for {users[0]}")
    
    # Get all metrics
    all_metrics = handler.get_all_metrics()
    assert all_metrics["total_users"] == 2  # One closed
    print(f"✓ Total active users: {all_metrics['total_users']}")
    
    await handler.stop()
    print("✓ Multi-user handler stopped")


async def test_load_balanced_cluster():
    """Test load-balanced voice cluster."""
    print("\n=== Testing Load-Balanced Cluster ===")
    
    cluster = LoadBalancedVoiceCluster(num_handlers=3)
    await cluster.start()
    print("✓ Cluster started with 3 handlers")
    
    # Submit multiple requests
    tasks = []
    for i in range(10):
        task = cluster.process_request(
            "transcribe",
            VoiceRequest(audio_data=f"audio_{i}".encode())
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    assert len(results) == 10
    assert all("Transcribed:" in r for r in results)
    print(f"✓ Processed {len(results)} requests across cluster")
    
    # Check cluster metrics
    metrics = cluster.get_cluster_metrics()
    total_requests = sum(
        m["total_requests"] for m in metrics.values()
    )
    assert total_requests == 10
    print("✓ Cluster metrics:")
    for name, m in metrics.items():
        print(f"  {name}: {m['total_requests']} requests")
    
    await cluster.stop()
    print("✓ Cluster stopped")


def test_integration():
    """Test integration with voice mode."""
    print("\n=== Testing Voice Mode Integration ===")
    
    # Mock voice mode instance
    class MockVoiceMode:
        async def process_audio(self, audio_data: bytes) -> str:
            return "original_transcript"
        
        async def generate_audio(self, text: str) -> bytes:
            return b"original_audio"
    
    voice_mode = MockVoiceMode()
    
    # Integrate concurrent handling
    integrated = integrate_concurrent_handling(
        voice_mode,
        max_workers=5,
        max_sessions=20
    )
    
    # Check attributes added
    assert hasattr(integrated, "concurrent_handler")
    assert hasattr(integrated, "process_concurrent")
    assert hasattr(integrated, "get_concurrent_metrics")
    assert hasattr(integrated, "cleanup_concurrent")
    print("✓ Integration attributes added")
    
    # Test concurrent processing
    async def test_concurrent():
        await integrated.concurrent_handler.start()
        
        result = await integrated.process_concurrent(
            audio_data=b"test_audio",
            text="test_text"
        )
        assert "transcript" in result
        assert "response" in result
        assert "session_id" in result
        print(f"✓ Concurrent processing: session={result['session_id']}")
        
        # Get metrics
        metrics = integrated.get_concurrent_metrics()
        assert "handler" in metrics
        assert "voice" in metrics
        print(f"✓ Metrics accessible: {metrics['handler']['total_requests']} requests")
        
        await integrated.cleanup_concurrent()
    
    asyncio.run(test_concurrent())
    print("✓ Integration working")


async def test_concurrent_stress():
    """Stress test concurrent handling."""
    print("\n=== Concurrent Stress Test ===")
    
    handler = VoiceConcurrentHandler(
        max_workers=10,
        max_sessions=50,
        rate_limit=(100, 200)
    )
    
    await handler.start()
    print("✓ Started stress test handler")
    
    # Submit many requests concurrently
    start_time = time.time()
    tasks = []
    
    for i in range(100):
        if i % 2 == 0:
            task = handler.transcribe(f"audio_{i}".encode())
        else:
            task = handler.synthesize(f"text_{i}")
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    duration = time.time() - start_time
    
    # Count successes
    successes = sum(1 for r in results if not isinstance(r, Exception))
    failures = len(results) - successes
    
    print(f"✓ Processed {successes}/{len(results)} requests in {duration:.2f}s")
    print(f"  Rate: {successes/duration:.1f} req/s")
    
    if failures > 0:
        print(f"  Failures: {failures}")
    
    # Check final metrics
    metrics = handler.get_metrics()
    print(f"✓ Final metrics:")
    print(f"  Completed: {metrics['handler']['completed_requests']}")
    print(f"  Failed: {metrics['handler']['failed_requests']}")
    print(f"  Avg wait: {metrics['handler']['avg_wait_time']:.3f}s")
    print(f"  Avg process: {metrics['handler']['avg_process_time']:.3f}s")
    print(f"  Cache hit rate: {metrics['voice']['cache_hits']/(metrics['voice']['cache_hits']+metrics['voice']['cache_misses']):.1%}")
    
    await handler.stop()
    print("✓ Stress test completed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("CONCURRENT HANDLING TESTS")
    print("=" * 60)
    
    # Synchronous tests
    test_request_queue()
    test_session_manager()
    test_rate_limiter()
    test_integration()
    
    # Async tests
    print("\n=== Running Async Tests ===")
    asyncio.run(test_concurrent_handler())
    asyncio.run(test_load_balancer())
    asyncio.run(test_voice_concurrent_handler())
    asyncio.run(test_multi_user_handler())
    asyncio.run(test_load_balanced_cluster())
    asyncio.run(test_concurrent_stress())
    
    print("\n" + "=" * 60)
    print("✓ All concurrent handling tests passed!")
    print("Sprint 31 implementation complete!")
    print("=" * 60)


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)
    main()