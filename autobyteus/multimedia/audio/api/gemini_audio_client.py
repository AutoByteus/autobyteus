import logging
import os
import base64
import uuid
import wave
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from google import genai
from google.genai import types as genai_types

from autobyteus.multimedia.audio.base_audio_client import BaseAudioClient
from autobyteus.multimedia.utils.response_types import SpeechGenerationResponse

if TYPE_CHECKING:
    from autobyteus.multimedia.audio.audio_model import AudioModel
    from autobyteus.multimedia.utils.multimedia_config import MultimediaConfig

logger = logging.getLogger(__name__)


def _save_audio_bytes_to_wav(pcm_bytes: bytes, channels=1, rate=24000, sample_width=2) -> str:
    """Saves PCM audio bytes to a temporary WAV file and returns the path."""
    temp_dir = "/tmp/autobyteus_audio"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{uuid.uuid4()}.wav")
    
    try:
        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm_bytes)
        logger.info(f"Successfully saved generated audio to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Failed to save audio to WAV file at {file_path}: {e}")
        raise


class GeminiAudioClient(BaseAudioClient):
    """
    An audio client that uses Google's Gemini models for audio tasks.

    **Setup Requirements:**
    1.  **Authentication:** Set the `GEMINI_API_KEY` environment variable with your API key.
    """

    def __init__(self, model: "AudioModel", config: "MultimediaConfig"):
        super().__init__(model, config)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Please set the GEMINI_API_KEY environment variable.")

        try:
            self.client = genai.Client()
            self.async_client = self.client.aio
            logger.info(f"GeminiAudioClient initialized for model '{self.model.name}'.")
        except Exception as e:
            logger.error(f"Failed to configure Gemini client: {e}")
            raise RuntimeError(f"Failed to configure Gemini client: {e}")


    async def generate_speech(
        self,
        prompt: str,
        generation_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> SpeechGenerationResponse:
        """
        Generates spoken audio from text using a Gemini TTS model, supporting single-speaker,
        multi-speaker, and style-controlled generation.
        """
        try:
            logger.info(f"Generating speech with Gemini TTS model '{self.model.value}'...")
            
            final_config = self.config.to_dict().copy()
            if generation_config:
                final_config.update(generation_config)
            
            # Handle style instructions by prepending them to the prompt
            style_instructions = final_config.get("style_instructions")
            final_prompt = f"{style_instructions}: {prompt}" if style_instructions else prompt
            logger.debug(f"Final prompt for TTS: '{final_prompt[:100]}...'")

            speech_config = None
            mode = final_config.get("mode", "single-speaker")

            # Handle multi-speaker generation
            if mode == "multi-speaker":
                speaker_mapping_list = final_config.get("speaker_mapping")
                if not speaker_mapping_list or not isinstance(speaker_mapping_list, list):
                    raise ValueError("Multi-speaker mode requires a 'speaker_mapping' list in generation_config.")
                
                logger.info(f"Configuring multi-speaker TTS with mapping: {speaker_mapping_list}")
                speaker_voice_configs = []
                for mapping_item in speaker_mapping_list:
                    speaker = mapping_item.get("speaker")
                    voice_name = mapping_item.get("voice")
                    if not speaker or not voice_name:
                        logger.warning(f"Skipping invalid item in speaker_mapping list: {mapping_item}")
                        continue
                    
                    speaker_voice_configs.append(
                        genai_types.SpeakerVoiceConfig(
                            speaker=speaker,
                            voice_config=genai_types.VoiceConfig(
                                prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name=voice_name)
                            )
                        )
                    )
                
                if not speaker_voice_configs:
                    raise ValueError("The 'speaker_mapping' list was empty or contained no valid mappings.")

                speech_config = genai_types.SpeechConfig(
                    multi_speaker_voice_config=genai_types.MultiSpeakerVoiceConfig(speaker_voice_configs=speaker_voice_configs)
                )

            # Handle single-speaker generation (default)
            else:
                voice_name = final_config.get("voice_name", "Kore") # A default voice
                logger.info(f"Configuring single-speaker TTS with voice: '{voice_name}'")
                speech_config = genai_types.SpeechConfig(
                    voice_config=genai_types.VoiceConfig(
                        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name=voice_name)
                    )
                )

            # The google-genai library's TTS endpoint uses a synchronous call.
            resp = self.client.models.generate_content(
                model=self.model.value,
                contents=final_prompt,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=speech_config
                ),
            )
            
            audio_b64 = resp.candidates[0].content.parts[0].inline_data.data
            audio_pcm = base64.b64decode(audio_b64)
            
            audio_path = _save_audio_bytes_to_wav(audio_pcm)

            return SpeechGenerationResponse(audio_urls=[audio_path])

        except Exception as e:
            logger.error(f"Error during Google Gemini speech generation: {str(e)}")
            raise ValueError(f"Google Gemini speech generation failed: {str(e)}")

    async def cleanup(self):
        logger.debug("GeminiAudioClient cleanup called.")
