import pytest
from unittest.mock import AsyncMock

from autobyteus.tools.browser.session_aware.browser_session_aware_element_trigger import BrowserSessionAwareElementTrigger

@pytest.mark.asyncio
async def test_browser_session_aware_element_trigger_execute_click():
    element_trigger = BrowserSessionAwareElementTrigger()

    await element_trigger.execute(element_locator="button", event_type="click")

    element_trigger.get_or_create_shared_browser_session.assert_called_once()
