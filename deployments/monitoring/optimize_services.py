#!/usr/bin/env python3
"""Service optimization improvements for CHATTA."""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def optimize_config():
    """Optimize service configuration for better performance."""
    
    config_optimizations = {
        "connection_pooling": {
            "max_connections": 10,
            "keepalive": True,
            "timeout": 30
        },
        "retry_strategy": {
            "max_retries": 3,
            "backoff_factor": 1.5,
            "max_backoff": 10
        },
        "cache_settings": {
            "voice_cache": True,
            "cache_ttl": 3600,
            "max_cache_size": 100
        },
        "performance": {
            "parallel_requests": True,
            "request_timeout": 5,
            "connection_timeout": 2
        }
    }
    
    # Write optimized config
    config_path = "voice_mode/config_optimized.json"
    with open(config_path, 'w') as f:
        json.dump(config_optimizations, f, indent=2)
    
    print(f"✅ Service optimizations saved to {config_path}")
    
    # Update environment variables for optimal performance
    env_updates = [
        "export CHATTA_CONNECTION_POOL_SIZE=10",
        "export CHATTA_REQUEST_TIMEOUT=5",
        "export CHATTA_CACHE_ENABLED=true",
        "export CHATTA_PARALLEL_REQUESTS=true",
        "export CHATTA_HEALTH_CHECK_INTERVAL=30"
    ]
    
    env_file = ".env.optimized"
    with open(env_file, 'w') as f:
        f.write("\n".join(env_updates))
    
    print(f"✅ Environment optimizations saved to {env_file}")
    
    return config_optimizations

def create_connection_pool_manager():
    """Create connection pool management for services."""
    
    pool_code = '''"""Connection pool management for optimized service access."""

import asyncio
from typing import Dict, Optional
import httpx
from collections import defaultdict

class ConnectionPoolManager:
    """Manages connection pools for different services."""
    
    def __init__(self, max_connections: int = 10):
        self.pools: Dict[str, httpx.AsyncClient] = {}
        self.max_connections = max_connections
        self._locks = defaultdict(asyncio.Lock)
    
    async def get_client(self, base_url: str) -> httpx.AsyncClient:
        """Get or create a pooled client for the given base URL."""
        async with self._locks[base_url]:
            if base_url not in self.pools:
                self.pools[base_url] = httpx.AsyncClient(
                    base_url=base_url,
                    timeout=httpx.Timeout(5.0, connect=2.0),
                    limits=httpx.Limits(
                        max_connections=self.max_connections,
                        max_keepalive_connections=5
                    ),
                    http2=True
                )
            return self.pools[base_url]
    
    async def close_all(self):
        """Close all connection pools."""
        for client in self.pools.values():
            await client.aclose()
        self.pools.clear()

# Global pool manager
pool_manager = ConnectionPoolManager()
'''
    
    with open("voice_mode/connection_pool.py", 'w') as f:
        f.write(pool_code)
    
    print("✅ Connection pool manager created")

def optimize_provider_selection():
    """Optimize provider selection logic."""
    
    selection_code = '''"""Optimized provider selection with caching and prediction."""

import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ProviderMetrics:
    """Track provider performance metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    total_latency: float = 0.0
    last_failure: Optional[float] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def avg_latency(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return self.total_latency / self.successful_requests

class OptimizedProviderSelector:
    """Select providers based on performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, ProviderMetrics] = {}
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._cache_ttl = 60  # 1 minute cache
    
    def record_success(self, provider: str, latency: float):
        """Record successful request."""
        if provider not in self.metrics:
            self.metrics[provider] = ProviderMetrics()
        
        metrics = self.metrics[provider]
        metrics.total_requests += 1
        metrics.successful_requests += 1
        metrics.total_latency += latency
    
    def record_failure(self, provider: str):
        """Record failed request."""
        if provider not in self.metrics:
            self.metrics[provider] = ProviderMetrics()
        
        metrics = self.metrics[provider]
        metrics.total_requests += 1
        metrics.last_failure = time.time()
    
    def select_best_provider(self, providers: list) -> str:
        """Select best provider based on metrics."""
        if not providers:
            raise ValueError("No providers available")
        
        # Check cache
        cache_key = ",".join(sorted(providers))
        if cache_key in self._cache:
            cached_provider, cached_time = self._cache[cache_key]
            if time.time() - cached_time < self._cache_ttl:
                return cached_provider
        
        # Score providers
        scores = {}
        for provider in providers:
            if provider not in self.metrics:
                # New provider gets neutral score
                scores[provider] = 0.5
            else:
                metrics = self.metrics[provider]
                
                # Calculate score based on success rate and latency
                success_weight = 0.7
                latency_weight = 0.3
                
                success_score = metrics.success_rate
                latency_score = 1.0 / (1.0 + metrics.avg_latency)
                
                # Penalize recent failures
                if metrics.last_failure:
                    time_since_failure = time.time() - metrics.last_failure
                    if time_since_failure < 30:  # Within 30 seconds
                        penalty = 0.5 * (1 - time_since_failure / 30)
                        success_score *= (1 - penalty)
                
                scores[provider] = (
                    success_weight * success_score +
                    latency_weight * latency_score
                )
        
        # Select best provider
        best_provider = max(scores, key=scores.get)
        
        # Cache result
        self._cache[cache_key] = (best_provider, time.time())
        
        return best_provider

# Global selector
provider_selector = OptimizedProviderSelector()
'''
    
    with open("voice_mode/optimized_selection.py", 'w') as f:
        f.write(selection_code)
    
    print("✅ Optimized provider selection created")

if __name__ == "__main__":
    print("Starting service optimization...")
    print("=" * 50)
    
    # Sprint 11-13: Optimize connections and pooling
    optimize_config()
    create_connection_pool_manager()
    
    # Sprint 14-15: Optimize provider selection
    optimize_provider_selection()
    
    print("\n" + "=" * 50)
    print("Service optimization complete!")
    print("\nNext steps:")
    print("1. Source .env.optimized for environment variables")
    print("2. Update imports to use connection pooling")
    print("3. Integrate optimized provider selection")