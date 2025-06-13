import asyncio
import logging
import sys
import os
import argparse
from pathlib import Path
from typing import Optional


# --- Boilerplate to make packages discoverable ---
SCRIPT_DIR = Path(__file__).resolve().parent
# Assuming the script is in 'examples', project root is one level up
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

# Add pptagent to path, assuming it's in examples/api/generate-ppt
PPTAGENT_DIR = SCRIPT_DIR / "api" / "generate-ppt"
if str(PPTAGENT_DIR) not in sys.path:
    sys.path.insert(0, str(PPTAGENT_DIR))
    print(f"Added pptagent path: {PPTAGENT_DIR}")

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


# --- Imports for AutoByteUs Agent ---
try:
    from autobyteus.agent.agent import Agent
    from autobyteus.agent.context.agent_config import AgentConfig
    from autobyteus.agent.factory.agent_factory import default_agent_factory
    from autobyteus.cli import agent_cli
    from autobyteus.tools import tool
    from autobyteus.tools.registry import default_tool_registry
    from autobyteus.llm.llm_factory import LLMFactory
    from autobyteus.llm.utils.llm_config import LLMConfig
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure that the autobyteus library is installed and accessible in your PYTHONPATH.", file=sys.stderr)
    sys.exit(1)

# --- Imports for PPTAgent Logic ---
try:
    from pptagent.pptgen import PPTAgentAsync
    from pptagent.document import Document
    from pptagent.presentation import Presentation
    from pptagent.induct import SlideInducterAsync
    from pptagent.multimodal import ImageLabler
    from pptagent.model_utils import ModelManager
    from pptagent.utils import Config, ppt_to_images_async
except ImportError as e:
    print(f"Error importing pptagent components: {e}", file=sys.stderr)
    print("Please ensure that the 'pptagent' directory is available at 'examples/api/generate-ppt/'.", file=sys.stderr)
    sys.exit(1)


# --- Basic Logging Setup ---
logger = logging.getLogger(__name__)

def setup_logging(debug: bool = False):
    """Configures logging for the script."""
    log_level = logging.DEBUG if debug else logging.INFO
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        stream=sys.stdout,
    )
    # Set autobyteus logger level
    logging.getLogger("autobyteus").setLevel(logging.INFO if not debug else logging.DEBUG)
    # Set pptagent logger level
    logging.getLogger("pptagent").setLevel(logging.INFO if not debug else logging.DEBUG)

    if debug:
        logger.info("Debug logging enabled.")

# --- Environment Variable Checks ---
def check_required_env_vars():
    """Checks for environment variables required by the pptagent components."""
    # pptagent's ModelManager will look for these.
    # At least one of these should be set.
    if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("API_BASE")):
        logger.warning(
            "Neither OPENAI_API_KEY nor API_BASE environment variables are set. "
            "The pptagent tool may fail if it requires LLM access."
        )


@tool(name="generate_powerpoint", description="Generates a PowerPoint presentation from a markdown document and a reference presentation.")
async def generate_powerpoint(
    markdown_path: str,
    reference_ppt_path: str,
    output_ppt_path: str,
    num_slides: Optional[int] = None,
) -> str:
    """
    Generates a PowerPoint presentation from a markdown document and a reference presentation.
    This tool encapsulates a complex, multi-step agentic workflow to analyze a reference
    presentation, understand a source document, and generate a new presentation.

    Note: This tool depends on the 'powerpoint-to-jpg' library, which can be installed via pip.
    It also requires various LLM models configured via environment variables (e.g., OPENAI_API_KEY,
    LANGUAGE_MODEL, VISION_MODEL) for the internal pptagent logic.

    Args:
        markdown_path: Path to the source markdown document.
        reference_ppt_path: Path to the reference .pptx file used as a template.
        output_ppt_path: Path to save the generated .pptx file.
        num_slides: Optional number of slides to generate in the final presentation.
    """
    logger.info("Starting PowerPoint generation process...")
    config = None
    try:
        # 1. Setup paths and config
        config = Config()
        logger.info(f"Using temporary directory for pptagent artifacts: {config.RUNDIR}")
        
        # 2. Initialize models for the pptagent workflow
        logger.info("Initializing models for pptagent...")
        model_manager = ModelManager()
        if not await model_manager.test_connections():
            return "Error: Could not connect to LLMs required by pptagent. Check your API keys and model configurations in environment variables."
        
        # 3. Induction step (Analyze reference presentation)
        logger.info(f"Analyzing reference presentation: {reference_ppt_path}")
        await ppt_to_images_async(reference_ppt_path, config.TEMPLATE_DIR)
        
        prs = Presentation.from_file(reference_ppt_path, config)
        
        inducter = SlideInducterAsync(
            prs=prs,
            ppt_image_folder=config.TEMPLATE_DIR,
            template_image_folder=config.TEMPLATE_DIR,
            config=config,
            image_models=[model_manager.image_model, model_manager.image_model],
            language_model=model_manager.language_model,
            vision_model=model_manager.vision_model
        )
        
        logger.info("Captioning images from reference presentation...")
        image_labler = ImageLabler(prs, config)
        await image_labler.caption_images_async(model_manager.vision_model)

        logger.info("Inducting layout and content schema...")
        slide_induction = await inducter.layout_induct()
        await inducter.content_induct(slide_induction)
        
        # 4. Parse source document
        logger.info(f"Parsing source markdown document: {markdown_path}")
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        image_dir = Path(markdown_path).parent
        if not image_dir.is_dir():
            logger.warning(f"Image directory '{image_dir}' for markdown does not exist. Assuming no local images.")
            image_dir.mkdir(parents=True, exist_ok=True)

        source_doc = await Document.from_markdown_async(
            markdown_content,
            language_model=model_manager.language_model,
            vision_model=model_manager.vision_model,
            image_dir=str(image_dir)
        )

        # 5. Generation step
        logger.info("Initializing PPTAgent for generation...")
        ppt_agent = PPTAgentAsync(
            language_model=model_manager.language_model,
            vision_model=model_manager.vision_model,
            text_embedder=model_manager.text_model,
            record_cost=True
        )
        ppt_agent.set_reference(
            config=config,
            slide_induction=slide_induction,
            presentation=prs
        )
        
        logger.info("Generating presentation content and slides...")
        generated_prs, _ = await ppt_agent.generate_pres(
            source_doc=source_doc,
            num_slides=num_slides
        )

        # 6. Save presentation
        if generated_prs:
            logger.info(f"Saving generated presentation to {output_ppt_path}")
            Path(output_ppt_path).parent.mkdir(parents=True, exist_ok=True)
            generated_prs.save(output_ppt_path)
            return f"Presentation successfully generated and saved to {output_ppt_path}"
        else:
            logger.error("Failed to generate presentation.")
            return "Failed to generate presentation. Check logs for details."
            
    except Exception as e:
        logger.error(f"An error occurred during PowerPoint generation: {e}", exc_info=True)
        return f"An error occurred: {e}"
    finally:
        if config:
            # Clean up temp dir
            config.remove_rundir()
            logger.info(f"Cleaned up temporary directory: {config.RUNDIR}")


