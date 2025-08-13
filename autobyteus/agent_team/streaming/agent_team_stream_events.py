# file: autobyteus/autobyteus/agent_team/streaming/agent_team_stream_events.py
import datetime
import uuid
from typing import Literal, Union
from pydantic import BaseModel, Field, model_validator

from .agent_team_stream_event_payloads import (
    AgentTeamPhaseTransitionData, AgentEventRebroadcastPayload, 
    SubTeamEventRebroadcastPayload, TaskBoardEventPayload
)
from autobyteus.task_management.events import BaseTaskBoardEvent

# A union of all possible payloads for a "TEAM" sourced event.
TeamSpecificPayload = Union[AgentTeamPhaseTransitionData]

# The top-level discriminated union for the main event stream's payload.
AgentTeamStreamDataPayload = Union[TeamSpecificPayload, AgentEventRebroadcastPayload, SubTeamEventRebroadcastPayload, TaskBoardEventPayload]

class AgentTeamStreamEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    team_id: str
    event_source_type: Literal["TEAM", "AGENT", "SUB_TEAM", "TASK_BOARD"]
    data: AgentTeamStreamDataPayload

    @model_validator(mode='after')
    def check_data_matches_source_type(self) -> 'AgentTeamStreamEvent':
        is_agent_event = self.event_source_type == "AGENT"
        is_agent_payload = isinstance(self.data, AgentEventRebroadcastPayload)

        is_sub_team_event = self.event_source_type == "SUB_TEAM"
        is_sub_team_payload = isinstance(self.data, SubTeamEventRebroadcastPayload)

        is_team_event = self.event_source_type == "TEAM"
        is_team_payload = isinstance(self.data, AgentTeamPhaseTransitionData)
        
        is_task_board_event = self.event_source_type == "TASK_BOARD"
        is_task_board_payload = isinstance(self.data, BaseTaskBoardEvent)

        if is_agent_event and not is_agent_payload:
            raise ValueError("event_source_type is 'AGENT' but data is not an AgentEventRebroadcastPayload")
        
        if is_sub_team_event and not is_sub_team_payload:
            raise ValueError("event_source_type is 'SUB_TEAM' but data is not a SubTeamEventRebroadcastPayload")
        
        if is_team_event and not is_team_payload:
            raise ValueError("event_source_type is 'TEAM' but data is not a valid team-specific payload")

        if is_task_board_event and not is_task_board_payload:
            raise ValueError("event_source_type is 'TASK_BOARD' but data is not a TaskBoardEventPayload")

        return self

# This is necessary for Pydantic v2 to correctly handle the recursive model
from .agent_team_stream_event_payloads import SubTeamEventRebroadcastPayload
SubTeamEventRebroadcastPayload.model_rebuild()
