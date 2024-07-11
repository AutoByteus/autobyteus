import xml.etree.ElementTree as ET

from autobyteus.agent.tool_invocation import ToolInvocation

class XMLLLMResponseParser:
    def parse_response(self, response):
        try:
            root = ET.fromstring(response)
            if root.tag == "command":
                name = root.attrib["name"]
                arguments = {arg.attrib["name"]: arg.text for arg in root.findall("arg")}
                return ToolInvocation(name=name, arguments=arguments)
            else:
                return ToolInvocation()
        except ET.ParseError:
            return ToolInvocation()