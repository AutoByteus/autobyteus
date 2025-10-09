import json
import logging
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


class CertificateError(Exception):
    """Custom exception for certificate-related errors."""


class AutobyteusClient:
    """Async + sync HTTP client for talking to an Autobyteus LLM server."""

    DEFAULT_SERVER_URL = "https://api.autobyteus.com"
    API_KEY_HEADER = "AUTOBYTEUS_API_KEY"
    API_KEY_ENV_VAR = "AUTOBYTEUS_API_KEY"
    SSL_CERT_FILE_ENV_VAR = "AUTOBYTEUS_SSL_CERT_FILE"

    def __init__(self, server_url: Optional[str] = None):
        """
        Initialize the client.

        Args:
            server_url: Explicit server URL. Takes precedence over env vars.
        """
        self.server_url = server_url or os.getenv(
            "AUTOBYTEUS_LLM_SERVER_URL", self.DEFAULT_SERVER_URL
        )
        self.api_key = os.getenv(self.API_KEY_ENV_VAR)

        if not self.api_key:
            raise ValueError(
                f"{self.API_KEY_ENV_VAR} environment variable is required. "
                "Please set it before initializing the client."
            )

        custom_cert_path_str = os.getenv(self.SSL_CERT_FILE_ENV_VAR)
        verify_param: Union[str, bool, Path]

        if custom_cert_path_str:
            custom_cert_path = Path(custom_cert_path_str)
            if not custom_cert_path.exists():
                raise CertificateError(
                    f"Custom SSL certificate file specified via {self.SSL_CERT_FILE_ENV_VAR} "
                    f"not found at: {custom_cert_path}"
                )
            if not custom_cert_path.is_file():
                raise CertificateError(
                    f"Custom SSL certificate path specified via {self.SSL_CERT_FILE_ENV_VAR} "
                    f"is not a file: {custom_cert_path}"
                )
            verify_param = str(custom_cert_path)
            logger.info(
                "Using custom SSL certificate file for TLS verification: %s. "
                "This is the recommended secure method for servers with self-signed or "
                "private CA certificates.",
                verify_param,
            )
        else:
            verify_param = False
            logger.warning(
                "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
                "SECURITY WARNING: SSL certificate verification is DISABLED because the \n"
                f"'{self.SSL_CERT_FILE_ENV_VAR}' environment variable is not set.\n"
                "This configuration is INSECURE and makes the client vulnerable to \n"
                "Man-in-the-Middle (MitM) attacks. It should ONLY be used for development \n"
                "or testing in trusted environments with self-signed certificates if \n"
                "providing the certificate path is not possible.\n"
                "FOR PRODUCTION or secure environments with self-signed certificates, \n"
                f"it is STRONGLY RECOMMENDED to set the '{self.SSL_CERT_FILE_ENV_VAR}' \n"
                "environment variable to the path of the server's certificate (.pem file) \n"
                "to enable proper TLS verification.\n"
                "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
            )

        timeout_config = httpx.Timeout(connect=10.0, read=None, write=None, pool=None)

        try:
            self.async_client = httpx.AsyncClient(
                verify=verify_param,
                headers={self.API_KEY_HEADER: self.api_key},
                timeout=timeout_config,
            )
            self.sync_client = httpx.Client(
                verify=verify_param,
                headers={self.API_KEY_HEADER: self.api_key},
                timeout=timeout_config,
            )
        except Exception as exc:
            logger.error(
                "Failed to initialize httpx client with SSL configuration (verify='%s'): %s",
                verify_param,
                exc,
            )
            raise RuntimeError(f"HTTP client initialization failed: {exc}") from exc

        logger.info("Initialized Autobyteus client with server URL: %s", self.server_url)

    async def get_available_llm_models(self) -> Dict[str, Any]:
        """Async discovery of available LLM models."""
        try:
            response = await self.async_client.get(
                urljoin(self.server_url, "/models/llm")
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.error("Async LLM model fetch error: %s", exc)
            raise RuntimeError(str(exc)) from exc

    def get_available_llm_models_sync(self) -> Dict[str, Any]:
        """Synchronous discovery of available LLM models."""
        try:
            response = self.sync_client.get(urljoin(self.server_url, "/models/llm"))
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.error("Sync LLM model fetch error: %s", exc)
            raise RuntimeError(str(exc)) from exc

    async def get_available_image_models(self) -> Dict[str, Any]:
        """Async discovery of available image models."""
        try:
            response = await self.async_client.get(
                urljoin(self.server_url, "/models/image")
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.error("Async image model fetch error: %s", exc)
            raise RuntimeError(str(exc)) from exc

    def get_available_image_models_sync(self) -> Dict[str, Any]:
        """Synchronous discovery of available image models."""
        try:
            response = self.sync_client.get(
                urljoin(self.server_url, "/models/image")
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.error("Sync image model fetch error: %s", exc)
            raise RuntimeError(str(exc)) from exc

    async def get_available_audio_models(self) -> Dict[str, Any]:
        """Async discovery of available audio models."""
        try:
            response = await self.async_client.get(
                urljoin(self.server_url, "/models/audio")
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.error("Async audio model fetch error: %s", exc)
            raise RuntimeError(str(exc)) from exc

    def get_available_audio_models_sync(self) -> Dict[str, Any]:
        """Synchronous discovery of available audio models."""
        try:
            response = self.sync_client.get(
                urljoin(self.server_url, "/models/audio")
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.error("Sync audio model fetch error: %s", exc)
            raise RuntimeError(str(exc)) from exc

    async def send_message(
        self,
        conversation_id: str,
        model_name: str,
        user_message: str,
        image_urls: Optional[List[str]] = None,
        audio_urls: Optional[List[str]] = None,
        video_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Send a message and get a response."""
        try:
            data = {
                "conversation_id": conversation_id,
                "model_name": model_name,
                "user_message": user_message,
                "image_urls": image_urls or [],
                "audio_urls": audio_urls or [],
                "video_urls": video_urls or [],
            }
            response = await self.async_client.post(
                urljoin(self.server_url, "/send-message"),
                json=data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.error("Error sending message: %s", exc)
            raise RuntimeError(str(exc)) from exc

    async def stream_message(
        self,
        conversation_id: str,
        model_name: str,
        user_message: str,
        image_urls: Optional[List[str]] = None,
        audio_urls: Optional[List[str]] = None,
        video_urls: Optional[List[str]] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream a message and get responses."""
        try:
            data = {
                "conversation_id": conversation_id,
                "model_name": model_name,
                "user_message": user_message,
                "image_urls": image_urls or [],
                "audio_urls": audio_urls or [],
                "video_urls": video_urls or [],
            }

            async with self.async_client.stream(
                "POST",
                urljoin(self.server_url, "/stream-message"),
                json=data,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            chunk = json.loads(line[6:])
                            if "error" in chunk:
                                raise RuntimeError(chunk["error"])
                            yield chunk
                        except json.JSONDecodeError as exc:
                            logger.error("Failed to parse stream chunk: %s", exc)
                            raise RuntimeError("Invalid stream response format") from exc

        except httpx.HTTPError as exc:
            logger.error("Stream error: %s", exc)
            raise RuntimeError(str(exc)) from exc

    async def generate_image(
        self,
        model_name: str,
        prompt: str,
        input_image_urls: Optional[List[str]] = None,
        mask_url: Optional[str] = None,
        generation_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate or edit an image and return the server response."""
        try:
            data = {
                "model_name": model_name,
                "prompt": prompt,
                "input_image_urls": input_image_urls or [],
                "mask_url": mask_url,
                "generation_config": generation_config or {},
            }
            response = await self.async_client.post(
                urljoin(self.server_url, "/generate-image"),
                json=data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.error("Error generating image: %s", exc)
            raise RuntimeError(str(exc)) from exc

    async def generate_speech(
        self,
        model_name: str,
        prompt: str,
        generation_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate speech from text and return the server response."""
        try:
            data = {
                "model_name": model_name,
                "prompt": prompt,
                "generation_config": generation_config or {},
            }
            response = await self.async_client.post(
                urljoin(self.server_url, "/generate-speech"),
                json=data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.error("Error generating speech: %s", exc)
            raise RuntimeError(str(exc)) from exc

    async def cleanup(self, conversation_id: str) -> Dict[str, Any]:
        """Clean up a conversation."""
        try:
            response = await self.async_client.post(
                urljoin(self.server_url, "/cleanup"),
                json={"conversation_id": conversation_id},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.error("Cleanup error: %s", exc)
            raise RuntimeError(str(exc)) from exc

    async def close(self) -> None:
        """Close both HTTP clients."""
        await self.async_client.aclose()
        self.sync_client.close()

    async def __aenter__(self) -> "AutobyteusClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        await self.close()
