# TTS Streaming Architecture Enhancement

## Current State Analysis

### Existing Implementation
- **Location**: `voice_mode/streaming.py` and `voice_mode/core.py`
- **Current Flow**: 
  1. TTS request → OpenAI/Kokoro API
  2. Streaming response with `iter_bytes()`
  3. Direct PCM playback via sounddevice
  4. Metrics tracking (TTFA, generation time, playback time)

### Current Settings
```python
STREAMING_ENABLED = True (default)
STREAM_CHUNK_SIZE = 4096 bytes
STREAM_BUFFER_MS = 150ms (initial buffer)
STREAM_MAX_BUFFER = 2.0 seconds
```

### Performance Metrics
- **TTFA (Time to First Audio)**: ~0.3-0.5s currently
- **Total Generation Time**: Variable based on text length
- **Playback Start**: After first chunk received

## Target Architecture: 35-50% Early Playback

### Goal
Start audio playback when only 35-50% of the response is generated, achieving more natural conversation cadence.

### Implementation Strategy

#### 1. Progressive Buffering System
```python
class AdaptiveStreamBuffer:
    """Intelligent buffer that starts playback at optimal point"""
    
    def __init__(self):
        self.chunks = []
        self.total_expected_duration = None
        self.buffered_duration = 0
        self.playback_started = False
        self.target_percentage = 0.35  # Start at 35%
        
    def should_start_playback(self):
        """Determine if we have enough buffered to start"""
        if self.total_expected_duration:
            percentage = self.buffered_duration / self.total_expected_duration
            return percentage >= self.target_percentage
        # Fallback: start after minimum buffer time
        return self.buffered_duration >= 0.5  # 500ms minimum
```

#### 2. Text Analysis for Duration Estimation
```python
def estimate_speech_duration(text: str, model: str = "nova") -> float:
    """Estimate TTS duration based on text length and model"""
    # Average speaking rates (words per minute)
    WPM_RATES = {
        "nova": 180,      # Natural speed
        "alloy": 170,     # Slightly slower
        "echo": 160,      # More deliberate
        "shimmer": 175,   # Similar to nova
        "onyx": 165,      # Deeper, slower
        "fable": 170      # British accent
    }
    
    word_count = len(text.split())
    wpm = WPM_RATES.get(model, 170)
    duration_minutes = word_count / wpm
    return duration_minutes * 60  # Convert to seconds
```

#### 3. Enhanced Streaming Pipeline
```python
async def stream_tts_with_early_start(
    text: str,
    openai_client,
    request_params: dict,
    early_start_percentage: float = 0.35
) -> Tuple[bool, StreamMetrics]:
    """Stream TTS with intelligent early playback start"""
    
    # Estimate total duration
    estimated_duration = estimate_speech_duration(
        text, 
        request_params.get('voice', 'nova')
    )
    
    # Create adaptive buffer
    buffer = AdaptiveStreamBuffer()
    buffer.total_expected_duration = estimated_duration
    buffer.target_percentage = early_start_percentage
    
    # Start streaming
    async with openai_client.audio.speech.with_streaming_response.create(
        **request_params
    ) as response:
        
        async for chunk in response.iter_bytes(chunk_size=STREAM_CHUNK_SIZE):
            if chunk:
                # Add to buffer
                buffer.add_chunk(chunk)
                
                # Start playback if conditions met
                if not buffer.playback_started and buffer.should_start_playback():
                    buffer.start_playback()
                    logger.info(f"Starting playback at {buffer.get_percentage():.1%} buffered")
```

#### 4. Dynamic Chunk Size Adjustment
```python
def calculate_optimal_chunk_size(text_length: int, network_latency: float) -> int:
    """Calculate optimal chunk size based on text and network conditions"""
    
    # Base chunk sizes
    if text_length < 100:  # Short response
        base_chunk = 2048
    elif text_length < 500:  # Medium response
        base_chunk = 4096
    else:  # Long response
        base_chunk = 8192
    
    # Adjust for network conditions
    if network_latency < 50:  # Excellent
        return base_chunk
    elif network_latency < 100:  # Good
        return int(base_chunk * 0.75)
    else:  # Poor
        return int(base_chunk * 0.5)
```

#### 5. Playback Rate Compensation
```python
class PlaybackController:
    """Control playback rate to prevent buffer underrun"""
    
    def __init__(self, base_rate: float = 1.0):
        self.base_rate = base_rate
        self.current_rate = base_rate
        self.buffer_health = 1.0  # 0 = empty, 1 = full
        
    def adjust_rate(self, buffer_percentage: float):
        """Dynamically adjust playback rate based on buffer health"""
        if buffer_percentage < 0.2:  # Buffer running low
            self.current_rate = self.base_rate * 0.95  # Slow down slightly
        elif buffer_percentage > 0.8:  # Buffer healthy
            self.current_rate = self.base_rate * 1.02  # Speed up slightly
        else:
            self.current_rate = self.base_rate
        
        # Apply rate limit
        self.current_rate = max(0.9, min(1.1, self.current_rate))
```

