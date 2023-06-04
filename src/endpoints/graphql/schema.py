import json
import strawberry
from strawberry.scalars import JSON
from src.endpoints.graphql.json.custom_json_encoder import CustomJSONEncoder
from src.automated_coding_workflow.automated_coding_workflow import AutomatedCodingWorkflow
from src.automated_coding_workflow.config import WORKFLOW_CONFIG


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
        workflow.start_workflow()
        return True


workflow = AutomatedCodingWorkflow()
schema = strawberry.Schema(query=Query, mutation=Mutation)
