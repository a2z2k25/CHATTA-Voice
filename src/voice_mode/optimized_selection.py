"""Optimized provider selection with caching and prediction."""

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
