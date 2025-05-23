# File: autobyteus/tools/browser/session_aware/browser_session_aware_web_element_trigger.py

import xml.etree.ElementTree as ET
from typing import Optional, TYPE_CHECKING, Dict, Any # Added Dict, Any
import logging # Added

from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.tools.browser.session_aware.web_element_action import WebElementAction
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType # Added

if TYPE_CHECKING:
    pass # AgentContext not directly used in perform_action for this tool

logger = logging.getLogger(__name__) # Added

class BrowserSessionAwareWebElementTrigger(BrowserSessionAwareTool):
    """
    A session-aware tool to trigger actions (click, type, select, etc.) on web elements
    identified by a CSS selector within a shared browser session.
    """
    def __init__(self): # No instantiation config
        super().__init__()
        logger.debug("BrowserSessionAwareWebElementTrigger tool initialized.")

    @classmethod
    def get_name(cls) -> str: # Ensure this matches desired registration name
        return "WebElementTrigger" # Original name in tool_usage_xml

    @classmethod
    def get_description(cls) -> str:
        action_names = ', '.join(str(action) for action in WebElementAction)
        return (f"Triggers actions on web elements on the current page in a shared browser session. "
                f"Supported actions: {action_names}. "
                f"Returns a confirmation message upon successful execution.")

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        # webpage_url is handled by BrowserSessionAwareTool's _execute if a session needs creation.
        # It's not strictly an argument to perform_action IF a session already exists.
        # However, BaseTool.execute validates all args from schema against kwargs passed to it.
        # So, if BrowserSessionAwareTool._execute might need it from kwargs to create session, it should be here.
        schema.add_parameter(ParameterDefinition(
            name="webpage_url", # Required by base BrowserSessionAwareTool if session doesn't exist
            param_type=ParameterType.STRING,
            description="URL of the webpage. Required if no browser session is active or to ensure context.",
            required=True # Making it required simplifies BaseTool validation
        ))
        schema.add_parameter(ParameterDefinition(
            name="css_selector",
            param_type=ParameterType.STRING,
            description="CSS selector to find the target web element.",
            required=True
        ))
        schema.add_parameter(ParameterDefinition(
            name="action",
            param_type=ParameterType.ENUM,
            description=f"Type of interaction to perform. Must be one of: {', '.join(str(act) for act in WebElementAction)}.",
            required=True,
            enum_values=[str(act) for act in WebElementAction]
        ))
        schema.add_parameter(ParameterDefinition(
            name="params",
            param_type=ParameterType.STRING, # XML string for parameters
            description="Optional XML-formatted string containing additional parameters for specific actions (e.g., text for 'type', option for 'select'). Example: <param><name>text</name><value>Hello</value></param>",
            required=False 
        ))
        return schema
        
    # get_config_schema() defaults to None.

    async def perform_action(
        self, 
        shared_session: SharedBrowserSession, 
        css_selector: str, 
        action: str, # Raw string from validated enum
        webpage_url: str, # Consumed by BrowserSessionAwareTool._execute, available here if needed
        params: Optional[str] = "" # Optional params XML string
    ) -> str: # Updated signature
        """
        Triggers an action on a web element.
        Arguments css_selector, action, webpage_url, and params are validated by BaseTool.execute().
        """
        logger.info(f"WebElementTrigger performing action '{action}' on selector '{css_selector}' for page related to URL '{webpage_url}'. Params: '{params[:50]}...'")

        # 'action' is already validated by schema to be one of enum values. Convert to Enum.
        try:
            action_enum = WebElementAction.from_string(action)
        except ValueError as e: # Should not happen if schema validation works
            logger.error(f"Invalid action string '{action}' passed to perform_action despite schema validation: {e}")
            raise # Re-raise, as this indicates a system issue

        parsed_params = self._parse_xml_params(params if params else "")

        element = shared_session.page.locator(css_selector)
        
        # Wait for element to be visible before interacting, good practice
        try:
            await element.wait_for(state="visible", timeout=10000) # Wait for visible state
        except Exception as e_wait: # Playwright TimeoutError typically
            error_msg = f"Element with selector '{css_selector}' not visible or found within timeout on page {shared_session.page.url}. Error: {e_wait}"
            logger.warning(error_msg)
            raise ValueError(error_msg) from e_wait


        if action_enum == WebElementAction.CLICK:
            await element.click()
        elif action_enum == WebElementAction.TYPE:
            text_to_type = parsed_params.get("text")
            if text_to_type is None: # Check for None, empty string might be valid
                raise ValueError("'text' parameter is required for 'type' action.")
            await element.fill("") # Clear existing content before typing for more predictable behavior
            await element.type(text_to_type)
        elif action_enum == WebElementAction.SELECT:
            option_value = parsed_params.get("option")
            if option_value is None:
                raise ValueError("'option' parameter is required for 'select' action.")
            await element.select_option(option_value)
        elif action_enum == WebElementAction.CHECK:
            # Default to 'true' if 'state' param not present or malformed
            state_str = parsed_params.get("state", "true")
            is_checked_state = state_str.lower() == "true"
            if is_checked_state:
                await element.check()
            else:
                await element.uncheck()
        elif action_enum == WebElementAction.SUBMIT:
            # Submit action might not be available on all elements.
            # Playwright does not have a direct .submit() on Locator.
            # Typically, submit is called on a form or a submit button is clicked.
            # Assuming this means clicking a submit-type button or the form itself.
            # For a generic element, click is often used. If it's a form, form.evaluate('form => form.submit()')
            logger.warning("WebElementAction.SUBMIT is interpreted as a click. Ensure CSS selector targets a submit button or form element intended for click-based submission.")
            await element.click() # Simplification: treat submit as click
        elif action_enum == WebElementAction.HOVER:
            await element.hover()
        elif action_enum == WebElementAction.DOUBLE_CLICK:
            await element.dblclick()
        else:
            # This case should ideally not be reached if schema validation of 'action' works.
            raise ValueError(f"Unsupported action: {action_enum}")

        # Original tool returned path to a screenshot. Now it returns a confirmation.
        # Screenshot taking can be a separate tool or an optional flag in this tool.
        # For now, adhering to "returns a confirmation message".
        success_msg = f"The WebElementTrigger action '{action_enum}' on selector '{css_selector}' was executed."
        logger.info(success_msg)
        return success_msg

    def _parse_xml_params(self, params_xml_str: str) -> Dict[str, str]: # Renamed from _parse_params
        if not params_xml_str:
            return {}
        
        try:
            # Wrap in a root element if params_xml_str contains multiple <param> at top level
            if not params_xml_str.strip().startswith("<root>"): # Basic check
                 xml_string_to_parse = f"<root>{params_xml_str}</root>"
            else:
                 xml_string_to_parse = params_xml_str
                 
            root = ET.fromstring(xml_string_to_parse)
            parsed_params: Dict[str, str] = {}
            for param_node in root.findall('param'):
                name_elem = param_node.find('name')
                value_elem = param_node.find('value')
                if name_elem is not None and name_elem.text and value_elem is not None and value_elem.text is not None:
                    parsed_params[name_elem.text] = value_elem.text
                elif name_elem is not None and name_elem.text and value_elem is not None and value_elem.text is None: # Handle empty value tag <value/>
                     parsed_params[name_elem.text] = ""

            return parsed_params
        except ET.ParseError as e_parse:
            logger.warning(f"Failed to parse params XML string: '{params_xml_str}'. Error: {e_parse}. Returning empty params.")
            return {}
