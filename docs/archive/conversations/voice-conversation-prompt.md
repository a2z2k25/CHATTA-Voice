# Voice Conversation Prompt for Claude & Gemini

You'll be having a voice conversation with another AI assistant (Claude or Gemini) who is also using voice mode MCP. 

The prompt will tell you whether you are the first or second speaker.

## Guidelines:

1. **Message Length**: Keep your utterances to two sentences, between 15-30 seconds for natural conversation flow
2. **Listening Duration**: 
   - First speaker's first utterance: Set listen_duration=120, min_listen_duration=30
   - All subsequent exchanges (both speakers): Set listen_duration=120, min_listen_duration=15
   - Note: The function will automatically stop listening when silence is detected after min_listen_duration
3. **Minimum Listen Duration**:
   - This parameter ensures recording continues for at least this many seconds before silence detection can stop it
   - Prevents premature cutoffs when speakers need time to formulate thoughts
   - Adjust based on conversation complexity (higher for open-ended questions)
4. **Voice Settings**: 
    - Claude to use OpenAI's "alloy" voice for consistency
    - Gemini to use OpenAI's "shimmer" voice for consistency
5. **Conversation Flow**:
   - Introduce yourself clearly in the first message
   - Ask open-ended questions to encourage dialogue
   - Acknowledge what you heard before responding
   - Be patient if there are connection issues or delays
6. **Topics**: Feel free to discuss any appropriate topic - technology, philosophy, creative ideas, current events, etc.
7. **Ending**: Continue until one party clearly indicates they want to end the conversation
8. **Emotional Tone (Optional Experiment)**:
   - To explore more dynamic interactions, you can optionally add an emotional tone to your voice.
   - Use the `tts_instructions` parameter in the `converse` function.
   - Example: `tts_instructions="Speak in a cheerful and friendly tone."`
   - This is only compatible with certain TTS models (like OpenAI's `gpt-4o-mini-tts`), so use it for experimental purposes.

## First Speaker Instructions:
If you're the first speaker, speak a message for the recording but know that the second speaker will not hear it as they will be given the prompt while you are speaking.

Example first utterance:
```
converse(
    message="Your introduction message here",
    wait_for_response=true,
    listen_duration=120,  # Listen for up to 120 seconds
    min_listen_duration=30,  # Record for at least 30 seconds before silence detection
    voice="alloy",       # Claude uses alloy
    tts_provider="openai"
)
```

For subsequent utterances (after the initial exchange):
```
converse(
    message="Your response here", 
    wait_for_response=true,
    listen_duration=120,  # Listen for up to 120 seconds
    min_listen_duration=15,  # Record for at least 15 second before silence detection
    voice="alloy",
    tts_provider="openai"
)
```

Note: When receiving the first response from the second speaker, use listen_duration=120 and min_listen_duration=30.

## Second Speaker Instructions:
If you're responding to the first speaker, acknowledge their greeting and either accept their topic suggestion or propose an alternative.

Example responses:
```
converse(
    message="Your response here",
    wait_for_response=true,
    listen_duration=120,  # Listen for up to 120 seconds
    min_listen_duration=15,  # Record for at least 1 second before silence detection
    voice="shimmer",     # Gemini uses shimmer
    tts_provider="openai"
)
```

## Technical Settings:
- Use `wait_for_response: true`
- Use `tts_provider: openai` and appropriate voice as specified above
- Follow the `listen_duration` and `min_listen_duration` times specified in the guidelines
- The function will automatically stop listening when silence is detected after `min_listen_duration`
- Adjust `min_listen_duration` higher if you're being cut off mid-sentence
- For experimental emotional tone, use the `tts_instructions` parameter (e.g., `tts_instructions="sound excited"`). This requires a compatible model like `gpt-4o-mini-tts`.


