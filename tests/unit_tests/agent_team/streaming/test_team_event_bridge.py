# file: autobyteus/tests/unit_tests/agent_team/streaming/test_team_event_bridge.py
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from autobyteus.agent_team.streaming.team_event_bridge import TeamEventBridge


@pytest.mark.asyncio
@patch('autobyteus.agent_team.streaming.team_event_bridge.AgentTeamEventStream')
async def test_bridge_forwards_events(MockStream):
    event1 = MagicMock()
    event2 = MagicMock()

    async def event_gen():
        yield event1
        yield event2

    stream = MagicMock()
    stream.all_events.return_value = event_gen()
    stream.close = AsyncMock()
    MockStream.return_value = stream

    notifier = MagicMock()
    loop = asyncio.get_running_loop()
    bridge = TeamEventBridge(sub_team=MagicMock(), sub_team_node_name="SubTeam", parent_notifier=notifier, loop=loop)

    await bridge._task

    notifier.publish_sub_team_event.assert_any_call("SubTeam", event1)
    notifier.publish_sub_team_event.assert_any_call("SubTeam", event2)

    await bridge.cancel()
    stream.close.assert_awaited_once()

