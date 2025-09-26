#!/usr/bin/env python3
"""Integration layer for latency reduction in voice mode."""

import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
import numpy as np
import hashlib
import logging

from .latency_reducer import (
    LatencyMode,
    LatencyReducer,
    PipelineOptimizer,
    PredictiveBuffer,
    StreamOptimizer,
    ConnectionPoolManager,
    get_latency_reducer,
    set_latency_mode
)

logger = logging.getLogger(__name__)


class AudioLatencyOptimizer:
    """Optimizes audio processing latency."""
    
    def __init__(self, mode: LatencyMode = LatencyMode.BALANCED):
        self.reducer = get_latency_reducer(mode)
        self.mode = mode
        
        # Setup audio pipelines
        self._setup_pipelines()
        
        # Setup predictive models
        self._setup_predictors()
        
        # Connection pools for services
        self._setup_connection_pools()
        
        # Metrics
        self._request_count = 0
        self._cache_hits = 0
        self._prediction_hits = 0
    
    def _setup_pipelines(self):
        """Setup processing pipelines."""
        # STT pipeline
        self.reducer.pipeline_optimizer.register_pipeline(
            "stt",
            [
                self._preprocess_audio,
                self._vad_detection,
                self._transcribe_audio,
                self._postprocess_transcript
            ]
        )
        
        # TTS pipeline
        self.reducer.pipeline_optimizer.register_pipeline(
            "tts",
            [
                self._preprocess_text,
                self._generate_speech,
                self._enhance_audio,
                self._compress_audio
            ]
        )
        
        # End-to-end pipeline
        self.reducer.pipeline_optimizer.register_pipeline(
            "end_to_end",
            [
                self._process_input,
                self._generate_response,
                self._synthesize_output
            ]
        )
    
    def _setup_predictors(self):
        """Setup predictive models."""
        # Predict likely next transcriptions
        async def predict_transcriptions():
            # Simple predictor based on recent history
            common_phrases = [
                {"key": "greeting", "value": "Hello"},
                {"key": "question", "value": "How can I help?"},
                {"key": "confirm", "value": "Yes"},
                {"key": "deny", "value": "No"}
            ]
            return common_phrases[self._request_count % len(common_phrases)]
        
        self.reducer.predictive_buffer.set_predictor(predict_transcriptions)
    
    def _setup_connection_pools(self):
        """Setup connection pools for services."""
        # OpenAI connection pool
        def create_openai_conn():
            return {"id": time.time(), "active": False}
        
        self.reducer.connection_pool.create_pool(
            "openai",
            create_openai_conn,
            size=5 if self.mode == LatencyMode.ULTRA_LOW else 3
        )
        
        # Whisper connection pool
        def create_whisper_conn():
            return {"id": time.time(), "active": False}
        
        self.reducer.connection_pool.create_pool(
            "whisper",
            create_whisper_conn,
            size=3 if self.mode == LatencyMode.ULTRA_LOW else 2
        )
    
    async def process_audio_with_optimization(self, audio_data: bytes) -> str:
        """Process audio with latency optimization."""
        metrics = self.reducer.track("stt")
        self._request_count += 1
        
        try:
            # Check predictive buffer
            audio_hash = hashlib.md5(audio_data).hexdigest()
            predicted = await self.reducer.predictive_buffer.get(audio_hash)
            if predicted:
                self._prediction_hits += 1
                return predicted
            
            # Check cache
            cached = self.reducer.pipeline_optimizer.get_cached(audio_hash)
            if cached:
                self._cache_hits += 1
                return cached
            
            # Process through optimized pipeline
            parallel = self.mode in [LatencyMode.ULTRA_LOW, LatencyMode.LOW]
            result = await self.reducer.pipeline_optimizer.execute_pipeline(
                "stt",
                audio_data,
                parallel=parallel
            )
            
            # Cache result
            self.reducer.pipeline_optimizer.cache_result(
                audio_hash,
                result,
                ttl=30
            )
            
            return result
            
        finally:
            self.reducer.complete(metrics)
    
    async def generate_audio_with_optimization(self, text: str) -> bytes:
        """Generate audio with latency optimization."""
        metrics = self.reducer.track("tts")
        
        try:
            # Check cache
            text_hash = hashlib.md5(text.encode()).hexdigest()
            cached = self.reducer.pipeline_optimizer.get_cached(text_hash)
            if cached:
                self._cache_hits += 1
                return cached
            
            # Get connection from pool
            conn = self.reducer.connection_pool.acquire("openai")
            if not conn:
                # Fallback to whisper
                conn = self.reducer.connection_pool.acquire("whisper")
            
            try:
                # Process through pipeline
                parallel = self.mode == LatencyMode.ULTRA_LOW
                result = await self.reducer.pipeline_optimizer.execute_pipeline(
                    "tts",
                    text,
                    parallel=parallel
                )
                
                # Cache result
                self.reducer.pipeline_optimizer.cache_result(
                    text_hash,
                    result,
                    ttl=60
                )
                
                return result
                
            finally:
                # Release connection
                if conn:
                    self.reducer.connection_pool.release(
                        "openai" if "openai" in str(conn) else "whisper",
                        conn
                    )
            
        finally:
            self.reducer.complete(metrics)
    
    async def stream_audio_with_optimization(self, audio_stream):
        """Stream audio with optimization."""
        results = []
        
        async def process_chunk(chunks):
            # Process accumulated chunks
            audio_data = b''.join(chunks)
            return await self.process_audio_with_optimization(audio_data)
        
        async def append_result(result):
            results.append(result)
        
        await self.reducer.stream_optimizer.stream_with_optimization(
            audio_stream,
            process_chunk,
            append_result
        )
        
        return results
    
    # Pipeline stages (simplified for testing)
    async def _preprocess_audio(self, audio_data):
        await asyncio.sleep(0.001)  # Simulate processing
        return audio_data
    
    async def _vad_detection(self, audio_data):
        await asyncio.sleep(0.002)  # Simulate VAD
        return audio_data
    
    async def _transcribe_audio(self, audio_data):
        await asyncio.sleep(0.01)  # Simulate transcription
        return "transcribed_text"
    
    async def _postprocess_transcript(self, text):
        await asyncio.sleep(0.001)  # Simulate postprocessing
        return text
    
    async def _preprocess_text(self, text):
        await asyncio.sleep(0.001)  # Simulate preprocessing
        return text
    
    async def _generate_speech(self, text):
        await asyncio.sleep(0.01)  # Simulate TTS
        return b"audio_data"
    
    async def _enhance_audio(self, audio):
        await asyncio.sleep(0.002)  # Simulate enhancement
        return audio
    
    async def _compress_audio(self, audio):
        await asyncio.sleep(0.001)  # Simulate compression
        return audio
    
    async def _process_input(self, data):
        await asyncio.sleep(0.005)
        return data
    
    async def _generate_response(self, data):
        await asyncio.sleep(0.02)
        return "response"
    
    async def _synthesize_output(self, data):
        await asyncio.sleep(0.01)
        return b"output_audio"
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics."""
        total_requests = max(1, self._request_count)
        return {
            "mode": self.mode.value,
            "request_count": self._request_count,
            "cache_hit_rate": self._cache_hits / total_requests,
            "prediction_hit_rate": self._prediction_hits / total_requests,
            "pipeline_cache_hit_rate": self.reducer.pipeline_optimizer.cache_hit_rate,
            "predictive_buffer_hit_rate": self.reducer.predictive_buffer.hit_rate,
            "latency_stats": self.reducer.tracker.get_all_stats(),
            "meeting_targets": self.reducer.tracker.is_meeting_targets()
        }


class VoiceLatencyOptimizer:
    """Voice-specific latency optimization."""
    
    def __init__(self, mode: LatencyMode = LatencyMode.BALANCED):
        self.audio_optimizer = AudioLatencyOptimizer(mode)
        self.reducer = get_latency_reducer(mode)
        
        # Voice-specific settings
        self._configure_for_voice()
        
        # Session management
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    def _configure_for_voice(self):
        """Configure for voice interaction."""
        if self.reducer.mode == LatencyMode.ULTRA_LOW:
            # Ultra-low latency voice settings
            self.chunk_duration_ms = 10
            self.lookahead_ms = 50
            self.buffer_ms = 100
        elif self.reducer.mode == LatencyMode.LOW:
            # Low latency voice settings
            self.chunk_duration_ms = 20
            self.lookahead_ms = 100
            self.buffer_ms = 200
        elif self.reducer.mode == LatencyMode.BALANCED:
            # Balanced voice settings
            self.chunk_duration_ms = 30
            self.lookahead_ms = 200
            self.buffer_ms = 500
        else:  # RELAXED
            # Relaxed voice settings
            self.chunk_duration_ms = 50
            self.lookahead_ms = 500
            self.buffer_ms = 1000
    
    def create_voice_session(self, session_id: str) -> Dict[str, Any]:
        """Create optimized voice session."""
        session = {
            "id": session_id,
            "created": time.time(),
            "chunk_duration_ms": self.chunk_duration_ms,
            "lookahead_ms": self.lookahead_ms,
            "buffer_ms": self.buffer_ms,
            "metrics": {
                "stt_count": 0,
                "tts_count": 0,
                "total_latency_ms": 0
            }
        }
        self.sessions[session_id] = session
        return session
    
    async def process_voice_chunk(self, session_id: str, audio_chunk: bytes) -> Optional[str]:
        """Process voice chunk with optimization."""
        if session_id not in self.sessions:
            self.create_voice_session(session_id)
        
        session = self.sessions[session_id]
        metrics = self.reducer.track("voice_chunk")
        
        try:
            # Process with optimization
            result = await self.audio_optimizer.process_audio_with_optimization(audio_chunk)
            
            # Update session metrics
            session["metrics"]["stt_count"] += 1
            session["metrics"]["total_latency_ms"] += metrics.duration_ms or 0
            
            return result
            
        finally:
            self.reducer.complete(metrics)
    
    async def generate_voice_response(self, session_id: str, text: str) -> bytes:
        """Generate voice response with optimization."""
        if session_id not in self.sessions:
            self.create_voice_session(session_id)
        
        session = self.sessions[session_id]
        metrics = self.reducer.track("voice_response")
        
        try:
            # Generate with optimization
            result = await self.audio_optimizer.generate_audio_with_optimization(text)
            
            # Update session metrics
            session["metrics"]["tts_count"] += 1
            session["metrics"]["total_latency_ms"] += metrics.duration_ms or 0
            
            return result
            
        finally:
            self.reducer.complete(metrics)
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get session statistics."""
        if session_id not in self.sessions:
            return {}
        
        session = self.sessions[session_id]
        total_operations = session["metrics"]["stt_count"] + session["metrics"]["tts_count"]
        
        return {
            "session_id": session_id,
            "duration_seconds": time.time() - session["created"],
            "stt_count": session["metrics"]["stt_count"],
            "tts_count": session["metrics"]["tts_count"],
            "avg_latency_ms": (
                session["metrics"]["total_latency_ms"] / max(1, total_operations)
            ),
            "configuration": {
                "chunk_duration_ms": session["chunk_duration_ms"],
                "lookahead_ms": session["lookahead_ms"],
                "buffer_ms": session["buffer_ms"]
            }
        }
    
    def close_session(self, session_id: str):
        """Close voice session."""
        if session_id in self.sessions:
            del self.sessions[session_id]


