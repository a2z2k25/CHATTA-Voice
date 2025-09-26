#!/usr/bin/env python3
"""Integration of resource management with voice mode."""

import asyncio
import os
import tempfile
import threading
from typing import Dict, Any, Optional, List, Callable
import numpy as np
import logging
from pathlib import Path
import shutil

from .resource_manager import (
    ResourceType,
    ResourceManager,
    get_resource_manager,
    with_resource_tracking,
    with_async_resource_tracking
)

logger = logging.getLogger(__name__)


class AudioResourceManager:
    """Manage audio-specific resources."""
    
    def __init__(self):
        self.manager = get_resource_manager()
        self._audio_buffers: Dict[str, np.ndarray] = {}
        self._temp_files: List[Path] = []
        self._lock = threading.Lock()
        
        # Register cleanup handlers
        self.manager.register_shutdown_handler(self._cleanup_audio)
    
    @with_async_resource_tracking(ResourceType.AUDIO_BUFFER)
    async def create_audio_buffer(self, 
                                 size: int,
                                 sample_rate: int = 16000) -> np.ndarray:
        """Create managed audio buffer."""
        buffer = np.zeros(size, dtype=np.float32)
        
        # Register with size tracking
        buffer_id = self.manager.tracker.register_resource(
            buffer,
            ResourceType.AUDIO_BUFFER,
            size_bytes=buffer.nbytes,
            cleanup_callback=lambda: self._release_buffer(buffer)
        )
        
        with self._lock:
            self._audio_buffers[buffer_id] = buffer
        
        logger.debug(f"Created audio buffer: {buffer_id} ({buffer.nbytes} bytes)")
        return buffer
    
    def _release_buffer(self, buffer: np.ndarray):
        """Release audio buffer."""
        # Clear buffer memory
        buffer.fill(0)
        
        # Remove from tracking
        with self._lock:
            for buffer_id, buf in list(self._audio_buffers.items()):
                if buf is buffer:
                    del self._audio_buffers[buffer_id]
                    break
    
    async def save_audio_temp(self, 
                             audio_data: bytes,
                             format: str = "wav") -> Path:
        """Save audio to temporary file with automatic cleanup."""
        # Create temp file
        fd, filepath = tempfile.mkstemp(suffix=f".{format}", prefix="voice_")
        os.close(fd)
        
        filepath = Path(filepath)
        
        # Write audio data
        filepath.write_bytes(audio_data)
        
        # Register for cleanup
        self.manager.tracker.register_resource(
            filepath,
            ResourceType.TEMP_FILE,
            size_bytes=len(audio_data),
            cleanup_callback=lambda: self._cleanup_temp_file(filepath),
            metadata={"path": str(filepath)}
        )
        
        with self._lock:
            self._temp_files.append(filepath)
        
        logger.debug(f"Saved audio to temp file: {filepath}")
        return filepath
    
    def _cleanup_temp_file(self, filepath: Path):
        """Clean up temporary file."""
        try:
            if filepath.exists():
                filepath.unlink()
                logger.debug(f"Removed temp file: {filepath}")
        except Exception as e:
            logger.error(f"Failed to remove temp file {filepath}: {e}")
        
        with self._lock:
            if filepath in self._temp_files:
                self._temp_files.remove(filepath)
    
    def _cleanup_audio(self):
        """Clean up all audio resources."""
        # Clear buffers
        with self._lock:
            for buffer in self._audio_buffers.values():
                buffer.fill(0)
            self._audio_buffers.clear()
        
        # Remove temp files
        for filepath in self._temp_files[:]:
            self._cleanup_temp_file(filepath)
        
        logger.info("Audio resources cleaned up")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get audio resource metrics."""
        metrics = self.manager.tracker.get_metrics()
        
        audio_metrics = {
            "buffers": {
                "count": len(self._audio_buffers),
                "total_bytes": sum(b.nbytes for b in self._audio_buffers.values())
            },
            "temp_files": {
                "count": len(self._temp_files),
                "total_bytes": sum(
                    f.stat().st_size if f.exists() else 0 
                    for f in self._temp_files
                )
            }
        }
        
        return {
            "audio": audio_metrics,
            "system": metrics.get(ResourceType.AUDIO_BUFFER.value, {}),
            "temp_files": metrics.get(ResourceType.TEMP_FILE.value, {})
        }


class ConnectionPoolManager:
    """Manage connection pools for voice services."""
    
    def __init__(self, max_connections: int = 10):
        self.manager = get_resource_manager()
        self.max_connections = max_connections
        self._pools: Dict[str, List[Any]] = {}
        self._active: Dict[str, Set[Any]] = {}
        self._lock = threading.Lock()
        
        # Register cleanup
        self.manager.register_shutdown_handler(self._cleanup_pools)
    
    async def get_connection(self, 
                            service: str,
                            factory: Callable) -> Any:
        """Get connection from pool."""
        with self._lock:
            if service not in self._pools:
                self._pools[service] = []
                self._active[service] = []  # Use list instead of set for unhashable types
            
            # Try to get from pool
            if self._pools[service]:
                conn = self._pools[service].pop()
                self._active[service].append(conn)
                logger.debug(f"Reused connection for {service}")
                return conn
            
            # Check limit
            if len(self._active[service]) >= self.max_connections:
                raise RuntimeError(f"Connection limit reached for {service}")
        
        # Create new connection
        conn = await factory()
        
        # Register resource
        self.manager.tracker.register_resource(
            conn,
            ResourceType.NETWORK_CONNECTION,
            cleanup_callback=lambda: self._close_connection(conn, service),
            metadata={"service": service}
        )
        
        with self._lock:
            self._active[service].append(conn)
        
        logger.debug(f"Created new connection for {service}")
        return conn
    
    async def release_connection(self, conn: Any, service: str):
        """Release connection back to pool."""
        with self._lock:
            if service in self._active and conn in self._active[service]:
                self._active[service].remove(conn)
                
                # Return to pool if space available
                if len(self._pools[service]) < self.max_connections // 2:
                    self._pools[service].append(conn)
                    logger.debug(f"Returned connection to pool for {service}")
                else:
                    # Close excess connections
                    self._close_connection(conn, service)
    
    def _close_connection(self, conn: Any, service: str):
        """Close a connection."""
        try:
            if hasattr(conn, 'close'):
                if asyncio.iscoroutinefunction(conn.close):
                    asyncio.create_task(conn.close())
                else:
                    conn.close()
            logger.debug(f"Closed connection for {service}")
        except Exception as e:
            logger.error(f"Failed to close connection: {e}")
    
    def _cleanup_pools(self):
        """Clean up all connection pools."""
        with self._lock:
            for service in list(self._pools.keys()):
                # Close pooled connections
                for conn in self._pools[service]:
                    self._close_connection(conn, service)
                
                # Close active connections
                for conn in self._active[service]:
                    self._close_connection(conn, service)
            
            self._pools.clear()
            self._active.clear()
        
        logger.info("Connection pools cleaned up")


class CacheResourceManager:
    """Manage cache resources with automatic eviction."""
    
    def __init__(self, max_memory_mb: int = 100):
        self.manager = get_resource_manager()
        self.max_memory = max_memory_mb * 1024 * 1024
        self._caches: Dict[str, Dict[str, Any]] = {}
        self._cache_sizes: Dict[str, int] = {}
        self._lock = threading.Lock()
        
        # LRU tracking
        self._access_order: Dict[str, List[str]] = {}
        
        # Register cleanup
        self.manager.register_shutdown_handler(self._cleanup_caches)
    
    def create_cache(self, name: str, max_size_mb: int = 10) -> Dict[str, Any]:
        """Create a managed cache."""
        with self._lock:
            if name in self._caches:
                return self._caches[name]
            
            cache = {}
            self._caches[name] = cache
            self._cache_sizes[name] = 0
            self._access_order[name] = []
            
            # Register resource
            self.manager.tracker.register_resource(
                cache,
                ResourceType.MEMORY_CACHE,
                cleanup_callback=lambda: self._cleanup_cache(name),
                metadata={"name": name, "max_size": max_size_mb * 1024 * 1024}
            )
            
            logger.debug(f"Created cache: {name}")
            return cache
    
    def get(self, cache_name: str, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if cache_name not in self._caches:
                return None
            
            cache = self._caches[cache_name]
            if key not in cache:
                return None
            
            # Update LRU
            access_order = self._access_order[cache_name]
            if key in access_order:
                access_order.remove(key)
            access_order.append(key)
            
            return cache[key]
    
    def put(self, cache_name: str, key: str, value: Any, size_bytes: int = 0):
        """Put value in cache."""
        with self._lock:
            if cache_name not in self._caches:
                self.create_cache(cache_name)
            
            cache = self._caches[cache_name]
            access_order = self._access_order[cache_name]
            
            # Calculate size if not provided
            if size_bytes == 0:
                size_bytes = self._estimate_size(value)
            
            # Check if eviction needed
            current_size = self._cache_sizes[cache_name]
            # Find the resource ID for this cache
            cache_resource = None
            for res_id, res in self.manager.tracker._resources.items():
                if res.metadata.get("name") == cache_name:
                    cache_resource = res
                    break
            
            max_size = cache_resource.metadata.get("max_size", 10 * 1024 * 1024) if cache_resource else 10 * 1024 * 1024
            
            # Evict if necessary
            while current_size + size_bytes > max_size and access_order:
                evict_key = access_order.pop(0)
                if evict_key in cache:
                    evicted_size = self._estimate_size(cache[evict_key])
                    del cache[evict_key]
                    current_size -= evicted_size
                    logger.debug(f"Evicted {evict_key} from {cache_name}")
            
            # Add to cache
            cache[key] = value
            self._cache_sizes[cache_name] = current_size + size_bytes
            
            # Update LRU
            if key in access_order:
                access_order.remove(key)
            access_order.append(key)
    
    def _estimate_size(self, obj: Any) -> int:
        """Estimate object size in bytes."""
        import sys
        
        if isinstance(obj, (str, bytes)):
            return len(obj)
        elif isinstance(obj, np.ndarray):
            return obj.nbytes
        else:
            return sys.getsizeof(obj)
    
    def _cleanup_cache(self, name: str):
        """Clean up a cache."""
        with self._lock:
            if name in self._caches:
                self._caches[name].clear()
                del self._caches[name]
                del self._cache_sizes[name]
                del self._access_order[name]
                logger.debug(f"Cleaned up cache: {name}")
    
    def _cleanup_caches(self):
        """Clean up all caches."""
        with self._lock:
            for name in list(self._caches.keys()):
                self._cleanup_cache(name)
        logger.info("All caches cleaned up")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics."""
        with self._lock:
            return {
                name: {
                    "entries": len(cache),
                    "size_bytes": self._cache_sizes[name],
                    "hit_rate": 0  # Could track this
                }
                for name, cache in self._caches.items()
            }


