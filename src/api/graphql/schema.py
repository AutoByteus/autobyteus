"""
Module: schema

This module combines all GraphQL queries and mutations to form the main GraphQL schema.
"""

import strawberry
from src.api.graphql.mutations import workspace_mutations

from src.api.graphql.queries import workspace_queries

@strawberry.type
class Query(workspace_queries):
    pass

@strawberry.type
class Mutation(workspace_mutations):
    pass

schema = strawberry.Schema(query=Query, mutation=Mutation)