class RealtimeLatencyMonitor:
    """Real-time latency monitoring."""
    
    def __init__(self):
        self.reducer = get_latency_reducer(LatencyMode.BALANCED)
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._alerts: List[Dict[str, Any]] = []
    
    async def start_monitoring(self, interval_seconds: float = 1.0):
        """Start real-time monitoring."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(
            self._monitor_loop(interval_seconds)
        )
    
    async def stop_monitoring(self):
        """Stop monitoring."""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self, interval: float):
        """Monitoring loop."""
        while self._monitoring:
            try:
                # Check latency targets
                if not self.reducer.tracker.is_meeting_targets():
                    self._generate_alert("latency_exceeded")
                
                # Check cache performance
                if self.reducer.pipeline_optimizer.cache_hit_rate < 0.2:
                    self._generate_alert("low_cache_hit_rate")
                
                # Check prediction performance
                if self.reducer.predictive_buffer.hit_rate < 0.1:
                    self._generate_alert("low_prediction_rate")
                
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
    
    def _generate_alert(self, alert_type: str):
        """Generate performance alert."""
        alert = {
            "type": alert_type,
            "timestamp": time.time(),
            "stats": self.reducer.tracker.get_all_stats(),
            "suggestions": self.reducer.get_optimization_suggestions()
        }
        self._alerts.append(alert)
        
        # Keep only recent alerts
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-100:]
    
    def get_alerts(self, since_timestamp: Optional[float] = None) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        if since_timestamp:
            return [a for a in self._alerts if a["timestamp"] > since_timestamp]
        return self._alerts
    
    def get_monitoring_report(self) -> Dict[str, Any]:
        """Get monitoring report."""
        return {
            "monitoring": self._monitoring,
            "performance_report": self.reducer.get_performance_report(),
            "recent_alerts": self._alerts[-10:] if self._alerts else [],
            "alert_count": len(self._alerts)
        }


def integrate_latency_optimization(voice_mode_instance, mode: LatencyMode = LatencyMode.BALANCED):
    """Integrate latency optimization with voice mode."""
    
    # Create optimizers
    audio_optimizer = AudioLatencyOptimizer(mode)
    voice_optimizer = VoiceLatencyOptimizer(mode)
    monitor = RealtimeLatencyMonitor()
    
    # Store original methods
    original_process_audio = voice_mode_instance.process_audio
    original_generate_audio = voice_mode_instance.generate_audio
    
    # Wrap with optimization
    async def optimized_process_audio(audio_data: bytes) -> str:
        return await audio_optimizer.process_audio_with_optimization(audio_data)
    
    async def optimized_generate_audio(text: str) -> bytes:
        return await audio_optimizer.generate_audio_with_optimization(text)
    
    # Replace methods
    voice_mode_instance.process_audio = optimized_process_audio
    voice_mode_instance.generate_audio = optimized_generate_audio
    
    # Add new methods
    voice_mode_instance.audio_latency_optimizer = audio_optimizer
    voice_mode_instance.voice_latency_optimizer = voice_optimizer
    voice_mode_instance.latency_monitor = monitor
    
    # Utility methods
    def get_latency_stats():
        return {
            "audio_stats": audio_optimizer.get_optimization_stats(),
            "voice_sessions": {
                sid: voice_optimizer.get_session_stats(sid)
                for sid in voice_optimizer.sessions
            },
            "monitoring": monitor.get_monitoring_report()
        }
    
    def set_optimization_mode(new_mode: LatencyMode):
        set_latency_mode(new_mode)
        voice_mode_instance.audio_latency_optimizer = AudioLatencyOptimizer(new_mode)
        voice_mode_instance.voice_latency_optimizer = VoiceLatencyOptimizer(new_mode)
    
    voice_mode_instance.get_latency_stats = get_latency_stats
    voice_mode_instance.set_latency_mode = set_optimization_mode
    
    return voice_mode_instance


# Export main components
__all__ = [
    "AudioLatencyOptimizer",
    "VoiceLatencyOptimizer", 
    "RealtimeLatencyMonitor",
    "integrate_latency_optimization"
]