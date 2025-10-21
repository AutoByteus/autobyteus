import pytest
from unittest.mock import AsyncMock, Mock, patch
from autobyteus.tools.browser.session_aware.browser_session_aware_web_element_trigger import BrowserSessionAwareWebElementTrigger, WebElementAction
# Removed BrowserSessionAwareWebPageReader as it's not directly tested here, only used as a helper in original.
from autobyteus.utils.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.agent.context import AgentContext
from autobyteus.tools.registry import default_tool_registry
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.tools.tool_state import ToolState


TOOL_NAME_ELEMENT_TRIGGER = "trigger_web_element"

@pytest.fixture
def mock_agent_context_trigger():
    mock_context = Mock(spec=AgentContext)
    mock_context.agent_id = "test_agent_trigger_session"
    return mock_context

@pytest.fixture
def mock_shared_browser_session_trigger(): # Specific fixture name
    session = AsyncMock(spec=SharedBrowserSession)
    session.page = AsyncMock()
    # Mock locator to return another AsyncMock for element actions
    session.page.locator.return_value = AsyncMock() 
    session.page.url = "https://mocked.page.url/test" # For logging inside tool
    return session

@pytest.fixture
def element_trigger_tool_instance(mock_agent_context_trigger):
    tool = BrowserSessionAwareWebElementTrigger()
    tool.set_agent_id(mock_agent_context_trigger.agent_id)
    return tool

def test_tool_state_initialization(element_trigger_tool_instance: BrowserSessionAwareWebElementTrigger):
    """Tests that the tool_state attribute is properly initialized."""
    assert hasattr(element_trigger_tool_instance, 'tool_state')
    assert isinstance(element_trigger_tool_instance.tool_state, ToolState)
    assert element_trigger_tool_instance.tool_state == {}
    # Verify it's usable
    element_trigger_tool_instance.tool_state['last_action'] = 'click'
    assert element_trigger_tool_instance.tool_state['last_action'] == 'click'

# Definition Tests
def test_element_trigger_definition():
    definition = default_tool_registry.get_tool_definition(TOOL_NAME_ELEMENT_TRIGGER)
    assert definition is not None
    assert definition.name == TOOL_NAME_ELEMENT_TRIGGER
    assert "Triggers actions on web elements" in definition.description
    action_names = ', '.join(str(action) for action in WebElementAction)
    assert action_names in definition.description # Check if actions are listed

    schema = definition.argument_schema
    assert isinstance(schema, ParameterSchema)
    assert len(schema.parameters) == 4 # webpage_url, css_selector, action, params
    
    assert schema.get_parameter("webpage_url").required is True
    assert schema.get_parameter("css_selector").required is True
    action_param = schema.get_parameter("action")
    assert action_param.required is True
    assert action_param.param_type == ParameterType.ENUM
    assert schema.get_parameter("params").required is False

# Test perform_action directly
@pytest.mark.asyncio
async def test_perform_action_click(
    element_trigger_tool_instance: BrowserSessionAwareWebElementTrigger, 
    mock_shared_browser_session_trigger: SharedBrowserSession
):
    css_selector = "#myButton"
    action_str = "click" # Valid string from enum
    
    # perform_action needs webpage_url due to its signature, even if not used directly in its logic
    # (it's used by the base class _execute method if session needs creation)
    result = await element_trigger_tool_instance.perform_action(
        mock_shared_browser_session_trigger, 
        css_selector=css_selector, 
        action=action_str,
        webpage_url="http://dummy.url/forclick", 
        params=""
    )
    
    assert f"action 'click' on selector '{css_selector}' was executed" in result
    mock_shared_browser_session_trigger.page.locator.assert_called_once_with(css_selector)
    # The locator returns an AsyncMock, check click was called on it
    mock_shared_browser_session_trigger.page.locator.return_value.wait_for.assert_called_once_with(state="visible", timeout=10000)
    mock_shared_browser_session_trigger.page.locator.return_value.click.assert_called_once()

