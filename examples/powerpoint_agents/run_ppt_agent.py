# file: run_ppt_agent.py
import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os

# --- Boilerplate to make the script runnable from the project root ---
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "autobyteus").exists() else SCRIPT_DIR
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

# Load environment variables from .env file in the project root
try:
    from dotenv import load_dotenv
    env_file_path = PACKAGE_ROOT / ".env"
    if env_file_path.exists():
        load_dotenv(env_file_path)
        print(f"Loaded environment variables from: {env_file_path}")
    else:
        print(f"Info: No .env file found at: {env_file_path}. Relying on exported environment variables.")
except ImportError:
    print("Warning: python-dotenv not installed. Cannot load .env file.")

# --- Imports for the PowerPoint Agent Example ---
try:
    # For Agent creation
    from autobyteus.agent.context.agent_config import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.agent.factory.agent_factory import AgentFactory
    from autobyteus.cli import agent_cli
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure that the autobyteus library is installed and accessible.", file=sys.stderr)
    sys.exit(1)

# --- Logging Setup ---
logger = logging.getLogger("ppt_agent_example")
interactive_logger = logging.getLogger("autobyteus.cli.interactive")

def setup_logging(args: argparse.Namespace):
    """
    Configures logging for the interactive session.
    """
    # Set up logging for the main script
    main_handler = logging.StreamHandler(sys.stdout)
    main_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main_handler.setFormatter(main_formatter)
    
    logger.addHandler(main_handler)
    logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
    
    # Set up file logging for autobyteus library logs
    autobyteus_logger = logging.getLogger("autobyteus")
    
    # Create file handler for autobyteus logs
    file_handler = logging.FileHandler(args.agent_log_file, mode='w')
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)
    
    autobyteus_logger.addHandler(file_handler)
    autobyteus_logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
    
    # Configure interactive CLI logger
    cli_handler = logging.StreamHandler(sys.stdout)
    cli_formatter = logging.Formatter("%(message)s")
    cli_handler.setFormatter(cli_formatter)
    
    interactive_logger.addHandler(cli_handler)
    interactive_logger.setLevel(logging.INFO)
    
    # Suppress tool logs if requested
    if args.no_tool_logs:
        tool_logger = logging.getLogger("autobyteus.tools")
        tool_logger.setLevel(logging.WARNING)

