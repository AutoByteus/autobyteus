import re
from .tool_invocation import ToolInvocation

class LLMResponseParser:
    def parse_response(self, response):
        tool_invocation_match = re.search(r"<<<(.+?)\((.+?)\)>>>", response, re.DOTALL)
        if tool_invocation_match:
            name = tool_invocation_match.group(1)
            arguments_str = tool_invocation_match.group(2)
            arguments = self._parse_arguments(arguments_str)
            return ToolInvocation(name=name, arguments=arguments)
        else:
            return ToolInvocation()

    def _parse_arguments(self, arguments_str):
        args_pattern = re.compile(r'(\w+)="([^"]*)"')
        matches = args_pattern.findall(arguments_str)
        arguments = {arg[0]: arg[1] for arg in matches}
        return arguments