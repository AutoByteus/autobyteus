import pyaudio
import numpy as np
import threading
import queue
import time
from transformers import WhisperProcessor, WhisperForConditionalGeneration

start_time = time.time()

# Initialize Whisper model and processor
processor = WhisperProcessor.from_pretrained("openai/whisper-large-v2")
model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-large-v2")

end_time = time.time()

print(f"loading model took {end_time - start_time:.2f} seconds)")

# Initialize pyaudio
p = pyaudio.PyAudio()

# Stream parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
BUFFER_SECONDS = 10  # Process every 2 seconds of audio
SILENCE_THRESHOLD = 500  # Adjust based on testing

q = queue.Queue()

def is_silent(audio_data):
    """Returns 'True' if below the 'silent' threshold"""
    rms = np.sqrt(np.mean(np.square(audio_data)))
    return rms < SILENCE_THRESHOLD

def audio_capture():
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    print("Capturing audio... (Press Ctrl+C to stop)")
    
    while True:
        audio_chunk = stream.read(CHUNK)
        if not is_silent(np.frombuffer(audio_chunk, dtype=np.int16)):
            q.put(audio_chunk)

    stream.stop_stream()
    stream.close()

def audio_processing():
    buffer = b""
    while True:
        try:
            print(f"Transcription: processing next 10 seconds")
            start_time = time.time()

            while len(buffer) < RATE * BUFFER_SECONDS * 2:  # 2 bytes per sample
                buffer += q.get(timeout=1)  # Wait for up to 1 second for a new chunk
                
            
            audio_np = np.frombuffer(buffer[:RATE * BUFFER_SECONDS * 2], dtype=np.int16)
            buffer = buffer[RATE * BUFFER_SECONDS * 2:]
            
            input_features = processor(audio_np, sampling_rate=RATE, return_tensors="pt").input_features
            predicted_ids = model.generate(input_features)
            transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)
            
            end_time = time.time()
            
            print(f"Transcription: {transcription[0]} (Processed in {end_time - start_time:.2f} seconds)")
            
        except queue.Empty:
            print("error happened here")
            continue

capture_thread = threading.Thread(target=audio_capture)
process_thread = threading.Thread(target=audio_processing)

capture_thread.start()
process_thread.start()

try:
    capture_thread.join()
    process_thread.join()
except KeyboardInterrupt:
    print("\nStopping audio transcription...")
    p.terminate()
