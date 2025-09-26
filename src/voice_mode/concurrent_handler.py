#!/usr/bin/env python3
"""Concurrent request handling framework for voice mode."""

import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List, Callable, Set, Tuple
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum
import threading
from concurrent.futures import ThreadPoolExecutor
import hashlib
import logging

logger = logging.getLogger(__name__)


class Priority(Enum):
    """Request priority levels."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5


class RequestStatus(Enum):
    """Request processing status."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class Request:
    """Concurrent request representation."""
    id: str
    type: str
    data: Any
    priority: Priority
    session_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: RequestStatus = RequestStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def duration(self) -> Optional[float]:
        """Get processing duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def wait_time(self) -> Optional[float]:
        """Get time spent waiting."""
        if self.started_at:
            return self.started_at - self.created_at
        return None


class RequestQueue:
    """Priority-based request queue with fair scheduling."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._queues: Dict[Priority, deque] = {
            priority: deque() for priority in Priority
        }
        self._lock = threading.RLock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)
        self._size = 0
        self._round_robin_state = 0
    
    def put(self, request: Request, timeout: Optional[float] = None) -> bool:
        """Add request to queue."""
        with self._not_full:
            # Wait if queue is full
            end_time = time.time() + timeout if timeout else None
            while self._size >= self.max_size:
                if timeout is None:
                    self._not_full.wait()
                else:
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        return False
                    self._not_full.wait(remaining)
            
            # Add to appropriate priority queue
            self._queues[request.priority].append(request)
            self._size += 1
            request.status = RequestStatus.QUEUED
            self._not_empty.notify()
            return True
    
    def get(self, timeout: Optional[float] = None) -> Optional[Request]:
        """Get next request using fair scheduling."""
        with self._not_empty:
            # Wait if all queues empty
            end_time = time.time() + timeout if timeout else None
            while self._size == 0:
                if timeout is None:
                    self._not_empty.wait()
                else:
                    remaining = end_time - time.time()
                    if remaining <= 0:
                        return None
                    self._not_empty.wait(remaining)
            
            # Fair scheduling with priority bias
            request = self._get_next_request()
            if request:
                self._size -= 1
                self._not_full.notify()
            return request
    
    def _get_next_request(self) -> Optional[Request]:
        """Get next request using weighted round-robin."""
        # Priority weights (higher priority = more slots)
        weights = {
            Priority.CRITICAL: 5,
            Priority.HIGH: 3,
            Priority.NORMAL: 2,
            Priority.LOW: 1,
            Priority.BACKGROUND: 0
        }
        
        # Build weighted schedule
        schedule = []
        for priority in Priority:
            schedule.extend([priority] * weights[priority])
        
        # Round-robin through schedule
        for _ in range(len(schedule)):
            priority = schedule[self._round_robin_state % len(schedule)]
            self._round_robin_state += 1
            
            if self._queues[priority]:
                return self._queues[priority].popleft()
        
        # Fallback: get from any non-empty queue
        for priority in Priority:
            if self._queues[priority]:
                return self._queues[priority].popleft()
        
        return None
    
    def size(self) -> int:
        """Get total queue size."""
        with self._lock:
            return self._size
    
    def clear(self):
        """Clear all queues."""
        with self._lock:
            for queue in self._queues.values():
                queue.clear()
            self._size = 0


