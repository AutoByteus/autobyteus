# file: autobyteus/autobyteus/agent/group/agent_group.py
import asyncio
import logging
import uuid
from typing import List, Dict, Optional, Any, cast, Tuple, Union 

from autobyteus.agent.registry.agent_definition import AgentDefinition
from autobyteus.agent.factory.agent_factory import AgentFactory
from autobyteus.agent.agent import Agent 
from autobyteus.agent.context import AgentContext
from autobyteus.agent.group.agent_group_context import AgentGroupContext
from autobyteus.agent.message.send_message_to import SendMessageTo
from autobyteus.agent.message.agent_input_user_message import AgentInputUserMessage
from autobyteus.agent.streaming.agent_event_stream import AgentEventStream
from autobyteus.llm.models import LLMModel 
from autobyteus.llm.utils.llm_config import LLMConfig 
from autobyteus.llm.utils.response_types import CompleteResponse
from autobyteus.tools.tool_config import ToolConfig

logger = logging.getLogger(__name__)

class AgentGroup:
    def __init__(self,
                    agent_factory: AgentFactory,
                    agent_definitions: List[AgentDefinition],
                    coordinator_definition_name: str,
                    group_id: Optional[str] = None,
                    agent_runtime_configs: Optional[Dict[str, Dict[str, Any]]] = None): 
        if not agent_factory or not isinstance(agent_factory, AgentFactory): # pragma: no cover
            raise TypeError("agent_factory must be an instance of AgentFactory.")
        if not agent_definitions or not all(isinstance(d, AgentDefinition) for d in agent_definitions): # pragma: no cover
            raise TypeError("agent_definitions must be a non-empty list of AgentDefinition instances.")
        if not coordinator_definition_name or not isinstance(coordinator_definition_name, str): # pragma: no cover
            raise TypeError("coordinator_definition_name must be a non-empty string.")
        
        self.group_id: str = group_id or f"group_{uuid.uuid4()}"
        self.agent_factory: AgentFactory = agent_factory
        self._agent_definitions_map: Dict[str, AgentDefinition] = {
            defn.name: defn for defn in agent_definitions
        }
        self.coordinator_definition_name: str = coordinator_definition_name
        self._agent_runtime_configs: Dict[str, Dict[str, Any]] = agent_runtime_configs or {} 
        self.agents: List[Agent] = []
        self.coordinator_agent: Optional[Agent] = None
        self.group_context: Optional[AgentGroupContext] = None # Initialize later
        self._is_initialized: bool = False
        self._is_running: bool = False
        
        if self.coordinator_definition_name not in self._agent_definitions_map: # pragma: no cover
            raise ValueError(f"Coordinator definition name '{self.coordinator_definition_name}' "
                                f"not found in provided agent_definitions. Available: {list(self._agent_definitions_map.keys())}")
        logger.info(f"AgentGroup '{self.group_id}' created with {len(agent_definitions)} definitions. "
                    f"Coordinator: '{self.coordinator_definition_name}'.")
        self._initialize_agents()

    def _initialize_agents(self): # pragma: no cover
        if self._is_initialized:
            logger.warning(f"AgentGroup '{self.group_id}' agents already initialized. Skipping.")
            return
        temp_agents_list: List[Agent] = []
        temp_coordinator_agent: Optional[Agent] = None
        for def_name, original_definition in self._agent_definitions_map.items():
            agent_id = f"{self.group_id}_{def_name}_{uuid.uuid4().hex[:6]}"
            runtime_overrides = self._agent_runtime_configs.get(def_name, {})
            llm_model_name_for_agent: Optional[str] = runtime_overrides.get("llm_model_name")
            raw_custom_llm_config = runtime_overrides.get("custom_llm_config") 
            llm_config_for_factory: Optional[LLMConfig] = None
            if isinstance(raw_custom_llm_config, LLMConfig):
                llm_config_for_factory = raw_custom_llm_config
            elif isinstance(raw_custom_llm_config, dict):
                llm_config_for_factory = LLMConfig.from_dict(raw_custom_llm_config)
            elif raw_custom_llm_config is not None:
                logger.warning(f"AgentGroup '{self.group_id}': custom_llm_config for agent '{def_name}' is of "
                                f"unexpected type {type(raw_custom_llm_config)}. Expected LLMConfig or dict. Ignoring this config.")
            raw_custom_tool_config = runtime_overrides.get("custom_tool_config") 
            tool_config_for_factory: Optional[Dict[str, ToolConfig]] = None
            if isinstance(raw_custom_tool_config, dict):
                if all(isinstance(k, str) and isinstance(v, ToolConfig) for k, v in raw_custom_tool_config.items()):
                        tool_config_for_factory = raw_custom_tool_config
                else:
                    logger.warning(f"AgentGroup '{self.group_id}': custom_tool_config for agent '{def_name}' is a dict but contains invalid items. Expected Dict[str, ToolConfig]. Ignoring.")
            elif raw_custom_tool_config is not None:
                    logger.warning(f"AgentGroup '{self.group_id}': custom_tool_config for agent '{def_name}' is of "
                                f"unexpected type {type(raw_custom_tool_config)}. Expected Dict[str, ToolConfig]. Ignoring this config.")
            auto_execute_tools: bool = runtime_overrides.get("auto_execute_tools", True) 
            if llm_model_name_for_agent is None: # AgentDefinition might not require an LLM
                logger.debug(f"LLM model name not specified for agent definition '{def_name}'. Agent may not use an LLM.")
            modified_tool_names = list(original_definition.tool_names)
            if SendMessageTo.TOOL_NAME not in modified_tool_names:
                modified_tool_names.append(SendMessageTo.TOOL_NAME)
            effective_definition = AgentDefinition(name=original_definition.name, role=original_definition.role, description=original_definition.description,
                                            system_prompt=original_definition.system_prompt, tool_names=modified_tool_names, 
                                            input_processor_names=original_definition.input_processor_names,
                                            llm_response_processor_names=original_definition.llm_response_processor_names,
                                            system_prompt_processor_names=original_definition.system_prompt_processor_names,
                                            use_xml_tool_format=original_definition.use_xml_tool_format)
            try:
                agent_runtime = self.agent_factory.create_agent_runtime(agent_id=agent_id, definition=effective_definition, llm_model_name=llm_model_name_for_agent,
                                                                    workspace=None, custom_llm_config=llm_config_for_factory, 
                                                                    custom_tool_config=tool_config_for_factory, auto_execute_tools=auto_execute_tools) 
                agent_instance = Agent(runtime=agent_runtime)
                temp_agents_list.append(agent_instance)
                if def_name == self.coordinator_definition_name:
                    temp_coordinator_agent = agent_instance
                logger.debug(f"Agent '{agent_id}' (Role: {original_definition.role}) created for group '{self.group_id}'.")
            except Exception as e:
                logger.error(f"Failed to create agent '{def_name}' for group '{self.group_id}': {e}", exc_info=True)
                raise RuntimeError(f"Failed to initialize agent '{def_name}' in group '{self.group_id}'.") from e
        if not temp_coordinator_agent:
            raise RuntimeError(f"Coordinator agent '{self.coordinator_definition_name}' could not be instantiated in group '{self.group_id}'.")
        self.agents = temp_agents_list
        self.coordinator_agent = temp_coordinator_agent
        self.group_context = AgentGroupContext(group_id=self.group_id, agents=self.agents, coordinator_agent_id=self.coordinator_agent.agent_id)
        for agent in self.agents:
            agent.context.custom_data['agent_group_context'] = self.group_context
        self._is_initialized = True
        logger.info(f"AgentGroup '{self.group_id}' all {len(self.agents)} agents initialized successfully.")

    async def start(self): # pragma: no cover
        if not self._is_initialized: raise RuntimeError(f"AgentGroup '{self.group_id}' must be initialized before starting.")
        if self._is_running: logger.warning(f"AgentGroup '{self.group_id}' is already running."); return
        logger.info(f"Starting all agents in AgentGroup '{self.group_id}'..."); self._is_running = True 
        try:
            start_tasks = []
            for agent in self.agents:
                if not agent.is_running: 
                    agent.start() # This is synchronous
                    start_tasks.append(asyncio.sleep(0.01)) # Give event loop a chance to pick up agent's loop
            if start_tasks:
                await asyncio.gather(*start_tasks)
            logger.info(f"All agents in AgentGroup '{self.group_id}' have been requested to start.")
        except Exception as e:
            self._is_running = False; logger.error(f"Error starting agents in AgentGroup '{self.group_id}': {e}", exc_info=True)
            await self.stop(timeout=2.0); raise

    async def stop(self, timeout: float = 10.0): # pragma: no cover
        if not self._is_running and not any(a.is_running for a in self.agents): 
                logger.info(f"AgentGroup '{self.group_id}' is already stopped or was never started."); self._is_running = False; return
        logger.info(f"Stopping all agents in AgentGroup '{self.group_id}' with timeout {timeout}s...")
        stop_tasks = [agent.stop(timeout=timeout) for agent in self.agents]
        results = await asyncio.gather(*stop_tasks, return_exceptions=True)
        for agent, result in zip(self.agents, results):
            if isinstance(result, Exception): logger.error(f"Error stopping agent '{agent.agent_id}': {result}", exc_info=result)
            else: logger.debug(f"Agent '{agent.agent_id}' stopped.")
        self._is_running = False; logger.info(f"All agents in AgentGroup '{self.group_id}' have been requested to stop.")

    async def process_task_for_coordinator(self, initial_input_content: str, user_id: Optional[str] = None) -> Any: # pragma: no cover
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
                    async for complete_response in streamer.stream_assistant_final_messages():
                        if isinstance(complete_response, CompleteResponse):
                            final_response_aggregator += complete_response.content
                        else:
                            logger.warning(f"Expected CompleteResponse but got {type(complete_response)}.")
                    logger.info(f"Coordinator '{self.coordinator_agent.agent_id}' final message stream ended. Aggregated Length: {len(final_response_aggregator)}")
                except Exception as e_stream:
                    logger.error(f"Error streaming final output from coordinator '{self.coordinator_agent.agent_id}': {e_stream}", exc_info=True)
            output_stream_listener_task = asyncio.create_task(listen_for_final_output())
            message_metadata = {"user_id": user_id} if user_id else {}
            input_message = AgentInputUserMessage(content=initial_input_content, metadata=message_metadata)
            logger.info(f"AgentGroup '{self.group_id}': Posting task to coordinator '{self.coordinator_agent.agent_id}'.")
            await self.coordinator_agent.post_user_message(input_message)
            if output_stream_listener_task: await output_stream_listener_task
            logger.info(f"AgentGroup '{self.group_id}': Coordinator task processing complete. Response length: {len(final_response_aggregator)}")
            return final_response_aggregator
        except Exception as e:
            logger.error(f"Error in AgentGroup '{self.group_id}' process_task_for_coordinator: {e}", exc_info=True); raise
        finally:
            if output_stream_listener_task and not output_stream_listener_task.done():
                output_stream_listener_task.cancel()
                try: await output_stream_listener_task
                except asyncio.CancelledError: logger.debug("Coordinator output listener task cancelled.")
            if streamer and hasattr(streamer, 'close') and asyncio.iscoroutinefunction(streamer.close):
                 await streamer.close()


    def get_agent_by_id(self, agent_id: str) -> Optional[Agent]: # pragma: no cover
        for agent in self.agents:
            if agent.agent_id == agent_id: return agent
        return None

    def get_agents_by_role(self, role_name: str) -> List[Agent]: # pragma: no cover
        return [agent for agent in self.agents if agent.context.definition.role == role_name]

    @property
    def is_running(self) -> bool: # pragma: no cover
        return self._is_running and any(a.is_running for a in self.agents)

