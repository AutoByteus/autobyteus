# File: autobyteus/tools/browser/session_aware/browser_session_aware_web_element_trigger.py

from datetime import datetime
import os
import xml.etree.ElementTree as ET
from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.shared_browser_session import SharedBrowserSession
from autobyteus.tools.browser.session_aware.web_element_action import WebElementAction

class BrowserSessionAwareWebElementTrigger(BrowserSessionAwareTool):
    def __init__(self):
        super().__init__()

    def get_name(self) -> str:
        return "WebElementTrigger"
    
    def tool_usage(self):
        return """WebElementTrigger: Triggers actions on web elements on web pages, takes a screenshot, and returns the absolute path of the screenshot.
    Usage: <<<WebElementTrigger(webpage_url='url', css_selector='selector', action='action', params='<param><name>param_name</name><value>param_value</value></param>')>>>

    Parameters:
    - webpage_url: String. URL of the webpage to interact with.
    - css_selector: String. CSS selector to find the target element.
    - action: String. Type of interaction to perform on the element. Must be one of: 
      {', '.join(str(action) for action in WebElementAction)}
    - params: String. XML-formatted string containing additional parameters for specific actions.

    Common actions and their parameters:
    1. click: No additional params required.
    2. type: Requires 'text' param. Example: <param><name>text</name><value>Hello, World!</value></param>
    3. select: Requires 'option' param. Example: <param><name>option</name><value>option1</value></param>
    4. check: Optional 'state' param (default: true). Example: <param><name>state</name><value>false</value></param>
    5. submit: No additional params required.
    6. hover: No additional params required.
    7. double_click: No additional params required.

    Return Value:
    - String: Absolute path to the screenshot taken after the action is performed.
      The screenshot is saved in the current working directory with the filename format:
      'screenshot_<action>_<timestamp>.png'

    Examples:
    1. Typing in a search box:
      <<<WebElementTrigger(webpage_url='https://example.com', css_selector='#search-input', action='type', params='<param><name>text</name><value>Python tutorial</value></param>')>>>
      Returns: '/path/to/screenshot_type_20230615_120530.png'

    2. Selecting an option from a dropdown:
      <<<WebElementTrigger(webpage_url='https://example.com', css_selector='#country-select', action='select', params='<param><name>option</name><value>USA</value></param>')>>>
      Returns: '/path/to/screenshot_select_20230615_120545.png'

    3. Clicking a button:
      <<<WebElementTrigger(webpage_url='https://example.com', css_selector='.submit-button', action='click')>>>
      Returns: '/path/to/screenshot_click_20230615_120600.png'
    """

    def tool_usage_xml(self):
        return f'''WebElementTrigger: Triggers actions on web elements on web pages, takes a screenshot, and returns the absolute path of the screenshot.
    <command name="WebElementTrigger">
      <arg name="webpage_url">url</arg>
      <arg name="css_selector">selector</arg>
      <arg name="action">action</arg>
      <arg name="params">
        <param>
          <name>param_name</name>
          <value>param_value</value>
        </param>
      </arg>
    </command>

    Parameters:
    - webpage_url: String. URL of the webpage to interact with.
    - css_selector: String. CSS selector to find the target element.
    - action: String. Type of interaction to perform on the element. Must be one of: 
      {', '.join(str(action) for action in WebElementAction)}
    - params: XML-formatted string containing additional parameters for specific actions.

    Common actions and their parameters:
    1. click: No additional params required.
    2. type: Requires 'text' param. 
       Example: <param><name>text</name><value>Hello, World!</value></param>
    3. select: Requires 'option' param. 
       Example: <param><name>option</name><value>option1</value></param>
    4. check: Optional 'state' param (default: true). 
       Example: <param><name>state</name><value>false</value></param>
    5. submit: No additional params required.
    6. hover: No additional params required.
    7. double_click: No additional params required.

    Return Value:
    - String: Absolute path to the screenshot taken after the action is performed.
      The screenshot is saved in the current working directory with the filename format:
      'screenshot_<action>_<timestamp>.png'

    Examples:
    1. Typing in a search box:
      <command name="WebElementTrigger">
        <arg name="webpage_url">https://example.com</arg>
        <arg name="css_selector">#search-input</arg>
        <arg name="action">type</arg>
        <arg name="params">
          <param>
            <name>text</name>
            <value>Python tutorial</value>
          </param>
        </arg>
      </command>
      Returns: '/path/to/screenshot_type_20230615_120530.png'

    2. Selecting an option from a dropdown:
      <command name="WebElementTrigger">
        <arg name="webpage_url">https://example.com</arg>
        <arg name="css_selector">#country-select</arg>
        <arg name="action">select</arg>
        <arg name="params">
          <param>
            <name>option</name>
            <value>USA</value>
          </param>
        </arg>
      </command>
      Returns: '/path/to/screenshot_select_20230615_120545.png'

    3. Clicking a button:
      <command name="WebElementTrigger">
        <arg name="webpage_url">https://example.com</arg>
        <arg name="css_selector">.submit-button</arg>
        <arg name="action">click</arg>
      </command>
      Returns: '/path/to/screenshot_click_20230615_120600.png'
    '''

    async def perform_action(self, shared_session: SharedBrowserSession, **kwargs):
        css_selector = kwargs.get("css_selector")
        action_str = kwargs.get("action")
        params_str = kwargs.get("params", "")

        if not css_selector:
            raise ValueError("CSS selector is required.")

        try:
            action = WebElementAction.from_string(action_str)
        except ValueError as e:
            raise ValueError(f"Invalid action: {action_str}. {str(e)}")

        params = self._parse_params(params_str)

        element = shared_session.page.locator(css_selector)
        
        if action == WebElementAction.CLICK:
            await element.click()
        elif action == WebElementAction.TYPE:
            text = params.get("text")
            if not text:
                raise ValueError("'text' parameter is required for 'type' action.")
            await element.type(text)
        elif action == WebElementAction.SELECT:
            option = params.get("option")
            if not option:
                raise ValueError("'option' parameter is required for 'select' action.")
            await element.select_option(option)
        elif action == WebElementAction.CHECK:
            state = params.get("state", "true").lower() == "true"
            if state:
                await element.check()
            else:
                await element.uncheck()
        elif action == WebElementAction.SUBMIT:
            await element.submit()
        elif action == WebElementAction.HOVER:
            await element.hover()
        elif action == WebElementAction.DOUBLE_CLICK:
            await element.dblclick()
        else:
            raise ValueError(f"Unsupported action: {action}")

        # Take screenshot after action
        #timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        #screenshot_filename = f"screenshot_{action}_{timestamp}.png"
        #screenshot_path = os.path.join(os.getcwd(), screenshot_filename)
        #await shared_session.page.screenshot(path=screenshot_path, full_page=True)
        #absolute_screenshot_path = os.path.abspath(screenshot_path)
        #return absolute_screenshot_path
        return "The WebElementTrigger command is executed"

    def _parse_params(self, params_str):
        if not params_str:
            return {}
        
        try:
            # Wrap the params string in a root element to make it valid XML
            xml_string = f"<root>{params_str}</root>"
            root = ET.fromstring(xml_string)
            params = {}
            for param in root.findall('param'):
                name_elem = param.find('name')
                value_elem = param.find('value')
                if name_elem is not None and value_elem is not None:
                    params[name_elem.text] = value_elem.text
            return params
        except ET.ParseError:
            # If parsing fails, return an empty dict
            return {}