class SessionManager:
    """Manages concurrent sessions."""
    
    def __init__(self, max_sessions: int = 100):
        self.max_sessions = max_sessions
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._session_requests: Dict[str, List[str]] = defaultdict(list)
        self._session_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create new session."""
        with self._lock:
            if len(self._sessions) >= self.max_sessions:
                # Remove oldest session
                oldest = min(self._sessions.items(), 
                           key=lambda x: x[1].get("created_at", 0))
                self.close_session(oldest[0])
            
            session_id = session_id or str(uuid.uuid4())
            self._sessions[session_id] = {
                "id": session_id,
                "created_at": time.time(),
                "last_activity": time.time(),
                "request_count": 0,
                "active_requests": 0,
                "state": {}
            }
            
            self._session_metrics[session_id] = {
                "total_requests": 0,
                "completed_requests": 0,
                "failed_requests": 0,
                "total_duration": 0,
                "avg_duration": 0
            }
            
            return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session["last_activity"] = time.time()
            return session
    
    def update_session(self, session_id: str, data: Dict[str, Any]):
        """Update session data."""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].update(data)
                self._sessions[session_id]["last_activity"] = time.time()
    
    def close_session(self, session_id: str):
        """Close session."""
        with self._lock:
            self._sessions.pop(session_id, None)
            self._session_requests.pop(session_id, None)
            self._session_metrics.pop(session_id, None)
    
    def add_request(self, session_id: str, request_id: str):
        """Add request to session."""
        with self._lock:
            if session_id in self._sessions:
                self._session_requests[session_id].append(request_id)
                self._sessions[session_id]["request_count"] += 1
                self._sessions[session_id]["active_requests"] += 1
                self._session_metrics[session_id]["total_requests"] += 1
    
    def complete_request(self, session_id: str, request_id: str, 
                        duration: float, success: bool = True):
        """Mark request as completed."""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id]["active_requests"] -= 1
                
                metrics = self._session_metrics[session_id]
                if success:
                    metrics["completed_requests"] += 1
                else:
                    metrics["failed_requests"] += 1
                
                metrics["total_duration"] += duration
                metrics["avg_duration"] = (
                    metrics["total_duration"] / 
                    max(1, metrics["completed_requests"])
                )
    
    def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get session metrics."""
        with self._lock:
            return self._session_metrics.get(session_id, {}).copy()
    
    def cleanup_inactive_sessions(self, timeout_seconds: float = 300):
        """Remove inactive sessions."""
        with self._lock:
            current_time = time.time()
            to_remove = []
            
            for session_id, session in self._sessions.items():
                if current_time - session["last_activity"] > timeout_seconds:
                    if session["active_requests"] == 0:
                        to_remove.append(session_id)
            
            for session_id in to_remove:
                self.close_session(session_id)
            
            return len(to_remove)


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: float, burst: int):
        """
        Args:
            rate: Tokens per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = burst
        self._tokens = burst
        self._last_update = time.time()
        self._lock = threading.RLock()
    
    def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """Try to acquire tokens."""
        with self._lock:
            self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            
            if timeout is None or timeout <= 0:
                return False
            
            # Wait for tokens
            tokens_needed = tokens - self._tokens
            wait_time = tokens_needed / self.rate
            
            if wait_time > timeout:
                return False
            
            time.sleep(wait_time)
            self._refill()
            
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            
            return False
    
    def _refill(self):
        """Refill token bucket."""
        current_time = time.time()
        elapsed = current_time - self._last_update
        
        new_tokens = elapsed * self.rate
        self._tokens = min(self.burst, self._tokens + new_tokens)
        self._last_update = current_time
    
    def available_tokens(self) -> float:
        """Get available tokens."""
        with self._lock:
            self._refill()
            return self._tokens


class ConcurrentRequestHandler:
    """Handles concurrent request processing."""
    
    def __init__(self, 
                 max_workers: int = 10,
                 max_queue_size: int = 1000,
                 rate_limit: Optional[Tuple[float, int]] = None):
        """
        Args:
            max_workers: Maximum concurrent workers
            max_queue_size: Maximum queue size
            rate_limit: Optional (rate, burst) tuple
        """
        self.max_workers = max_workers
        self.queue = RequestQueue(max_queue_size)
        self.sessions = SessionManager()
        
        # Rate limiting
        self.rate_limiter = None
        if rate_limit:
            self.rate_limiter = RateLimiter(rate_limit[0], rate_limit[1])
        
        # Worker management
        self._workers: List[asyncio.Task] = []
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._running = False
        self._lock = threading.RLock()
        
        # Request tracking
        self._requests: Dict[str, Request] = {}
        self._active_requests: Set[str] = set()
        
        # Metrics
        self._metrics = {
            "total_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "cancelled_requests": 0,
            "timeout_requests": 0,
            "avg_wait_time": 0,
            "avg_process_time": 0,
            "current_queue_size": 0,
            "active_workers": 0
        }
        
        # Handlers
        self._handlers: Dict[str, Callable] = {}
    
    def register_handler(self, request_type: str, handler: Callable):
        """Register request handler."""
        self._handlers[request_type] = handler
    
    async def start(self):
        """Start request processing."""
        if self._running:
            return
        
        self._running = True
        
        # Start workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(i))
            self._workers.append(worker)
        
        logger.info(f"Started {self.max_workers} concurrent workers")
    
    async def stop(self):
        """Stop request processing."""
        self._running = False
        
        # Cancel workers
        for worker in self._workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        logger.info("Stopped concurrent request handler")
    
    async def submit_request(self,
                            request_type: str,
                            data: Any,
                            priority: Priority = Priority.NORMAL,
                            session_id: Optional[str] = None,
                            timeout: Optional[float] = None) -> str:
        """Submit request for processing."""
        # Rate limiting
        if self.rate_limiter and not self.rate_limiter.acquire(timeout=1.0):
            raise RuntimeError("Rate limit exceeded")
        
        # Create request
        request = Request(
            id=str(uuid.uuid4()),
            type=request_type,
            data=data,
            priority=priority,
            session_id=session_id
        )
        
        # Track request
        with self._lock:
            self._requests[request.id] = request
            self._metrics["total_requests"] += 1
        
        # Add to session
        if session_id:
            self.sessions.add_request(session_id, request.id)
        
        # Queue request
        if not self.queue.put(request, timeout=timeout):
            request.status = RequestStatus.TIMEOUT
            self._metrics["timeout_requests"] += 1
            raise TimeoutError("Request queue timeout")
        
        return request.id
    
    async def wait_for_request(self, 
                              request_id: str,
                              timeout: Optional[float] = None) -> Any:
        """Wait for request completion."""
        start_time = time.time()
        
        while True:
            with self._lock:
                request = self._requests.get(request_id)
                
                if not request:
                    raise ValueError(f"Unknown request: {request_id}")
                
                if request.status == RequestStatus.COMPLETED:
                    return request.result
                
                if request.status == RequestStatus.FAILED:
                    raise RuntimeError(f"Request failed: {request.error}")
                
                if request.status == RequestStatus.CANCELLED:
                    raise RuntimeError("Request cancelled")
                
                if request.status == RequestStatus.TIMEOUT:
                    raise TimeoutError("Request timeout")
            
            if timeout and time.time() - start_time > timeout:
                await self.cancel_request(request_id)
                raise TimeoutError("Wait timeout")
            
            await asyncio.sleep(0.01)
    
    async def cancel_request(self, request_id: str):
        """Cancel pending request."""
        with self._lock:
            request = self._requests.get(request_id)
            
            if not request:
                return
            
            if request.status in [RequestStatus.PENDING, RequestStatus.QUEUED]:
                request.status = RequestStatus.CANCELLED
                self._metrics["cancelled_requests"] += 1
    
    def get_request_status(self, request_id: str) -> Optional[RequestStatus]:
        """Get request status."""
        with self._lock:
            request = self._requests.get(request_id)
            return request.status if request else None
    
    async def _worker_loop(self, worker_id: int):
        """Worker processing loop."""
        logger.debug(f"Worker {worker_id} started")
        
        while self._running:
            try:
                # Get next request
                request = await asyncio.get_event_loop().run_in_executor(
                    None, self.queue.get, 1.0
                )
                
                if not request:
                    continue
                
                # Process request
                await self._process_request(request, worker_id)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
        
        logger.debug(f"Worker {worker_id} stopped")
    
    async def _process_request(self, request: Request, worker_id: int):
        """Process single request."""
        with self._lock:
            self._active_requests.add(request.id)
            self._metrics["active_workers"] = len(self._active_requests)
        
        request.status = RequestStatus.PROCESSING
        request.started_at = time.time()
        
        try:
            # Get handler
            handler = self._handlers.get(request.type)
            if not handler:
                raise ValueError(f"No handler for request type: {request.type}")
            
            # Process request
            if asyncio.iscoroutinefunction(handler):
                result = await handler(request.data)
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    self._executor, handler, request.data
                )
            
            # Complete request
            request.result = result
            request.status = RequestStatus.COMPLETED
            request.completed_at = time.time()
            
            # Update metrics
            with self._lock:
                self._metrics["completed_requests"] += 1
                self._update_avg_times(request)
            
            # Update session
            if request.session_id:
                self.sessions.complete_request(
                    request.session_id,
                    request.id,
                    request.duration(),
                    success=True
                )
            
        except Exception as e:
            logger.error(f"Request {request.id} failed: {e}")
            request.error = str(e)
            request.status = RequestStatus.FAILED
            request.completed_at = time.time()
            
            with self._lock:
                self._metrics["failed_requests"] += 1
            
            if request.session_id:
                self.sessions.complete_request(
                    request.session_id,
                    request.id,
                    request.duration() or 0,
                    success=False
                )
        
        finally:
            with self._lock:
                self._active_requests.discard(request.id)
                self._metrics["active_workers"] = len(self._active_requests)
    
    def _update_avg_times(self, request: Request):
        """Update average timing metrics."""
        total = self._metrics["completed_requests"]
        
        if request.wait_time():
            self._metrics["avg_wait_time"] = (
                (self._metrics["avg_wait_time"] * (total - 1) + request.wait_time()) / total
            )
        
        if request.duration():
            self._metrics["avg_process_time"] = (
                (self._metrics["avg_process_time"] * (total - 1) + request.duration()) / total
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get handler metrics."""
        with self._lock:
            metrics = self._metrics.copy()
            metrics["current_queue_size"] = self.queue.size()
            return metrics


