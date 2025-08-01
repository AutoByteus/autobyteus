import logging
from typing import TYPE_CHECKING
from autobyteus.tools import tool
from autobyteus.tools.tool_category import ToolCategory

if TYPE_CHECKING:
    from autobyteus.agent.context import AgentContext

logger = logging.getLogger(__name__)

# Mocked documents for demonstration purposes
DOCUMENTS = [
    "Artificial Intelligence (AI) in the automotive industry is revolutionizing vehicle design, manufacturing, and driving experience. Key applications include autonomous driving, predictive maintenance, and in-car personalization.",
    "Autonomous driving levels range from Level 0 (no automation) to Level 5 (full automation). Companies like Waymo and Cruise are testing Level 4 systems, while Tesla's Autopilot is considered a strong Level 2 system.",
    "AI-powered predictive maintenance uses sensor data to predict when vehicle components will fail, allowing for proactive repairs. This reduces downtime and improves safety.",
    "In manufacturing, AI algorithms optimize robotic assembly lines, improve quality control through computer vision, and manage complex supply chains, leading to increased efficiency and reduced costs.",
    "The user experience inside the car is being enhanced by AI through voice assistants, personalized infotainment recommendations, and driver monitoring systems to detect fatigue."
]

@tool(name="DocumentSearch", category=ToolCategory.WEB)
async def document_search(context: 'AgentContext', query: str) -> str:
    """
    Searches a collection of internal documents for a given query and returns relevant information.
    """
    logger.info(f"Tool 'DocumentSearch' called by agent '{context.agent_id}' with query: {query}")
    
    results = [doc for doc in DOCUMENTS if query.lower() in doc.lower()]
    
    if not results:
        return f"No relevant documents found for the query: '{query}'."
        
    return "\n\n".join(results)