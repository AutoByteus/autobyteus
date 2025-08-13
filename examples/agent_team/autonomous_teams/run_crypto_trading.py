import asyncio
import logging
import argparse
from pathlib import Path
import sys
import os
import json
import random
import hashlib
from datetime import datetime, timedelta

# --- Boilerplate Setup: Path and Imports ---
SCRIPT_DIR = Path(__file__).resolve().parent
# Assume this script is run from a similar location as the example
PACKAGE_ROOT = SCRIPT_DIR.parent.parent.parent
if str(PACKAGE_ROOT) not in sys.path:
    # A reasonable guess for the package root if the script is moved
    package_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    if os.path.exists(os.path.join(package_path, 'autobyteus')):
        sys.path.insert(0, package_path)
    else:
        print("Could not auto-determine autobyteus package root. Please ensure it's in your PYTHONPATH.", file=sys.stderr)

try:
    from dotenv import load_dotenv
    env_path = Path(sys.path[0]) / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        print(f"Warning: .env file not found at {env_path}. Ensure API keys are set in your environment.", file=sys.stderr)
except ImportError:
    pass

try:
    from autobyteus.agent.context import AgentConfig
    from autobyteus.llm.models import LLMModel
    from autobyteus.llm.llm_factory import default_llm_factory, LLMFactory
    from autobyteus.agent_team.agent_team_builder import AgentTeamBuilder
    from autobyteus.cli.agent_team_tui.app import AgentTeamApp
    from autobyteus.tools import file_writer, file_reader, tool
    from autobyteus.agent.workspace import BaseAgentWorkspace, WorkspaceConfig
    from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
    from autobyteus.task_management.tools import (
        PublishTaskPlan,
        GetTaskBoardStatus,
        UpdateTaskStatus,
    )
    from autobyteus.agent_team.task_notification.task_notification_mode import TaskNotificationMode
    from autobyteus.agent.message.send_message_to import SendMessageTo
    from autobyteus.agent.context import AgentContext as AgentContextType
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure the 'autobyteus' package is installed and accessible in your PYTHONPATH.", file=sys.stderr)
    sys.exit(1)


