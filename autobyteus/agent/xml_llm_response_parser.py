import xml.etree.ElementTree as ET
from .parsed_response import ParsedResponse

class XMLLLMResponseParser:
    def parse_response(self, response):
        try:
            root = ET.fromstring(response)
            if root.tag == "command":
                tool_name = root.attrib["name"]
                tool_args = {arg.attrib["name"]: arg.text for arg in root.findall("arg")}
                return ParsedResponse(tool_name=tool_name, tool_args=tool_args)
            else:
                return ParsedResponse()
        except ET.ParseError:
            return ParsedResponse()