@pytest.mark.asyncio
async def test_perform_action_type(
    element_trigger_tool_instance: BrowserSessionAwareWebElementTrigger, 
    mock_shared_browser_session_trigger: SharedBrowserSession
):
    css_selector = "input[name='search']"
    action_str = "type"
    text_to_type = "Hello World"
    params_xml = f"<param><name>text</name><value>{text_to_type}</value></param>"

    result = await element_trigger_tool_instance.perform_action(
        mock_shared_browser_session_trigger, 
        css_selector=css_selector, 
        action=action_str,
        webpage_url="http://dummy.url/fortype",
        params=params_xml
    )
    assert f"action 'type' on selector '{css_selector}' was executed" in result
    mock_element = mock_shared_browser_session_trigger.page.locator.return_value
    mock_element.fill.assert_called_once_with("") # Check clear before type
    mock_element.type.assert_called_once_with(text_to_type)

@pytest.mark.asyncio
async def test_perform_action_type_missing_text_param(
    element_trigger_tool_instance: BrowserSessionAwareWebElementTrigger, 
    mock_shared_browser_session_trigger: SharedBrowserSession
):
    with pytest.raises(ValueError, match="'text' parameter is required for 'type' action."):
        await element_trigger_tool_instance.perform_action(
            mock_shared_browser_session_trigger, 
            css_selector="#input", 
            action="type",
            webpage_url="http://dummy.url",
            params="" # Missing text param
        )

@pytest.mark.asyncio
async def test_perform_action_element_not_visible(
    element_trigger_tool_instance: BrowserSessionAwareWebElementTrigger, 
    mock_shared_browser_session_trigger: SharedBrowserSession
):
    mock_element = mock_shared_browser_session_trigger.page.locator.return_value
    mock_element.wait_for.side_effect = Exception("Element not visible timeout") # Simulate Playwright TimeoutError

    with pytest.raises(ValueError, match="Element with selector .* not visible or found"):
        await element_trigger_tool_instance.perform_action(
            mock_shared_browser_session_trigger,
            css_selector="#hiddenButton",
            action="click",
            webpage_url="http://dummy.url"
        )

# Test full .execute() method to ensure BrowserSessionAwareTool base class integration
@pytest.mark.asyncio
async def test_full_execute_click_with_session_mocking(
    element_trigger_tool_instance: BrowserSessionAwareWebElementTrigger, 
    mock_agent_context_trigger: AgentContext,
    mock_shared_browser_session_trigger: SharedBrowserSession # Re-use fixture for the session itself
):
    # Mock the SharedBrowserSessionManager that BrowserSessionAwareTool instantiates
    mock_session_manager_instance = AsyncMock()
    mock_session_manager_instance.get_shared_browser_session.return_value = mock_shared_browser_session_trigger
    mock_session_manager_instance.create_shared_browser_session = AsyncMock(
        # Side effect to set the session on the manager if create is called
        side_effect=lambda: setattr(mock_session_manager_instance, 'shared_browser_session', mock_shared_browser_session_trigger)
    )

    with patch('autobyteus.tools.browser.session_aware.browser_session_aware_tool.SharedBrowserSessionManager', return_value=mock_session_manager_instance):
        # Re-initialize the tool instance so it picks up the patched manager, or patch its instance manager
        # Simpler: patch the instance's manager directly after it's created by fixture
        element_trigger_tool_instance.shared_browser_session_manager = mock_session_manager_instance

        result = await element_trigger_tool_instance.execute(
            mock_agent_context_trigger,
            webpage_url="https://example.com/triggerpage", # Required by schema & base class
            css_selector="#myButton",
            action="click",
            params="" 
        )

    assert "action 'click' on selector '#myButton' was executed" in result
    # Verify that perform_action (which is mocked indirectly via mock_shared_browser_session_trigger.page.locator().click) was effectively called
    mock_shared_browser_session_trigger.page.locator.assert_called_with("#myButton")
    mock_shared_browser_session_trigger.page.locator.return_value.click.assert_called_once()
