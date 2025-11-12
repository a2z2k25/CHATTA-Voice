# Add Output Profiles to Converse Tool

## Feature Request

Make the converse tool output configurable with different profiles to control what information is displayed.

## Current Behavior

Currently always shows full timing information:
```
Voice response: {text} | Timing: ttfa {n}s, gen {n}s, play {n}s, record {n}s, stt {n}s, total {n}s
```

## Proposed Profiles

### minimal
Just the voice response text, no timing or metadata:
```
Voice response: {text}
```

### timing (current default)
Full timing breakdown as currently shown:
```
Voice response: {text} | Timing: ttfa {n}s, gen {n}s, play {n}s, record {n}s, stt {n}s, total {n}s
```

### debug
Everything including additional diagnostic information:
```
Voice response: {text}
Provider: {provider} | Model: {model} | Voice: {voice}
Timing: ttfa {n}s, gen {n}s, play {n}s, record {n}s, stt {n}s, total {n}s
Audio: format={format}, sample_rate={rate}, duration={duration}s
```

## Implementation

1. Add `output_profile` parameter to converse tool
2. Default to "timing" for backward compatibility  
3. Match Claude Code's naming convention if they use "output_profile"
4. Allow LLM to specify profile when calling converse
5. Add environment variable configuration:
   - `VOICEMODE_OUTPUT_PROFILE` environment variable
   - Include in default config with sensible default (probably "timing")
   - Can be overridden in `~/.voicemode/voicemode.env`
   - Document available options in config comments

## Configuration

### Environment Variable
```bash
# Output profile for converse tool responses
# Options: minimal, timing, debug
# Default: timing
VOICEMODE_OUTPUT_PROFILE=timing
```

### Priority Order
1. Tool parameter (if specified)
2. Environment variable (if set)
3. Default value ("timing")

## Usage

```python
# Minimal output for production use
converse("Hello", output_profile="minimal")

# Timing for performance monitoring
converse("Hello", output_profile="timing")

# Debug for troubleshooting
converse("Hello", output_profile="debug")
```

## Benefits

- Cleaner output when timing isn't needed
- Better user experience with minimal profile
- Easier debugging with debug profile
- Consistency with Claude Code if using same parameter name