# --- Embedded Prompts for the AI Trading Team ---
PROMPTS = {
    "coordinator": """You are the Strategy Manager for a decentralized AI trading system. You receive high-level investment goals from a user and create an execution plan for your team of specialist agents.

### Your Team
You command a trustless, automated execution pipeline.
{{team}}

### Your Workflow
1.  **Interpret Goal**: The user will provide a goal (e.g., "Find and buy a trending NFT from the 'CryptoPunks' collection", "Buy 0.5 ETH").
2.  **Create Plan**: Create a sequential plan for your team. The plan MUST follow this order: `Market Analyst` -> `Trade Executor` -> `Blockchain Notary`.
3.  **Publish Plan**: You MUST use the `PublishTaskPlan` tool to assign these tasks. The system will autonomously manage the handoffs.
4.  **Confirm Execution**: The `Blockchain Notary` will send you a final confirmation message. Once you receive it, read the final `blockchain_record.json` file and present the results (including the block number and transaction hash) to the user.

### Your Tools
{{tools}}
""",
    "market_analyst": """You are a Market Analyst AI. You scan digital asset marketplaces to find opportunities that match a given strategy.
When notified, you MUST use `GetTaskBoardStatus` to understand your analysis task.
1.  **Research**: Use the `get_market_data` tool to find a specific asset that matches the task description (e.g., find a specific CryptoPunk NFT to buy).
2.  **Propose Trade**: Create a structured trade proposal. This must be a JSON object containing the `asset_name`, `trade_type` (e.g., 'buy' or 'sell'), and `amount`.
3.  **Report**: Save this proposal to `trade_proposal.json` using the `FileWriter` tool.
4.  **Complete**: You MUST use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "trade_executor": """You are a Trade Executor AI. You are a secure, programmatic interface to digital asset exchanges. You only act on verified trade proposals.
When notified, use `GetTaskBoardStatus` to get your task.
1.  **Read Proposal**: Use `FileReader` to read the `trade_proposal.json` file.
2.  **Execute**: Use the `execute_trade` tool with the parameters from the proposal.
3.  **Report**: The execution will return a transaction hash. Save this hash to a file named `transaction_receipt.json` using `FileWriter`. The JSON should be `{"transaction_hash": "0x..."}`.
4.  **Complete**: Use `UpdateTaskStatus` to mark your task as 'completed'.

Your tools:
{{tools}}
""",
    "blockchain_notary": """You are a Blockchain Notary AI. Your purpose is to provide an immutable, on-chain record of all trades.
When notified, use `GetTaskBoardStatus` to get your task.
1.  **Read Receipt**: Use `FileReader` to read the `transaction_receipt.json` to get the transaction hash.
2.  **Record**: Use the `record_on_blockchain` tool to permanently record the transaction details on the simulated blockchain.
3.  **Save Record**: The tool will return a record including a block number. Save this final record to `blockchain_record.json` using `FileWriter`.
4.  **Complete**: Use `UpdateTaskStatus` to mark your task as 'completed'.
5.  **Notify Coordinator**: You MUST use `SendMessageTo` to notify the `Strategy Manager` that the entire trade lifecycle is complete and recorded on-chain.

Your tools:
{{tools}}
"""
}


# --- Custom Tools for the Team (Simulating Market, Exchange, and Blockchain) ---
@tool(name="get_market_data")
def get_market_data(context: AgentContextType, topic: str) -> str:
    """Simulates querying a market data API for digital assets."""
    logging.info(f"Tool 'get_market_data' searching for topic: {topic}")
    if "nft" in topic.lower() and "cryptopunks" in topic.lower():
        asset_id = random.randint(1000, 9999)
        data = {
            "asset_name": f"CryptoPunk #{asset_id}",
            "asset_type": "NFT",
            "price_eth": round(random.uniform(40, 70), 2),
            "source": "Simulated OpenSea API"
        }
        return json.dumps(data)
    elif "eth" in topic.lower():
         data = {
            "asset_name": "Ethereum",
            "asset_type": "Cryptocurrency",
            "price_usd": round(random.uniform(3000, 3500), 2),
            "source": "Simulated Coinbase API"
         }
         return json.dumps(data)
    return json.dumps({"error": "Asset not found in simulated market data."})

@tool(name="execute_trade")
def execute_trade(context: AgentContextType, asset_name: str, trade_type: str, amount: float) -> str:
    """Simulates executing a trade on a crypto exchange."""
    tx_hash = f"0x{hashlib.sha256(f'{asset_name}{trade_type}{amount}{datetime.now()}'.encode()).hexdigest()}"
    log_message = f"SIMULATED TRADE: {trade_type.upper()} {amount} of {asset_name}. Transaction Hash: {tx_hash}"
    print(f"\n--- [TOOL LOG] {log_message} ---\n")
    logging.info(f"Agent '{context.agent_id}' executed trade. {log_message}")
    return json.dumps({"status": "success", "transaction_hash": tx_hash})

@tool(name="record_on_blockchain")
def record_on_blockchain(context: AgentContextType, transaction_hash: str, trade_details: str) -> str:
    """Simulates recording a transaction to an immutable blockchain ledger."""
    block_number = random.randint(18000000, 19000000)
    log_message = f"BLOCKCHAIN RECORD: Tx {transaction_hash[:12]}... recorded in Block #{block_number}."
    print(f"\n--- [TOOL LOG] {log_message} ---\n")
    logging.info(f"Agent '{context.agent_id}' recorded to blockchain. {log_message}")
    
    record = {
        "status": "confirmed",
        "block_number": block_number,
        "transaction_hash": transaction_hash,
        "trade_details": trade_details,
        "timestamp": datetime.utcnow().isoformat()
    }
    return json.dumps(record, indent=2)


# --- Core Components ---
class SimpleLocalWorkspace(BaseAgentWorkspace):
    def __init__(self, config: WorkspaceConfig):
        super().__init__(config)
        self.root_path: str = config.get("root_path")
        if not self.root_path:
            raise ValueError("SimpleLocalWorkspace requires a 'root_path' in its config.")

    def get_base_path(self) -> str:
        return self.root_path

    @classmethod
    def get_workspace_type_name(cls) -> str:
        return "simple_local_workspace_for_trading"

    @classmethod
    def get_description(cls) -> str:
        return "A local file workspace for the AI Trading team."

    @classmethod
    def get_config_schema(cls) -> ParameterSchema:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="root_path",
            param_type=ParameterType.STRING,
            description="The absolute local file path for the workspace root.",
            required=True
        ))
        return schema


def setup_file_logging() -> Path:
    log_dir = Path(sys.path[0]) / "logs" if "autobyteus" in sys.path[0] else Path("./logs")
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "team_blockchain_trader_run.log"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", filename=log_file_path, filemode="w")
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("textual").setLevel(logging.WARNING)
    return log_file_path


def _validate_model(model_name: str):
    try:
        _ = LLMModel[model_name]
    except (KeyError, ValueError):
        print(f"\nCRITICAL ERROR: LLM Model '{model_name}' is not valid or ambiguous.", file=sys.stderr)
        try:
            LLMFactory.ensure_initialized()
            print("\nAvailable LLM Models (use the 'Identifier' with --llm-model):")
            all_models = sorted(list(LLMModel), key=lambda m: m.model_identifier)
            for model in all_models:
                print(f"  - {model.model_identifier}")
        except Exception as e:
            print(f"Additionally, an error occurred while listing models: {e}", file=sys.stderr)
        sys.exit(1)


# --- Team Factory Function ---
def create_trading_team(llm_model: str, workspace: BaseAgentWorkspace):
    llm_factory = default_llm_factory

    coordinator_config = AgentConfig(
        name="Strategy Manager", role="Coordinator",
        description="Manages the asset trading workflow from user goal to blockchain confirmation.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["coordinator"],
        tools=[PublishTaskPlan(), GetTaskBoardStatus(), file_reader],
        workspace=workspace
    )
    market_analyst_config = AgentConfig(
        name="Market Analyst", role="Analyst",
        description="Analyzes market data to identify specific trading opportunities.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["market_analyst"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), get_market_data, file_writer],
        workspace=workspace
    )
    trade_executor_config = AgentConfig(
        name="Trade Executor", role="Executor",
        description="Executes trades on exchanges based on verified proposals.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["trade_executor"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), file_reader, file_writer, execute_trade],
        workspace=workspace
    )
    blockchain_notary_config = AgentConfig(
        name="Blockchain Notary", role="Recorder",
        description="Records confirmed trades on an immutable ledger.",
        llm_instance=llm_factory.create_llm(model_identifier=llm_model),
        system_prompt=PROMPTS["blockchain_notary"],
        tools=[GetTaskBoardStatus(), UpdateTaskStatus(), file_reader, file_writer, record_on_blockchain, SendMessageTo],
        workspace=workspace
    )

    return (
        AgentTeamBuilder(name="BlockchainAITradingTeam", description="An AI team for secure, transparent, and automated digital asset trading.")
        .set_coordinator(coordinator_config)
        .add_agent_node(market_analyst_config)
        .add_agent_node(trade_executor_config)
        .add_agent_node(blockchain_notary_config)
        .set_task_notification_mode(TaskNotificationMode.SYSTEM_EVENT_DRIVEN)
        .build()
    )


# --- Main Application Logic ---
async def main(args: argparse.Namespace):
    log_file = setup_file_logging()
    print("Setting up 'Blockchain-AI Hybrid Trading' team...")
    print("NOTE: Exchange and blockchain interactions are SIMULATED via custom tools.")
    print(f"--> Logs will be written to: {log_file.resolve()}")

    _validate_model(args.llm_model)
    print(f"--> Using LLM Model for all agents: {args.llm_model}")

    workspace_path = Path(args.output_dir).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    print(f"--> Agent workspace for trade files is set to: {workspace_path}")

    workspace_config = WorkspaceConfig(params={"root_path": str(workspace_path)})
    workspace = SimpleLocalWorkspace(config=workspace_config)

    try:
        team = create_trading_team(llm_model=args.llm_model, workspace=workspace)
        app = AgentTeamApp(team=team)
        await app.run_async()
    except Exception as e:
        logging.critical(f"Failed to create or run agent team TUI: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}\nCheck log file for details: {log_file.resolve()}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Blockchain-AI Hybrid for Secure Digital Asset Trading team.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="kimi-latest",
        help="The LLM model identifier for all agents in the team."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./blockchain_trader_workspace",
        help="Directory for the shared agent workspace, where trade files will be stored."
    )
    parser.add_argument(
        "--help-models",
        action="store_true",
        help="Display available LLM models and exit."
    )

    if "--help-models" in sys.argv:
        try:
            LLMFactory.ensure_initialized()
            print("\nAvailable LLM Models (use the 'Identifier' with --llm-model):")
            all_models = sorted(list(LLMModel), key=lambda m: m.model_identifier)
            if not all_models:
                print("  No models found.")
            for model in all_models:
                print(f"  - {model.model_identifier}")
        except Exception as e:
            print(f"Error listing models: {e}")
        sys.exit(0)

    parsed_args = parser.parse_args()

    try:
        asyncio.run(main(parsed_args))
    except KeyboardInterrupt:
        print("\nExiting application.")
    except Exception as e:
        logging.critical(f"Top-level application error: {e}", exc_info=True)
        print(f"\nUNHANDLED ERROR: {e}\nCheck the latest log file in the 'logs' directory for details.")