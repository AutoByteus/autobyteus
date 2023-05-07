from src.llm_integrations.puppeteer_llm_integration import PuppeteerLLMIntegration

def command_line_mode(config):
    """
    Run the application in command line mode.
    
    :param config: Config object containing the loaded configuration.
    """
    print("Running in command line mode")
    
    puppeteer_llm_integration = PuppeteerLLMIntegration(config)
    
    # Run the chat interaction loop
    puppeteer_llm_integration()
