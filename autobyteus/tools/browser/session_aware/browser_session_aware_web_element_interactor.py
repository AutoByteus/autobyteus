from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool
from autobyteus.tools.browser.session_aware.web_element_action import WebElementAction

class BrowserSessionAwareWebElementInteractor(BrowserSessionAwareTool):
    def __init__(self):
        super().__init__()

    def tool_usage(self):
        return """BrowserSessionAwareWebElementInteractor: Interacts with web elements while maintaining browser session awareness.
Usage: <<<BrowserSessionAwareWebElementInteractor(css_selector='selector', action='action', params={'param': 'value'})>>>

Parameters:
- css_selector: String. CSS selector to find the target element.
- action: String. Type of interaction to perform on the element. Must be one of: 
  {', '.join(str(action) for action in WebElementAction)}
- params: Optional dict. Additional parameters for specific actions.

Common actions and their parameters:
1. click: No additional params required.
2. type: Requires 'text' param. Example: params={'text': 'Hello, World!'}
   Used for input fields, search boxes, etc.
3. select: Requires 'value' param. Example: params={'value': 'option1'}
   Used for dropdown menus.
4. check: Optional 'checked' param (default: True). Example: params={'checked': False}
   Used for checkboxes or radio buttons.
5. submit: No additional params required. Used for form submission.
6. hover: No additional params required.
7. double_click: No additional params required.

Examples:
1. Typing in a search box:
   <<<BrowserSessionAwareWebElementInteractor(css_selector='#search-input', action='type', params={'text': 'Python tutorial'})>>>

2. Selecting an option from a dropdown:
   <<<BrowserSessionAwareWebElementInteractor(css_selector='#country-select', action='select', params={'value': 'USA'})>>>

3. Clicking a button:
   <<<BrowserSessionAwareWebElementInteractor(css_selector='.submit-button', action='click')>>>
"""

    def tool_usage_xml(self):
        return f'''BrowserSessionAwareWebElementInteractor: Interacts with web elements.
<command name="BrowserSessionAwareWebElementInteractor">
  <arg name="css_selector">selector</arg>
  <arg name="action">action</arg>
  <arg name="params">
    <dict>
      <key>param</key>
      <value>value</value>
    </dict>
  </arg>
</command>

Parameters:
- css_selector: String. CSS selector to find the target element.
- action: String. Type of interaction to perform on the element. Must be one of: 
  {', '.join(str(action) for action in WebElementAction)}
- params: Optional dict. Additional parameters for specific actions.

Common actions and their parameters:
1. click: No additional params required.
2. type: Requires 'text' param. Example: params={{"text": "Hello, World!"}}
   Used for input fields, search boxes, etc.
3. select: Requires 'value' param. Example: params={{"value": "option1"}}
   Used for dropdown menus.
4. check: Optional 'checked' param (default: True). Example: params={{"checked": false}}
   Used for checkboxes or radio buttons.
5. submit: No additional params required. Used for form submission.
6. hover: No additional params required.
7. double_click: No additional params required.

Examples:
1. Typing in a search box:
   <command name="BrowserSessionAwareWebElementInteractor">
     <arg name="css_selector">#search-input</arg>
     <arg name="action">type</arg>
     <arg name="params">
       <dict>
         <key>text</key>
         <value>Python tutorial</value>
       </dict>
     </arg>
   </command>

2. Selecting an option from a dropdown:
   <command name="BrowserSessionAwareWebElementInteractor">
     <arg name="css_selector">#country-select</arg>
     <arg name="action">select</arg>
     <arg name="params">
       <dict>
         <key>value</key>
         <value>USA</value>
       </dict>
     </arg>
   </command>

3. Clicking a button:
   <command name="BrowserSessionAwareWebElementInteractor">
     <arg name="css_selector">.submit-button</arg>
     <arg name="action">click</arg>
   </command>
'''

    async def execute(self, **kwargs):
        css_selector = kwargs.get("css_selector")
        action_str = kwargs.get("action")
        params = kwargs.get("params", {})

        if not css_selector:
            raise ValueError("CSS selector is required.")

        try:
            action = WebElementAction.from_string(action_str)
        except ValueError as e:
            raise ValueError(f"Invalid action: {action_str}. {str(e)}")

        shared_browser_session = await self.get_or_create_shared_browser_session()

        element = shared_browser_session.page.locator(css_selector)
        
        if action == WebElementAction.CLICK:
            await element.click()
        elif action == WebElementAction.TYPE:
            text = params.get("text")
            if not text:
                raise ValueError("'text' parameter is required for 'type' action.")
            await element.type(text)
        elif action == WebElementAction.SELECT:
            value = params.get("value")
            if not value:
                raise ValueError("'value' parameter is required for 'select' action.")
            await element.select_option(value)
        elif action == WebElementAction.CHECK:
            checked = params.get("checked", True)
            if checked:
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