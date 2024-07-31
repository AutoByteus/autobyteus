# File: /home/ryan-ai/miniHDD/Learning/chatgpt/autobyteus/autobyteus/agent/xml_llm_response_parser.py

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
                    name = root.attrib.get("name")
                    arguments = self._parse_arguments(root)
                    return ToolInvocation(name=name, arguments=arguments)
            except ET.ParseError:
                pass
        
        return ToolInvocation()

    def _parse_arguments(self, command_element):
        arguments = {}
        for arg in command_element.findall('arg'):
            arg_name = arg.attrib.get('name')
            if len(arg) > 0:  # If the arg has child elements
                arg_value = ET.tostring(arg, encoding='unicode', method='xml').strip()
                # Remove the outer <arg> tags
                arg_value = arg_value.split('>', 1)[1].rsplit('<', 1)[0].strip()
            else:
                arg_value = arg.text.strip() if arg.text else ''
            arguments[arg_name] = arg_value
        return arguments