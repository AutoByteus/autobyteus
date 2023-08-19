from fastapi import FastAPI
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from src.api.graphql.schema import schema
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

    origins = [
        "http://localhost:5173",
        # Add other origins if required
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    graphql_router = GraphQLRouter(schema)
    app.include_router(graphql_router, prefix="/graphql")

    uvicorn.run(app, host=host, port=port)
