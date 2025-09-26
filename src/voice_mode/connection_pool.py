"""Connection pool management for optimized service access."""

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
