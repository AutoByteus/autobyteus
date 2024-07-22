from autobyteus.tools.browser.session_aware.browser_session_aware_tool import BrowserSessionAwareTool

class BrowserSessionAwareElementTrigger(BrowserSessionAwareTool):
    def __init__(self):
        super().__init__()

    def tool_usage(self):
        return "ElementTrigger: Triggers an event on a specified element. Usage: <<<ElementTrigger(element_locator='element_locator', event_type='event_type', event_args={'arg_name': 'arg_value'})>>>, where 'element_locator' is a string containing the locator strategy and value to find the target element, 'event_type' is a string specifying the type of event to trigger (e.g., 'click', 'type', 'select', 'check', 'submit', 'hover', 'double_click'), and 'event_args' is an optional dictionary containing event-specific arguments."

    def tool_usage_xml(self):
        return '''ElementTrigger: Triggers an event on a specified element. Usage:
<command name="ElementTrigger">
  <arg name="element_locator">element_locator</arg>
  <arg name="event_type">event_type</arg>
  <arg name="event_args">
    <dict>
      <key>arg_name</key>
      <value>arg_value</value>
    </dict>
  </arg>
</command>
where "element_locator" is a string containing the locator strategy and value to find the target element, "event_type" is a string specifying the type of event to trigger (e.g., "click", "type", "select", "check", "submit", "hover", "double_click"), and "event_args" is an optional dictionary containing event-specific arguments.
'''

    async def execute(self, **kwargs):
        element_locator = kwargs.get("element_locator")
        event_type = kwargs.get("event_type")
        event_args = kwargs.get("event_args", {})

        if not element_locator:
            raise ValueError("Element locator is required.")

        shared_session = self.get_shared_session()
        if not shared_session:
            self.emit("create_shared_session")
            shared_session = self.get_shared_session()

        element = await shared_session.page.locator(element_locator)

        if event_type == "click":
            await element.click()
        elif event_type == "type":
            text = event_args.get("text")
            if not text:
                raise ValueError("Text argument is required for typing event.")
            await element.type(text)
        elif event_type == "select":
            value = event_args.get("value")
            if not value:
                raise ValueError("Value argument is required for select event.")
            await element.select_option(value)
        elif event_type == "check":
            checked = event_args.get("checked", True)
            if checked:
                await element.check()
            else:
                await element.uncheck()
        elif event_type == "submit":
            await element.submit()
        elif event_type == "hover":
            await element.hover()
        elif event_type == "double_click":
            await element.dblclick()
        else:
            raise ValueError(f"Unsupported event type: {event_type}")