import json
import strawberry
from typing import Any
from autobyteus.api.graphql.json.custom_json_encoder import CustomJSONEncoder


@strawberry.scalar(name="JSON")
class JSONScalar:
    @staticmethod
    def serialize(value: Any) -> str:
        custom_encoder = CustomJSONEncoder()
        return custom_encoder.encode(value)

    @staticmethod
    def parse_value(value: str) -> Any:
        return json.loads(value)

    @staticmethod
    def parse_literal(ast: Any) -> Any:
        return json.loads(ast.value)
