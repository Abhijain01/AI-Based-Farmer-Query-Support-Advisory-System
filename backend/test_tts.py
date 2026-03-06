from gtts import gTTS
import os

try:
    print("Testing TTS connection...")
    tts = gTTS(text="Hello world", lang="en")
    tts.save("test.mp3")
    print("TTS Success: test.mp3 created")
    os.remove("test.mp3")
except Exception as e:
    print(f"TTS Failed: {e}")
