from fastapi import FastAPI
import uvicorn
from src.graphql.schema import schema
from strawberry.fastapi import GraphQLRouter

def graphql_server_mode(config, host, port):
    """
    Run the application in GraphQL server mode.

    :param config: Config object containing the loaded configuration.
    :param host: Server hostname.
    :param port: Server port.
    """
    print("Running in GraphQL server mode")
    app = FastAPI()
    graphql_router = GraphQLRouter(schema)
    app.include_router(graphql_router, prefix="/graphql")
    uvicorn.run(app, host=host, port=port)