class VoiceResourceManager:
    """Main voice mode resource manager."""
    
    def __init__(self):
        self.manager = get_resource_manager()
        self.audio = AudioResourceManager()
        self.connections = ConnectionPoolManager()
        self.cache = CacheResourceManager()
        
        # Temp directory management
        self.temp_dir = Path(tempfile.gettempdir()) / "voice_mode"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Register cleanup
        self.manager.register_shutdown_handler(self._cleanup_all)
    
    async def start(self):
        """Start resource management."""
        await self.manager.start()
        logger.info("Voice resource manager started")
    
    async def stop(self):
        """Stop resource management."""
        await self.manager.stop()
        logger.info("Voice resource manager stopped")
    
    def _cleanup_all(self):
        """Clean up all voice resources."""
        # Clean temp directory
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temp directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Failed to clean temp directory: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics."""
        return {
            "memory": self.manager.get_memory_snapshot(),
            "audio": self.audio.get_metrics(),
            "connections": {
                "pools": len(self.connections._pools),
                "active": sum(len(a) for a in self.connections._active.values())
            },
            "cache": self.cache.get_metrics(),
            "temp_dir": {
                "path": str(self.temp_dir),
                "exists": self.temp_dir.exists(),
                "size_bytes": sum(
                    f.stat().st_size 
                    for f in self.temp_dir.rglob("*") 
                    if f.is_file()
                ) if self.temp_dir.exists() else 0
            }
        }
    
    async def cleanup_session(self, session_id: str):
        """Clean up resources for a specific session."""
        logger.info(f"Cleaning up session: {session_id}")
        
        # Clean session-specific temp files
        session_temp = self.temp_dir / session_id
        if session_temp.exists():
            shutil.rmtree(session_temp)
        
        # Force cleanup of old resources
        await self.manager.cleaner.cleanup()
    
    def optimize(self):
        """Optimize resource usage."""
        self.manager.optimize_memory()
        
        # Clean old temp files
        import time
        current_time = time.time()
        
        if self.temp_dir.exists():
            for f in self.temp_dir.rglob("*"):
                if f.is_file():
                    age = current_time - f.stat().st_mtime
                    if age > 3600:  # 1 hour old
                        try:
                            f.unlink()
                            logger.debug(f"Removed old temp file: {f}")
                        except:
                            pass


def integrate_resource_management(voice_mode_instance):
    """Integrate resource management with voice mode."""
    
    # Create resource manager
    resource_manager = VoiceResourceManager()
    
    # Store original methods
    original_init = voice_mode_instance.__init__ if hasattr(voice_mode_instance, '__init__') else None
    original_process = voice_mode_instance.process_audio if hasattr(voice_mode_instance, 'process_audio') else None
    
    # Add resource management
    voice_mode_instance.resource_manager = resource_manager
    
    # Wrap methods with resource tracking
    async def managed_process_audio(audio_data: bytes) -> str:
        # Create managed audio buffer
        buffer = await resource_manager.audio.create_audio_buffer(len(audio_data))
        
        # Copy data to buffer
        audio_array = np.frombuffer(audio_data, dtype=np.float32)
        buffer[:len(audio_array)] = audio_array
        
        # Process with original method
        if original_process:
            result = await original_process(audio_data)
        else:
            result = "Processed"
        
        return result
    
    voice_mode_instance.process_audio = managed_process_audio
    
    # Add resource management methods
    voice_mode_instance.get_resource_metrics = resource_manager.get_metrics
    voice_mode_instance.cleanup_session = resource_manager.cleanup_session
    voice_mode_instance.optimize_resources = resource_manager.optimize
    
    # Add lifecycle management
    async def start_with_resources():
        await resource_manager.start()
    
    async def stop_with_resources():
        await resource_manager.stop()
    
    voice_mode_instance.start = start_with_resources
    voice_mode_instance.stop = stop_with_resources
    
    logger.info("Resource management integrated with voice mode")
    
    return voice_mode_instance


# Export main components
__all__ = [
    "AudioResourceManager",
    "ConnectionPoolManager",
    "CacheResourceManager",
    "VoiceResourceManager",
    "integrate_resource_management"
]