# file: autobyteus/tests/unit_tests/workflow/streaming/test_workflow_stream_events.py
import pytest
from pydantic import ValidationError

from autobyteus.agent.status.status_enum import AgentStatus
from autobyteus.workflow.streaming.workflow_stream_events import WorkflowStreamEvent, WorkflowSpecificPayload, AgentEventRebroadcastPayload, WorkflowPhaseTransitionData
from autobyteus.workflow.phases import WorkflowOperationalPhase
from autobyteus.agent.streaming.stream_events import StreamEvent, StreamEventType

def test_workflow_phase_transition_event_creation():
    """Tests successful creation of a WORKFLOW-sourced event."""
    data = WorkflowPhaseTransitionData(
        new_status=WorkflowOperationalPhase.IDLE,
        old_status=WorkflowOperationalPhase.PROCESSING
    )
    event = WorkflowStreamEvent(
        workflow_id="wf-1",
        event_source_type="WORKFLOW",
        data=data
    )
    assert isinstance(event.data, WorkflowPhaseTransitionData)
    assert event.data.new_status == WorkflowOperationalPhase.IDLE

def test_agent_event_rebroadcast_event_creation():
    """Tests successful creation of an AGENT-sourced event."""
    # FIX: Provide a valid data payload for the StreamEvent. The AGENT_IDLE
    # event type requires an AgentStatusTransitionData payload.
    mock_agent_event = StreamEvent(
        agent_id="agent-1",
        event_type=StreamEventType.AGENT_IDLE,
        data={"new_status": AgentStatus.IDLE}
    )
    data = AgentEventRebroadcastPayload(
        agent_name="Coordinator",
        agent_event=mock_agent_event
    )
    event = WorkflowStreamEvent(
        workflow_id="wf-1",
        event_source_type="AGENT",
        data=data
    )
    assert isinstance(event.data, AgentEventRebroadcastPayload)
    assert event.data.agent_name == "Coordinator"
    assert event.data.agent_event.agent_id == "agent-1"

def test_validation_error_on_mismatched_data():
    """Tests that Pydantic raises an error for incorrect data shapes."""
    with pytest.raises(ValidationError):
        # WORKFLOW source type expects WorkflowPhaseTransitionData, but we provide AGENT data
        WorkflowStreamEvent(
            workflow_id="wf-1",
            event_source_type="WORKFLOW",
            data={"agent_name": "test", "agent_event": {}}
        )
    
    with pytest.raises(ValidationError):
        # AGENT source type expects AgentEventRebroadcastPayload, but we provide WORKFLOW data
        WorkflowStreamEvent(
            workflow_id="wf-1",
            event_source_type="AGENT",
            data={"new_status": "idle"}
        )
