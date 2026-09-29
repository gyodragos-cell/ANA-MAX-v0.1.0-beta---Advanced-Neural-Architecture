import os
import urllib.request
import urllib.error
import logging
import sounddevice as sd

# We will try to import kokoro_onnx safely.
try:
    from kokoro_onnx import Kokoro
except ImportError:
    Kokoro = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KokoroVoice:
    def __init__(self, model_dir="model_cache"):
        self.model_dir = os.path.join(os.path.dirname(__file__), model_dir)
        os.makedirs(self.model_dir, exist_ok=True)
        
        self.model_path = os.path.join(self.model_dir, "kokoro-v1.0.onnx")
        self.voices_path = os.path.join(self.model_dir, "voices-v1.0.bin")
        
        self._ensure_models_downloaded()
        
        if Kokoro is None:
            raise RuntimeError("kokoro-onnx is not installed. Run pip install kokoro-onnx")
            
        self.kokoro = Kokoro(self.model_path, self.voices_path)
        logger.info("Kokoro Voice initialized successfully.")

    def _ensure_models_downloaded(self):
        # URLs for standard ONNX model and voices
        model_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
        voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
        
        if not os.path.exists(self.model_path):
            logger.info(f"Downloading Kokoro ONNX model to {self.model_path}...")
            try:
                urllib.request.urlretrieve(model_url, self.model_path)
            except urllib.error.URLError as exc:
                raise Exception("Reteaua este indisponibila. Bazeaza-te pe datele locale.") from exc
            logger.info("Model downloaded.")
            
        if not os.path.exists(self.voices_path):
            logger.info(f"Downloading Kokoro voices to {self.voices_path}...")
            try:
                urllib.request.urlretrieve(voices_url, self.voices_path)
            except urllib.error.URLError as exc:
                raise Exception("Reteaua este indisponibila. Bazeaza-te pe datele locale.") from exc
            logger.info("Voices downloaded.")

    def speak(self, text, voice="af_heart", speed=1.0):
        if not text.strip():
            return
            
        logger.info(f"Generating voice for: {text[:50]}...")
        audio, sample_rate = self.kokoro.create(text, voice=voice, speed=speed, lang="en-us")
        
        logger.info("Playing audio...")
        sd.play(audio, sample_rate)
        sd.wait()
