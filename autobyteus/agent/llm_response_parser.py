import re

class LLMResponse:
    def __init__(self, text, tool_name=None, tool_args=None):
        self.text = text
        self.tool_name = tool_name
        self.tool_args = tool_args

    def is_tool_invocation(self):
        return self.tool_name is not None and self.tool_args is not None


class LLMResponseParser:
    def parse_response(self, response: str) -> LLMResponse:
        tool_match = re.search(r"<<<(\w+)\((.*)\)>>>", response)
        
        if tool_match:
            tool_name = tool_match.group(1)
            tool_args_str = tool_match.group(2)
            tool_args = eval(f"dict({tool_args_str})")
            return LLMResponse(response, tool_name, tool_args)
        else:
            return LLMResponse(response)