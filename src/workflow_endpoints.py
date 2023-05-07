from fastapi import APIRouter
from strawberry.fastapi import GraphQLRouter
from src.config.config import config
from src.workflow.automated_coding_workflow import AutomatedCodingWorkflow
from src.graphql.schema import schema

router = APIRouter()
workflow = AutomatedCodingWorkflow(config)

graphql_router = GraphQLRouter(schema)
router.include_router(graphql_router, prefix="/graphql")
