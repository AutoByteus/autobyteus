class ToolInvocation:
    def __init__(self, name=None, arguments=None):
        self.name = name
        self.arguments = arguments

    def is_valid(self):
        return self.name is not None and self.arguments is not None