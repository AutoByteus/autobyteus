import re

class ParsedResponse:
    def __init__(self, tool_name=None, tool_args=None):
        self.tool_name = tool_name
        self.tool_args = tool_args

    def is_tool_invocation(self):
        return self.tool_name is not None and self.tool_args is not None


class LLMResponseParser:
    def parse_response(self, response):
        tool_invocation_match = re.search(r"<<<(.+?)\((.+?)\)>>>", response, re.DOTALL)
        if tool_invocation_match:
            tool_name = tool_invocation_match.group(1)
            tool_args_str = tool_invocation_match.group(2)
            tool_args = self._parse_tool_args(tool_args_str)
            return ParsedResponse(tool_name=tool_name, tool_args=tool_args)
        else:
            return ParsedResponse()

    def _parse_tool_args(self, tool_args_str):
        args_pattern = re.compile(r'(\w+)="([^"]*)"')
        matches = args_pattern.findall(tool_args_str)
        tool_args = {arg[0]: arg[1] for arg in matches}
        return tool_args