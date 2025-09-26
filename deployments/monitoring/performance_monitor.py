#!/usr/bin/env python3
"""Performance monitoring for CHATTA system."""

import time
import psutil
import asyncio
from typing import Dict, List
from dataclasses import dataclass, asdict
import json
from datetime import datetime

@dataclass
class PerformanceMetrics:
    """System performance metrics."""
    timestamp: str
    cpu_percent: float
    memory_mb: float
    latency_ms: float
    active_connections: int
    requests_per_second: float
    error_rate: float
    cache_hit_rate: float

class PerformanceMonitor:
    """Monitor and track system performance."""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.request_times: List[float] = []
        self.error_count = 0
        self.total_requests = 0
        self.cache_hits = 0
        self.cache_attempts = 0
        self.active_connections = 0
    
    def record_request(self, duration: float, success: bool = True):
        """Record a request."""
        self.request_times.append(duration)
        self.total_requests += 1
        if not success:
            self.error_count += 1
        
        # Keep only last 100 requests for RPS calculation
        if len(self.request_times) > 100:
            self.request_times.pop(0)
    
    def record_cache_attempt(self, hit: bool):
        """Record cache attempt."""
        self.cache_attempts += 1
        if hit:
            self.cache_hits += 1
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_mb = memory.used / (1024 * 1024)
        
        # Latency (average of recent requests)
        if self.request_times:
            latency_ms = sum(self.request_times) / len(self.request_times) * 1000
        else:
            latency_ms = 0
        
        # Requests per second (based on last 100 requests)
        if len(self.request_times) >= 2:
            time_span = time.time() - (time.time() - len(self.request_times))
            rps = len(self.request_times) / max(time_span, 1)
        else:
            rps = 0
        
        # Error rate
        error_rate = self.error_count / max(self.total_requests, 1)
        
        # Cache hit rate
        cache_hit_rate = self.cache_hits / max(self.cache_attempts, 1)
        
        return PerformanceMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            latency_ms=latency_ms,
            active_connections=self.active_connections,
            requests_per_second=rps,
            error_rate=error_rate,
            cache_hit_rate=cache_hit_rate
        )
    
    def save_metrics(self, filepath: str = "performance_metrics.json"):
        """Save metrics history to file."""
        metrics = self.get_current_metrics()
        self.metrics_history.append(metrics)
        
        # Keep only last 1000 metrics
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]
        
        with open(filepath, 'w') as f:
            json.dump(
                [asdict(m) for m in self.metrics_history],
                f,
                indent=2
            )
    
    def get_health_status(self) -> Dict[str, str]:
        """Get system health status."""
        metrics = self.get_current_metrics()
        
        health = {
            "status": "healthy",
            "cpu": "ok",
            "memory": "ok",
            "latency": "ok",
            "errors": "ok"
        }
        
        # Check thresholds
        if metrics.cpu_percent > 80:
            health["cpu"] = "critical"
            health["status"] = "degraded"
        elif metrics.cpu_percent > 60:
            health["cpu"] = "warning"
        
        if metrics.memory_mb > 500:
            health["memory"] = "critical"
            health["status"] = "degraded"
        elif metrics.memory_mb > 300:
            health["memory"] = "warning"
        
        if metrics.latency_ms > 3000:
            health["latency"] = "critical"
            health["status"] = "degraded"
        elif metrics.latency_ms > 2000:
            health["latency"] = "warning"
        
        if metrics.error_rate > 0.1:
            health["errors"] = "critical"
            health["status"] = "unhealthy"
        elif metrics.error_rate > 0.05:
            health["errors"] = "warning"
        
        return health

# Global monitor
monitor = PerformanceMonitor()

async def monitor_loop():
    """Background monitoring loop."""
    while True:
        monitor.save_metrics()
        await asyncio.sleep(10)  # Save metrics every 10 seconds

if __name__ == "__main__":
    print("Performance Monitor Test")
    print("=" * 50)
    
    # Simulate some activity
    monitor.record_request(0.5, True)
    monitor.record_request(0.7, True)
    monitor.record_request(1.2, False)
    monitor.record_cache_attempt(True)
    monitor.record_cache_attempt(False)
    monitor.record_cache_attempt(True)
    
    # Get metrics
    metrics = monitor.get_current_metrics()
    print(f"CPU: {metrics.cpu_percent:.1f}%")
    print(f"Memory: {metrics.memory_mb:.1f} MB")
    print(f"Latency: {metrics.latency_ms:.1f} ms")
    print(f"Error Rate: {metrics.error_rate:.1%}")
    print(f"Cache Hit Rate: {metrics.cache_hit_rate:.1%}")
    
    # Get health
    health = monitor.get_health_status()
    print(f"\nHealth Status: {health['status'].upper()}")
    for component, status in health.items():
        if component != "status":
            print(f"  {component}: {status}")
    
    print("\n✅ Performance monitoring ready!")