# The @tool decorator above handles registration automatically.
# The manual registration call below is now removed as it was causing the error.
# ToolRegistry.register_tool(ToolDefinition(
#     name="generate_powerpoint",
#     description="Generates a PowerPoint presentation from a markdown document and a reference presentation.",
#     parameters=generate_powerpoint.__annotations__,
#     tool_class=generate_powerpoint,
#     tool_config=ToolConfig()
# ))


async def main():
    """
    Main function to set up and run the PowerPoint Generator Agent.
    """
    parser = argparse.ArgumentParser(description="Run the PowerPoint Generator Agent.", formatter_class=argparse.RawTextHelpFormatter)
    # The add_cli_args function was removed, so we add the arguments directly.
    parser.add_argument(
        "--show-tool-logs",
        dest="show_tool_logs",
        action="store_true",
        default=True,
        help="Show detailed logs of tool interactions. (default: True)",
    )
    parser.add_argument(
        "--hide-tool-logs",
        dest="show_tool_logs",
        action="store_false",
        help="Hide detailed logs of tool interactions.",
    )
    parser.add_argument(
        "--show-token-usage",
        action="store_true",
        default=False,
        help="Show token usage for each LLM call. (default: False)",
    )
    parser.add_argument(
        "--initial-prompt",
        type=str,
        default=None,
        help="The initial prompt to send to the agent upon starting.",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug level logging.")
    
    args = parser.parse_args()
    
    setup_logging(debug=args.debug)
    check_required_env_vars()

    # The tool is registered via the @tool decorator on the `generate_powerpoint` function.
    
    # 1. Create the LLM instance
    llm_config = LLMConfig(temperature=0.0, max_tokens=2000)
    llm_instance = LLMFactory.create_llm("GEMINI_2_0_FLASH_API", llm_config=llm_config)

    # 2. Create tool instances from the registry
    tool_definitions = default_tool_registry.list_tools()
    tool_instances = [default_tool_registry.create_tool(definition.name) for definition in tool_definitions]

    # 3. Create the AgentConfig with all required parameters
    agent_config = AgentConfig(
        name="PPTGeneratorAgent",
        role="PowerPoint Generation Assistant",
        description="An agent that generates PowerPoint presentations from markdown and a reference.",
        llm_instance=llm_instance,
        system_prompt=(
            "You are a helpful assistant that generates PowerPoint presentations. "
            "You have access to a powerful `generate_powerpoint` tool. "
            "When a user asks to create a presentation, you should:\n"
            "1. Identify the required file paths: the source markdown, the reference PPTX, and the desired output path.\n"
            "2. If any of these are missing, ask the user for the information.\n"
            "3. Once you have all the paths, call the `generate_powerpoint` tool with the correct arguments.\n"
            "4. Inform the user about the result of the tool call."
        ),
        tools=tool_instances,
    )
    
    agent = default_agent_factory.create_agent(agent_config)

    try:
        # Pass the parsed arguments to the agent_cli.run function
        await agent_cli.run(
            agent,
            show_tool_logs=args.show_tool_logs,
            show_token_usage=args.show_token_usage,
            initial_prompt=args.initial_prompt,
        )
    except (KeyboardInterrupt, SystemExit):
        logger.info("Agent CLI stopped.")
    finally:
        if agent.is_running:
            await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())