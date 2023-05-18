from src.config.config import Config
from src.llm_integrations.openai_gpt_integration import OpenAIGPTIntegration
from src.config.config import config
# Import other LLM integrations as needed

def create_llm_integration():
    """
    create_llm_integration is a factory function that creates and returns an instance of 
    the required LLM integration based on the type provided in the configuration.

    :param config: A dictionary containing the configuration for the LLM integration.
    :type config: dict
    :return: An instance of the required LLM integration.
    :rtype: BaseLLMIntegration
    """
    integration_type = config.get('LLM_INTEGRATION_TYPE')
    
    if integration_type == 'openai':
        return OpenAIGPTIntegration(config)
    # Add more elif conditions for other LLM integration types as needed
    else:
        raise ValueError(f"Unsupported LLM integration type: {integration_type}")