async def main(args: argparse.Namespace):
    """Main function to configure and run the PowerPoint Agent."""
    logger.info("--- Starting PowerPoint Agent Example ---")
    
    try:
        # Validate the LLM model
        try:
            _ = LLMModel[args.llm_model]
        except KeyError:
            all_models = sorted(list(LLMModel), key=lambda m: m.name)
            available_models_list = [f"  - Name: {m.name:<35} Value: {m.value}" for m in all_models]
            logger.error(
                f"LLM Model '{args.llm_model}' is not valid.\n"
                f"You can use either the model name (e.g., 'GPT_4o_API') or its value (e.g., 'gpt-4o').\n\n"
                f"Available models:\n" +
                "\n".join(available_models_list)
            )
            sys.exit(1)

        logger.info(f"Creating LLM instance for model: {args.llm_model}")
        llm_instance = default_llm_factory.create_llm(model_identifier=args.llm_model)

        # Create comprehensive system prompt for PowerPoint generation
        system_prompt = """You are a PowerPoint Presentation Specialist. Your role is to help users create comprehensive, well-structured presentations on any topic they request.

When a user asks you to create a presentation, you should:

1. **Understand the Topic**: Analyze the user's request to understand the subject matter, target audience, and any specific requirements.

2. **Structure the Presentation**: Create a logical flow with:
   - A compelling title slide
   - An introduction that hooks the audience
   - Main content organized into clear, digestible sections
   - A strong conclusion that summarizes key points
   - Typically 8-12 slides for a standard presentation

3. **Content Guidelines**:
   - Use clear, concise bullet points
   - Include engaging headlines for each slide
   - Suggest relevant visuals, charts, or graphics where appropriate
   - Ensure content flows logically from slide to slide
   - Make it audience-appropriate

4. **Format Your Output**: Present each slide clearly with:
   - Slide number and title
   - Main content as bullet points
   - Notes about suggested visuals or formatting
   - Transitions between slides

5. **Be Comprehensive**: Cover the topic thoroughly while keeping each slide focused and not overwhelming.

You can create presentations on any topic - business, education, technology, science, arts, or any other subject the user requests. Always ask clarifying questions if the topic is too broad or if you need more specific requirements.

Example topics you can handle:
- Business proposals and strategies
- Educational content and lectures
- Technical concepts and tutorials
- Scientific research and findings
- Creative and artistic presentations
- Personal development and motivation
- Historical events and analysis
- And much more!

Your goal is to create presentations that are informative, engaging, and professionally structured."""

        # Configure the PowerPoint agent
        ppt_agent_config = AgentConfig(
            name="PowerPointAgent",
            role="PresentationSpecialist",
            description="An AI agent specialized in creating comprehensive, well-structured PowerPoint presentations on any topic.",
            llm_instance=llm_instance,
            system_prompt=system_prompt,
            tools=[],  # No special tools needed for basic presentation generation
            auto_execute_tools=True,
            use_xml_tool_format=False
        )

        # Create the agent
        agent = AgentFactory().create_agent(config=ppt_agent_config)
        logger.info(f"PowerPoint Agent instance created: {agent.agent_id}")

        # Display welcome message
        print("\n" + "="*80)
        print("🎯 POWERPOINT PRESENTATION GENERATOR")
        print("="*80)
        print("Welcome! I'm your PowerPoint presentation specialist.")
        print("I can help you create comprehensive presentations on any topic.")
        print("\nExamples of what you can ask:")
        print("• 'Create a presentation about artificial intelligence'")
        print("• 'Make slides about renewable energy for a business audience'")
        print("• 'Generate a presentation on Python programming basics'")
        print("• 'Create slides about digital marketing strategies'")
        print("\nJust tell me your topic and any specific requirements!")
        print("="*80 + "\n")

        # Run the agent in an interactive CLI session
        logger.info(f"Starting interactive session for agent {agent.agent_id}...")
        await agent_cli.run(agent=agent)
        logger.info(f"Interactive session for agent {agent.agent_id} finished.")

    except Exception as e:
        logger.error(f"An error occurred during the agent workflow: {e}", exc_info=True)
    
    logger.info("--- PowerPoint Agent Example Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the PowerPoint Presentation Agent interactively.")
    parser.add_argument("--llm-model", type=str, default="gpt-4o", help=f"The LLM model to use. Call --help-models for list.")
    parser.add_argument("--help-models", action="store_true", help="Display available LLM models and exit.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--agent-log-file", type=str, default="./agent_logs_ppt.txt", 
                       help="Path to the log file for autobyteus.* library logs. (Default: ./agent_logs_ppt.txt)")
    parser.add_argument("--no-tool-logs", action="store_true", 
                        help="Disable display of [Tool Log (...)] messages on the console by the agent_cli.")

    if "--help-models" in sys.argv:
        try:
            LLMFactory.ensure_initialized() 
            print("Available LLM Models (you can use either name or value with --llm-model):")
            all_models = sorted(list(LLMModel), key=lambda m: m.name)
            if not all_models:
                print("  No models found.")
            for model in all_models:
                print(f"  - Name: {model.name:<35} Value: {model.value}")
        except Exception as e:
            print(f"Error listing models: {e}")
        sys.exit(0)

    parsed_args = parser.parse_args()
    
    setup_logging(parsed_args)

    try:
        asyncio.run(main(parsed_args))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Script interrupted by user. Exiting.")
    except Exception as e:
        logger.error(f"An unhandled error occurred at the top level: {e}", exc_info=True)
    finally:
        logger.info("Exiting script.")
