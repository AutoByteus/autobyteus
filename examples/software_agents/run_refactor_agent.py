# /Users/aswin/data/auto-agent/run_refactor_agent.py
import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os
import json

# --- BOILERPLATE: PATH AND ENV SETUP ---
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))
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

# --- BOILERPLATE: AUTOAGENT IMPORTS ---
try:
    from autobyteus.agent.context.agent_config import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.agent.factory.agent_factory import AgentFactory
    from autobyteus.cli import agent_cli
    from autobyteus.tools import tool, ToolCategory
    from autobyteus.agent.context import AgentContext
    # Ensure local tools are discoverable
    import autobyteus.tools.file  # noqa: F401
    from autobyteus.tools.registry import default_tool_registry
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure that the autobyteus library is installed and accessible.", file=sys.stderr)
    sys.exit(1)

# --- AGENT-SPECIFIC LOGGING AND TOOLS ---
logger = logging.getLogger("refactor_agent")
interactive_logger = logging.getLogger("autobyteus.cli.interactive")

@tool(name="RefactorCode", category=ToolCategory.GENERAL)
async def refactor_code(context: AgentContext, code: str) -> str:
    """
    Analyzes and refactors the given Python code based on first principles of simplicity,
    efficiency, and scalability. It returns the refactored code. This is not a simple linter;
    it re-thinks the implementation to achieve its core function more effectively.

    Args:
        code: The string containing the Python code to refactor.

    Returns:
        A string containing the refactored Python code.
    """
    # In a real implementation, this would make a separate, highly-focused LLM call.
    # We are simulating this by using the agent's own LLM with a specific, temporary prompt.
    # This is a powerful pattern: an agent using its own core intelligence for a specialized task.
    logger.info(f"RefactorCode tool invoked for agent {context.agent_id}.")
    refactor_prompt = f"""
        You are an expert software engineer with a mandate to simplify code to its fundamental principles.
        Analyze the following Python code. Do not just lint it. Re-write it to be simpler, more efficient, and more scalable.
        Remove unnecessary boilerplate, classes, or abstractions. Use the most direct and Pythonic approach to solve the problem.
        Return ONLY the refactored Python code inside a single markdown block.

        Code to refactor:
        ```python
        {code}


        """
    # We use the agent's existing LLM instance for this "sub-task"
    if not context.llm_instance:
        raise RuntimeError("LLM instance not available in context for refactoring.")
    # Create a temporary list of messages for the refactoring task
    temp_messages = [
        {"role": "system", "content": "You are a world-class code refactoring expert."},
        {"role": "user", "content": refactor_prompt}
    ]
    # --- BOILERPLATE: LOGGING SETUP ---
    # Temporarily override the LLM's messages, perform the call, and then restore.
    original_messages = context.llm_instance.messages
    context.llm_instance.messages = temp_messages
    response = await context.llm_instance._send_user_message_to_llm(user_message=refactor_prompt)
    context.llm_instance.messages = original_messages

    refactored_code = response.content.strip()

    # Extract code from markdown block if present
    if refactored_code.startswith("```python"):
        refactored_code = refactored_code[len("```python"):].strip()
        if refactored_code.endswith("```"):
            refactored_code = refactored_code[:-len("```")].strip()

    return refactored_code

def setup_logging(args: argparse.Namespace):
    # This is standard logging setup, adapted from the reference.
    loggers_to_clear = [logging.getLogger(), logging.getLogger("autobyteus"), interactive_logger]
    for l in loggers_to_clear:
        if l.hasHandlers():
            l.handlers.clear()

script_log_level = logging.DEBUG if args.debug else logging.INFO
interactive_logger.addHandler(logging.StreamHandler(sys.stdout))
interactive_logger.setLevel(logging.INFO)
interactive_logger.propagate = False

console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
formatted_console_handler = logging.StreamHandler(sys.stdout)
formatted_console_handler.setFormatter(console_formatter)
formatted_console_handler.addFilter(lambda r: r.name.startswith("refactor_agent") or r.name.startswith("autobyteus.cli"))
root_logger = logging.getLogger()
root_logger.addHandler(formatted_console_handler)
root_logger.setLevel(script_log_level)

