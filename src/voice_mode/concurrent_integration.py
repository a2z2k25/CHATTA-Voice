#!/usr/bin/env python3
"""Integration layer for concurrent request handling in voice mode."""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
import hashlib
import logging
from dataclasses import dataclass

from .concurrent_handler import (
    Priority,
    RequestStatus,
    ConcurrentRequestHandler,
    SessionManager,
    RateLimiter,
    LoadBalancer,
    get_concurrent_handler
)

logger = logging.getLogger(__name__)


@dataclass
class VoiceRequest:
    """Voice-specific request data."""
    audio_data: Optional[bytes] = None
    text: Optional[str] = None
    operation: str = "transcribe"  # transcribe, synthesize, or process
    language: str = "en"
    voice: Optional[str] = None
    options: Dict[str, Any] = None


class VoiceConcurrentHandler:
    """Concurrent handler for voice requests."""
    
    def __init__(self,
                 max_workers: int = 5,
                 max_sessions: int = 100,
                 rate_limit: Optional[tuple] = (10, 20)):  # 10 req/s, burst 20
        """
        Initialize voice concurrent handler.
        
        Args:
            max_workers: Maximum concurrent voice processing workers
            max_sessions: Maximum concurrent sessions
            rate_limit: (rate, burst) tuple for rate limiting
        """
        self.handler = ConcurrentRequestHandler(
            max_workers=max_workers,
            max_queue_size=1000,
            rate_limit=rate_limit
        )
        
        # Session management
        self.sessions = self.handler.sessions
        self.sessions.max_sessions = max_sessions
        
        # Register voice handlers
        self._register_handlers()
        
        # Metrics
        self._voice_metrics = {
            "transcriptions": 0,
            "syntheses": 0,
            "avg_transcription_time": 0,
            "avg_synthesis_time": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Simple cache
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 60  # seconds
    
    def _register_handlers(self):
        """Register voice-specific handlers."""
        self.handler.register_handler("transcribe", self._handle_transcription)
        self.handler.register_handler("synthesize", self._handle_synthesis)
        self.handler.register_handler("process", self._handle_process)
    
    async def _handle_transcription(self, request: VoiceRequest) -> str:
        """Handle transcription request."""
        start_time = time.time()
        
        # Check cache
        cache_key = hashlib.md5(request.audio_data).hexdigest()
        cached = self._get_cached(cache_key)
        if cached:
            self._voice_metrics["cache_hits"] += 1
            return cached
        
        self._voice_metrics["cache_misses"] += 1
        
        # Simulate transcription
        await asyncio.sleep(0.05)  # Simulate STT processing
        result = f"Transcribed: {len(request.audio_data)} bytes"
        
        # Cache result
        self._set_cached(cache_key, result)
        
        # Update metrics
        duration = time.time() - start_time
        self._update_avg_time("transcription", duration)
        self._voice_metrics["transcriptions"] += 1
        
        return result
    
    async def _handle_synthesis(self, request: VoiceRequest) -> bytes:
        """Handle synthesis request."""
        start_time = time.time()
        
        # Check cache
        cache_key = hashlib.md5(request.text.encode()).hexdigest()
        cached = self._get_cached(cache_key)
        if cached:
            self._voice_metrics["cache_hits"] += 1
            return cached
        
        self._voice_metrics["cache_misses"] += 1
        
        # Simulate synthesis
        await asyncio.sleep(0.03)  # Simulate TTS processing
        result = f"Audio for: {request.text}".encode()
        
        # Cache result
        self._set_cached(cache_key, result)
        
        # Update metrics
        duration = time.time() - start_time
        self._update_avg_time("synthesis", duration)
        self._voice_metrics["syntheses"] += 1
        
        return result
    
    async def _handle_process(self, request: VoiceRequest) -> Dict[str, Any]:
        """Handle full processing request."""
        # Transcribe if audio provided
        transcript = None
        if request.audio_data:
            transcript = await self._handle_transcription(request)
        
        # Generate response
        response_text = f"Response to: {transcript or request.text}"
        
        # Synthesize response
        audio = await self._handle_synthesis(
            VoiceRequest(text=response_text, operation="synthesize")
        )
        
        return {
            "transcript": transcript,
            "response": response_text,
            "audio": audio
        }
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value."""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self._cache_ttl:
                return entry["value"]
            else:
                del self._cache[key]
        return None
    
    def _set_cached(self, key: str, value: Any):
        """Set cached value."""
        self._cache[key] = {
            "value": value,
            "timestamp": time.time()
        }
        
        # Simple cache size limit
        if len(self._cache) > 1000:
            # Remove oldest entries
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k]["timestamp"]
            )
            for k in sorted_keys[:100]:
                del self._cache[k]
    
    def _update_avg_time(self, metric_type: str, duration: float):
        """Update average time metric."""
        key = f"avg_{metric_type}_time"
        # Handle plural forms correctly
        if metric_type == "synthesis":
            count_key = "syntheses"
        else:
            count_key = f"{metric_type}s"
        
        current_avg = self._voice_metrics[key]
        current_count = self._voice_metrics[count_key]
        
        new_avg = (current_avg * current_count + duration) / (current_count + 1)
        self._voice_metrics[key] = new_avg
    
    async def start(self):
        """Start the handler."""
        await self.handler.start()
    
    async def stop(self):
        """Stop the handler."""
        await self.handler.stop()
    
    async def transcribe(self,
                         audio_data: bytes,
                         session_id: Optional[str] = None,
                         priority: Priority = Priority.NORMAL) -> str:
        """Transcribe audio concurrently."""
        request = VoiceRequest(
            audio_data=audio_data,
            operation="transcribe"
        )
        
        request_id = await self.handler.submit_request(
            "transcribe",
            request,
            priority=priority,
            session_id=session_id
        )
        
        return await self.handler.wait_for_request(request_id)
    
    async def synthesize(self,
                         text: str,
                         session_id: Optional[str] = None,
                         priority: Priority = Priority.NORMAL,
                         voice: Optional[str] = None) -> bytes:
        """Synthesize speech concurrently."""
        request = VoiceRequest(
            text=text,
            operation="synthesize",
            voice=voice
        )
        
        request_id = await self.handler.submit_request(
            "synthesize",
            request,
            priority=priority,
            session_id=session_id
        )
        
        return await self.handler.wait_for_request(request_id)
    
    async def process_conversation(self,
                                   audio_data: Optional[bytes] = None,
                                   text: Optional[str] = None,
                                   session_id: Optional[str] = None) -> Dict[str, Any]:
        """Process full conversation turn."""
        if not session_id:
            session_id = self.sessions.create_session()
        
        request = VoiceRequest(
            audio_data=audio_data,
            text=text,
            operation="process"
        )
        
        request_id = await self.handler.submit_request(
            "process",
            request,
            priority=Priority.HIGH,
            session_id=session_id
        )
        
        result = await self.handler.wait_for_request(request_id)
        result["session_id"] = session_id
        
        return result
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get combined metrics."""
        return {
            "handler": self.handler.get_metrics(),
            "voice": self._voice_metrics.copy(),
            "cache_size": len(self._cache)
        }


class MultiUserVoiceHandler:
    """Handles voice requests for multiple users concurrently."""
    
    def __init__(self, max_users: int = 50):
        self.max_users = max_users
        self.voice_handler = VoiceConcurrentHandler(
            max_workers=10,
            max_sessions=max_users,
            rate_limit=(20, 50)  # Higher limits for multi-user
        )
        
        # User sessions
        self._user_sessions: Dict[str, str] = {}
        
        # User-specific rate limiters
        self._user_rate_limiters: Dict[str, RateLimiter] = {}
        self._default_user_rate = (5, 10)  # 5 req/s per user
    
    async def start(self):
        """Start multi-user handler."""
        await self.voice_handler.start()
    
    async def stop(self):
        """Stop multi-user handler."""
        await self.voice_handler.stop()
    
    def _get_user_session(self, user_id: str) -> str:
        """Get or create user session."""
        if user_id not in self._user_sessions:
            session_id = self.voice_handler.sessions.create_session()
            self._user_sessions[user_id] = session_id
            
            # Create user rate limiter
            self._user_rate_limiters[user_id] = RateLimiter(
                self._default_user_rate[0],
                self._default_user_rate[1]
            )
        
        return self._user_sessions[user_id]
    
    def _check_user_rate_limit(self, user_id: str) -> bool:
        """Check user rate limit."""
        if user_id in self._user_rate_limiters:
            return self._user_rate_limiters[user_id].acquire()
        return True
    
    async def process_user_request(self,
                                   user_id: str,
                                   audio_data: Optional[bytes] = None,
                                   text: Optional[str] = None) -> Dict[str, Any]:
        """Process request for specific user."""
        # Check user rate limit
        if not self._check_user_rate_limit(user_id):
            raise RuntimeError(f"Rate limit exceeded for user {user_id}")
        
        # Get user session
        session_id = self._get_user_session(user_id)
        
        # Determine priority based on user activity
        session = self.voice_handler.sessions.get_session(session_id)
        if session and session["request_count"] == 0:
            # First request from user gets higher priority
            priority = Priority.HIGH
        else:
            priority = Priority.NORMAL
        
        # Process request
        result = await self.voice_handler.process_conversation(
            audio_data=audio_data,
            text=text,
            session_id=session_id
        )
        
        result["user_id"] = user_id
        return result
    
    def close_user_session(self, user_id: str):
        """Close user session."""
        if user_id in self._user_sessions:
            session_id = self._user_sessions[user_id]
            self.voice_handler.sessions.close_session(session_id)
            del self._user_sessions[user_id]
            
            if user_id in self._user_rate_limiters:
                del self._user_rate_limiters[user_id]
    
    def get_user_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get metrics for specific user."""
        if user_id not in self._user_sessions:
            return {}
        
        session_id = self._user_sessions[user_id]
        return self.voice_handler.sessions.get_session_metrics(session_id)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        return {
            "total_users": len(self._user_sessions),
            "handler_metrics": self.voice_handler.get_metrics(),
            "user_sessions": {
                user_id: self.get_user_metrics(user_id)
                for user_id in self._user_sessions
            }
        }


class LoadBalancedVoiceCluster:
    """Load-balanced cluster of voice handlers."""
    
    def __init__(self, num_handlers: int = 3):
        # Create multiple handlers
        self.handlers = [
            ConcurrentRequestHandler(
                max_workers=5,
                max_queue_size=500,
                rate_limit=(10, 20)
            )
            for _ in range(num_handlers)
        ]
        
        # Setup load balancer
        self.load_balancer = LoadBalancer(self.handlers)
        
        # Register handlers on all instances
        for handler in self.handlers:
            self._register_handlers(handler)
    
    def _register_handlers(self, handler: ConcurrentRequestHandler):
        """Register voice handlers."""
        async def transcribe(request):
            await asyncio.sleep(0.05)
            return f"Transcribed: {len(request.audio_data)} bytes"
        
        async def synthesize(request):
            await asyncio.sleep(0.03)
            return f"Audio for: {request.text}".encode()
        
        handler.register_handler("transcribe", transcribe)
        handler.register_handler("synthesize", synthesize)
    
    async def start(self):
        """Start all handlers."""
        for handler in self.handlers:
            await handler.start()
    
    async def stop(self):
        """Stop all handlers."""
        for handler in self.handlers:
            await handler.stop()
    
    async def process_request(self, request_type: str, data: Any) -> Any:
        """Process request using load balancing."""
        # Get the handler that will process this request
        handler = self.load_balancer.get_next_handler()
        
        # Submit directly to that handler
        request_id = await handler.submit_request(
            request_type,
            data,
            priority=Priority.NORMAL
        )
        
        # Wait on the same handler
        return await handler.wait_for_request(request_id)
    
    def get_cluster_metrics(self) -> Dict[str, Any]:
        """Get metrics for all handlers."""
        return {
            f"handler_{i}": handler.get_metrics()
            for i, handler in enumerate(self.handlers)
        }


def integrate_concurrent_handling(voice_mode_instance,
                                 max_workers: int = 10,
                                 max_sessions: int = 100):
    """Integrate concurrent handling with voice mode."""
    
    # Create concurrent handler
    concurrent_handler = VoiceConcurrentHandler(
        max_workers=max_workers,
        max_sessions=max_sessions
    )
    
    # Store original methods
    original_process = voice_mode_instance.process_audio
    original_synthesize = voice_mode_instance.generate_audio
    
    # Wrap with concurrent handling
    async def concurrent_process(audio_data: bytes) -> str:
        await concurrent_handler.start()
        return await concurrent_handler.transcribe(audio_data)
    
    async def concurrent_synthesize(text: str) -> bytes:
        await concurrent_handler.start()
        return await concurrent_handler.synthesize(text)
    
    # Replace methods
    voice_mode_instance.process_audio = concurrent_process
    voice_mode_instance.generate_audio = concurrent_synthesize
    
    # Add new methods
    voice_mode_instance.concurrent_handler = concurrent_handler
    
    async def process_concurrent_conversation(audio_data=None, text=None, session_id=None):
        await concurrent_handler.start()
        return await concurrent_handler.process_conversation(
            audio_data, text, session_id
        )
    
    voice_mode_instance.process_concurrent = process_concurrent_conversation
    
    def get_concurrent_metrics():
        return concurrent_handler.get_metrics()
    
    voice_mode_instance.get_concurrent_metrics = get_concurrent_metrics
    
    async def cleanup_concurrent():
        await concurrent_handler.stop()
    
    voice_mode_instance.cleanup_concurrent = cleanup_concurrent
    
    return voice_mode_instance


# Export main components
__all__ = [
    "VoiceRequest",
    "VoiceConcurrentHandler",
    "MultiUserVoiceHandler",
    "LoadBalancedVoiceCluster",
    "integrate_concurrent_handling"
]