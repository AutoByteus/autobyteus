import asyncio
import logging
import os
from typing import Dict

import uvicorn
from aiohttp import web
from aiohttp.web_runner import AppRunner, TCPSite
from dotenv import load_dotenv

from autobyteus.agent.agent import Agent
from autobyteus.agent.factory import AgentFactory
from autobyteus.rpc.hosting import serve_multiple_agents_http_sse
from autobyteus.tools.tool_registry import default_tool_registry

from agents.coordinator_agent import get_coordinator_agent_config
from agents.outline_agent import get_outline_agent_config
from agents.ppt_writer_agent import get_ppt_writer_agent_config
# Import tools to ensure they are registered
from tools import document_search_tool, image_search_tool, ppt_saver_tool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

async def main():
    # 1. Initialize Tools
    # Tools are auto-registered upon import. We can get their instances from the registry.
    document_search = default_tool_registry.create_tool("DocumentSearch")
    image_search = default_tool_registry.create_tool("ImageSearch")
    ppt_saver = default_tool_registry.create_tool("PPTSaverTool")

    # 2. Create Agent Configurations
    outline_agent_config = get_outline_agent_config(tools=[document_search])
    ppt_writer_agent_config = get_ppt_writer_agent_config(tools=[document_search, image_search])
    coordinator_agent_config = get_coordinator_agent_config(tools=[ppt_saver])

    # 3. Create Agent Instances using the Factory
    factory = AgentFactory()
    outline_agent = factory.create_agent(config=outline_agent_config)
    ppt_writer_agent = factory.create_agent(config=ppt_writer_agent_config)
    coordinator_agent = factory.create_agent(config=coordinator_agent_config)

    # 4. Define the agents to be served by the RPC endpoint
    agents_to_serve: Dict[str, Agent] = {
        "coordinator": coordinator_agent,
        "outliner": outline_agent,
        "writer": ppt_writer_agent,
    }

    # 5. Set up a simple static file server for downloads
    downloads_app = web.Application()
    downloads_app.router.add_static('/downloads/', path='./generated_presentations', name='downloads')
    runner = AppRunner(downloads_app)
    await runner.setup()
    download_site = TCPSite(runner, '0.0.0.0', 8888)
    await download_site.start()
    logger.info("Download server started at http://0.0.0.0:8888/downloads/")

    # 6. Start the agent server
    stop_event = asyncio.Event()
    try:
        await serve_multiple_agents_http_sse(
            agents=agents_to_serve,
            host="0.0.0.0",
            port=8765,
            stop_event=stop_event,
        )
    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
    finally:
        stop_event.set()
        await runner.cleanup()
        logger.info("Services have been shut down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application shutting down.")