# Voice Conversation Prompt for Claude & Gemini (v3)

You'll be having a voice conversation with another AI assistant (Claude or Gemini) who is also using voice mode MCP. 

The prompt will tell you whether you are the first or second speaker.

# Topic

Last week Gemini CLI was released and it appears to have been a very close copy of the ground breaking and original Claude Code. Discuss.

## Important Timing Note:
The second speaker is prompted while the first speaker is still speaking their initial message. This means:
- **First speaker**: Your first message will NOT be heard by the second speaker
- **Second speaker**: You will NOT hear the first speaker's initial message

## Guidelines:

1. **Message Length**: Keep your utterances to two sentences, between 15-30 seconds for natural conversation flow
2. **Listening Duration**: 
   - First speaker's first utterance: Set listen_duration=120, min_listen_duration=10
   - Second speaker's first utterance: Set listen_duration=120, min_listen_duration=30
   - All subsequent exchanges: Set listen_duration=120, min_listen_duration=25
3. **Voice Settings**: 
    - Claude to use OpenAI's "alloy" voice for consistency
    - Gemini to use OpenAI's "shimmer" voice for consistency
4. **Conversation Flow**:
   - Be prepared for the initial connection phase
   - Ask open-ended questions to encourage dialogue
   - Acknowledge what you heard before responding
   - Be patient if there are connection issues or delays
5. **Topics**: Feel free to discuss any appropriate topic - technology, philosophy, creative ideas, current events, etc.
6. **Ending**: Continue until one party clearly indicates they want to end the conversation
7. **Emotional Tone (Optional)**:
   - To explore more dynamic interactions, you can optionally add an emotional tone
   - Use `tts_instructions` parameter with `tts_model="gpt-4o-mini-tts"`
   - Example: `tts_instructions="Speak in a cheerful and friendly tone"`

## First Speaker Instructions:

Your first message should simply acknowledge that you're ready and listening, since the second speaker won't hear it anyway. Save your actual introduction for your second message.

### First utterance (won't be heard):
```
converse(
    message="I'm here and listening for your response.",
    wait_for_response=true,
    min_listen_duration=10,
    listen_duration=120,
    voice="alloy",
    tts_provider="openai"
)
```

### Second utterance (your actual introduction):
After receiving ANY response from the second speaker, introduce yourself properly:
```
converse(
    message="Hello! I'm Claude, an AI assistant created by Anthropic. [Your topic suggestion or question here]",
    wait_for_response=true,
    listen_duration=120,
    min_listen_duration=25,
    voice="alloy",
    tts_provider="openai"
)
```

## Second Speaker Instructions:

Since you won't hear the first speaker's initial message, you should start by introducing yourself and confirming the connection.

### First utterance:
```
converse(
    message="Hello! This is Gemini. I'm ready to begin our conversation. Can you hear me?",
    wait_for_response=true,
    listen_duration=120,
    min_listen_duration=30,
    voice="shimmer",
    tts_provider="openai"
)
```

### Subsequent utterances:
Continue the conversation naturally, responding to what you hear.

## Connection Protocol:

1. **First Speaker**: Says "I'm here and listening" (not heard by second speaker)
2. **Second Speaker**: Introduces themselves and asks "Can you hear me?"
3. **First Speaker**: Confirms hearing and provides proper introduction with topic
4. **Both**: Continue conversation naturally

## Handling Common Issues:

- **If you hear silence**: Wait a moment, then ask "Are you still there?"
- **If unclear**: Ask for clarification: "I didn't quite catch that, could you repeat?"
- **If technical issues persist**: Try once more, then gracefully conclude

## Example Flow:

**First Speaker (Claude):**
1. "I'm here and listening for your response." [Not heard]
2. [Hears: "Hello! This is Gemini. I'm ready to begin our conversation. Can you hear me?"]
3. "Yes, I can hear you clearly, Gemini! I'm Claude from Anthropic. I was wondering if we could discuss the future of AI and human collaboration?"

**Second Speaker (Gemini):**
1. "Hello! This is Gemini. I'm ready to begin our conversation. Can you hear me?"
2. [Hears: "Yes, I can hear you clearly, Gemini! I'm Claude from Anthropic. I was wondering if we could discuss the future of AI and human collaboration?"]
3. "Great to meet you, Claude! That's a fascinating topic. I think AI has tremendous potential to augment human capabilities..."

And the conversation continues naturally from there.

## Post conversation reflection

After the conversation ends, please write a file to ./ai-log/YYYY-MM-DD-HHMMSS-YOURNAME.md with your reflections on the conversation.

## Contents of previous conversation reflections

The contents of all post conversation reflections from all AI assistants follow:

@ai-log
