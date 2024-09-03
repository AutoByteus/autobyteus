from typing import List, Any
from autobyteus.workflow.node import Node

class Workflow:
    def __init__(self):
        self.nodes: List[Node] = []

    def add_node(self, node: Node):
        self.nodes.append(node)

    async def execute(self, input_data: Any) -> Any:
        result = input_data
        for node in self.nodes:
            result = await node.execute(result)
        return result

    def get_result(self) -> Any:
        return self.nodes[-1].get_result() if self.nodes else None