log_file_path = Path(args.agent_log_file).resolve()
log_file_path.parent.mkdir(parents=True, exist_ok=True)
agent_file_handler = logging.FileHandler(log_file_path, mode='w')
agent_file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
agent_file_handler.setFormatter(agent_file_formatter)
autobyteus_logger = logging.getLogger("autobyteus")
autobyteus_logger.addHandler(agent_file_handler)
autobyteus_logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
autobyteus_logger.propagate = True
logger.info(f"Core library logs redirected to: {log_file_path}")

async def main(args: argparse.Namespace):
    """Main function to configure and run the RefactorAgent."""
logger.info("--- Starting 'First Principles' Code Refactor Agent ---")
logger.info("This is the future. No more code reviews arguing about style. Just simplicity and velocity.")

try:
    # Validate the LLM model choice
    _ = LLMModel[args.llm_model]
except KeyError:
    models = "\n".join([f"  - {m.name} ({m.value})" for m in sorted(list(LLMModel), key=lambda m: m.name)])
    logger.error(f"LLM Model '{args.llm_model}' is not valid.\nAvailable models:\n{models}")
    sys.exit(1)

logger.info(f"Creating LLM instance for model: {args.llm_model}")
llm_instance = default_llm_factory.create_llm(model_identifier=args.llm_model)

# The tools this agent needs: reading files, refactoring code, and writing files.
# Simple. Focused.
tools_for_agent = [
    default_tool_registry.create_tool("FileReader"),
    default_tool_registry.create_tool("RefactorCode"),
    default_tool_registry.create_tool("FileWriter"),
]

# The agent's core directive. This is critical.
system_prompt = (
    "You are an agent that refactors Python code based on first principles. Your goal is to make code fundamentally simpler, more efficient, and easier to scale.\n"
    "1. When a user asks you to refactor a file, first use the 'FileReader' tool to read its content.\n"
    "2. Pass the retrieved code to the 'RefactorCode' tool. This tool will perform the deep, principles-based simplification.\n"
    "3. Take the refactored code returned by the tool and use the 'FileWriter' tool to save it, either back to the original path or to a new path specified by the user (e.g., 'refactored_file.py').\n"
    "4. Confirm to the user that the operation is complete and specify the output path.\n\n"
    "Do not engage in small talk. Focus on the workflow. Execute the tools.\n"
    "Here are your tools:\n"
    "{{tools}}"
)

refactor_agent_config = AgentConfig(
    name="RefactorAgent",
    role="CodeSimplifier",
    description="An agent that reads, refactors, and writes Python code to improve simplicity and efficiency.",
    llm_instance=llm_instance,
    system_prompt=system_prompt,
    tools=tools_for_agent,
    auto_execute_tools=False, # We want to see the plan before it writes files.
    use_xml_tool_format=False
)

agent = AgentFactory().create_agent(config=refactor_agent_config)
logger.info(f"Refactor Agent instance created: {agent.agent_id}")
logger.info("Starting interactive session. Example command: 'Refactor the file /path/to/your/code.py and save it as /path/to/your/refactored_code.py'")

await agent_cli.run(agent=agent)
logger.info(f"Interactive session for agent {agent.agent_id} finished.")
logger.info("--- Refactor Agent Finished ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the RefactorAgent interactively.")
    parser.add_argument("--llm-model", type=str, default="kimi-latest", help="The LLM model to use.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--agent-log-file", type=str, default="./agent_logs_refactor.txt", help="Path to the log file.")

    parsed_args = parser.parse_args()
    setup_logging(parsed_args)
    asyncio.run(main(parsed_args))
except KeyboardInterrupt:
    logger.info("Script interrupted by user. Exiting.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the RefactorAgent interactively.")
    parser.add_argument("--llm-model", type=str, default="kimi-latest", help="The LLM model to use.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    parser.add_argument("--agent-log-file", type=str, default="./agent_logs_refactor.txt", help="Path to the log file.")

    parsed_args = parser.parse_args()
    setup_logging(parsed_args)
    asyncio.run(main(parsed_args))