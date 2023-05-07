import json
import strawberry
from strawberry.scalars import JSON
from src.graphql.custom_json_encoder import CustomJSONEncoder
from src.workflow.automated_coding_workflow import AutomatedCodingWorkflow
from src.workflow.config.workflow_config import WORKFLOW_CONFIG

from src.graphql.json_scalar import JSONScalar

@strawberry.type
class Query:
    @strawberry.field
    def workflow_config(self) -> JSON:
        custom_encoder = CustomJSONEncoder()
        return custom_encoder.encode(WORKFLOW_CONFIG)

@strawberry.type
class Mutation:
    @strawberry.mutation
    def start_workflow(self) -> bool:
        workflow = AutomatedCodingWorkflow()
        workflow.start_workflow()
        return True

schema = strawberry.Schema(query=Query, mutation=Mutation)
