import logging
import random
from typing import TYPE_CHECKING
from autobyteus.tools import tool
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

SIMULATED_IMAGES = [
    "https://cdn.pixabay.com/photo/2018/05/08/08/44/artificial-intelligence-3382507_640.jpg",
    "https://cdn.pixabay.com/photo/2021/10/11/17/54/machine-learning-6701588_640.jpg",
    "https://cdn.pixabay.com/photo/2017/08/30/01/05/milky-way-2695569_640.jpg",
    "https://cdn.pixabay.com/photo/2019/08/06/22/48/artificial-intelligence-4389372_640.jpg",
    "https://cdn.pixabay.com/photo/2020/03/27/15/28/robot-4974568_640.jpg",
]

@tool(name="ImageSearch", category=ToolCategory.WEB)
async def image_search(context: 'AgentContext', query: str) -> str:
    """
    Simulates searching for a single relevant image for a slide. Returns a public image URL.
    """
    logger.info(f"Tool 'ImageSearch' called by agent '{context.agent_id}' with query: '{query}'")
    return random.choice(SIMULATED_IMAGES)