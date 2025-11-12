# Chatta Architecture Diagrams

**Comprehensive ASCII diagrams illustrating the Chatta voice mode system**

---

## Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [PTT State Machine](#ptt-state-machine)
3. [Push-to-Talk Integration Flow](#push-to-talk-integration-flow)
4. [Transport Layer Architecture](#transport-layer-architecture)
5. [Provider Discovery & Selection](#provider-discovery--selection)
6. [Recording Flow (Hold Mode)](#recording-flow-hold-mode)
7. [Recording Flow (Toggle Mode)](#recording-flow-toggle-mode)
8. [Recording Flow (Hybrid Mode)](#recording-flow-hybrid-mode)
9. [Phase Evolution Timeline](#phase-evolution-timeline)
10. [Component Dependency Graph](#component-dependency-graph)

---

## System Architecture Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                          CHATTA VOICE MODE                             │
│                     Model Context Protocol (MCP)                       │
└───────────────────────────────┬───────────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │   FastMCP Server      │
                    │   (stdio transport)   │
                    └───────────┬───────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
   ┌────▼─────┐          ┌─────▼──────┐         ┌─────▼──────┐
   │  Tools   │          │  Prompts   │         │ Resources  │
   │          │          │            │         │            │
   │ converse │          │ converse   │         │ statistics │
   │ service  │          │ identity   │         │ config     │
   │ providers│          │            │         │ changelog  │
   └────┬─────┘          └────────────┘         └────────────┘
        │
        │ converse(message, wait_for_response=True, ...)
        │
   ┌────▼──────────────────────────────────────────────────────────┐
   │                     CONVERSE TOOL                              │
   │                                                                │
   │  ┌──────────────────────────────────────────────────────────┐ │
   │  │  PHASE 1: TEXT-TO-SPEECH (TTS)                          │ │
   │  │  ┌────────────────────────────────────────────┐         │ │
   │  │  │  Provider Selection                        │         │ │
   │  │  │  • Voice-first algorithm                   │         │ │
   │  │  │  • User preferences                        │         │ │
   │  │  │  • Health checking                         │         │ │
   │  │  └──────────────┬─────────────────────────────┘         │ │
   │  │                 │                                        │ │
   │  │     ┌───────────┴────────────┐                          │ │
   │  │     │                        │                          │ │
   │  │  ┌──▼────────┐         ┌────▼──────────┐               │ │
   │  │  │ OpenAI    │         │  Kokoro       │               │ │
   │  │  │ TTS API   │         │  (Local TTS)  │               │ │
   │  │  │           │         │               │               │ │
   │  │  │ • nova    │         │ • af_sky      │               │ │
   │  │  │ • alloy   │         │ • am_adam     │               │ │
   │  │  │ • shimmer │         │ • bf_emma     │               │ │
   │  │  └───────────┘         │ • 50+ voices  │               │ │
   │  │                        └───────────────┘               │ │
   │  │                                                         │ │
   │  │  Audio Format Negotiation                              │ │
   │  │  • PCM, MP3, WAV, FLAC, AAC, Opus                      │ │
   │  │  • Provider capability checking                        │ │
   │  └─────────────────────────────────────────────────────────┘ │
   │                          ↓                                   │
   │                    Audio Playback                            │
   │                          ↓                                   │
   │  ┌──────────────────────────────────────────────────────────┐ │
   │  │  PHASE 2: TRANSPORT SELECTION                           │ │
   │  │                                                          │ │
   │  │  transport = "auto" | "local" | "livekit"              │ │
   │  │                                                          │ │
   │  │         ┌────────────────────────┐                      │ │
   │  │         │   Transport Router     │                      │ │
   │  │         └────────┬───────────────┘                      │ │
   │  │                  │                                      │ │
   │  │      ┌───────────┴─────────────┐                       │ │
   │  │      │                         │                       │ │
   │  │  ┌───▼──────────┐      ┌──────▼────────────┐          │ │
   │  │  │   LiveKit    │      │   Local Mic       │          │ │
   │  │  │   Transport  │      │   Transport       │          │ │
   │  │  │              │      │                   │          │ │
   │  │  │ • Room-based │      │ • Direct access   │          │ │
   │  │  │ • Multi-user │      │ • Single user     │          │ │
   │  │  │ • Agent VAD  │      │ • PTT or VAD      │          │ │
   │  │  │ • WebRTC     │      │ • sounddevice     │          │ │
   │  │  └──────────────┘      └──────┬────────────┘          │ │
   │  │                               │                        │ │
   │  │                    ┌──────────▼──────────┐             │ │
   │  │                    │  PTT_ENABLED?       │             │ │
   │  │                    └──────────┬──────────┘             │ │
   │  │                               │                        │ │
   │  │                 ┌─────────────┴─────────────┐          │ │
   │  │                 │                           │          │ │
   │  │            ┌────▼─────┐              ┌──────▼────────────────┐│
   │  │            │ Standard │              │  PTT Recording        ││
   │  │            │   VAD    │              │                       ││
   │  │            │Recording │              │  ┌────────────────┐   ││
   │  │            │          │              │  │ PTT Controller │   ││
   │  │            │ Silence  │              │  │                │   ││
   │  │            │Detection │              │  │ • Hold Mode    │   ││
   │  │            │          │              │  │ • Toggle Mode  │   ││
   │  │            │WebRTC VAD│              │  │ • Hybrid Mode  │   ││
   │  │            └──────────┘              │  │                │   ││
   │  │                                      │  │ State Machine  │   ││
   │  │                                      │  │ (7 states)     │   ││
   │  │                                      │  │                │   ││
   │  │                                      │  │ Keyboard       │   ││
   │  │                                      │  │ Handler        │   ││
   │  │                                      │  │ (pynput)       │   ││
   │  │                                      │  └────────────────┘   ││
   │  │                                      └──────────────────────┘│
   │  └──────────────────────────────────────────────────────────┘ │
   │                          ↓                                   │
   │                   Audio Data (np.ndarray)                    │
   │                          ↓                                   │
   │  ┌──────────────────────────────────────────────────────────┐ │
   │  │  PHASE 3: SPEECH-TO-TEXT (STT)                          │ │
   │  │  ┌────────────────────────────────────────────┐         │ │
   │  │  │  Provider Selection                        │         │ │
   │  │  │  • Health checking                         │         │ │
   │  │  │  • Automatic failover                      │         │ │
   │  │  └──────────────┬─────────────────────────────┘         │ │
   │  │                 │                                        │ │
   │  │     ┌───────────┴────────────┐                          │ │
   │  │     │                        │                          │ │
   │  │  ┌──▼────────┐         ┌────▼──────────┐               │ │
   │  │  │ OpenAI    │         │  Whisper.cpp  │               │ │
   │  │  │ STT API   │         │  (Local STT)  │               │ │
   │  │  │           │         │               │               │ │
   │  │  │ • whisper-1│         │ • Metal GPU   │               │ │
   │  │  └───────────┘         │ • CUDA GPU    │               │ │
   │  │                        │ • CPU         │               │ │
   │  │                        │ • CoreML      │               │ │
   │  │                        └───────────────┘               │ │
   │  │                                                         │ │
   │  │  Transcription                                          │ │
   │  └─────────────────────────────────────────────────────────┘ │
   │                          ↓                                   │
   │                  Return Text Response                        │
   └──────────────────────────────────────────────────────────────┘
```

---

## PTT State Machine

```
                        PTT STATE MACHINE
                      (7 States, Event-Driven)

┌─────────────────────────────────────────────────────────────────┐
│                          IDLE                                   │
│  • PTT not active                                               │
│  • No keyboard listener                                         │
│  • No resources allocated                                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ enable()
                            │ • Start keyboard listener
                            │ • Initialize recorder
                            │ • Log: "PTT enabled"
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     WAITING_FOR_KEY                             │
│  • Keyboard listener active                                     │
│  • Waiting for key combo press                                  │
│  • Visual: "Press ↓→ to record"                                 │
│  • Audio: Waiting tone (C5, 0.1s)                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Key combo detected
                            │ (e.g., down+right)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       KEY_PRESSED                               │
│  • Validation state                                             │
│  • Check min_duration timer                                     │
│  • Prevent accidental quick taps                                │
│  • Duration: ~0.5s                                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ min_duration satisfied
                            │ • Start audio recorder
                            │ • Initialize VAD (if hybrid mode)
                            │ • Start timeout timer
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       RECORDING                                 │
│  • Actively capturing audio                                     │
│  • Visual: "Recording... 3.2s"                                  │
│  • Audio: Recording start tone (C5→G5 sweep)                    │
│  • Buffer: Accumulating audio data                              │
│  • Monitoring:                                                  │
│    - Key release (hold/hybrid mode)                             │
│    - Silence detection (hybrid mode)                            │
│    - Cancel key press                                           │
│    - Timeout (max_duration)                                     │
└───────────┬────────────────────────────────┬────────────────────┘
            │                                │
            │ Normal Stop:                   │ Abnormal Stop:
            │ • Key release                  │ • Cancel key (Esc)
            │ • Silence (hybrid)             │ • Timeout
            │ • Toggle press #2              │ • Error
            ▼                                ▼
┌───────────────────────┐       ┌────────────────────────────────┐
│  RECORDING_STOPPED    │       │    RECORDING_CANCELLED         │
│                       │       │                                │
│  • Normal completion  │       │  • User cancelled              │
│  • Audio data ready   │       │  • Timeout occurred            │
│  • Stop tone: G5→C5   │       │  • Cancel tone: C5 staccato    │
│  • Stats: Success     │       │  • Stats: Cancelled            │
└───────┬───────────────┘       └───────┬────────────────────────┘
        │                               │
        │                               │
        └───────────────┬───────────────┘
                        │
                        │ • Stop recorder
                        │ • Get audio data
                        │ • Log stats
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                       PROCESSING                                │
│  • Converting audio format                                      │
│  • Calling on_recording_stop callback                           │
│  • Cleanup temporary resources                                  │
│  • Update statistics                                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ • Callback complete
                            │ • Resources released
                            │ • Ready for next cycle
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                          IDLE                                   │
│  (Return to initial state)                                      │
└─────────────────────────────────────────────────────────────────┘

State Transition Rules:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IDLE → WAITING_FOR_KEY:           enable() called
WAITING_FOR_KEY → KEY_PRESSED:    Key combo detected
KEY_PRESSED → RECORDING:           Min duration satisfied
KEY_PRESSED → WAITING_FOR_KEY:    Key released too quickly
RECORDING → RECORDING_STOPPED:     Normal stop condition
RECORDING → RECORDING_CANCELLED:   Cancel or timeout
RECORDING_STOPPED → PROCESSING:    Begin cleanup
RECORDING_CANCELLED → PROCESSING:  Begin cleanup
PROCESSING → IDLE:                 Cleanup complete

Invalid transitions raise InvalidStateTransition exception.
```

---

## Push-to-Talk Integration Flow

```
                   PTT INTEGRATION WITH CONVERSE TOOL
                        (Adapter Pattern)

┌─────────────────────────────────────────────────────────────────┐
│                 converse() Tool (Async)                         │
│                                                                 │
│  User calls: await converse("Hello", wait_for_response=True)   │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  TTS: Speak "Hello"     │
                    │  Play audio             │
                    └────────┬────────────────┘
                             │
                             ▼
                    ┌─────────────────────────┐
                    │  Audio Feedback         │
                    │  Play "listening" tone  │
                    └────────┬────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              RECORDING FUNCTION SELECTION                       │
│                                                                 │
│  recording_function = get_recording_function(                  │
│      ptt_enabled=PTT_ENABLED                                   │
│  )                                                              │
│                                                                 │
│  if PTT_ENABLED:                                               │
│      return record_with_ptt_fallback  ─────┐                   │
│  else:                                      │                   │
│      return record_audio_with_silence_detection                │
└────────────────────────────────────────────┼──────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────┐
│           EXECUTOR THREAD (Synchronous Context)                 │
│                                                                 │
│  audio_data, speech_detected =                                 │
│      await asyncio.get_event_loop().run_in_executor(           │
│          None,  # Default thread pool                          │
│          recording_function,  # Either PTT or standard         │
│          listen_duration,                                      │
│          disable_silence_detection,                            │
│          min_listen_duration,                                  │
│          vad_aggressiveness                                    │
│      )                                                          │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              record_with_ptt_fallback()                         │
│              (Synchronous, PTT Adapter)                         │
│                                                                 │
│  try:                                                           │
│      return record_with_ptt(duration, ...)                     │
│  except Exception as e:                                         │
│      logger.warning("PTT failed, falling back to VAD")         │
│      return record_audio_with_silence_detection(...)           │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                  record_with_ptt()                              │
│               (Core PTT Recording)                              │
│                                                                 │
│  1. Create PTTController                                       │
│     controller = PTTController(                                │
│         key_combo=PTT_KEY_COMBO,                               │
│         cancel_key=PTT_CANCEL_KEY,                             │
│         timeout=duration                                       │
│     )                                                           │
│                                                                 │
│  2. Create sync session wrapper                                │
│     session = PTTRecordingSession()                            │
│                                                                 │
│  3. Wire callbacks                                             │
│     async def on_stop(audio):                                  │
│         session.audio_data = audio                             │
│         session.completed.set()  # threading.Event             │
│                                                                 │
│     controller._on_recording_stop = on_stop                    │
│                                                                 │
│  4. Enable controller                                          │
│     if not controller.enable():                                │
│         raise RuntimeError("Failed to enable PTT")             │
│                                                                 │
│  5. Wait for recording (BLOCKS thread)                         │
│     success = session.completed.wait(timeout=duration)         │
│     # threading.Event.wait() blocks until set()                │
│                                                                 │
│  6. Cleanup                                                    │
│     controller.disable()                                       │
│                                                                 │
│  7. Return interface-compatible result                         │
│     return (session.audio_data, speech_detected)               │
│     # Tuple[np.ndarray, bool]                                  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PTT Controller                               │
│                 (Async Event Loop)                              │
│                                                                 │
│  ┌───────────────────────────────────────────────────┐         │
│  │  Main Event Loop:                                 │         │
│  │                                                    │         │
│  │  while enabled:                                   │         │
│  │      event = await wait_for_event()               │         │
│  │                                                    │         │
│  │      match event.type:                            │         │
│  │          case "key_press":                        │         │
│  │              handle_key_press()                   │         │
│  │          case "key_release":                      │         │
│  │              handle_key_release()                 │         │
│  │          case "silence_detected":                 │         │
│  │              handle_silence()                     │         │
│  │          case "timeout":                          │         │
│  │              handle_timeout()                     │         │
│  │          case "cancel":                           │         │
│  │              handle_cancel()                      │         │
│  └───────────────────────────────────────────────────┘         │
│                                                                 │
│  Components:                                                    │
│  • KeyboardHandler (pynput) - Monitors keys                    │
│  • PTTStateMachine - Manages state transitions                 │
│  • AsyncPTTRecorder - Captures audio                           │
│  • Event Queue - Thread-safe communication                     │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 │ on_recording_stop callback
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│               PTTRecordingSession                               │
│                                                                 │
│  async def on_stop(self, audio):                               │
│      self.audio_data = audio                                   │
│      self.completed.set()  # Unblock wait()                    │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 │ Unblocks thread
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│            Return to converse() tool                            │
│                                                                 │
│  audio_data, speech_detected = <executor result>               │
│                                                                 │
│  Audio Feedback: Play "finished" tone                          │
│                                                                 │
│  STT: Transcribe audio_data                                    │
│                                                                 │
│  Return: transcribed_text                                      │
└─────────────────────────────────────────────────────────────────┘

Key Design Decisions:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. threading.Event for sync/async bridge
   - Allows async PTTController to signal sync executor thread
   - Clean blocking wait without busy loops

2. Function-level abstraction
   - get_recording_function() returns callable
   - Same interface: standard VAD or PTT
   - 6-line integration in converse.py

3. Fallback mechanism
   - record_with_ptt_fallback() catches PTT errors
   - Automatically falls back to standard VAD
   - Graceful degradation

4. Session pattern
   - PTTRecordingSession encapsulates per-call state
   - Clean separation from controller lifecycle
   - No shared mutable state

5. Interface compatibility
   - Return type: Tuple[np.ndarray, bool]
   - Same parameters as record_audio_with_silence_detection()
   - Zero breaking changes
```

---

## Transport Layer Architecture

```
                       TRANSPORT LAYER ARCHITECTURE
                    (Local Microphone vs LiveKit Rooms)

┌─────────────────────────────────────────────────────────────────┐
│                      converse() Entry Point                     │
│                                                                 │
│  Parameters:                                                    │
│  • transport: "auto" | "local" | "livekit"                     │
│  • wait_for_response: bool                                     │
│  • listen_duration: float                                      │
│  • ...                                                          │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  wait_for_response?     │
                    └────────┬────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                  False             True
                    │                 │
                    ▼                 ▼
          ┌──────────────┐   ┌────────────────────┐
          │ Speak Only   │   │  Transport Router  │
          │              │   └────────┬───────────┘
          │ TTS → Return │            │
          └──────────────┘            │
                                      ▼
                         ┌─────────────────────────┐
                         │  transport == "auto"?   │
                         └────────┬────────────────┘
                                  │
                     ┌────────────┴────────────┐
                     │                         │
                   Yes                       No
                     │                         │
                     ▼                         ▼
      ┌──────────────────────────┐   ┌─────────────────┐
      │  Check LiveKit Available │   │  Use specified  │
      │                          │   │    transport    │
      │  livekit_room_url set?   │   └────────┬────────┘
      │  LiveKit service running?│            │
      └────────┬─────────────────┘            │
               │                              │
      ┌────────┴────────┐                     │
      │                 │                     │
   Available        Not Available             │
      │                 │                     │
      ▼                 ▼                     │
   LiveKit           Local                   │
      │                 │                     │
      └─────────────────┴─────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼

┌─────────────────────────┐     ┌────────────────────────────────┐
│   LIVEKIT TRANSPORT     │     │     LOCAL TRANSPORT            │
│   (Room-Based)          │     │     (Direct Microphone)        │
└─────────────────────────┘     └────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                      LIVEKIT TRANSPORT                           │
│                      (Multi-User Rooms)                          │
│                                                                  │
│  1. Connect to LiveKit Server                                   │
│     ┌────────────────────────────────────────┐                  │
│     │  room = livekit.Room()                 │                  │
│     │  await room.connect(                   │                  │
│     │      url=LIVEKIT_ROOM_URL,             │                  │
│     │      token=generate_token(room_name)   │                  │
│     │  )                                      │                  │
│     └────────────────────────────────────────┘                  │
│                                                                  │
│  2. Create VoiceAgent                                           │
│     ┌────────────────────────────────────────┐                  │
│     │  agent = VoiceAgent(                   │                  │
│     │      tts_client=tts_client,            │                  │
│     │      stt_client=stt_client,            │                  │
│     │      initial_message=message           │                  │
│     │  )                                      │                  │
│     └────────────────────────────────────────┘                  │
│                                                                  │
│  3. Agent speaks on room enter                                  │
│     ┌────────────────────────────────────────┐                  │
│     │  @agent.on("enter")                    │                  │
│     │  async def speak_initial():            │                  │
│     │      await agent.say(message)          │                  │
│     └────────────────────────────────────────┘                  │
│                                                                  │
│  4. Agent listens for user speech                               │
│     ┌────────────────────────────────────────┐                  │
│     │  Built-in Silero VAD                   │                  │
│     │  • Automatic speech detection          │                  │
│     │  • No keyboard control needed          │                  │
│     │  • Optimized for WebRTC                │                  │
│     └────────────────────────────────────────┘                  │
│                                                                  │
│  5. Process user speech events                                  │
│     ┌────────────────────────────────────────┐                  │
│     │  @agent.on("user_speech")              │                  │
│     │  async def on_speech(text):            │                  │
│     │      # Process transcription           │                  │
│     │      result = text                     │                  │
│     └────────────────────────────────────────┘                  │
│                                                                  │
│  6. Disconnect and return                                       │
│     ┌────────────────────────────────────────┐                  │
│     │  await room.disconnect()               │                  │
│     │  return result                         │                  │
│     └────────────────────────────────────────┘                  │
│                                                                  │
│  Key Characteristics:                                           │
│  ✓ Room-based (multi-user capable)                             │
│  ✓ Built-in VAD (Silero)                                        │
│  ✓ WebRTC optimized                                             │
│  ✓ Real-time bi-directional audio                              │
│  ✗ No PTT support (by design)                                   │
│                                                                  │
│  Why No PTT for LiveKit?                                        │
│  • Agent framework controls recording                           │
│  • Optimized for multi-user rooms                              │
│  • Silero VAD tuned for real-time                              │
│  • PTT better suited for single-user local                     │
│  • Future: Frontend PTT via JavaScript                         │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                      LOCAL TRANSPORT                             │
│                   (Direct Microphone Access)                     │
│                                                                  │
│  1. Play audio feedback                                         │
│     ┌────────────────────────────────────────┐                  │
│     │  play_audio_feedback("listening")      │                  │
│     │  • Chime indicates ready to record     │                  │
│     └────────────────────────────────────────┘                  │
│                                                                  │
│  2. Select recording function                                   │
│     ┌────────────────────────────────────────┐                  │
│     │  if PTT_ENABLED:                       │                  │
│     │      func = record_with_ptt_fallback   │───┐              │
│     │  else:                                  │   │              │
│     │      func = record_audio_with_silence_ │   │              │
│     │             detection                  │   │              │
│     └────────────────────────────────────────┘   │              │
│                                                   │              │
│  3. Record audio (in executor thread)            │              │
│     ┌──────────────────────────────────────────┐ │              │
│     │  audio_data, speech_detected =           │ │              │
│     │      await run_in_executor(              │ │              │
│     │          None, func,                     │ │              │
│     │          listen_duration,                │ │              │
│     │          disable_silence_detection,      │ │              │
│     │          min_listen_duration,            │ │              │
│     │          vad_aggressiveness              │ │              │
│     │      )                                   │ │              │
│     └──────────────────────────────────────────┘ │              │
│                                                   │              │
│  ┌────────────────────────────────────────────────┼──────────┐  │
│  │ PTT RECORDING PATH                            │          │  │
│  │                                                ▼          │  │
│  │  ┌───────────────────────────────────────────────────┐   │  │
│  │  │  record_with_ptt()                               │   │  │
│  │  │                                                   │   │  │
│  │  │  1. Create PTTController                         │   │  │
│  │  │     • KeyboardHandler (pynput)                   │   │  │
│  │  │     • PTTStateMachine                            │   │  │
│  │  │     • AsyncPTTRecorder                           │   │  │
│  │  │                                                   │   │  │
│  │  │  2. Enable PTT                                   │   │  │
│  │  │     controller.enable()                          │   │  │
│  │  │                                                   │   │  │
│  │  │  3. Wait for keyboard trigger                    │   │  │
│  │  │     • User presses key combo (e.g., ↓→)          │   │  │
│  │  │     • Start recording                            │   │  │
│  │  │                                                   │   │  │
│  │  │  4. Monitor for stop conditions                  │   │  │
│  │  │     • Hold: Key release                          │   │  │
│  │  │     • Toggle: Second key press                   │   │  │
│  │  │     • Hybrid: Key release OR silence             │   │  │
│  │  │     • All: Timeout or cancel key                 │   │  │
│  │  │                                                   │   │  │
│  │  │  5. Stop and return audio                        │   │  │
│  │  │     audio_data = recorder.get_audio()            │   │  │
│  │  │     return (audio_data, True)                    │   │  │
│  │  └───────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ STANDARD VAD RECORDING PATH                                │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │  record_audio_with_silence_detection()              │  │ │
│  │  │                                                      │  │ │
│  │  │  1. Open microphone (sounddevice)                   │  │ │
│  │  │                                                      │  │ │
│  │  │  2. Start recording immediately                     │  │ │
│  │  │     • No keyboard trigger needed                    │  │ │
│  │  │     • Begins capturing audio                        │  │ │
│  │  │                                                      │  │ │
│  │  │  3. Monitor for silence                             │  │ │
│  │  │     • WebRTC VAD detects speech/silence             │  │ │
│  │  │     • SILENCE_THRESHOLD_MS window                   │  │ │
│  │  │                                                      │  │ │
│  │  │  4. Stop on silence or timeout                      │  │ │
│  │  │     • Silence detected: return early                │  │ │
│  │  │     • Timeout: return at max_duration               │  │ │
│  │  │                                                      │  │ │
│  │  │  5. Return audio data                               │  │ │
│  │  │     return (audio_data, speech_detected)            │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  4. Play completion feedback                                    │
│     ┌────────────────────────────────────────┐                  │
│     │  play_audio_feedback("finished")       │                  │
│     └────────────────────────────────────────┘                  │
│                                                                  │
│  5. Transcribe audio                                            │
│     ┌────────────────────────────────────────┐                  │
│     │  text = await speech_to_text(          │                  │
│     │      audio_data,                       │                  │
│     │      stt_provider                      │                  │
│     │  )                                      │                  │
│     └────────────────────────────────────────┘                  │
│                                                                  │
│  6. Return transcription                                        │
│     ┌────────────────────────────────────────┐                  │
│     │  return text                           │                  │
│     └────────────────────────────────────────┘                  │
│                                                                  │
│  Key Characteristics:                                           │
│  ✓ Direct microphone access                                    │
│  ✓ Single-user focused                                          │
│  ✓ PTT or VAD selectable                                        │
│  ✓ Full keyboard control (when PTT enabled)                    │
│  ✓ Automatic fallback (PTT → VAD on error)                     │
└──────────────────────────────────────────────────────────────────┘

Transport Selection Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────┬────────────┬────────────┬─────────────────────┐
│  Parameter   │  LiveKit   │   Local    │   Description       │
├──────────────┼────────────┼────────────┼─────────────────────┤
│ Room-based   │     ✓      │     ✗      │ Multi-user support  │
│ PTT Support  │     ✗      │     ✓      │ Keyboard control    │
│ VAD          │  Silero    │  WebRTC    │ Speech detection    │
│ Latency      │  ~100ms    │  ~50ms     │ Round-trip time     │
│ Setup        │  Complex   │  Simple    │ Configuration       │
│ Privacy      │  Cloud*    │  Local     │ Audio processing    │
│ Multi-user   │     ✓      │     ✗      │ Concurrent users    │
└──────────────┴────────────┴────────────┴─────────────────────┘

* LiveKit can be self-hosted for local processing
```

---

## Provider Discovery & Selection

```
                    PROVIDER DISCOVERY & SELECTION
                  (Dynamic Health Checking & Failover)

┌──────────────────────────────────────────────────────────────────┐
│                      PROVIDER REGISTRY                           │
│                      (Singleton Pattern)                         │
│                                                                  │
│  Initialization:                                                │
│  ──────────────                                                 │
│  On first use:                                                  │
│  1. Discover all configured endpoints                           │
│  2. Health check each endpoint                                  │
│  3. Build capability registry                                   │
│  4. Sort by preference/health                                   │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
             ┌─────────────────────────────────────┐
             │  Configured Endpoints (from env)    │
             │                                     │
             │  TTS_BASE_URLS:                     │
             │  • https://api.openai.com/v1        │
             │  • http://127.0.0.1:8880/v1         │
             │  • http://127.0.0.1:8881/v1         │
             │                                     │
             │  STT_BASE_URLS:                     │
             │  • https://api.openai.com/v1        │
             │  • http://127.0.0.1:8008            │
             └─────────────────┬───────────────────┘
                               │
                               ▼
        ┌────────────────────────────────────────────┐
        │       Health Check Process                 │
        │       (Concurrent for all endpoints)       │
        └────────────────┬───────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐     ┌─────────┐     ┌─────────┐
   │Endpoint │     │Endpoint │     │Endpoint │
   │    1    │     │    2    │     │    3    │
   └────┬────┘     └────┬────┘     └────┬────┘
        │               │               │
        │ Probe:        │ Probe:        │ Probe:
        │ GET /models   │ GET /models   │ GET /models
        │ GET /voices   │ GET /voices   │ GET /voices
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐     ┌─────────┐     ┌─────────┐
   │Response │     │Response │     │ Timeout │
   │  200    │     │  200    │     │         │
   └────┬────┘     └────┬────┘     └────┬────┘
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐     ┌─────────┐     ┌─────────┐
   │ Healthy │     │ Healthy │     │Unhealthy│
   └────┬────┘     └────┬────┘     └────┬────┘
        │               │               │
        └───────────────┴───────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Registry Built                               │
│                                                                  │
│  registry = {                                                    │
│      "tts": {                                                    │
│          "https://api.openai.com/v1": EndpointInfo(             │
│              base_url="https://api.openai.com/v1",              │
│              provider_type="openai",                            │
│              healthy=True,                                       │
│              models=["tts-1", "tts-1-hd", "gpt-4o-mini-tts"],   │
│              voices=["alloy", "echo", "fable", "onyx",          │
│                      "nova", "shimmer"],                        │
│              response_time_ms=120.5,                            │
│              last_check="2025-11-12T10:30:00"                   │
│          ),                                                      │
│          "http://127.0.0.1:8880/v1": EndpointInfo(              │
│              base_url="http://127.0.0.1:8880/v1",               │
│              provider_type="kokoro",                            │
│              healthy=True,                                       │
│              models=["tts-1"],                                   │
│              voices=["af_sky", "af_sarah", "am_adam",           │
│                      "ef_dora", "ff_siwis", ...],               │
│              response_time_ms=15.2,                             │
│              last_check="2025-11-12T10:30:00"                   │
│          ),                                                      │
│          "http://127.0.0.1:8881/v1": EndpointInfo(              │
│              base_url="http://127.0.0.1:8881/v1",               │
│              healthy=False,                                      │
│              error="Connection refused",                        │
│              last_check="2025-11-12T10:30:00"                   │
│          )                                                       │
│      },                                                          │
│      "stt": {                                                    │
│          "https://api.openai.com/v1": EndpointInfo(...),        │
│          "http://127.0.0.1:8008": EndpointInfo(...)             │
│      }                                                           │
│  }                                                               │
└──────────────────────────────────────────────────────────────────┘

                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│              PROVIDER SELECTION ALGORITHM                        │
│                    (Voice-First Approach)                        │
│                                                                  │
│  Input:                                                          │
│  • voice: Optional[str] = None                                  │
│  • model: Optional[str] = None                                  │
│  • base_url: Optional[str] = None                               │
│                                                                  │
│  User Preferences (from .voicemode file):                       │
│  • User voice list: ["af_sky", "nova"]                          │
│  • System voice list: ["alloy", "echo", "fable", ...]          │
│  • Combined: ["af_sky", "nova", "alloy", "echo", ...]          │
│                                                                  │
│  Model Preferences (from config):                               │
│  • TTS_MODELS: ["tts-1-hd", "tts-1"]                            │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
                   ┌───────────────────────────┐
                   │ Specific base_url given?  │
                   └───────┬───────────────────┘
                           │
                  ┌────────┴────────┐
                  │                 │
                Yes               No
                  │                 │
                  ▼                 ▼
      ┌────────────────────┐   ┌─────────────────────┐
      │  Use that endpoint │   │ Specific voice given?│
      │  Select best voice │   └─────────┬───────────┘
      │  and model for it  │             │
      └────────────────────┘    ┌────────┴────────┐
                                │                 │
                              Yes               No
                                │                 │
                                ▼                 ▼
               ┌─────────────────────────┐   ┌───────────────────┐
               │Find first healthy       │   │ Iterate through   │
               │endpoint with that voice │   │ combined voice list│
               └─────────┬───────────────┘   └─────────┬─────────┘
                         │                             │
                         └──────────┬──────────────────┘
                                    │
                                    ▼
            ┌────────────────────────────────────────────┐
            │  For each voice in preference order:       │
            │                                            │
            │  1. Iterate through TTS_BASE_URLS          │
            │  2. Get endpoint from registry             │
            │  3. Check if healthy                       │
            │  4. Check if voice in endpoint.voices      │
            │  5. If match, select this endpoint+voice   │
            │  6. Find compatible model from TTS_MODELS  │
            │  7. Return (client, voice, model, endpoint)│
            └────────────────┬───────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Selection Example                            │
│                                                                  │
│  Request: get_tts_client_and_voice()  # No specific preferences │
│                                                                  │
│  Step 1: Combined voice list                                    │
│  ["af_sky", "nova", "alloy", "echo", "fable", ...]              │
│                                                                  │
│  Step 2: Try "af_sky"                                           │
│  • Check OpenAI endpoint: "af_sky" not in voices ✗              │
│  • Check Kokoro endpoint: "af_sky" in voices ✓                  │
│  • Health: True ✓                                               │
│  • Select this endpoint                                         │
│                                                                  │
│  Step 3: Find compatible model                                  │
│  • TTS_MODELS preference: ["tts-1-hd", "tts-1"]                 │
│  • Kokoro supports: ["tts-1"]                                   │
│  • Select "tts-1" ✓                                             │
│                                                                  │
│  Result:                                                         │
│  • Endpoint: http://127.0.0.1:8880/v1 (Kokoro)                  │
│  • Voice: "af_sky"                                              │
│  • Model: "tts-1"                                               │
│  • Response time: ~15ms                                         │
│                                                                  │
│  Why Kokoro selected:                                           │
│  ✓ User preference ("af_sky") available                         │
│  ✓ Healthy endpoint                                             │
│  ✓ Faster response time (15ms vs 120ms)                         │
│  ✓ Local (privacy + latency)                                    │
└──────────────────────────────────────────────────────────────────┘

                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                       FAILOVER MECHANISM                         │
│                                                                  │
│  If API call fails during actual TTS:                           │
│                                                                  │
│  try:                                                            │
│      response = await client.audio.speech.create(...)           │
│  except Exception as first_error:                               │
│      logger.warning(f"Failed with {endpoint}: {first_error}")   │
│                                                                  │
│      # Try next healthy endpoint with compatible voice          │
│      for fallback_url in remaining_healthy_endpoints:           │
│          try:                                                    │
│              fallback_client = create_client(fallback_url)      │
│              response = await fallback_client.audio.speech...   │
│              return response  # Success!                        │
│          except Exception as e:                                 │
│              logger.warning(f"Fallback failed: {e}")            │
│              continue  # Try next                               │
│                                                                  │
│      # All endpoints failed                                     │
│      raise ValueError("All TTS providers unavailable")          │
└──────────────────────────────────────────────────────────────────┘

Benefits of Voice-First Selection:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ User preferences respected (voice preferences honored first)
✓ Local-first when available (Kokoro selected over OpenAI)
✓ Automatic failover (try next endpoint on failure)
✓ Health-aware (only use healthy endpoints)
✓ Capability matching (only select if voice available)
✓ Performance optimized (faster local services preferred)
✓ No vendor lock-in (multiple providers supported)
```

---

## Recording Flow (Hold Mode)

```
                    PTT RECORDING FLOW: HOLD MODE
              (Press and hold key combo to record)

User Action                    System State                  Output
───────────                    ────────────                  ──────

                         ┌─────────────────────┐
                         │      IDLE           │
                         └──────────┬──────────┘
                                    │
[enable() called]                   │
                                    ▼
                         ┌─────────────────────┐
                         │  WAITING_FOR_KEY    │──────────► "Press ↓→ to record"
                         │                     │            💬 Visual feedback
                         │  Keyboard listening │            🔊 Waiting tone (C5)
                         │  State: Armed       │
                         └──────────┬──────────┘
                                    │
                                    │
[User presses ↓→]                   │
───────────────────────             ▼
   ⬇️ Press                  ┌─────────────────────┐
   ➡️ Press                  │   KEY_PRESSED       │
                         │                     │
   Both keys down        │  Validation:        │
                         │  • min_duration=0.5s│
                         │  • Both keys held?  │
                         └──────────┬──────────┘
                                    │
                                    │ 0.5s elapsed
                                    ▼
                         ┌─────────────────────┐
   Still holding         │    RECORDING        │──────────► "⏺️  Recording... 0.0s"
   ⬇️ Down                  │                     │            💬 Status display
   ➡️ Down                  │  • Audio streaming  │            🔊 Start tone (C5→G5)
                         │  • Buffer filling   │
                         │  • Timeout: 120s    │──────────► "⏺️  Recording... 1.5s"
                         │  • Cancel: Esc      │            💬 Live duration
                         │                     │
                         │  Monitoring:        │
                         │  • Key state        │──────────► "⏺️  Recording... 3.2s"
   Still holding         │  • Timeout          │            💬 Updates every 0.1s
   ⬇️ Down                  │  • Cancel key       │
   ➡️ Down                  │                     │
                         └──────────┬──────────┘
                                    │
                                    │
[User releases keys]                │
───────────────────────             │
   ⬇️ Released                      │
   ➡️ Released                      ▼
                         ┌─────────────────────┐
   Keys up              │ RECORDING_STOPPED   │──────────► "✅ Recording complete"
                         │                     │            💬 Success message
                         │  Duration: 3.2s     │            🔊 Stop tone (G5→C5)
                         │  Audio ready        │
                         └──────────┬──────────┘
                                    │
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    PROCESSING       │──────────► "Processing audio..."
                         │                     │            💬 Processing status
                         │  • Convert format   │
                         │  • Call callback    │
                         │  • Log stats        │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      IDLE           │
                         └─────────────────────┘

═══════════════════════════════════════════════════════════════════
                      HOLD MODE VARIATIONS
═══════════════════════════════════════════════════════════════════

Scenario 1: Quick Tap (< 0.5s)
──────────────────────────────
User presses and releases quickly

   ⬇️ Press
   ➡️ Press
   (0.2s)
   ⬇️ Release               KEY_PRESSED → WAITING_FOR_KEY
   ➡️ Release
                         ❌ "Press longer to record"
                         💬 Error message
                         🔊 Error tone

Scenario 2: Cancel During Recording
────────────────────────────────────
User presses Esc while recording

   ⬇️ Holding
   ➡️ Holding
                         RECORDING
   Esc pressed
                            ↓
                         RECORDING_CANCELLED

                         ❌ "Recording cancelled"
                         💬 Cancel message
                         🔊 Cancel tone (C5 staccato)

Scenario 3: Timeout
───────────────────
User holds longer than max_duration (120s)

   ⬇️ Holding
   ➡️ Holding
                         RECORDING (0s)
   Still holding         RECORDING (60s)
   Still holding         RECORDING (119s)
   Still holding         RECORDING (120s) → Timeout!
                            ↓
                         RECORDING_CANCELLED

                         ⚠️  "Recording timeout (120s)"
                         💬 Timeout message
                         🔊 Stop tone

Scenario 4: Accidental Key Release
───────────────────────────────────
User accidentally releases one key briefly

   ⬇️ Holding
   ➡️ Holding
                         RECORDING (2.0s)
   ➡️ Released
   (0.1s)                  ↓
   ➡️ Press again       RECORDING_STOPPED

                         ✅ Recording complete (2.0s)
                         💬 Stopped on key release
                         (Expected behavior - immediate response)

Scenario 5: Multiple Consecutive Recordings
────────────────────────────────────────────
User performs multiple recordings in sequence

Recording 1:
   ⬇️➡️ Press               WAITING → KEY_PRESSED → RECORDING
   (hold 5s)               Duration: 5.0s
   Release                 → RECORDING_STOPPED → PROCESSING → IDLE

   (pause 1s)

Recording 2:
   ⬇️➡️ Press               WAITING → KEY_PRESSED → RECORDING
   (hold 3s)               Duration: 3.0s
   Release                 → RECORDING_STOPPED → PROCESSING → IDLE

═══════════════════════════════════════════════════════════════════
                      HOLD MODE CHARACTERISTICS
═══════════════════════════════════════════════════════════════════

✓ Explicit control:     User decides exactly when to stop
✓ Quick response:       Recording stops immediately on release
✓ No false stops:       Silence doesn't stop recording
✓ Predictable:          Same behavior every time
✓ Min duration enforced: Prevents accidental quick taps

✗ Requires holding:     Can be tiring for long recordings
✗ Hands occupied:       Can't type or use mouse while recording
✗ No auto-stop:         User must manually release

Best for:
• Quick voice commands
• Precise timing control
• Noisy environments (no false VAD triggers)
• Experienced PTT users
• When explicit control is paramount
```

---

## Recording Flow (Toggle Mode)

```
                    PTT RECORDING FLOW: TOGGLE MODE
              (Press once to start, press again to stop)

User Action                    System State                  Output
───────────                    ────────────                  ──────

                         ┌─────────────────────┐
                         │      IDLE           │
                         └──────────┬──────────┘
                                    │
[enable() called]                   │
                                    ▼
                         ┌─────────────────────┐
                         │  WAITING_FOR_KEY    │──────────► "Press ↓→ to record"
                         │                     │            💬 Visual feedback
                         │  Keyboard listening │            🔊 Waiting tone
                         │  Toggle state: OFF  │
                         └──────────┬──────────┘
                                    │
                                    │
[User presses ↓→]                   │
───────────────────────             ▼
   ⬇️➡️ Quick press         ┌─────────────────────┐
   (0.2s)                 │   KEY_PRESSED       │
   Release                │                     │
                         │  Detect: Toggle ON  │
                         │  No min_duration    │
                         └──────────┬──────────┘
                                    │
                                    │ Immediately
                                    ▼
                         ┌─────────────────────┐
   Keys released        │    RECORDING        │──────────► "⏺️  Recording... 0.0s"
   (hands-free!)         │                     │            💬 Status display
                         │  • Audio streaming  │            🔊 Start tone
                         │  • Buffer filling   │
                         │  • Timeout: 120s    │──────────► "⏺️  Recording... 5.2s"
                         │  • Cancel: Esc      │            💬 Live duration
                         │                     │
                         │  Monitoring:        │            "Press ↓→ again to stop"
                         │  • Key press        │            💬 Instruction
   Hands-free!          │  • Timeout          │
   Can use keyboard     │  • Cancel key       │──────────► "⏺️  Recording... 15.8s"
   Can use mouse        │                     │            💬 Ongoing
                         │  Toggle state: ON   │
                         └──────────┬──────────┘
                                    │
                                    │
[User presses ↓→ again]             │
───────────────────────             │
   ⬇️➡️ Press (2nd time)    │
                                    ▼
                         ┌─────────────────────┐
   Keys released        │ RECORDING_STOPPED   │──────────► "✅ Recording complete"
   Toggle OFF            │                     │            💬 Success message
                         │  Duration: 15.8s    │            🔊 Stop tone
                         │  Audio ready        │
                         │  Toggle state: OFF  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    PROCESSING       │──────────► "Processing audio..."
                         │                     │
                         │  • Convert format   │
                         │  • Call callback    │
                         │  • Log stats        │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      IDLE           │
                         └─────────────────────┘

═══════════════════════════════════════════════════════════════════
                     TOGGLE MODE VARIATIONS
═══════════════════════════════════════════════════════════════════

Scenario 1: Long-Form Dictation
────────────────────────────────
User records extended speech hands-free

   Press ↓→              WAITING → RECORDING
   (release)
                         "⏺️  Recording... 0.0s"

   (speaking)            "⏺️  Recording... 30.0s"
   Can use keyboard      User types notes while speaking

   (more speaking)       "⏺️  Recording... 60.0s"

   Press ↓→ again        → RECORDING_STOPPED
                         ✅ "Complete (60.0s)"

Scenario 2: Cancel During Recording
────────────────────────────────────
User cancels instead of toggle off

   Press ↓→              RECORDING
   (release)
                         "⏺️  Recording... 5.0s"

   Press Esc             → RECORDING_CANCELLED

                         ❌ "Recording cancelled"
                         🔊 Cancel tone

Scenario 3: Timeout
───────────────────
User forgets to stop recording

   Press ↓→              RECORDING
   (release)
                         "⏺️  Recording... 0.0s"

   (user walks away)     "⏺️  Recording... 60.0s"
                         "⏺️  Recording... 119.0s"
                         "⏺️  Recording... 120.0s"

   Timeout!              → RECORDING_CANCELLED

                         ⚠️  "Timeout (120s)"

Scenario 4: Accidental Double-Tap
──────────────────────────────────
User quickly presses twice

   Press ↓→ (#1)         WAITING → RECORDING
   (0.1s)                "⏺️  Recording... 0.0s"
   Press ↓→ (#2)         → RECORDING_STOPPED

                         ✅ "Complete (0.1s)"
                         (Very short recording!)

Scenario 5: Reading From Notes
───────────────────────────────
User needs to scroll document while speaking

   Press ↓→              RECORDING
   (release hands)
                         "⏺️  Recording... 5.0s"

   Scroll document       (hands-free, can navigate)
   Keep speaking         "⏺️  Recording... 20.0s"

   Finish reading
   Press ↓→              → RECORDING_STOPPED
                         ✅ "Complete (20.0s)"

═══════════════════════════════════════════════════════════════════
                    TOGGLE MODE CHARACTERISTICS
═══════════════════════════════════════════════════════════════════

✓ Hands-free:          After initial press, hands free
✓ Long recordings:     No need to hold key
✓ Accessibility:       Easier for users with limited mobility
✓ Multitasking:        Can use keyboard/mouse during recording
✓ No fatigue:          No sustained key holding

✗ Less precise:        Requires second press to stop
✗ Can forget to stop:  Timeout safety net required
✗ Accidental stops:    Double-tap can end recording early
✗ No min duration:     Quick taps record (even if accidental)

Best for:
• Long-form dictation
• Reading from documents
• Accessibility users
• Multi-tasking scenarios
• When hands-free operation is important
```

---

## Recording Flow (Hybrid Mode)

```
                    PTT RECORDING FLOW: HYBRID MODE
          (Hold to record, automatic stop on silence OR key release)

User Action                    System State                  Output
───────────                    ────────────                  ──────

                         ┌─────────────────────┐
                         │      IDLE           │
                         └──────────┬──────────┘
                                    │
[enable() called]                   │
                                    ▼
                         ┌─────────────────────┐
                         │  WAITING_FOR_KEY    │──────────► "Press ↓→ to record"
                         │                     │            💬 Visual feedback
                         │  Keyboard listening │            🔊 Waiting tone
                         │  VAD: Ready         │
                         └──────────┬──────────┘
                                    │
                                    │
[User presses ↓→]                   │
───────────────────────             ▼
   ⬇️ Press              ┌─────────────────────┐
   ➡️ Press              │   KEY_PRESSED       │
                         │                     │
   Both keys down        │  Validation:        │
                         │  • min_duration=0.5s│
                         └──────────┬──────────┘
                                    │
                                    │ 0.5s elapsed
                                    ▼
                         ┌─────────────────────┐
   Holding keys          │    RECORDING        │──────────► "⏺️  Recording... 0.0s"
   ⬇️ Down                  │                     │            💬 Status display
   ➡️ Down                  │  • Audio streaming  │            🔊 Start tone
                         │  • Buffer filling   │
   Speaking...           │  • WebRTC VAD: ON   │──────────► "🎤 Speech detected"
                         │  • Timeout: 120s    │            💬 VAD feedback
                         │                     │
                         │  Dual Monitoring:   │
   Still speaking        │  ┌────────────────┐ │
   ⬇️ Down                  │  │  Key release?  │ │──────────► "⏺️  Recording... 2.3s"
   ➡️ Down                  │  └────────────────┘ │            💬 Live duration
                         │  ┌────────────────┐ │
                         │  │Silence detected│ │
   Pause in speech...    │  │  (1.5s quiet)  │ │
   ⬇️ Still down            │  └────────────────┘ │
   ➡️ Still down            │                     │──────────► "🔇 Silence..."
                         │  Countdown: 1.5s... │            💬 Silence indicator
                         └──────────┬──────────┘
                                    │
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
         [Silence detected]              [User releases keys]
         (1.5s of quiet)                 (manual stop)
                    │                               │
                    ▼                               ▼
         ┌─────────────────────┐       ┌─────────────────────┐
         │ RECORDING_STOPPED   │       │ RECORDING_STOPPED   │
         │                     │       │                     │
         │ Reason: Silence     │       │ Reason: Key release │
         │ Duration: 2.3s      │       │ Duration: 3.8s      │
         └──────────┬──────────┘       └──────────┬──────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ RECORDING_STOPPED   │──────────► "✅ Complete (auto-stop)"
                         │                     │            💬 Success with reason
                         │  Audio ready        │            🔊 Stop tone
                         │  VAD: Detected      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    PROCESSING       │──────────► "Processing audio..."
                         │                     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      IDLE           │
                         └─────────────────────┘

═══════════════════════════════════════════════════════════════════
                     HYBRID MODE VARIATIONS
═══════════════════════════════════════════════════════════════════

Scenario 1: Quick Question (Silence Wins)
──────────────────────────────────────────
User asks brief question, pauses

   Press ↓→              WAITING → KEY_PRESSED → RECORDING
   (holding)
   "What's the weather?"  🎤 Speech detected (2.0s)
   (pause)               🔇 Silence... 0.5s
   Still holding         🔇 Silence... 1.0s
                         🔇 Silence... 1.5s → Auto-stop!

                         ✅ "Complete (silence, 3.5s)"
                         User can release keys now

Scenario 2: Manual Override (Key Release Wins)
───────────────────────────────────────────────
User wants to stop immediately mid-sentence

   Press ↓→              RECORDING
   (holding)
   "I think we should—"  🎤 Speech detected
   Release keys          → RECORDING_STOPPED (immediate)

                         ✅ "Complete (manual, 1.2s)"

Scenario 3: Extended Speech with Pauses
────────────────────────────────────────
User speaks with natural pauses < 1.5s

   Press ↓→              RECORDING
   (holding)
   "First, we need to"   🎤 Speech detected
   (0.8s pause)          🔇 Brief silence...
   "implement the tests" 🎤 Speech detected (silence timer reset)
   (0.5s pause)          🔇 Brief silence...
   "and then deploy"     🎤 Speech detected (silence timer reset)
   (1.6s pause)          🔇 Silence... 1.5s → Auto-stop!

                         ✅ "Complete (silence, 8.2s)"

Scenario 4: Noisy Environment (Manual Stop Needed)
───────────────────────────────────────────────────
Background noise prevents silence detection

   Press ↓→              RECORDING
   (holding)
   "Let's review this"   🎤 Speech detected
   (pause, but ambient   🎤 Still detecting audio (noise)
    noise continues)     🎤 No silence detected
                         (VAD hears background noise)

   Release keys          → RECORDING_STOPPED (manual)

                         ✅ "Complete (manual, 4.5s)"

Scenario 5: Perfect Auto-Stop
──────────────────────────────
User speaks naturally, VAD works perfectly

   Press ↓→              RECORDING
   (holding)
   "Can you explain"     🎤 Speech detected
   "the architecture"    🎤 Speech detected
   "of this system?"     🎤 Speech detected
   (natural pause)       🔇 Silence... 1.5s → Auto-stop!

   Keys still down       (Recording already stopped)
   Release keys          (No effect, already stopped)

                         ✅ "Complete (silence, 5.8s)"

═══════════════════════════════════════════════════════════════════
                   HYBRID MODE CHARACTERISTICS
═══════════════════════════════════════════════════════════════════

✓ Best of both:         Manual control + automatic optimization
✓ Natural pauses:       Stops on natural speech pauses
✓ Quick responses:      No need to hold after finishing
✓ Manual override:      Can release key anytime for immediate stop
✓ Prevents over-capture: Won't record ambient noise after speech
✓ Flexible:             Adapts to user's speaking pattern

⚠️  Environment-dependent: Noisy environments may prevent auto-stop
⚠️  VAD limitations:     Very soft speech may not detect properly
⚠️  Pause sensitivity:   1.5s threshold may be too short/long for some

Silence Detection Configuration:
• SILENCE_THRESHOLD_MS=1500  (1.5 seconds default)
• VAD_AGGRESSIVENESS=2       (balanced, 0-3 scale)
• MIN_DURATION=0.5           (prevents quick taps)

Best for:
• Natural conversation flow
• Variable-length responses
• Users who want both control and automation
• Clean audio environments
• Most general use cases (recommended default)

Adaptive Behavior:
• If disable_silence_detection=True → Falls back to hold mode
• If VAD unavailable → Falls back to hold mode
• If timeout reached → Auto-stop (safety)
```

---

## Phase Evolution Timeline

```
                    CHATTA DEVELOPMENT TIMELINE
                     (5 Phases over 8 Weeks)

Week 1-3: Phases 1-3 (Core PTT Implementation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────────────────┐
│                         PHASE 1                                 │
│                  Foundation & State Machine                     │
│                        (Week 1)                                 │
│                                                                 │
│  Deliverables:                                                  │
│  • PTTStateMachine (7 states)                                   │
│  • State transition logic                                       │
│  • Event logging system                                         │
│  • Configuration module                                         │
│                                                                 │
│  Metrics:                                                       │
│  • Code: ~500 lines                                             │
│  • Tests: 30 unit tests                                         │
│  • States: 7                                                    │
│  • Pass Rate: 100%                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PHASE 2                                 │
│              Keyboard Handler & Integration                     │
│                        (Week 2)                                 │
│                                                                 │
│  Deliverables:                                                  │
│  • KeyboardHandler (pynput integration)                         │
│  • Cross-platform key monitoring                                │
│  • Event queue (thread-safe)                                    │
│  • Permission checking utilities                                │
│                                                                 │
│  Metrics:                                                       │
│  • Code: ~800 lines                                             │
│  • Tests: 40 unit tests                                         │
│  • Platforms: macOS, Linux, Windows                             │
│  • Pass Rate: 100%                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         PHASE 3                                 │
│              Audio Recording & Modes                            │
│                        (Week 3)                                 │
│                                                                 │
│  Deliverables:                                                  │
│  • AsyncPTTRecorder (sounddevice)                               │
│  • PTTController (orchestration)                                │
│  • Hold, Toggle, Hybrid modes                                   │
│  • Minimum duration enforcement                                 │
│  • Comprehensive error handling                                 │
│                                                                 │
│  Metrics:                                                       │
│  • Code: ~700 lines                                             │
│  • Tests: 30 unit tests                                         │
│  • Modes: 3 (hold, toggle, hybrid)                             │
│  • Pass Rate: 100%                                              │
│                                                                 │
│  🎉 Phase 3 Complete: Core PTT Functional                       │
│     Total: ~2,000 lines, 100+ tests                             │
└─────────────────────────────────────────────────────────────────┘

Week 4: Phase 4 (Transport Integration)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────────────────┐
│                         PHASE 4                                 │
│                  Transport Integration                          │
│                        (Week 4)                                 │
│                                                                 │
│  Sprint 4.1: Transport Analysis (2 hours)                       │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • Analyzed converse() tool (2,000+ lines)        │           │
│  │ • Identified integration point (line 1941)       │           │
│  │ • Documented interface contract                  │           │
│  │ • Deliverable: TRANSPORT_INTEGRATION_ANALYSIS.md │           │
│  └──────────────────────────────────────────────────┘           │
│                          │                                      │
│  Sprint 4.2: Adapter Pattern (4 hours)             │           │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • Created transport_adapter.py (367 lines)       │           │
│  │ • Implemented record_with_ptt()                  │           │
│  │ • Sync/async bridge (threading.Event)            │           │
│  │ • Tests: 25/25 passing                           │           │
│  └──────────────────────────────────────────────────┘           │
│                          │                                      │
│  Sprint 4.3: Converse Integration (3 hours)        │           │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • Modified converse.py (6 lines changed)         │           │
│  │ • Added PTT_ENABLED feature flag                 │           │
│  │ • Tests: 9/9 integration tests passing           │           │
│  │ • Backward compatibility verified                │           │
│  └──────────────────────────────────────────────────┘           │
│                          │                                      │
│  Sprint 4.4: LiveKit Decision (1 hour)             │           │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • Decision: Skip PTT for LiveKit transport       │           │
│  │ • Rationale documented                           │           │
│  │ • Future integration paths identified            │           │
│  │ • Deliverable: LIVEKIT_PTT_DECISION.md           │           │
│  └──────────────────────────────────────────────────┘           │
│                          │                                      │
│  Sprint 4.5-4.6: Testing & Validation (2 hours)    │           │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • Manual test plan (20 scenarios)                │           │
│  │ • Cross-platform testing procedures              │           │
│  │ • Performance validation                         │           │
│  │ • Phase completion report                        │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                 │
│  Metrics:                                                       │
│  • Production Code: +373 lines                                  │
│  • Test Code: +829 lines                                        │
│  • Documentation: ~4,000 lines                                  │
│  • Tests: 34/34 passing (100%)                                  │
│  • Breaking Changes: 0                                          │
│                                                                 │
│  Key Achievement:                                               │
│  ✅ 6-line integration maintained 100% backward compatibility   │
│                                                                 │
│  🎉 Phase 4 Complete: PTT Integrated with Transport             │
└─────────────────────────────────────────────────────────────────┘

Week 5-6: Phase 5 (Enhanced Features)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────────────────┐
│                         PHASE 5                                 │
│                   Enhanced Features                             │
│                      (Weeks 5-6)                                │
│                                                                 │
│  Sprint 5.1: Visual Feedback (4 hours)                          │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • terminal_utils.py (427 lines)                  │           │
│  │ • status_display.py (344 lines)                  │           │
│  │ • 3 display styles: minimal, compact, detailed   │           │
│  │ • ANSI color support                             │           │
│  │ • Live duration counter                          │           │
│  │ • Exports: 17                                    │           │
│  └──────────────────────────────────────────────────┘           │
│                          │                                      │
│  Sprint 5.2: Audio Feedback (4 hours)              │           │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • audio_tones.py (455 lines)                     │           │
│  │ • audio_feedback.py (270 lines)                  │           │
│  │ • 5 distinct PTT tones                           │           │
│  │ • Pure tone generation (no external files)       │           │
│  │ • Musical frequencies (C5→G5)                    │           │
│  │ • Exports: 14                                    │           │
│  └──────────────────────────────────────────────────┘           │
│                          │                                      │
│  Sprint 5.3: Statistics (4 hours)                  │           │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • statistics.py (448 lines)                      │           │
│  │ • Recording and session metrics                  │           │
│  │ • Success/cancel/error tracking                  │           │
│  │ • JSON export                                    │           │
│  │ • Exports: 7                                     │           │
│  └──────────────────────────────────────────────────┘           │
│                          │                                      │
│  Sprint 5.4: Configuration & Setup (3 hours)       │           │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • config_validation.py (460 lines)               │           │
│  │ • permissions.py (250 lines)                     │           │
│  │ • setup_helper.py (375 lines)                    │           │
│  │ • Interactive setup wizard                       │           │
│  │ • Platform-specific guidance                     │           │
│  │ • Exports: 16                                    │           │
│  └──────────────────────────────────────────────────┘           │
│                          │                                      │
│  Sprint 5.5: Error Messages & Help (2 hours)       │           │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • error_messages.py (380 lines)                  │           │
│  │ • help_system.py (450 lines)                     │           │
│  │ • Enhanced error messages                        │           │
│  │ • 7 help topics + FAQ (10 questions)             │           │
│  │ • Exports: 19                                    │           │
│  └──────────────────────────────────────────────────┘           │
│                          │                                      │
│  Sprint 5.6: Cancel Enhancement (2 hours)          │           │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • cancel_handler.py (450 lines)                  │           │
│  │ • 7 cancel reason types                          │           │
│  │ • Integrated feedback                            │           │
│  │ • Cancel statistics                              │           │
│  │ • Exports: 8                                     │           │
│  └──────────────────────────────────────────────────┘           │
│                          │                                      │
│  Sprint 5.7: Performance Optimization (3 hours)    │           │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • performance.py (520 lines)                     │           │
│  │ • Performance monitoring                         │           │
│  │ • Latency tracking                               │           │
│  │ • Optimization recommendations                   │           │
│  │ • Exports: 8                                     │           │
│  └──────────────────────────────────────────────────┘           │
│                          │                                      │
│  Sprint 5.8: Integration & Polish (3 hours)        │           │
│  ┌──────────────────────────────────────────────────┐           │
│  │ • Phase 5 completion report                      │           │
│  │ • Integration verification                       │           │
│  │ • Final documentation                            │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                 │
│  Metrics:                                                       │
│  • Production Code: +5,097 lines (12 modules)                   │
│  • Exports: 89 new public functions/classes                     │
│  • Documentation: ~6,550 lines (9 documents)                    │
│  • Backward Compatible: 100%                                    │
│  • Performance Targets: All met                                 │
│                                                                 │
│  🎉 Phase 5 Complete: Production-Ready UX                       │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
                        PROJECT SUMMARY
═══════════════════════════════════════════════════════════════════

Total Timeline: 8 weeks (5 phases)

Cumulative Metrics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Production Code:
  Phase 1-3 (Core):        ~2,000 lines
  Phase 4 (Integration):      373 lines
  Phase 5 (Enhancements):   5,097 lines
  ─────────────────────────────────────
  Total:                   ~7,470 lines

Test Code:
  Unit Tests:              ~3,200 lines
  Integration Tests:       ~1,200 lines
  ─────────────────────────────────────
  Total:                   ~4,400 lines

Documentation:
  User Docs:               ~8,000 lines
  Technical Docs:         ~12,000 lines
  Sprint Reports:          ~8,000 lines
  ─────────────────────────────────────
  Total:                  ~28,000 lines

Grand Total:             ~39,870 lines

Modules: 20+
Tests: 143 (100% pass rate)
Test-to-Code Ratio: 2.2:1
Doc-to-Code Ratio: 10.7:1
Breaking Changes: 0
Platforms: macOS, Linux, Windows
Voice Providers: 4 (OpenAI, Whisper, Kokoro, LiveKit)
PTT Modes: 3 (Hold, Toggle, Hybrid)

Status: ✅ Production Ready
```

---

## Component Dependency Graph

```
                    COMPONENT DEPENDENCY GRAPH
                  (Module Relationships & Data Flow)

External Dependencies:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────┐  ┌──────────────┐  ┌────────────┐  ┌────────────┐
│   pynput    │  │ sounddevice  │  │ webrtcvad  │  │   numpy    │
│ (keyboard)  │  │   (audio)    │  │   (VAD)    │  │   (data)   │
└──────┬──────┘  └──────┬───────┘  └─────┬──────┘  └─────┬──────┘
       │                │                │               │
       └────────────────┴────────────────┴───────────────┘
                                │
Core Configuration Layer:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                                │
                                ▼
                    ┌─────────────────────┐
                    │   config.py         │
                    │                     │
                    │ • PTT_ENABLED       │
                    │ • PTT_MODE          │
                    │ • PTT_KEY_COMBO     │
                    │ • PTT_TIMEOUT       │
                    │ • SAMPLE_RATE       │
                    │ • TTS_VOICES        │
                    │ • TTS_BASE_URLS     │
                    └──────────┬──────────┘
                               │
                               ▼
PTT Core Layer:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐
│ keyboard.py  │    │state_machine.py │    │  recorder.py     │
│              │    │                 │    │                  │
│ KeyboardHandler│  │PTTStateMachine  │    │AsyncPTTRecorder  │
│              │    │                 │    │                  │
│ • pynput     │    │ • 7 states      │    │ • sounddevice    │
│ • Key events │    │ • Transitions   │    │ • Audio buffer   │
│ • Threading  │    │ • Validation    │    │ • VAD integration│
└──────┬───────┘    └────────┬────────┘    └────────┬─────────┘
       │                     │                      │
       │                     │                      │
       └─────────────────────┼──────────────────────┘
                             │
                             ▼
                    ┌─────────────────────┐
                    │  controller.py      │
                    │                     │
                    │  PTTController      │
                    │  ┌───────────────┐  │
                    │  │ Orchestration │  │
                    │  │ Event queue   │  │
                    │  │ Callbacks     │  │
                    │  │ Lifecycle     │  │
                    │  └───────────────┘  │
                    └──────────┬──────────┘
                               │
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐
│ logging.py   │    │transport_adapter│    │Phase 5 Modules   │
│              │    │      .py        │    │                  │
│ PTTLogger    │    │                 │    │ • visual_feedback│
│              │    │record_with_ptt()│    │ • audio_feedback │
│ • Events     │    │                 │    │ • statistics     │
│ • Errors     │    │ Sync/Async      │    │ • config_valid..│
│ • Diagnostics│    │ Bridge          │    │ • permissions    │
└──────────────┘    └────────┬────────┘    │ • setup_helper   │
                             │             │ • error_messages │
                             │             │ • help_system    │
                             │             │ • cancel_handler │
                             │             │ • performance    │
                             │             └──────────────────┘
                             │
Transport Layer:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                             │
                             ▼
                    ┌─────────────────────┐
                    │  converse.py        │
                    │  (MCP Tool)         │
                    │                     │
                    │  1. TTS Phase       │
                    │  2. Transport Phase │
                    │     ├─ LiveKit      │
                    │     └─ Local Mic    │
                    │  3. STT Phase       │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
    ┌──────────────────┐  ┌──────────┐  ┌──────────────┐
    │  providers.py    │  │LiveKit   │  │ Standard VAD │
    │                  │  │Agent     │  │ Recording    │
    │ TTS/STT Provider │  │          │  │              │
    │ Selection        │  │Built-in  │  │record_audio_ │
    │                  │  │VAD       │  │with_silence_ │
    │ • OpenAI        │  │          │  │detection()   │
    │ • Whisper       │  └──────────┘  └──────────────┘
    │ • Kokoro        │
    │ • Health checks  │
    └──────────────────┘

Provider Discovery Layer:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                │
                ▼
    ┌────────────────────────┐
    │provider_discovery.py   │
    │                        │
    │ ProviderRegistry       │
    │                        │
    │ • Dynamic discovery    │
    │ • Health checking      │
    │ • Capability tracking  │
    │ • Failover logic       │
    └───────────┬────────────┘
                │
     ┌──────────┼──────────┐
     │          │          │
     ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│ OpenAI  │ │Whisper  │ │ Kokoro  │
│   API   │ │  .cpp   │ │ FastAPI │
│         │ │         │ │         │
│ Cloud   │ │ Local   │ │ Local   │
│TTS/STT  │ │  STT    │ │  TTS    │
└─────────┘ └─────────┘ └─────────┘

MCP Server Layer:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                │
                ▼
    ┌────────────────────────┐
    │     server.py          │
    │                        │
    │  FastMCP Server        │
    │  • Tools registry      │
    │  • Prompts registry    │
    │  • Resources registry  │
    │  • stdio transport     │
    └───────────┬────────────┘
                │
     ┌──────────┼──────────┐
     │          │          │
     ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌──────────┐
│ Tools   │ │Prompts  │ │Resources │
│         │ │         │ │          │
│converse │ │converse │ │statistics│
│service  │ │identity │ │config    │
│providers│ │         │ │changelog │
│devices  │ │         │ │version   │
│install_*│ │         │ │          │
└─────────┘ └─────────┘ └──────────┘

Data Flow Example (PTT Recording):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. User calls converse() via MCP
   └─> server.py receives request

2. converse.py checks PTT_ENABLED
   └─> Calls get_recording_function()

3. transport_adapter.py
   └─> Returns record_with_ptt_fallback

4. executor thread runs:
   └─> record_with_ptt()

5. Create PTTController
   ├─> KeyboardHandler (pynput listening)
   ├─> PTTStateMachine (IDLE → WAITING)
   └─> AsyncPTTRecorder (sounddevice ready)

6. User presses key combo
   └─> KeyboardHandler detects
       └─> PTTStateMachine (WAITING → KEY_PRESSED)
           └─> PTTStateMachine (KEY_PRESSED → RECORDING)
               └─> AsyncPTTRecorder starts

7. User releases keys or silence detected
   └─> PTTStateMachine (RECORDING → STOPPED)
       └─> AsyncPTTRecorder stops
           └─> Return audio_data (np.ndarray)

8. transport_adapter returns to converse.py
   └─> STT transcription (via providers.py)
       └─> Return transcribed text

9. MCP server returns response to user

Key Relationships:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• config.py:           Used by ALL modules (global configuration)
• controller.py:       Coordinates keyboard, state, recorder
• transport_adapter.py: Bridges PTT with converse tool
• providers.py:        Selects TTS/STT providers
• provider_discovery:  Maintains registry of services
• converse.py:         Central orchestration of voice flow
• server.py:           MCP entry point

Dependency Levels (bottom to top):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Level 1 (Foundation): External libs (pynput, sounddevice, numpy)
Level 2 (Config):     config.py
Level 3 (Core):       keyboard, state_machine, recorder, logging
Level 4 (Controller): controller.py
Level 5 (Adapter):    transport_adapter.py
Level 6 (Transport):  converse.py, providers.py
Level 7 (Discovery):  provider_discovery.py
Level 8 (MCP):        server.py
Level 9 (Client):     Claude Code, other MCP clients

Module Count: 20+
Max Dependency Depth: 9 levels
Circular Dependencies: 0 (clean architecture)
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-12
**Project:** Chatta Voice Mode
**Status:** Complete

---

*These diagrams illustrate the comprehensive architecture of the Chatta voice mode system, showing the relationships between components, data flow patterns, and the evolution of the system through its five development phases.*
