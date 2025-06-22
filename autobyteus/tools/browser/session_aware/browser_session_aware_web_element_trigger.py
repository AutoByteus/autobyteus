# File: autobyteus/tools/browser/session_aware/browser_session_aware_web_element_trigger.py

import xml.etree.ElementTree as ET
from typing import Optional, TYPE_CHECKING, Dict, Any
import logging

from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.tools.browser.session_aware.web_element_action import WebElementAction
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType
from autobyteus.tools.tool_config import ToolConfig

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

class BrowserSessionAwareWebElementTrigger(BrowserSessionAwareTool):
    """
    A session-aware tool to trigger actions on web elements identified by a CSS selector.
    """
    def __init__(self, config: Optional[ToolConfig] = None):
        super().__init__(config=config)
        logger.debug("BrowserSessionAwareWebElementTrigger tool initialized.")

    @classmethod
    def get_name(cls) -> str:
        return "WebElementTrigger"

    @classmethod
    def get_description(cls) -> str:
        action_names = ', '.join(str(action) for action in WebElementAction)
        return (f"Triggers actions on web elements on the current page in a shared browser session. "
                f"Supported actions: {action_names}. "
                f"Returns a confirmation message upon successful execution.")

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        schema = ParameterSchema()
        schema.add_parameter(ParameterDefinition(
            name="webpage_url",
            param_type=ParameterType.STRING,
            description="URL of the webpage. Required if no browser session is active or to ensure context.",
            required=True
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
            param_type=ParameterType.STRING,
            description="Optional XML-formatted string containing additional parameters for specific actions (e.g., text for 'type', option for 'select'). Example: <param><name>text</name><value>Hello</value></param>",
            required=False 
        ))
        return schema
        
    async def perform_action(
        self, 
        shared_session: SharedBrowserSession, 
        css_selector: str, 
        action: str,
        webpage_url: str,
        params: Optional[str] = ""
    ) -> str:
        logger.info(f"WebElementTrigger performing action '{action}' on selector '{css_selector}' for page related to URL '{webpage_url}'. Params: '{params[:50]}...'")

        try:
            action_enum = WebElementAction.from_string(action)
        except ValueError as e:
            logger.error(f"Invalid action string '{action}' passed to perform_action despite schema validation: {e}")
            raise

        parsed_params = self._parse_xml_params(params if params else "")

        element = shared_session.page.locator(css_selector)
        
        try:
            await element.wait_for(state="visible", timeout=10000)
        except Exception as e_wait:
            error_msg = f"Element with selector '{css_selector}' not visible or found within timeout on page {shared_session.page.url}. Error: {e_wait}"
            logger.warning(error_msg)
            raise ValueError(error_msg) from e_wait

        if action_enum == WebElementAction.CLICK:
            await element.click()
        elif action_enum == WebElementAction.TYPE:
            text_to_type = parsed_params.get("text")
            if text_to_type is None:
                raise ValueError("'text' parameter is required for 'type' action.")
            await element.fill("")
            await element.type(text_to_type)
        elif action_enum == WebElementAction.SELECT:
            option_value = parsed_params.get("option")
            if option_value is None:
                raise ValueError("'option' parameter is required for 'select' action.")
            await element.select_option(option_value)
        elif action_enum == WebElementAction.CHECK:
            state_str = parsed_params.get("state", "true")
            is_checked_state = state_str.lower() == "true"
            if is_checked_state:
                await element.check()
            else:
                await element.uncheck()
        elif action_enum == WebElementAction.SUBMIT:
            logger.warning("WebElementAction.SUBMIT is interpreted as a click. Ensure CSS selector targets a submit button or form element intended for click-based submission.")
            await element.click()
        elif action_enum == WebElementAction.HOVER:
            await element.hover()
        elif action_enum == WebElementAction.DOUBLE_CLICK:
            await element.dblclick()
        else:
            raise ValueError(f"Unsupported action: {action_enum}")

        success_msg = f"The WebElementTrigger action '{action_enum}' on selector '{css_selector}' was executed."
        logger.info(success_msg)
        return success_msg

    def _parse_xml_params(self, params_xml_str: str) -> Dict[str, str]:
        if not params_xml_str:
            return {}
        
        try:
            if not params_xml_str.strip().startswith("<root>"):
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
                elif name_elem is not None and name_elem.text and value_elem is not None and value_elem.text is None:
                     parsed_params[name_elem.text] = ""

            return parsed_params
        except ET.ParseError as e_parse:
            logger.warning(f"Failed to parse params XML string: '{params_xml_str}'. Error: {e_parse}. Returning empty params.")
            return {}
