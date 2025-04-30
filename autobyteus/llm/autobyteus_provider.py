from autobyteus.llm.api.autobyteus_llm import AutobyteusLLM
from autobyteus.llm.models import LLMModel
from autobyteus.llm.providers import LLMProvider
from autobyteus.llm.utils.llm_config import LLMConfig, TokenPricingConfig
from typing import Dict, Any, TYPE_CHECKING
import os
import logging
from urllib.parse import urlparse
from autobyteus_llm_client import AutobyteusClient

if TYPE_CHECKING:
    from autobyteus.llm.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

class AutobyteusModelProvider:
    DEFAULT_SERVER_URL = 'https://localhost:8000'
    CONNECTION_TIMEOUT = 5.0

    @staticmethod
    def discover_and_register():
        """Discover and register Autobyteus models synchronously"""
        try:
            from autobyteus.llm.llm_factory import LLMFactory  # Local import to avoid circular dependency

            client = None
            try:
                client = AutobyteusClient()
                response = client.get_available_models_sync()
            except Exception as e:
                logger.error(f"Client initialization failed: {str(e)}")
                return
            finally:
                if client:
                    client.sync_client.close()

            if not AutobyteusModelProvider._validate_server_response(response):
                return

            models = response.get('models', [])
            registered_count = 0
            
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
                        provider=LLMProvider(model_info["provider"]),  # Convert string to enum
                        llm_class=AutobyteusLLM,
                        default_config=llm_config
                    )
                    
                    LLMFactory.register_model(llm_model)
                    registered_count += 1
                    logger.debug(f"Registered model: {model_info['name']}")
                    
                except Exception as e:
                    logger.error(f"Model registration failed: {str(e)}")
                    continue
                        
            logger.info(f"Registered {registered_count} Autobyteus models")

        except Exception as e:
            logger.error(f"Discovery failed: {str(e)}", exc_info=True)

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
