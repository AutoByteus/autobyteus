import asyncio
import base64
import logging
import os
import uuid
import wave
from typing import Optional, Dict, Any, TYPE_CHECKING, List

# Old/legacy Gemini SDK (as requested)
import google.generativeai as genai

from autobyteus.multimedia.audio.base_audio_client import BaseAudioClient
from autobyteus.multimedia.utils.response_types import SpeechGenerationResponse

if TYPE_CHECKING:
    from autobyteus.multimedia.audio.audio_model import AudioModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)


def _save_audio_bytes_to_wav(
    pcm_bytes: bytes,
    channels: int = 1,
    rate: int = 24000,
    sample_width: int = 2,
) -> str:
    """
    Save raw PCM (s16le) audio bytes to a temporary WAV file and return the file path.

    Gemini TTS models output mono, 24 kHz, 16-bit PCM by default.
    """
    temp_dir = "/tmp/autobyteus_audio"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.wav")

    try:
        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)  # 2 bytes => 16-bit
            wf.setframerate(rate)
            wf.writeframes(pcm_bytes)
        logger.info("Successfully saved generated audio to %s", file_path)
        return file_path
    except Exception as e:
        logger.error("Failed to save audio to WAV file at %s: %s", file_path, e)
        raise


def _extract_inline_audio_bytes(response) -> bytes:
    """
    Extract inline audio bytes from a google.generativeai response.

    The legacy SDK returns a Response object with candidates -> content -> parts[0].inline_data.data.
    Depending on version, `.data` can be bytes or base64-encoded str.
    """
    try:
        # Access the first candidate's first part's inline_data
        part = response.candidates[0].content.parts[0]
        inline = getattr(part, "inline_data", None)
        if not inline or not hasattr(inline, "data"):
            raise ValueError("No inline audio data found in response.")
        data = inline.data
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return base64.b64decode(data)
        raise TypeError(f"Unexpected inline_data.data type: {type(data)}")
    except Exception as e:
        logger.error("Failed to extract audio from response: %s", e)
        raise


class GeminiAudioClient(BaseAudioClient):
    """
    An audio client that uses Google's Gemini models for TTS via the *legacy* SDK
    (`google.generativeai`).

    Usage notes:
      - Ensure your model value is a TTS-capable model (e.g. "gemini-2.5-flash-preview-tts"
        or "gemini-2.5-pro-preview-tts").
      - Single-speaker is default. For simple usage, provide `voice_name` (e.g. "Kore", "Puck")
        in MultimediaConfig or generation_config.
      - Multi-speaker preview exists in the API; if you want it, pass:
          generation_config = {
              "mode": "multi-speaker",
              "speakers": [
                  {"speaker": "Alice", "voice_name": "Kore"},
                  {"speaker": "Bob",   "voice_name": "Puck"},
              ]
          }
        and make sure your prompt contains lines for each named speaker.
    """

    def __init__(self, model: "AudioModel", config: "MultimediaConfig"):
        super().__init__(model, config)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Please set the GEMINI_API_KEY environment variable.")

        try:
            # Legacy library uses a global configure call
            genai.configure(api_key=api_key)
            # Create a GenerativeModel handle
            self._model = genai.GenerativeModel(self.model.value or "gemini-2.5-flash-preview-tts")
            logger.info("GeminiAudioClient (legacy SDK) configured for model '%s'.", self.model.value)
        except Exception as e:
            logger.error("Failed to configure Gemini client: %s", e)
            raise RuntimeError(f"Failed to configure Gemini client: {e}")

    @staticmethod
    def _build_single_speaker_generation_config(voice_name: str) -> Dict[str, Any]:
        """
        Build generation_config for single-speaker TTS in the legacy SDK.
        Key bits:
          - response_mime_type => request audio
          - speech_config.voice_config.prebuilt_voice_config.voice_name => set the voice
        """
        return {
            "response_mime_type": "audio/pcm",
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": voice_name,
                    }
                }
            },
        }

    @staticmethod
    def _build_multi_speaker_generation_config(speakers: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Build generation_config for multi-speaker TTS (preview).
        `speakers` = [{"speaker": "...", "voice_name": "..."}, ...]
        """
        speaker_voice_configs = []
        for s in speakers:
            spk = s.get("speaker")
            vname = s.get("voice_name")
            if not spk or not vname:
                raise ValueError("Each speaker must include 'speaker' and 'voice_name'.")
            speaker_voice_configs.append(
                {
                    "speaker": spk,
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": vname,
                        }
                    },
                }
            )
        return {
            "response_mime_type": "audio/pcm",
            "speech_config": {
                "multi_speaker_voice_config": {
                    "speaker_voice_configs": speaker_voice_configs
                }
            },
        }

    async def generate_speech(
        self,
        prompt: str,
        generation_config: Optional[Dict[str, Any]] = None
    ) -> SpeechGenerationResponse:
        """
        Generates spoken audio from text using a Gemini TTS model through the legacy SDK.

        Implementation details:
          - We call `GenerativeModel.generate_content(...)` with a `generation_config`
            that asks for AUDIO and sets the voice settings.
          - The legacy SDK call is synchronous; we offload to a worker thread.
        """
        try:
            logger.info("Generating speech with Gemini TTS (legacy SDK) model '%s'...", self.model.value)

            # Merge base config with per-call overrides
            final_cfg = self.config.to_dict().copy()
            if generation_config:
                final_cfg.update(generation_config or {})

            # Style instructions: prepend if provided
            style_instructions = final_cfg.get("style_instructions")
            final_prompt = f"{style_instructions}: {prompt}" if style_instructions else prompt
            logger.debug("Final prompt for TTS (truncated): '%s...'", final_prompt[:160])

            # Mode & voice
            mode = final_cfg.get("mode", "single-speaker")
            default_voice = final_cfg.get("voice_name", "Kore")

            if mode == "multi-speaker":
                speakers = final_cfg.get("speakers")
                if not speakers or not isinstance(speakers, list):
                    raise ValueError(
                        "For multi-speaker mode, provide generation_config['speakers'] "
                        "as a list of {'speaker': <name>, 'voice_name': <prebuilt voice>}."
                    )
                gen_config = self._build_multi_speaker_generation_config(speakers)
            else:
                gen_config = self._build_single_speaker_generation_config(default_voice)

            # Run the blocking gen call in a thread so this coroutine stays non-blocking
            response = await asyncio.to_thread(
                self._model.generate_content,
                final_prompt,
                generation_config=gen_config,
            )

            audio_pcm = _extract_inline_audio_bytes(response)
            audio_path = _save_audio_bytes_to_wav(audio_pcm)

            return SpeechGenerationResponse(audio_urls=[audio_path])

        except Exception as e:
            logger.error("Error during Google Gemini speech generation (legacy SDK): %s", str(e))
            raise ValueError(f"Google Gemini speech generation failed: {str(e)}")

    async def cleanup(self):
        logger.debug("GeminiAudioClient cleanup called (legacy SDK; nothing to release).")
