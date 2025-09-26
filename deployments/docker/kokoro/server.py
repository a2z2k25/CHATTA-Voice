from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
import kokoro_onnx
import io
import numpy as np
import scipy.io.wavfile as wavfile

app = FastAPI()

# Initialize Kokoro with downloaded model files
kokoro = kokoro_onnx.Kokoro("/app/kokoro.onnx", "/app/voices.bin")

class TTSRequest(BaseModel):
    input: str
    voice: str = "af_alloy"  # Default to af_alloy which is available
    model: str = "tts-1"

@app.post("/v1/audio/speech")
async def text_to_speech(request: TTSRequest):
    """OpenAI-compatible TTS endpoint."""
    try:
        # Generate audio using the create method which returns samples and sample rate
        samples, sample_rate = kokoro.create(request.input, voice=request.voice)
        
        # Convert numpy array to WAV format in memory
        wav_buffer = io.BytesIO()
        
        # Ensure samples are in the correct format (int16)
        if samples.dtype != np.int16:
            # Convert float32 to int16 if needed
            if samples.dtype == np.float32:
                samples = (samples * 32767).astype(np.int16)
        
        # Write WAV data to buffer
        wavfile.write(wav_buffer, sample_rate, samples)
        wav_buffer.seek(0)
        
        # Return as audio response
        return Response(
            content=wav_buffer.read(),
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav"
            }
        )
    except AttributeError as e:
        # If 'generate' doesn't exist, try 'synthesize' or other method names
        try:
            # Try alternative method names
            if hasattr(kokoro, 'synthesize'):
                samples, sample_rate = kokoro.synthesize(request.input, voice=request.voice)
            elif hasattr(kokoro, 'speak'):
                samples, sample_rate = kokoro.speak(request.input, voice=request.voice)
            elif hasattr(kokoro, 'run'):
                samples, sample_rate = kokoro.run(request.input, voice=request.voice)
            else:
                # List available methods for debugging
                methods = [m for m in dir(kokoro) if not m.startswith('_')]
                raise HTTPException(
                    status_code=500, 
                    detail=f"No suitable TTS method found. Available methods: {methods}"
                )
            
            # Process the audio as above
            wav_buffer = io.BytesIO()
            if samples.dtype != np.int16:
                if samples.dtype == np.float32:
                    samples = (samples * 32767).astype(np.int16)
            wavfile.write(wav_buffer, sample_rate, samples)
            wav_buffer.seek(0)
            
            return Response(
                content=wav_buffer.read(),
                media_type="audio/wav",
                headers={
                    "Content-Disposition": "attachment; filename=speech.wav"
                }
            )
        except Exception as inner_e:
            raise HTTPException(status_code=500, detail=str(inner_e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "kokoro-tts"}