class LoadBalancer:
    """Load balances requests across multiple handlers."""
    
    def __init__(self, handlers: List[ConcurrentRequestHandler]):
        self.handlers = handlers
        self._current = 0
        self._lock = threading.RLock()
        self._weights: List[float] = [1.0] * len(handlers)
    
    def get_next_handler(self) -> ConcurrentRequestHandler:
        """Get next handler using weighted round-robin."""
        with self._lock:
            # Update weights based on load
            self._update_weights()
            
            # Weighted selection
            total_weight = sum(self._weights)
            if total_weight == 0:
                # All handlers overloaded, use simple round-robin
                handler = self.handlers[self._current % len(self.handlers)]
                self._current += 1
                return handler
            
            # Select based on weights
            target = (self._current % total_weight)
            cumulative = 0
            
            for i, weight in enumerate(self._weights):
                cumulative += weight
                if target < cumulative:
                    self._current += 1
                    return self.handlers[i]
            
            # Fallback
            self._current += 1
            return self.handlers[0]
    
    def _update_weights(self):
        """Update weights based on handler load."""
        for i, handler in enumerate(self.handlers):
            metrics = handler.get_metrics()
            
            # Calculate load score (lower is better)
            queue_size = metrics.get("current_queue_size", 0)
            active_workers = metrics.get("active_workers", 0)
            
            load_score = queue_size + (active_workers * 2)
            
            # Convert to weight (inverse of load)
            if load_score == 0:
                self._weights[i] = 10.0
            else:
                self._weights[i] = 100.0 / load_score
    
    async def submit_request(self, *args, **kwargs) -> str:
        """Submit request to least loaded handler."""
        handler = self.get_next_handler()
        return await handler.submit_request(*args, **kwargs)


# Global instance
_global_handler: Optional[ConcurrentRequestHandler] = None


def get_concurrent_handler(max_workers: int = 10) -> ConcurrentRequestHandler:
    """Get global concurrent handler."""
    global _global_handler
    if _global_handler is None:
        _global_handler = ConcurrentRequestHandler(max_workers=max_workers)
    return _global_handler


# Export main components
__all__ = [
    "Priority",
    "RequestStatus",
    "Request",
    "RequestQueue",
    "SessionManager",
    "RateLimiter",
    "ConcurrentRequestHandler",
    "LoadBalancer",
    "get_concurrent_handler"
]