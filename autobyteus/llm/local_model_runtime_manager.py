import asyncio
import atexit
import logging
import os
import shlex
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Type

import httpx

from autobyteus.llm.api.llama_cpp_llm import LlamaCppLLM
from autobyteus.llm.api.mlx_llm import MlxLLM
from autobyteus.llm.base_llm import BaseLLM
from autobyteus.llm.llm_factory import LLMFactory
from autobyteus.llm.local_model_provider_resolver import LocalModelProviderResolver
from autobyteus.llm.models import LLMModel
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.utils.llm_config import LLMConfig
from autobyteus.utils.singleton import SingletonMeta

logger = logging.getLogger(__name__)

@dataclass
class RunningModelInfo:
    process: subprocess.Popen
    model: LLMModel
    port: int

class LocalModelRuntimeManager(metaclass=SingletonMeta):
    """
    Manages the lifecycle of local LLM server processes (e.g., llama-server, mlx_lm.server),
    including starting, stopping, and tracking them.
    """
    def __init__(self):
        self._running_models: Dict[str, RunningModelInfo] = {}
        self._runtime_configs = {
            LLMRuntime.LLAMA_CPP: {
                "binary_env": "LLAMACPP_SERVER_BINARY",
                "llm_class": LlamaCppLLM
            },
            LLMRuntime.MLX: {
                "binary_env": "MLX_PYTHON_PATH",
                "llm_class": MlxLLM
            }
        }
        atexit.register(self.shutdown)

    def _find_free_port(self) -> int:
        """Finds and returns an available TCP port."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    async def _wait_for_server_ready(self, host: str, port: int, timeout: int = 60):
        """Waits for a server to become responsive."""
        start_time = time.time()
        url = f"http://{host}:{port}/"
        async with httpx.AsyncClient(timeout=2.0) as client:
            while time.time() - start_time < timeout:
                try:
                    # MLX server uses `/`, llama.cpp uses `/health` but also responds on `/`
                    response = await client.get(url)
                    if response.status_code < 500:
                        logger.info(f"Server at {url} is ready.")
                        return
                except (httpx.ConnectError, httpx.ReadTimeout):
                    await asyncio.sleep(1)
            raise TimeoutError(f"Server at {url} did not become ready within {timeout} seconds.")

    def _build_command(self, model_path: str, port: int, runtime: LLMRuntime) -> List[str]:
        """Builds the command to execute for the given runtime."""
        config = self._runtime_configs.get(runtime)
        if not config:
            raise ValueError(f"Unsupported local runtime: {runtime.value}")
        
        binary_path = os.getenv(config["binary_env"])
        if not binary_path:
            raise ValueError(f"Environment variable '{config['binary_env']}' must be set for {runtime.value} runtime.")

        if runtime == LLMRuntime.LLAMA_CPP:
            return [
                binary_path, "-m", model_path, "--port", str(port),
                "--host", "127.0.0.1", "-c", "4096", # Sensible defaults
            ]
        elif runtime == LLMRuntime.MLX:
            return [
                binary_path, "-m", "mlx_lm.server", "--model", model_path,
                "--host", "127.0.0.1", "--port", str(port),
            ]
        return []

    async def load_model(self, model_path: str, runtime: LLMRuntime) -> LLMModel:
        """
        Loads a model by starting its server process and registering it with the factory.
        """
        if runtime == LLMRuntime.MLX and sys.platform != "darwin":
            raise RuntimeError("MLX runtime is only available on macOS.")

        if not Path(model_path).exists() and not runtime == LLMRuntime.MLX:
             raise FileNotFoundError(f"Model file not found: {model_path}")
        
        model_name = Path(model_path).name if runtime != LLMRuntime.MLX else model_path

        port = self._find_free_port()
        host = "127.0.0.1"
        command = self._build_command(model_path, port, runtime)
        
        logger.info(f"Starting {runtime.value} server for model '{model_name}' on port {port}...")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        try:
            await self._wait_for_server_ready(host, port)
        except TimeoutError as e:
            stdout, _ = process.communicate()
            logger.error(f"Server failed to start. Logs:\n{stdout}")
            process.kill()
            raise e

        llm_class = self._runtime_configs[runtime]["llm_class"]
        provider = LocalModelProviderResolver.resolve(model_name)
        
        llm_model = LLMModel(
            name=model_name,
            value=model_name,
            provider=provider,
            llm_class=llm_class,
            canonical_name=model_name.split(':')[0], # e.g., 'llama3' from 'llama3:8b'
            runtime=runtime,
            host_url=f"http://{host}:{port}",
            default_config=LLMConfig() # Local models have no cost
        )

        LLMFactory.register_model(llm_model)
        self._running_models[llm_model.model_identifier] = RunningModelInfo(
            process=process,
            model=llm_model,
            port=port
        )
        logger.info(f"Successfully loaded and registered model: {llm_model.model_identifier}")
        return llm_model

    def unload_model(self, model_identifier: str) -> bool:
        """
        Unloads a model by stopping its server process and unregistering it.
        """
        if model_identifier not in self._running_models:
            logger.warning(f"No running model found with identifier: {model_identifier}")
            return False
            
        running_info = self._running_models.pop(model_identifier)
        logger.info(f"Stopping server for model {model_identifier} on port {running_info.port}...")
        
        running_info.process.terminate()
        try:
            running_info.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning(f"Process for {model_identifier} did not terminate gracefully. Killing.")
            running_info.process.kill()

        LLMFactory.unregister_model(model_identifier)
        logger.info(f"Successfully unloaded model: {model_identifier}")
        return True

    def get_running_models(self) -> List[LLMModel]:
        """Returns a list of all currently running local models."""
        return [info.model for info in self._running_models.values()]

    def shutdown(self):
        """Shuts down all managed server processes."""
        if not self._running_models:
            return
        logger.info("Shutting down all local model runtimes...")
        # Create a copy of keys to avoid issues with modifying dict during iteration
        for model_id in list(self._running_models.keys()):
            self.unload_model(model_id)
        logger.info("All local model runtimes shut down.")
