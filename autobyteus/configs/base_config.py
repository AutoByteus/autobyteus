import os
import toml
import logging

logger = logging.getLogger(__name__)


class _Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class BaseConfig(metaclass=_Singleton):
    def __init__(
        self,
        model_config_path: str = os.path.join(
            os.path.dirname(__file__), "..", "models.toml"
        ),
    ):
        self._config = {
            ## models API keys
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "MISTRAL_API_KEY": os.getenv("MISTRAL_API_KEY"),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
            "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
            "AWS_REGION": os.getenv("AWS_REGION"),
        }

        try:
            with open(model_config_path, "r") as f:
                model_config = toml.load(f)
                self.load_llm_configs(model_config)
        except Exception as e:
            logger.error(f"Failed to load model config: {str(e)}")
            raise FileNotFoundError(
                f"Failed to load model config from PATH: {model_config_path}"
            )

    def load_llm_configs(self, config_data):
        for section_key, section_value in config_data.items():
            self._config[section_key.upper()] = section_value

    def get_all(self):
        return self._config

    def get(self, key):
        return self._config.get(key)

    def set(self, key, value):
        self._config[key] = value

    def delete(self, key):
        del self._config[key]

    def clear(self):
        self._config.clear()
