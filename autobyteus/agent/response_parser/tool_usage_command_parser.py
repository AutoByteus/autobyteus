
import xml.etree.ElementTree as ET
import re
from xml.sax.saxutils import escape, unescape
from urllib.parse import unquote
import xml.parsers.expat
from autobyteus.agent.tool_invocation import ToolInvocation
import logging

logger = logging.getLogger(__name__)

class ToolUsageCommandParser:
    def parse_response(self, response: str) -> ToolInvocation:
        logger.debug(f"Full response: {response}")

        start_tag = "<command"
        end_tag = "</command>"
        start_index = response.find(start_tag)
        end_index = response.find(end_tag)

        if start_index != -1 and end_index != -1:
            xml_content = response[start_index : end_index + len(end_tag)]
            logger.debug(f"Extracted XML content: {xml_content}")

            # Preprocess the XML content
            processed_xml = self._preprocess_xml(xml_content)
            logger.debug(f"Processed XML content: {processed_xml}")

            try:
                root = ET.fromstring(processed_xml)
                logger.debug(f"Parsed XML root: {root}")

                if root.tag == "command":
                    name = root.attrib.get("name")
                    logger.debug(f"Command name: {name}")

                    arguments = self._parse_arguments(root)
                    logger.debug(f"Parsed arguments: {arguments}")

                    return ToolInvocation(name=name, arguments=arguments)
            except (ET.ParseError, xml.parsers.expat.ExpatError) as e:
                logger.debug(f"XML parsing error: {e}")
                logger.debug("Attempting to fix malformed XML...")
                fixed_xml = self._fix_malformed_xml(processed_xml)
                try:
                    root = ET.fromstring(fixed_xml)
                    if root.tag == "command":
                        name = root.attrib.get("name")
                        logger.debug(f"Command name: {name}")

                        arguments = self._parse_arguments(root)
                        logger.debug(f"Parsed arguments: {arguments}")

                        return ToolInvocation(name=name, arguments=arguments)
                except (ET.ParseError, xml.parsers.expat.ExpatError) as e:
                    logger.debug(f"Failed to fix XML: {e}")

        logger.debug("No valid command found")
        return ToolInvocation()

    def _preprocess_xml(self, xml_content: str) -> str:
        def wrap_arg_in_cdata(match):
            full_tag = match.group(1)
            content = match.group(2)
            # Escape the content, but don't wrap in CDATA to allow for further processing
            escaped_content = escape(content)
            return f"{full_tag}{escaped_content}"

        # Process all <arg> elements
        processed_content = re.sub(
            r'(<arg name="[^"]*">)(.*?)(?=</arg>)',
            wrap_arg_in_cdata,
            xml_content,
            flags=re.DOTALL
        )
        return processed_content

    def _parse_arguments(self, command_element: ET.Element) -> dict:
        arguments = {}
        for arg in command_element.findall('arg'):
            arg_name = arg.attrib.get('name')
            if len(arg) > 0:  # If the arg has child elements
                arg_value = ET.tostring(arg, encoding='unicode', method='xml').split('>', 1)[1].rsplit('<', 1)[0].strip()
            else:
                arg_value = arg.text.strip() if arg.text else ''
            
            # Unescape the value for all arguments
            arg_value = unescape(arg_value)
            
            # Special handling for URL-like arguments
            if 'url' in arg_name.lower():
                arg_value = unquote(arg_value)  # Decode URL-encoded characters
            
            arguments[arg_name] = arg_value
        return arguments

    def _fix_malformed_xml(self, xml_content: str) -> str:
        # This is a simple fix attempt. You might need to expand this based on common issues.
        fixed_content = xml_content.replace('&', '&amp;')
        return fixed_content
