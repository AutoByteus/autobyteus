import xml.etree.ElementTree as ET
import re
from xml.sax.saxutils import escape, unescape
from autobyteus.agent.tool_invocation import ToolInvocation

class XMLLLMResponseParser:
    def parse_response(self, response):
        print(f"Full response: {response}")
        
        start_tag = "<command"
        end_tag = "</command>"
        start_index = response.find(start_tag)
        end_index = response.find(end_tag)
        
        print(f"Start index: {start_index}, End index: {end_index}")
        
        if start_index != -1 and end_index != -1:
            xml_content = response[start_index : end_index + len(end_tag)]
            print(f"Extracted XML content: {xml_content}")
            
            # Preprocess the XML content
            processed_xml = self._preprocess_xml(xml_content)
            print(f"Processed XML content: {processed_xml}")
            
            try:
                root = ET.fromstring(processed_xml)
                print(f"Parsed XML root: {root}")
                
                if root.tag == "command":
                    name = root.attrib.get("name")
                    print(f"Command name: {name}")
                    
                    arguments = self._parse_arguments(root)
                    print(f"Parsed arguments: {arguments}")
                    
                    return ToolInvocation(name=name, arguments=arguments)
            except ET.ParseError as e:
                print(f"XML parsing error: {e}")
        
        print("No valid command found")
        return ToolInvocation()

    def _preprocess_xml(self, xml_content):
        def escape_content(match):
            full_tag = match.group(1)
            content = match.group(2)
            escaped_content = escape(content, entities={'"': "&quot;"})
            return f"{full_tag}{escaped_content}"

        # Escape content within tags, but not the tags themselves
        processed_content = re.sub(r'(<[^>]+>)(.*?)(?=</?)', escape_content, xml_content, flags=re.DOTALL)
        return processed_content

    def _parse_arguments(self, command_element):
        arguments = {}
        for arg in command_element.findall('arg'):
            arg_name = arg.attrib.get('name')
            if len(arg) > 0:  # If the arg has child elements
                arg_value = ET.tostring(arg, encoding='unicode', method='xml').split('>', 1)[1].rsplit('<', 1)[0].strip()
            else:
                arg_value = arg.text.strip() if arg.text else ''
            arguments[arg_name] = unescape(arg_value)
        return arguments