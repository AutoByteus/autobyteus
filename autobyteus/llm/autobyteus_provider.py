from autobyteus.llm.api.autobyteus_llm import AutobyteusLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.runtimes import LLMRuntime
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig
from typing import Dict, Any, TYPE_CHECKING, List, Optional
import os
import logging
from urllib.parse import urlparse
from autobyteus_llm_client import AutobyteusClient

if TYPE_CHECKING:
    from autobyteus.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

class AutobyteusModelProvider:
    DEFAULT_SERVER_URL = 'https://localhost:8000'

    @staticmethod
    def _get_hosts() -> List[str]:
        """
        Gets Autobyteus LLM server hosts from env vars. Skips discovery if no host is configured.
        """
        hosts_str = os.getenv('AUTOBYTEUS_LLM_SERVER_HOSTS')
        if hosts_str:
            return [host.strip() for host in hosts_str.split(',')]
        
        legacy_host = os.getenv('AUTOBYTEUS_LLM_SERVER_URL')
        if legacy_host:
            return [legacy_host]
            
        return []

    @staticmethod
    def discover_and_register():
        """Discover and register Autobyteus models from all configured hosts."""
        try:
            from autobyteus.llm.llm_factory import LLMFactory

            hosts = AutobyteusModelProvider._get_hosts()
            if not hosts:
                logger.info("No Autobyteus LLM server hosts configured. Skipping Autobyteus LLM model discovery.")
                return

            total_registered_count = 0

            for host_url in hosts:
                if not AutobyteusModelProvider.is_valid_url(host_url):
                    logger.error(f"Invalid Autobyteus host URL: {host_url}, skipping.")
                    continue
                
                logger.info(f"Discovering Autobyteus models from host: {host_url}")
                client = None
                try:
                    # Instantiate client for this specific host
                    client = AutobyteusClient(server_url=host_url)
                    response = client.get_available_llm_models_sync()
                except Exception as e:
                    logger.warning(f"Could not connect or fetch models from Autobyteus server at {host_url}: {e}")
                    continue
                finally:
                    if client:
                        client.sync_client.close()

                if not AutobyteusModelProvider._validate_server_response(response):
                    continue

                models = response.get('models', [])
                host_registered_count = 0
                for model_info in models:
                    try:
                        validation_result = AutobyteusModelProvider._validate_model_info(model_info)
                        if not validation_result["valid"]:
                            logger.warning(validation_result["message"])
                            continue
                        
                        llm_config = AutobyteusModelProvider._parse_llm_config(model_info["config"])
                        if not llm_config:
                            continue
                        
                        llm_model = LLMModel(
                            name=model_info["name"],
                            value=model_info["value"],
                            provider=LLMProvider(model_info["provider"]),
                            llm_class=AutobyteusLLM,
                            canonical_name=model_info["canonical_name"],
                            runtime=LLMRuntime.AUTOBYTEUS,
                            host_url=host_url,
                            default_config=llm_config
                        )
                        
                        LLMFactory.register_model(llm_model)
                        host_registered_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to register Autobyteus model '{model_info.get('name')}' from {host_url}: {e}")
                
                if host_registered_count > 0:
                    logger.info(f"Registered {host_registered_count} models from Autobyteus host {host_url}")
                total_registered_count += host_registered_count
            
            if total_registered_count > 0:
                 logger.info(f"Finished Autobyteus discovery. Total models registered: {total_registered_count}")

        except Exception as e:
            logger.error(f"An unexpected error occurred during Autobyteus model discovery: {e}", exc_info=True)

    @staticmethod
    def _validate_server_response(response: Dict[str, Any]) -> bool:
        """Validate root server response structure"""
        if not isinstance(response, dict):
            logger.error("Invalid server response format")
            return False
            
        if "models" not in response:
            logger.error("Missing 'models' field in response")
            return False
            
        if not isinstance(response["models"], list):
            logger.error("Models field must be a list")
            return False
            
        return True

    @staticmethod
    def _validate_model_info(model_info: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual model information"""
        result = {"valid": False, "message": ""}
        required_fields = ["name", "value", "provider", "config"]
        
        for field in required_fields:
            if field not in model_info:
                result["message"] = f"Missing required field '{field}' in model info"
                return result
                
            if not model_info[field]:
                result["message"] = f"Empty value for required field '{field}'"
                return result
                
        try:
            # Validate provider string matches an LLMProvider enum value
            LLMProvider(model_info["provider"])
        except ValueError as e:
            result["message"] = f"Invalid provider '{model_info['provider']}': {str(e)}"
            return result
            
        if not isinstance(model_info["config"], dict):
            result["message"] = "Config must be a dictionary"
            return result
            
        result["valid"] = True
        return result

    @staticmethod
    def _parse_llm_config(config_data: Dict[str, Any]) -> LLMConfig:
        """Parse and validate LLM configuration"""
        try:
            pricing_data = config_data.get("pricing_config", {})
            if not AutobyteusModelProvider._validate_pricing_config(pricing_data):
                raise ValueError("Invalid pricing configuration")
                
            llm_config = LLMConfig.from_dict(config_data)
            
            if not llm_config.token_limit or llm_config.token_limit < 1:
                logger.warning("Setting default token limit (8192)")
                llm_config.token_limit = 8192
                
            if not 0 <= llm_config.temperature <= 2:
                logger.warning("Temperature out of range, resetting to 0.7")
                llm_config.temperature = 0.7
                
            return llm_config
            
        except Exception as e:
            logger.error(f"Config parsing failed: {str(e)}")
            return None

    @staticmethod
    def _validate_pricing_config(pricing_data: Dict[str, Any]) -> bool:
        """Validate token pricing configuration"""
        required_keys = ["input_token_pricing", "output_token_pricing"]
        
        for key in required_keys:
            if key not in pricing_data:
                logger.error(f"Missing pricing key: {key}")
                return False
                
            if not isinstance(pricing_data[key], (int, float)):
                logger.error(f"Invalid pricing type for {key}")
                return False
                
            if pricing_data[key] < 0:
                logger.error(f"Negative pricing for {key}")
                return False
                
        return True

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