## Configuration Updates

### New Environment Variables
```bash
# Early start configuration
export CHATTA_TTS_EARLY_START=true
export CHATTA_TTS_EARLY_START_PERCENTAGE=0.35  # Start at 35%
export CHATTA_TTS_MIN_BUFFER_MS=500            # Minimum 500ms buffer
export CHATTA_TTS_ADAPTIVE_RATE=true           # Enable rate adjustment

# Chunk size optimization
export CHATTA_TTS_DYNAMIC_CHUNKS=true
export CHATTA_TTS_MIN_CHUNK_SIZE=2048
export CHATTA_TTS_MAX_CHUNK_SIZE=8192
```

### Updated .mcp.json
```json
{
  "mcpServers": {
    "voicemode": {
      "env": {
        "CHATTA_TTS_EARLY_START": "true",
        "CHATTA_TTS_EARLY_START_PERCENTAGE": "0.35",
        "CHATTA_TTS_MIN_BUFFER_MS": "500",
        "CHATTA_TTS_ADAPTIVE_RATE": "true",
        "CHATTA_TTS_DYNAMIC_CHUNKS": "true"
      }
    }
  }
}
```

## Implementation Phases

### Phase 1: Duration Estimation (Current Sprint)
- [x] Analyze text for duration estimation
- [x] Create WPM-based calculation
- [x] Map voice models to speaking rates

### Phase 2: Adaptive Buffering
- [ ] Implement AdaptiveStreamBuffer class
- [ ] Add percentage-based trigger logic
- [ ] Integrate with existing streaming

### Phase 3: Dynamic Optimization
- [ ] Add chunk size calculation
- [ ] Implement playback rate control
- [ ] Add buffer health monitoring

### Phase 4: Testing & Tuning
- [ ] Test with various text lengths
- [ ] Measure actual vs estimated durations
- [ ] Fine-tune percentage thresholds
- [ ] Validate across different network conditions

## Expected Improvements

### Current Metrics
- TTFA: 300-500ms
- Full buffering before playback
- Fixed chunk sizes
- No rate adaptation

### Target Metrics
- TTFA: 150-250ms (50% reduction)
- Playback at 35% buffered
- Dynamic chunk sizing
- Adaptive playback rate
- Natural conversation flow

## Risk Mitigation

### Buffer Underrun Prevention
1. Monitor buffer health continuously
2. Adjust playback rate dynamically
3. Fallback to full buffering if network degrades
4. Pre-buffer minimum duration (500ms)

### Quality Preservation
1. Never drop below 90% playback rate
2. Never exceed 110% playback rate
3. Smooth rate transitions (no abrupt changes)
4. Maintain audio quality during rate adjustment

## Testing Strategy

### Unit Tests
```python
def test_duration_estimation():
    """Test speech duration calculation"""
    text = "Hello, this is a test message."
    duration = estimate_speech_duration(text, "nova")
    assert 1.5 <= duration <= 2.5  # Reasonable range

def test_early_start_trigger():
    """Test early playback triggering"""
    buffer = AdaptiveStreamBuffer()
    buffer.total_expected_duration = 10.0
    buffer.buffered_duration = 3.5
    assert buffer.should_start_playback() == True
```

### Integration Tests
1. Test with short responses (<5 seconds)
2. Test with medium responses (5-15 seconds)
3. Test with long responses (>15 seconds)
4. Test with poor network conditions
5. Test with interruptions

## Monitoring & Metrics

### Key Performance Indicators
- **Early Start Success Rate**: % of conversations starting at target
- **Buffer Underrun Rate**: % of playbacks with stuttering
- **Average TTFA**: Target <250ms
- **User Perceived Latency**: Survey feedback

### Logging
```python
logger.info(f"TTS Streaming Metrics:")
logger.info(f"  - Early start at: {percentage:.1%}")
logger.info(f"  - TTFA: {ttfa:.3f}s")
logger.info(f"  - Buffer health: {buffer_health:.1%}")
logger.info(f"  - Playback rate: {rate:.2f}x")
```

## Success Criteria
- ✅ 35-50% early playback achieved
- ✅ No audio stuttering or gaps
- ✅ Natural conversation cadence
- ✅ Reduced perceived latency
- ✅ Maintained audio quality