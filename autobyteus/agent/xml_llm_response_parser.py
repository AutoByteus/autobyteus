import xml.etree.ElementTree as ET

from autobyteus.agent.tool_invocation import ToolInvocation

class XMLLLMResponseParser:
    def parse_response(self, response):
        start_tag = "<command"
        end_tag = "</command>"
        start_index = response.find(start_tag)
        end_index = response.find(end_tag)
        
        if start_index != -1 and end_index != -1:
            xml_content = response[start_index : end_index + len(end_tag)]
            try:
                root = ET.fromstring(xml_content)
                if root.tag == "command":
                    name = root.attrib["name"]
                    arguments = {arg.attrib["name"]: arg.text for arg in root.findall("arg")}
                    return ToolInvocation(name=name, arguments=arguments)
            except ET.ParseError:
                pass
        
        return ToolInvocation()