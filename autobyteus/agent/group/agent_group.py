# file: autobyteus/autobyteus/agent/group/agent_group.py
import asyncio
import logging
import uuid
from typing import List, Dict, Optional, Any

from autobyteus.agent.context.agent_config import AgentConfig
from autobyteus.agent.factory import AgentFactory
from autobyteus.agent.agent import Agent 
from autobyteus.agent.group.agent_group_context import AgentGroupContext
from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from autobyteus.llm.utils.response_types import CompleteResponse

logger = logging.getLogger(__name__)

class AgentGroup:
    def __init__(self,
                    agent_configs: List[AgentConfig],
                    coordinator_config_name: str,
                    group_id: Optional[str] = None): 
        if not agent_configs or not all(isinstance(c, AgentConfig) for c in agent_configs):
            raise TypeError("agent_configs must be a non-empty list of AgentConfig instances.")
        if not coordinator_config_name or not isinstance(coordinator_config_name, str):
            raise TypeError("coordinator_config_name must be a non-empty string.")
        
        self.group_id: str = group_id or f"group_{uuid.uuid4()}"
        self.agent_factory = AgentFactory() # Get singleton instance
        self._agent_configs_map: Dict[str, AgentConfig] = {
            config.name: config for config in agent_configs
        }
        self.coordinator_config_name: str = coordinator_config_name
        self.agents: List[Agent] = []
        self.coordinator_agent: Optional[Agent] = None
        self.group_context: Optional[AgentGroupContext] = None
        self._is_initialized: bool = False
        self._is_running: bool = False
        
        if self.coordinator_config_name not in self._agent_configs_map:
            raise ValueError(f"Coordinator config name '{self.coordinator_config_name}' "
                                f"not found in provided agent_configs. Available: {list(self._agent_configs_map.keys())}")
        logger.info(f"AgentGroup '{self.group_id}' created with {len(agent_configs)} configurations. "
                    f"Coordinator: '{self.coordinator_config_name}'.")
        self._initialize_agents()

    def _initialize_agents(self):
        if self._is_initialized:
            logger.warning(f"AgentGroup '{self.group_id}' agents already initialized. Skipping.")
            return
            
        temp_agents_list: List[Agent] = []
        temp_coordinator_agent: Optional[Agent] = None
        for config_name, original_config in self._agent_configs_map.items():
            
            modified_tools = list(original_config.tools)
            is_send_message_present = any(isinstance(tool, SendMessageTo) for tool in modified_tools)
            if not is_send_message_present:
                modified_tools.append(SendMessageTo())

            # This logic correctly re-uses the user-provided LLM instance and other properties
            # when creating the effective config for the agent factory.
            effective_config = AgentConfig(
                name=original_config.name,
                role=original_config.role,
                description=original_config.description,
                llm_instance=original_config.llm_instance,
                system_prompt=original_config.system_prompt,
                tools=modified_tools, 
                auto_execute_tools=original_config.auto_execute_tools,
                use_xml_tool_format=original_config.use_xml_tool_format,
                input_processors=original_config.input_processors,
                llm_response_processors=original_config.llm_response_processors,
                system_prompt_processors=original_config.system_prompt_processors,
                workspace=original_config.workspace,
                phase_hooks=original_config.phase_hooks,
                initial_custom_data=original_config.initial_custom_data
            )

            try:
                agent_instance = self.agent_factory.create_agent(config=effective_config)
                temp_agents_list.append(agent_instance)
                
                if config_name == self.coordinator_config_name:
                    temp_coordinator_agent = agent_instance
                logger.debug(f"Agent '{agent_instance.agent_id}' (Role: {original_config.role}) created for group '{self.group_id}'.")
            except Exception as e:
                logger.error(f"Failed to create agent for config '{config_name}' for group '{self.group_id}': {e}", exc_info=True)
                raise RuntimeError(f"Failed to initialize agent for config '{config_name}' in group '{self.group_id}'.") from e
                
        if not temp_coordinator_agent:
            raise RuntimeError(f"Coordinator agent '{self.coordinator_config_name}' could not be instantiated.")
        
        self.agents = temp_agents_list
        self.coordinator_agent = temp_coordinator_agent
        self.group_context = AgentGroupContext(group_id=self.group_id, agents=self.agents, coordinator_agent_id=self.coordinator_agent.agent_id)
        for agent in self.agents:
            agent.context.custom_data['agent_group_context'] = self.group_context
        self._is_initialized = True
        logger.info(f"AgentGroup '{self.group_id}' all {len(self.agents)} agents initialized successfully.")

    async def start(self):
        if not self._is_initialized: raise RuntimeError(f"AgentGroup '{self.group_id}' must be initialized before starting.")
        if self._is_running: logger.warning(f"AgentGroup '{self.group_id}' is already running."); return
        logger.info(f"Starting all agents in AgentGroup '{self.group_id}'..."); self._is_running = True 
        try:
            for agent in self.agents:
                if not agent.is_running:
                    agent.start()
            # Give loops a chance to start
            await asyncio.sleep(0.01)
            logger.info(f"All agents in AgentGroup '{self.group_id}' have been requested to start.")
        except Exception as e:
            self._is_running = False; logger.error(f"Error starting agents in AgentGroup '{self.group_id}': {e}", exc_info=True)
            await self.stop(timeout=2.0); raise

    async def stop(self, timeout: float = 10.0):
        if not self._is_running and not any(a.is_running for a in self.agents): 
            logger.info(f"AgentGroup '{self.group_id}' is already stopped or was never started."); self._is_running = False; return
        logger.info(f"Stopping all agents in AgentGroup '{self.group_id}' with timeout {timeout}s...")
        stop_tasks = [agent.stop(timeout=timeout) for agent in self.agents]
        results = await asyncio.gather(*stop_tasks, return_exceptions=True)
        for agent, result in zip(self.agents, results):
            if isinstance(result, Exception): logger.error(f"Error stopping agent '{agent.agent_id}': {result}", exc_info=result)
        self._is_running = False; logger.info(f"All agents in AgentGroup '{self.group_id}' have been requested to stop.")

    async def process_task_for_coordinator(self, initial_input_content: str, user_id: Optional[str] = None) -> Any:
        if not self.coordinator_agent: raise RuntimeError(f"Coordinator agent not set in group '{self.group_id}'.")
        await self.start() 
        final_response_aggregator = ""
        output_stream_listener_task = None
        streamer = None
        try:
            streamer = AgentEventStream(self.coordinator_agent) 
            async def listen_for_final_output():
                nonlocal final_response_aggregator
                try:
                    async for complete_response_data in streamer.stream_assistant_final_response():
                        final_response_aggregator += complete_response_data.content
                except Exception as e_stream:
                    logger.error(f"Error streaming final output from coordinator: {e_stream}", exc_info=True)
            output_stream_listener_task = asyncio.create_task(listen_for_final_output())
            input_message = AgentInputUserMessage(content=initial_input_content, metadata={"user_id": user_id} if user_id else {})
            await self.coordinator_agent.post_user_message(input_message)
            
            # Wait for the listener to finish, which happens after the agent is done and the stream closes.
            if output_stream_listener_task: 
                await output_stream_listener_task
            
            return final_response_aggregator
        finally:
            if output_stream_listener_task and not output_stream_listener_task.done():
                output_stream_listener_task.cancel()
            if streamer: await streamer.close()

    def get_agent_by_id(self, agent_id: str) -> Optional[Agent]:
        return next((agent for agent in self.agents if agent.agent_id == agent_id), None)

    def get_agents_by_role(self, role_name: str) -> List[Agent]:
        return [agent for agent in self.agents if agent.context.config.role == role_name]

    @property
    def is_running(self) -> bool:
        return self._is_running and any(a.is_running for a in self.agents)
